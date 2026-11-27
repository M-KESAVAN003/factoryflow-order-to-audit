from decimal import Decimal

from sqlalchemy import func, select

from app.core.permissions import Role
from app.models.product import Product
from app.models.stock_item import StockItem, StockItemType
from app.models.unit import Unit, UnitConversion
from app.services.master_seed_service import seed_benchmark_master_data
from tests.conftest import auth_headers_for


def test_benchmark_seed_and_idempotency(db_session):
    first_counts = seed_benchmark_master_data(db_session)
    assert first_counts["units"] == 7
    assert first_counts["stock_items"] == 5
    assert first_counts["products"] == 1
    assert first_counts["conversions"] == 3
    assert first_counts["suppliers"] == 1
    assert first_counts["customers"] == 2

    # Running seed a second time must insert zero duplicate records
    second_counts = seed_benchmark_master_data(db_session)
    assert all(v == 0 for v in second_counts.values())

    assert db_session.scalar(select(func.count(Unit.id))) == 7
    assert db_session.scalar(select(func.count(Product.id))) == 1
    assert db_session.scalar(select(func.count(UnitConversion.id))) == 3


def test_product_crud_and_stock_item_relationship(client, db_session):
    seed_benchmark_master_data(db_session)
    headers = auth_headers_for(client, Role.ADMIN)

    # Benchmark product Murukku 200 g exists with linked FINISHED_GOOD StockItem
    list_resp = client.get("/api/v1/products?search=MUR-200", headers=headers)
    assert list_resp.status_code == 200
    murukku = list_resp.json()["items"][0]
    assert murukku["sku"] == "MUR-200"
    assert Decimal(murukku["selling_price"]) == Decimal("50.00")
    assert Decimal(murukku["gst_rate"]) == Decimal("5.00")
    assert murukku["stock_item_type"] == "FINISHED_GOOD"
    assert murukku["packets_per_carton"] == 20

    # Referenced by carton-to-packet conversion -> DELETE deactivates safely
    del_ref = client.delete(f"/api/v1/products/{murukku['id']}", headers=headers)
    assert del_ref.status_code == 200
    assert del_ref.json()["status"] == "deactivated"

    # Create a standalone product and verify auto-created FINISHED_GOOD StockItem + update + delete
    packet_unit = next(
        u for u in client.get("/api/v1/units", headers=headers).json()["items"] if u["symbol"] == "packet"
    )
    create_resp = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": "Banana Chips 150 g",
            "sku": "CHIP-150",
            "category": "Snacks",
            "pack_size": "150 g",
            "selling_price": "45.00",
            "gst_rate": "5.00",
            "hsn_code": "20089999",
            "unit_id": packet_unit["id"],
            "packets_per_carton": 24,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["stock_item_type"] == "FINISHED_GOOD"

    # Duplicate SKU must be rejected with 409
    dup_resp = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": "Duplicate Chips",
            "sku": "CHIP-150",
            "category": "Snacks",
            "pack_size": "150 g",
            "selling_price": "45.00",
            "gst_rate": "5.00",
            "hsn_code": "20089999",
            "unit_id": packet_unit["id"],
        },
    )
    assert dup_resp.status_code == 409

    # Update & delete unreferenced product
    put_resp = client.put(
        f"/api/v1/products/{created['id']}",
        headers=headers,
        json={"selling_price": "48.00"},
    )
    assert put_resp.status_code == 200
    assert Decimal(put_resp.json()["selling_price"]) == Decimal("48.00")

    del_resp = client.delete(f"/api/v1/products/{created['id']}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"


def test_raw_material_packaging_and_stock_item_validation(client, db_session):
    seed_benchmark_master_data(db_session)
    headers = auth_headers_for(client, Role.ADMIN)

    rm_resp = client.get("/api/v1/raw-materials", headers=headers)
    assert rm_resp.status_code == 200
    rm_names = {item["name"]: Decimal(item["purchase_rate"]) for item in rm_resp.json()["items"]}
    assert rm_names == {
        "Flour": Decimal("42.0000"),
        "Cooking oil": Decimal("140.0000"),
        "Salt and spice mix": Decimal("200.0000"),
    }

    pkg_resp = client.get("/api/v1/packaging-materials", headers=headers)
    assert pkg_resp.status_code == 200
    pkg_names = {item["name"]: Decimal(item["purchase_rate"]) for item in pkg_resp.json()["items"]}
    assert pkg_names == {
        "200 g pouch": Decimal("2.5000"),
        "Carton": Decimal("15.0000"),
    }

    # Reject linking a RAW_MATERIAL stock item to a Product
    units = client.get("/api/v1/units", headers=headers).json()["items"]
    kg_id = next(u["id"] for u in units if u["symbol"] == "kg")
    pkt_id = next(u["id"] for u in units if u["symbol"] == "packet")
    flour_id = rm_resp.json()["items"][0]["id"]

    bad_prod = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": "Bad Link Product",
            "sku": "BAD-001",
            "category": "Snacks",
            "pack_size": "200 g",
            "selling_price": "20.00",
            "gst_rate": "5.00",
            "hsn_code": "19059090",
            "unit_id": pkt_id,
            "stock_item_id": flour_id,
        },
    )
    assert bad_prod.status_code == 422

    # Reject cross-dimension base_unit vs purchase_unit on StockItem
    litre_id = next(u["id"] for u in units if u["symbol"] == "litre")
    bad_stock = client.post(
        "/api/v1/stock-items",
        headers=headers,
        json={
            "name": "Invalid Dimension Item",
            "sku": "INV-DIM-1",
            "item_type": "RAW_MATERIAL",
            "base_unit_id": kg_id,
            "purchase_unit_id": litre_id,
            "purchase_rate": "10.00",
        },
    )
    assert bad_stock.status_code == 422


