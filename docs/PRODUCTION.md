# FactoryFlow — Production & BOM Operator Guide

This guide explains how plant supervisors and administrators use the **BOM & Production Management** module (Phase 4).

## 1. Managing Bills of Materials (BOM)
1. Navigate to **Production & BOM → BOMs** (`/boms`).
2. Click **Create BOM** (`/boms/new`) to define a product formulation:
   - Select the **Finished Product** (e.g., *Murukku 200 g*).
   - Enter **Batch Size** (`1`) and **Expected Output** (`200` packets).
   - Add each **Raw Material** (`Flour 40 kg`, `Cooking oil 10 L`, `Salt and spice mix 1.2 kg`) and **Packaging Material** (`200 g pouch 200 pcs`, `Carton 10 pcs`).
   - Check **Activate immediately** to make this the active BOM version, or save as **Draft** for later editing.
3. Click **History** on any BOM to inspect all historical versions (`/boms/:id/versions`). Activating a new version automatically marks prior versions inactive without affecting existing production runs.

## 2. Executing a Production Run
1. Navigate to **Production & BOM → Production Runs** (`/production/runs`) and click **Create Production Run** (`/production/runs/new`).
2. Select the product, BOM version, batch number, production date, and planned batches.
   - The planner automatically computes material requirements and highlights any insufficient stock before creation.
3. Open the created run (`/production/runs/:id`) and follow the floor workflow:
   - **Mark Planned** (optional review step) → **Start Production** (`IN_PROGRESS`).
   - **Material Issue** (`/production/runs/:id/materials`): Enter actual good material/packaging consumed and any damaged pouches/packaging.
   - **Record Output** (`/production/runs/:id/output`): Enter **Actual Good Packets**, **Damaged Packets**, and **Cartons Used**. If good packets exceed carton capacity (`cartons_used × packets_per_carton`), an unpacked-packets warning is displayed.
   - **Wastage** (`/production/runs/:id/wastage`): Log scrap, damaged pouches, or process loss reasons.
   - **Complete Run** → **Post Production**: Atomically deducts consumed raw materials & packaging (`PRODUCTION_ISSUE`) and adds good packets (`PRODUCTION_OUTPUT`) to the append-only Stock Ledger.

## 3. Monitoring Variance & Alerts
- Open **Production Hub** (`/production`) for live summary metrics, daily output vs planned charts, product-wise yield, variance alerts, and raw material stock levels.
- Open **Variance Report** (`/production/variance`) to inspect exact consumption and yield variances color-coded against the 3% tolerance (`GREEN`, `ORANGE` boundary, `RED` alert).
