from decimal import Decimal
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import Role
from app.models.customer import Customer, CustomerType
from app.models.product import Product
from app.models.stock_item import StockItem, StockItemType
from app.models.supplier import Supplier
from app.models.unit import Unit, UnitConversion, UnitDimension
from app.models.user import User
from app.schemas.master_data import (
    CustomerCreate,
    ProductCreate,
    StockItemCreate,
    SupplierCreate,
    UnitConversionCreate,
    UnitCreate,
)
from app.services.partner_service import create_customer, create_supplier
from app.services.product_service import create_product
from app.services.stock_item_service import create_stock_item
from app.services.unit_service import create_unit, create_unit_conversion


def seed_benchmark_master_data(db: Session) -> Dict[str, int]:
    """Idempotently seed Phase 2 benchmark master records without opening stock balances."""
    counts = {
        "units": 0,
        "stock_items": 0,
        "products": 0,
        "conversions": 0,
        "suppliers": 0,
        "customers": 0,
    }

    # 1. Units
    unit_specs = [
        ("Kilogram", "kg", UnitDimension.MASS, True),
        ("Gram", "g", UnitDimension.MASS, False),
        ("Litre", "litre", UnitDimension.VOLUME, True),
        ("Millilitre", "ml", UnitDimension.VOLUME, False),
        ("Piece", "piece", UnitDimension.COUNT, True),
        ("Packet", "packet", UnitDimension.COUNT, False),
        ("Carton", "carton", UnitDimension.COUNT, False),
    ]
    units_by_symbol: Dict[str, Unit] = {}
    for name, symbol, dimension, is_base in unit_specs:
        existing = db.scalar(select(Unit).where(func.lower(Unit.symbol) == symbol))
        if existing is None:
            existing = create_unit(
                db,
                UnitCreate(name=name, symbol=symbol, dimension=dimension, is_base=is_base),
            )
            counts["units"] += 1
        units_by_symbol[symbol] = existing

    # 2. Raw Materials & Packaging Materials (shared StockItem master)
    stock_specs = [
        ("Flour", "RM-FLOUR", StockItemType.RAW_MATERIAL, "kg", "kg", Decimal("42.0000"), Decimal("25.0000"), "Primary rice & gram flour blend"),
        ("Cooking oil", "RM-OIL", StockItemType.RAW_MATERIAL, "litre", "litre", Decimal("140.0000"), Decimal("10.0000"), "Refined groundnut/sunflower frying oil"),
        ("Salt and spice mix", "RM-SPICE", StockItemType.RAW_MATERIAL, "kg", "kg", Decimal("200.0000"), Decimal("2.0000"), "Seasoning blend for Murukku"),
        ("200 g pouch", "PKG-POUCH-200", StockItemType.PACKAGING, "piece", "piece", Decimal("2.5000"), Decimal("100.0000"), "Food-grade laminated 200 g retail pouch"),
        ("Carton", "PKG-CARTON", StockItemType.PACKAGING, "piece", "piece", Decimal("15.0000"), Decimal("10.0000"), "Corrugated master carton (capacity 20 packets)"),
    ]
    stock_by_sku: Dict[str, StockItem] = {}
    for name, sku, item_type, base_sym, purch_sym, rate, reorder, desc in stock_specs:
        existing_item = db.scalar(select(StockItem).where(func.upper(StockItem.sku) == sku))
        if existing_item is None:
            existing_item = create_stock_item(
                db,
                StockItemCreate(
                    name=name,
                    sku=sku,
                    item_type=item_type,
                    base_unit_id=units_by_symbol[base_sym].id,
                    purchase_unit_id=units_by_symbol[purch_sym].id,
                    purchase_rate=rate,
                    reorder_level=reorder,
                    description=desc,
                ),
            )
            counts["stock_items"] += 1
        stock_by_sku[sku] = existing_item

    # 3. Benchmark Product: Murukku 200 g (linked 1:1 to FINISHED_GOOD StockItem)
    murukku = db.scalar(select(Product).where(func.upper(Product.sku) == "MUR-200"))
    if murukku is None:
        murukku = create_product(
            db,
            ProductCreate(
                name="Murukku 200 g",
                sku="MUR-200",
                category="Savory Snacks",
                description="Traditional crispy South Indian Murukku packed in 200 g retail pouches.",
                pack_size="200 g",
                selling_price=Decimal("50.00"),
                gst_rate=Decimal("5.00"),
                hsn_code="19059090",
                unit_id=units_by_symbol["packet"].id,
                pouch_stock_item_id=stock_by_sku["PKG-POUCH-200"].id,
                carton_stock_item_id=stock_by_sku["PKG-CARTON"].id,
                packets_per_carton=20,
            ),
        )
        counts["products"] += 1

    # 4. Unit Conversions
    conversion_specs = [
        ("kg", "g", None, Decimal("1000.000000")),
        ("litre", "ml", None, Decimal("1000.000000")),
        ("carton", "packet", murukku.id, Decimal("20.000000")),
    ]
    for from_sym, to_sym, prod_id, factor in conversion_specs:
        from_u = units_by_symbol[from_sym]
        to_u = units_by_symbol[to_sym]
        stmt = select(UnitConversion).where(
            UnitConversion.from_unit_id == from_u.id,
            UnitConversion.to_unit_id == to_u.id,
        )
        if prod_id is None:
            stmt = stmt.where(UnitConversion.product_id.is_(None))
        else:
            stmt = stmt.where(UnitConversion.product_id == prod_id)

        if db.scalar(stmt) is None:
            create_unit_conversion(
                db,
                UnitConversionCreate(
                    from_unit_id=from_u.id,
                    to_unit_id=to_u.id,
                    product_id=prod_id,
                    conversion_factor=factor,
                ),
            )
            counts["conversions"] += 1

    # 5. Benchmark Supplier (clearly marked dummy data)
    supplier_gstin = "33BENCH0001A1Z5"
    if db.scalar(select(Supplier).where(Supplier.gstin == supplier_gstin)) is None:
        create_supplier(
            db,
            SupplierCreate(
                name="Benchmark Supplier",
                gstin=supplier_gstin,
                phone="+91-44-0000-0100",
                email="benchmark.supplier@example.com",
                address="Plot 10, Industrial Estate (Dummy Seed Record)",
                state="Tamil Nadu",
                state_code="33",
            ),
        )
        counts["suppliers"] += 1

    # 6. Benchmark Customers (assigned to order_manager user if present)
    sales_user = db.scalar(select(User).where(User.role == Role.ORDER_MANAGER).limit(1))
    sales_user_id = sales_user.id if sales_user else None

    customer_specs = [
        (
            "Retailer A",
            CustomerType.RETAILER,
            "33RETLA0001A1Z5",
            "+91-44-0000-0201",
            "12 Market Road (Dummy Seed Record)",
            "Chennai",
            "Tamil Nadu",
            "33",
            Decimal("50000.00"),
        ),
        (
            "Distributor B",
            CustomerType.DISTRIBUTOR,
            "29DISTB0002B1Z5",
            "+91-80-0000-0302",
            "45 Logistics Park (Dummy Seed Record)",
            "Bengaluru",
            "Karnataka",
            "29",
            Decimal("250000.00"),
        ),
    ]
    for name, ctype, gstin, phone, addr, city, state, scode, limit in customer_specs:
        if db.scalar(select(Customer).where(Customer.gstin == gstin)) is None:
            create_customer(
                db,
                CustomerCreate(
                    name=name,
                    customer_type=ctype,
                    gstin=gstin,
                    phone=phone,
                    address=addr,
                    city=city,
                    state=state,
                    state_code=scode,
                    assigned_salesman_id=sales_user_id,
                    credit_limit=limit,
                ),
            )
            counts["customers"] += 1

    return counts