def test_supplier_and_customer_crud(client, db_session):
    seed_benchmark_master_data(db_session)
    headers = auth_headers_for(client, Role.ADMIN)

    sup_list = client.get("/api/v1/suppliers?search=Benchmark", headers=headers)
    assert sup_list.status_code == 200
    assert sup_list.json()["total"] == 1
    assert sup_list.json()["items"][0]["name"] == "Benchmark Supplier"

    new_sup = client.post(
        "/api/v1/suppliers",
        headers=headers,
        json={
            "name": "Delta Oils Pvt Ltd",
            "gstin": "33DELTA1234F1Z9",
            "phone": "+91-44-2222-3333",
            "email": "orders@deltaoils.example.com",
            "address": "88 Industrial Area",
            "state": "Tamil Nadu",
            "state_code": "33",
        },
    )
    assert new_sup.status_code == 201
    sup_id = new_sup.json()["id"]

    upd_sup = client.put(
        f"/api/v1/suppliers/{sup_id}",
        headers=headers,
        json={"phone": "+91-44-2222-9999"},
    )
    assert upd_sup.status_code == 200
    assert upd_sup.json()["phone"] == "+91-44-2222-9999"

    cust_list = client.get("/api/v1/customers", headers=headers)
    assert cust_list.status_code == 200
    cust_names = {c["name"]: c["state"] for c in cust_list.json()["items"]}
    assert cust_names == {"Retailer A": "Tamil Nadu", "Distributor B": "Karnataka"}

    new_cust = client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "name": "Retailer C",
            "customer_type": "Retailer",
            "gstin": "33RETLC0003C1Z5",
            "phone": "+91-44-5555-6666",
            "address": "99 Bazaar Street",
            "city": "Madurai",
            "state": "Tamil Nadu",
            "state_code": "33",
            "credit_limit": "75000.00",
        },
    )
    assert new_cust.status_code == 201
    assert Decimal(new_cust.json()["credit_limit"]) == Decimal("75000.00")


def test_unit_conversions_and_invalid_conversion_rejection(client, db_session):
    seed_benchmark_master_data(db_session)
    headers = auth_headers_for(client, Role.ADMIN)

    units = {
        u["symbol"]: u["id"]
        for u in client.get("/api/v1/units", headers=headers).json()["items"]
    }
    murukku_id = client.get("/api/v1/products?search=MUR-200", headers=headers).json()["items"][0]["id"]

    # 2.5 kg -> 2500 g
    mass_conv = client.post(
        "/api/v1/unit-conversions/convert",
        headers=headers,
        json={"quantity": "2.5", "from_unit_id": units["kg"], "to_unit_id": units["g"]},
    )
    assert mass_conv.status_code == 200
    assert Decimal(mass_conv.json()["converted_quantity"]) == Decimal("2500")

    # 1.5 litre -> 1500 ml
    vol_conv = client.post(
        "/api/v1/unit-conversions/convert",
        headers=headers,
        json={"quantity": "1.5", "from_unit_id": units["litre"], "to_unit_id": units["ml"]},
    )
    assert vol_conv.status_code == 200
    assert Decimal(vol_conv.json()["converted_quantity"]) == Decimal("1500")

    # 3 cartons -> 60 packets for Murukku 200 g
    pack_conv = client.post(
        "/api/v1/unit-conversions/convert",
        headers=headers,
        json={
            "quantity": "3",
            "from_unit_id": units["carton"],
            "to_unit_id": units["packet"],
            "product_id": murukku_id,
        },
    )
    assert pack_conv.status_code == 200
    assert Decimal(pack_conv.json()["converted_quantity"]) == Decimal("60")

    # Reject invalid cross-dimension conversion (kg -> litre)
    invalid_rule = client.post(
        "/api/v1/unit-conversions",
        headers=headers,
        json={
            "from_unit_id": units["kg"],
            "to_unit_id": units["litre"],
            "conversion_factor": "1",
        },
    )
    assert invalid_rule.status_code == 422

    # Reject non-positive conversion factor
    zero_rule = client.post(
        "/api/v1/unit-conversions",
        headers=headers,
        json={
            "from_unit_id": units["kg"],
            "to_unit_id": units["g"],
            "conversion_factor": "0",
        },
    )
    assert zero_rule.status_code == 422
