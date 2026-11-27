from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    boms,
    costing,
    dashboard,
    dispatches,
    health,
    inventory,
    invoices,
    partners,
    payments,
    production,
    products,
    purchases,
    receivables,
    reports,
    sales_orders,
    stock_items,
    units,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
api_router.include_router(products.router)
api_router.include_router(stock_items.router)
api_router.include_router(partners.router)
api_router.include_router(units.router)
api_router.include_router(purchases.router)
api_router.include_router(inventory.router)
api_router.include_router(boms.router)
api_router.include_router(production.router)
api_router.include_router(sales_orders.router)
api_router.include_router(invoices.router)
api_router.include_router(dispatches.router)
api_router.include_router(costing.router)
api_router.include_router(payments.router)
api_router.include_router(receivables.router)
api_router.include_router(reports.router)
