from decimal import Decimal
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.stock_item import StockItem, StockItemType
from app.models.unit import Unit, UnitConversion
from app.models.user import User
from app.schemas.master_data import ProductCreate, ProductOut, ProductUpdate
from app.services.audit_service import record_audit_event


def to_product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        name=product.name,
        sku=product.sku,
        category=product.category,
        description=product.description,
        pack_size=product.pack_size,
        selling_price=product.selling_price,
        gst_rate=product.gst_rate,
        hsn_code=product.hsn_code,
        unit_id=product.unit_id,
        unit_symbol=product.unit.symbol,
        stock_item_id=product.stock_item_id,
        stock_item_sku=product.stock_item.sku,
        stock_item_type=product.stock_item.item_type,
        pouch_stock_item_id=product.pouch_stock_item_id,
        pouch_stock_item_name=product.pouch_stock_item.name if product.pouch_stock_item else None,
        carton_stock_item_id=product.carton_stock_item_id,
        carton_stock_item_name=product.carton_stock_item.name if product.carton_stock_item else None,
        packets_per_carton=product.packets_per_carton,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def list_products(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    only_active: bool = False,
    sort_by: str = "name",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Product], int]:
    filters = []
    if only_active:
        filters.append(Product.is_active.is_(True))
    elif is_active is not None:
        filters.append(Product.is_active.is_(is_active))

    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.hsn_code.ilike(term),
            )
        )
    if category:
        filters.append(func.lower(Product.category) == category.strip().lower())

    total = int(db.scalar(select(func.count(Product.id)).where(*filters)) or 0)
    col = getattr(Product, sort_by, Product.name)
    order_fn = desc if sort_dir == "desc" else asc
    stmt = (
        select(Product)
        .where(*filters)
        .order_by(order_fn(col))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def get_product_or_404(db: Session, product_id: str) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def _validate_packaging_link(db: Session, item_id: str | None, label: str) -> None:
    if item_id is None:
        return
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} stock item not found.")
    if item.item_type != StockItemType.PACKAGING:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} must reference a PACKAGING StockItem.",
        )


def create_product(
    db: Session,
    payload: ProductCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> Product:
    sku_norm = payload.sku.strip().upper()
    if db.scalar(select(Product).where(func.upper(Product.sku) == sku_norm)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product SKU '{sku_norm}' already exists.",
        )

    unit = db.get(Unit, payload.unit_id)
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced unit not found.")

    _validate_packaging_link(db, payload.pouch_stock_item_id, "Pouch")
    _validate_packaging_link(db, payload.carton_stock_item_id, "Carton")

    if payload.stock_item_id:
        stock_item = db.get(StockItem, payload.stock_item_id)
        if not stock_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced stock item not found.")
        if stock_item.item_type != StockItemType.FINISHED_GOOD:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Product must reference a StockItem of type FINISHED_GOOD.",
            )
        if db.scalar(select(Product).where(Product.stock_item_id == stock_item.id)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This FINISHED_GOOD stock item is already linked to another product.",
            )
    else:
        if db.scalar(select(StockItem).where(func.upper(StockItem.sku) == sku_norm)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stock item SKU '{sku_norm}' already exists.",
            )
        stock_item = StockItem(
            name=payload.name.strip(),
            sku=sku_norm,
            item_type=StockItemType.FINISHED_GOOD,
            base_unit_id=payload.unit_id,
            purchase_unit_id=payload.unit_id,
            purchase_rate=Decimal("0.0000"),
            reorder_level=Decimal("0.0000"),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.is_active,
        )
        db.add(stock_item)
        db.flush()

    product = Product(
        name=payload.name.strip(),
        sku=sku_norm,
        category=payload.category.strip(),
        description=payload.description.strip() if payload.description else None,
        pack_size=payload.pack_size.strip(),
        selling_price=payload.selling_price,
        gst_rate=payload.gst_rate,
        hsn_code=payload.hsn_code.strip(),
        unit_id=payload.unit_id,
        stock_item_id=stock_item.id,
        pouch_stock_item_id=payload.pouch_stock_item_id,
        carton_stock_item_id=payload.carton_stock_item_id,
        packets_per_carton=payload.packets_per_carton,
        is_active=payload.is_active,
    )
    db.add(product)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="master.product_created",
        resource_type="product",
        resource_id=product.id,
        details=f"Created product {product.sku} ({product.name}) linked to StockItem {stock_item.id}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session,
    product_id: str,
    payload: ProductUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Product:
    product = get_product_or_404(db, product_id)

    if payload.sku is not None:
        sku_norm = payload.sku.strip().upper()
        conflict = db.scalar(
            select(Product).where(func.upper(Product.sku) == sku_norm, Product.id != product.id)
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product SKU '{sku_norm}' already exists.",
            )
        product.sku = sku_norm
        product.stock_item.sku = sku_norm

    if payload.unit_id is not None:
        if not db.get(Unit, payload.unit_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")
        product.unit_id = payload.unit_id
        product.stock_item.base_unit_id = payload.unit_id
        product.stock_item.purchase_unit_id = payload.unit_id

    if payload.pouch_stock_item_id is not None:
        _validate_packaging_link(db, payload.pouch_stock_item_id, "Pouch")
        product.pouch_stock_item_id = payload.pouch_stock_item_id
    if payload.carton_stock_item_id is not None:
        _validate_packaging_link(db, payload.carton_stock_item_id, "Carton")
        product.carton_stock_item_id = payload.carton_stock_item_id

    if payload.name is not None:
        product.name = payload.name.strip()
        product.stock_item.name = product.name
    if payload.category is not None:
        product.category = payload.category.strip()
    if payload.description is not None:
        product.description = payload.description.strip() or None
    if payload.pack_size is not None:
        product.pack_size = payload.pack_size.strip()
    if payload.selling_price is not None:
        product.selling_price = payload.selling_price
    if payload.gst_rate is not None:
        product.gst_rate = payload.gst_rate
    if payload.hsn_code is not None:
        product.hsn_code = payload.hsn_code.strip()
    if payload.packets_per_carton is not None:
        product.packets_per_carton = payload.packets_per_carton
    if payload.is_active is not None:
        product.is_active = payload.is_active
        product.stock_item.is_active = payload.is_active

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="master.product_updated",
        resource_type="product",
        resource_id=product.id,
        details=f"Updated product {product.sku}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(product)
    return product


def deactivate_or_delete_product(
    db: Session,
    product_id: str,
    *,
    actor: User,
    ip_address: str | None = None,
) -> dict[str, str]:
    """Deactivate referenced products or delete unreferenced ones while preserving referential integrity."""
    product = get_product_or_404(db, product_id)
    has_conversions = db.scalar(
        select(func.count(UnitConversion.id)).where(UnitConversion.product_id == product.id)
    )
    if has_conversions:
        product.is_active = False
        product.stock_item.is_active = False
        record_audit_event(
            db,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_role=actor.role.value,
            action="master.product_deactivated",
            resource_type="product",
            resource_id=product.id,
            details=f"Deactivated referenced product {product.sku}",
            ip_address=ip_address,
            commit=False,
        )
        db.commit()
        return {"status": "deactivated", "message": "Product is referenced by conversion rules and was deactivated."}

    stock_item = product.stock_item
    sku = product.sku
    db.delete(product)
    db.flush()
    db.delete(stock_item)
    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="master.product_deleted",
        resource_type="product",
        resource_id=product_id,
        details=f"Deleted unreferenced product {sku}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    return {"status": "deleted", "message": f"Product {sku} deleted."}
