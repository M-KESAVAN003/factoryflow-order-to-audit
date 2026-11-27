from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.unit import Unit, UnitConversion
from app.models.user import User
from app.schemas.master_data import (
    UnitConversionCreate,
    UnitConversionOut,
    UnitConvertResponse,
    UnitCreate,
)
from app.services.audit_service import record_audit_event


def to_conversion_out(conv: UnitConversion) -> UnitConversionOut:
    return UnitConversionOut(
        id=conv.id,
        from_unit_id=conv.from_unit_id,
        from_unit_symbol=conv.from_unit.symbol,
        from_unit_dimension=conv.from_unit.dimension,
        to_unit_id=conv.to_unit_id,
        to_unit_symbol=conv.to_unit.symbol,
        to_unit_dimension=conv.to_unit.dimension,
        product_id=conv.product_id,
        product_name=conv.product.name if conv.product else None,
        conversion_factor=conv.conversion_factor,
        is_active=conv.is_active,
        created_at=conv.created_at,
    )


def list_units(
    db: Session,
    *,
    search: str | None = None,
    dimension: str | None = None,
    is_active: bool | None = None,
    sort_by: str = "symbol",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Unit], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Unit.name.ilike(term), Unit.symbol.ilike(term)))
    if dimension:
        filters.append(Unit.dimension == dimension)
    if is_active is not None:
        filters.append(Unit.is_active.is_(is_active))

    total = int(db.scalar(select(func.count(Unit.id)).where(*filters)) or 0)
    col = getattr(Unit, sort_by, Unit.symbol)
    order_fn = desc if sort_dir == "desc" else asc
    stmt = (
        select(Unit)
        .where(*filters)
        .order_by(order_fn(col))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def create_unit(
    db: Session,
    payload: UnitCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> Unit:
    symbol = payload.symbol.strip().lower()
    name = payload.name.strip()
    existing = db.scalar(
        select(Unit).where(
            or_(func.lower(Unit.symbol) == symbol, func.lower(Unit.name) == name.lower())
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A unit with this name or symbol already exists.",
        )

    unit = Unit(
        name=name,
        symbol=symbol,
        dimension=payload.dimension,
        is_base=payload.is_base,
        is_active=payload.is_active,
    )
    db.add(unit)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="master.unit_created",
        resource_type="unit",
        resource_id=unit.id,
        details=f"Created unit {unit.symbol} ({unit.dimension.value})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(unit)
    return unit


def list_unit_conversions(
    db: Session,
    *,
    product_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[UnitConversion], int]:
    filters = []
    if product_id:
        filters.append(UnitConversion.product_id == product_id)

    total = int(db.scalar(select(func.count(UnitConversion.id)).where(*filters)) or 0)
    stmt = (
        select(UnitConversion)
        .where(*filters)
        .order_by(UnitConversion.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def create_unit_conversion(
    db: Session,
    payload: UnitConversionCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> UnitConversion:
    if payload.from_unit_id == payload.to_unit_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source unit and target unit must be different.",
        )

    from_unit = db.get(Unit, payload.from_unit_id)
    to_unit = db.get(Unit, payload.to_unit_id)
    if not from_unit or not to_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both referenced units were not found.",
        )

    if from_unit.dimension != to_unit.dimension:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid dimensional conversion: '{from_unit.symbol}' ({from_unit.dimension.value}) "
                f"cannot be converted to '{to_unit.symbol}' ({to_unit.dimension.value})."
            ),
        )

    if payload.product_id is not None:
        product = db.get(Product, payload.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referenced product for conversion was not found.",
            )

    dup_stmt = select(UnitConversion).where(
        UnitConversion.from_unit_id == payload.from_unit_id,
        UnitConversion.to_unit_id == payload.to_unit_id,
    )
    if payload.product_id is None:
        dup_stmt = dup_stmt.where(UnitConversion.product_id.is_(None))
    else:
        dup_stmt = dup_stmt.where(UnitConversion.product_id == payload.product_id)

    if db.scalar(dup_stmt):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This unit conversion rule already exists.",
        )

    conv = UnitConversion(
        from_unit_id=payload.from_unit_id,
        to_unit_id=payload.to_unit_id,
        product_id=payload.product_id,
        conversion_factor=payload.conversion_factor,
        is_active=payload.is_active,
    )
    db.add(conv)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="master.unit_conversion_created",
        resource_type="unit_conversion",
        resource_id=conv.id,
        details=f"1 {from_unit.symbol} = {payload.conversion_factor} {to_unit.symbol}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(conv)
    return conv


def convert_quantity(
    db: Session,
    *,
    quantity: Decimal,
    from_unit_id: str,
    to_unit_id: str,
    product_id: str | None = None,
) -> UnitConvertResponse:
    """Convert a quantity between compatible units using exact Decimal arithmetic."""
    from_unit = db.get(Unit, from_unit_id)
    to_unit = db.get(Unit, to_unit_id)
    if not from_unit or not to_unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")

    if from_unit.dimension != to_unit.dimension:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot convert {from_unit.dimension.value} to {to_unit.dimension.value}.",
        )

    if from_unit_id == to_unit_id:
        return UnitConvertResponse(
            input_quantity=quantity,
            converted_quantity=quantity,
            from_unit_symbol=from_unit.symbol,
            to_unit_symbol=to_unit.symbol,
            factor_applied=Decimal("1"),
        )

    # Prefer product-scoped conversion when product_id is supplied, then fall back to global rule.
    def _find_rule(src: str, dst: str) -> UnitConversion | None:
        if product_id:
            scoped = db.scalar(
                select(UnitConversion).where(
                    UnitConversion.from_unit_id == src,
                    UnitConversion.to_unit_id == dst,
                    UnitConversion.product_id == product_id,
                    UnitConversion.is_active.is_(True),
                )
            )
            if scoped:
                return scoped
        return db.scalar(
            select(UnitConversion).where(
                UnitConversion.from_unit_id == src,
                UnitConversion.to_unit_id == dst,
                UnitConversion.product_id.is_(None),
                UnitConversion.is_active.is_(True),
            )
        )

    direct = _find_rule(from_unit_id, to_unit_id)
    if direct:
        factor = Decimal(direct.conversion_factor)
        converted = (quantity * factor).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        return UnitConvertResponse(
            input_quantity=quantity,
            converted_quantity=converted,
            from_unit_symbol=from_unit.symbol,
            to_unit_symbol=to_unit.symbol,
            factor_applied=factor,
        )

    inverse = _find_rule(to_unit_id, from_unit_id)
    if inverse:
        factor = (Decimal("1") / Decimal(inverse.conversion_factor)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        converted = (quantity / Decimal(inverse.conversion_factor)).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        return UnitConvertResponse(
            input_quantity=quantity,
            converted_quantity=converted,
            from_unit_symbol=from_unit.symbol,
            to_unit_symbol=to_unit.symbol,
            factor_applied=factor,
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"No conversion rule configured between '{from_unit.symbol}' and '{to_unit.symbol}'.",
    )
