import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { OfflineSyncProvider } from "./context/OfflineSyncContext";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AddProductionExpensePage } from "./pages/AddProductionExpensePage";
import { AdminOrdersDashboardPage } from "./pages/AdminOrdersDashboardPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { AuditReportPage } from "./pages/AuditReportPage";
import { AuditorDashboardPage } from "./pages/AuditorDashboardPage";
import { BomDetailPage } from "./pages/BomDetailPage";
import { BomFormPage } from "./pages/BomFormPage";
import { BomsPage } from "./pages/BomsPage";
import { BomVersionsPage } from "./pages/BomVersionsPage";
import { CustomerFormPage } from "./pages/CustomerFormPage";
import { CustomerLedgerPage } from "./pages/CustomerLedgerPage";
import { CustomerSalesPage } from "./pages/CustomerSalesPage";
import { CustomerStatementPage } from "./pages/CustomerStatementPage";
import { CustomersPage } from "./pages/CustomersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DispatchesPage } from "./pages/DispatchesPage";
import { InventoryCategoryPage } from "./pages/InventoryCategoryPage";
import { InventoryItemDetailPage } from "./pages/InventoryItemDetailPage";
import { InventoryOverviewPage } from "./pages/InventoryOverviewPage";
import { InvoiceDetailPage } from "./pages/InvoiceDetailPage";
import { InvoicePaymentDetailPage } from "./pages/InvoicePaymentDetailPage";
import { InvoicePdfPreviewPage } from "./pages/InvoicePdfPreviewPage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { LoginPage } from "./pages/LoginPage";
import { LowStockAlertsPage } from "./pages/LowStockAlertsPage";
import { MasterDataDashboardPage } from "./pages/MasterDataDashboardPage";
import { MobileOrderEntryPage } from "./pages/MobileOrderEntryPage";
import { MyOrdersPage } from "./pages/MyOrdersPage";
import { OfflineOrderDetailPage } from "./pages/OfflineOrderDetailPage";
import { OfflineOrderEntryPage } from "./pages/OfflineOrderEntryPage";
import { OfflineOrdersQueuePage } from "./pages/OfflineOrdersQueuePage";
import { OrderApprovalPage } from "./pages/OrderApprovalPage";
import { OwnerDashboardPage } from "./pages/OwnerDashboardPage";
import { PaymentDashboardPage } from "./pages/PaymentDashboardPage";
import { PaymentHistoryPage } from "./pages/PaymentHistoryPage";
import { PermissionsPage } from "./pages/PermissionsPage";
import { ProductFormPage } from "./pages/ProductFormPage";
import { ProductionCostingDashboardPage } from "./pages/ProductionCostingDashboardPage";
import { ProductionDashboardPage } from "./pages/ProductionDashboardPage";
import { ProductionExpensesPage } from "./pages/ProductionExpensesPage";
import { ProductionMaterialIssuePage } from "./pages/ProductionMaterialIssuePage";
import { ProductionOutputPage } from "./pages/ProductionOutputPage";
import { ProductionRunDetailPage } from "./pages/ProductionRunDetailPage";
import { ProductionRunFormPage } from "./pages/ProductionRunFormPage";
import { ProductionRunsPage } from "./pages/ProductionRunsPage";
import { ProductionVariancePage } from "./pages/ProductionVariancePage";
import { ProductionWastagePage } from "./pages/ProductionWastagePage";
import { ProductsPage } from "./pages/ProductsPage";
import { PurchaseDetailPage } from "./pages/PurchaseDetailPage";
import { PurchaseFormPage } from "./pages/PurchaseFormPage";
import { PurchasesPage } from "./pages/PurchasesPage";
import { ReceivablesAgeingPage } from "./pages/ReceivablesAgeingPage";
import { ReceivablesPage } from "./pages/ReceivablesPage";
import { RecordPaymentPage } from "./pages/RecordPaymentPage";
import { ReportExportCenterPage } from "./pages/ReportExportCenterPage";
import { RunCostDetailPage } from "./pages/RunCostDetailPage";
import { SalesOrderDetailPage } from "./pages/SalesOrderDetailPage";
import { SalesmanDashboardPage } from "./pages/SalesmanDashboardPage";
import { StockAdjustmentsPage } from "./pages/StockAdjustmentsPage";
import { StockAvailabilityPreviewPage } from "./pages/StockAvailabilityPreviewPage";
import { StockItemFormPage } from "./pages/StockItemFormPage";
import { StockItemListPage } from "./pages/StockItemListPage";
import { StockLedgerPage } from "./pages/StockLedgerPage";
import { SupplierFormPage } from "./pages/SupplierFormPage";
import { SuppliersPage } from "./pages/SuppliersPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import { UnitConversionsPage } from "./pages/UnitConversionsPage";
import { UnitsPage } from "./pages/UnitsPage";
import { UsersPage } from "./pages/UsersPage";

function ShellRoute({
  permission,
  children,
}: {
  permission?: string;
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute requiredPermission={permission}>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}

export function AppRoutes() {
  return (
    <OfflineSyncProvider>
      <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ShellRoute permission="dashboard:view">
            <DashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ShellRoute permission="users:read">
            <UsersPage />
          </ShellRoute>
        }
      />
      <Route
        path="/audit-logs"
        element={
          <ShellRoute permission="audit:read">
            <AuditLogsPage />
          </ShellRoute>
        }
      />
      <Route
        path="/permissions"
        element={
          <ShellRoute permission="roles:read">
            <PermissionsPage />
          </ShellRoute>
        }
      />

      {/* Phase 2 Master Data */}
      <Route
        path="/master-data"
        element={
          <ShellRoute permission="dashboard:view">
            <MasterDataDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/products"
        element={
          <ShellRoute permission="products:read">
            <ProductsPage />
          </ShellRoute>
        }
      />
      <Route
        path="/products/new"
        element={
          <ShellRoute permission="products:manage">
            <ProductFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/products/:id/edit"
        element={
          <ShellRoute permission="products:manage">
            <ProductFormPage />
          </ShellRoute>
        }
      />

      <Route
        path="/raw-materials"
        element={
          <ShellRoute permission="stock_items:read">
            <StockItemListPage
              itemType="RAW_MATERIAL"
              title="Raw Materials"
              subtitle="Ingredient StockItem records (type: RAW_MATERIAL) with base/purchase units and rates."
              basePath="/raw-materials"
            />
          </ShellRoute>
        }
      />
      <Route
        path="/raw-materials/new"
        element={
          <ShellRoute permission="stock_items:manage">
            <StockItemFormPage
              itemType="RAW_MATERIAL"
              title="Raw Material"
              basePath="/raw-materials"
            />
          </ShellRoute>
        }
      />
      <Route
        path="/raw-materials/:id/edit"
        element={
          <ShellRoute permission="stock_items:manage">
            <StockItemFormPage
              itemType="RAW_MATERIAL"
              title="Raw Material"
              basePath="/raw-materials"
            />
          </ShellRoute>
        }
      />

      <Route
        path="/packaging-materials"
        element={
          <ShellRoute permission="stock_items:read">
            <StockItemListPage
              itemType="PACKAGING"
              title="Packaging Materials"
              subtitle="Pouches and cartons stored as StockItem records (type: PACKAGING)."
              basePath="/packaging-materials"
            />
          </ShellRoute>
        }
      />
      <Route
        path="/packaging-materials/new"
        element={
          <ShellRoute permission="stock_items:manage">
            <StockItemFormPage
              itemType="PACKAGING"
              title="Packaging Material"
              basePath="/packaging-materials"
            />
          </ShellRoute>
        }
      />
      <Route
        path="/packaging-materials/:id/edit"
        element={
          <ShellRoute permission="stock_items:manage">
            <StockItemFormPage
              itemType="PACKAGING"
              title="Packaging Material"
              basePath="/packaging-materials"
            />
          </ShellRoute>
        }
      />

      <Route
        path="/suppliers"
        element={
          <ShellRoute permission="suppliers:read">
            <SuppliersPage />
          </ShellRoute>
        }
      />
      <Route
        path="/suppliers/new"
        element={
          <ShellRoute permission="suppliers:manage">
            <SupplierFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/suppliers/:id/edit"
        element={
          <ShellRoute permission="suppliers:manage">
            <SupplierFormPage />
          </ShellRoute>
        }
      />

      <Route
        path="/customers"
        element={
          <ShellRoute permission="customers:read">
            <CustomersPage />
          </ShellRoute>
        }
      />
      <Route
        path="/customers/new"
        element={
          <ShellRoute permission="customers:manage">
            <CustomerFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/customers/:id/edit"
        element={
          <ShellRoute permission="customers:manage">
            <CustomerFormPage />
          </ShellRoute>
        }
      />

      <Route
        path="/units"
        element={
          <ShellRoute permission="units:read">
            <UnitsPage />
          </ShellRoute>
        }
      />
      <Route
        path="/unit-conversions"
        element={
          <ShellRoute permission="units:read">
            <UnitConversionsPage />
          </ShellRoute>
        }
      />

      {/* Phase 3 Inventory & Purchases */}
      <Route
        path="/inventory"
        element={
          <ShellRoute permission="inventory:read">
            <InventoryOverviewPage />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/raw-materials"
        element={
          <ShellRoute permission="inventory:read">
            <InventoryCategoryPage
              category="RAW_MATERIAL"
              title="Raw Material Inventory"
              subtitle="Available quantities, weighted-average rates, and stock valuation for raw materials."
            />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/packaging"
        element={
          <ShellRoute permission="inventory:read">
            <InventoryCategoryPage
              category="PACKAGING"
              title="Packaging Inventory"
              subtitle="Available quantities and valuation for pouches and cartons."
            />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/finished-goods"
        element={
          <ShellRoute permission="inventory:read">
            <InventoryCategoryPage
              category="FINISHED_GOOD"
              title="Finished Goods Inventory"
              subtitle="Available finished-good packet balances and valuation."
            />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/items/:id"
        element={
          <ShellRoute permission="inventory:read">
            <InventoryItemDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/ledger"
        element={
          <ShellRoute permission="inventory:read">
            <StockLedgerPage />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/adjustments"
        element={
          <ShellRoute permission="inventory:read">
            <StockAdjustmentsPage />
          </ShellRoute>
        }
      />
      <Route
        path="/inventory/alerts"
        element={
          <ShellRoute permission="inventory:read">
            <LowStockAlertsPage />
          </ShellRoute>
        }
      />

      <Route
        path="/purchases"
        element={
          <ShellRoute permission="purchases:read">
            <PurchasesPage />
          </ShellRoute>
        }
      />
      <Route
        path="/purchases/new"
        element={
          <ShellRoute permission="purchases:manage">
            <PurchaseFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/purchases/:id"
        element={
          <ShellRoute permission="purchases:read">
            <PurchaseDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/purchases/:id/edit"
        element={
          <ShellRoute permission="purchases:manage">
            <PurchaseFormPage />
          </ShellRoute>
        }
      />

      {/* Phase 4 BOM & Production */}
      <Route
        path="/boms"
        element={
          <ShellRoute permission="bom:read">
            <BomsPage />
          </ShellRoute>
        }
      />
      <Route
        path="/boms/new"
        element={
          <ShellRoute permission="bom:manage">
            <BomFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/boms/:id"
        element={
          <ShellRoute permission="bom:read">
            <BomDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/boms/:id/edit"
        element={
          <ShellRoute permission="bom:manage">
            <BomFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/boms/:id/versions"
        element={
          <ShellRoute permission="bom:read">
            <BomVersionsPage />
          </ShellRoute>
        }
      />

      <Route
        path="/production"
        element={
          <ShellRoute permission="production_runs:read">
            <ProductionDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/runs"
        element={
          <ShellRoute permission="production_runs:read">
            <ProductionRunsPage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/runs/new"
        element={
          <ShellRoute permission="production_runs:manage">
            <ProductionRunFormPage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/runs/:id"
        element={
          <ShellRoute permission="production_runs:read">
            <ProductionRunDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/runs/:id/materials"
        element={
          <ShellRoute permission="production_runs:manage">
            <ProductionMaterialIssuePage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/runs/:id/output"
        element={
          <ShellRoute permission="production_runs:manage">
            <ProductionOutputPage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/runs/:id/wastage"
        element={
          <ShellRoute permission="production_runs:manage">
            <ProductionWastagePage />
          </ShellRoute>
        }
      />
      <Route
        path="/production/variance"
        element={
          <ShellRoute permission="production_runs:read">
            <ProductionVariancePage />
          </ShellRoute>
        }
      />

      {/* Phase 5 Sales Orders, GST Invoices & Dispatches */}
      <Route
        path="/sales/dashboard"
        element={
          <ShellRoute permission="sales_orders:read">
            <SalesmanDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/mobile-order"
        element={
          <ShellRoute permission="sales_orders:create">
            <MobileOrderEntryPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/offline-order"
        element={
          <ShellRoute permission="sales_orders:create">
            <OfflineOrderEntryPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/pending-sync"
        element={
          <ShellRoute permission="sales_orders:create">
            <OfflineOrdersQueuePage mode="pending" />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/failed-orders"
        element={
          <ShellRoute permission="sales_orders:create">
            <OfflineOrdersQueuePage mode="failed" />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/sync-history"
        element={
          <ShellRoute permission="sales_orders:create">
            <OfflineOrdersQueuePage mode="history" />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/offline-orders/:localOrderId"
        element={
          <ShellRoute permission="sales_orders:create">
            <OfflineOrderDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/my-orders"
        element={
          <ShellRoute permission="sales_orders:read">
            <MyOrdersPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/customers"
        element={
          <ShellRoute permission="sales_orders:read">
            <CustomerSalesPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/admin"
        element={
          <ShellRoute permission="sales_orders:approve">
            <AdminOrdersDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/orders/:id"
        element={
          <ShellRoute permission="sales_orders:read">
            <SalesOrderDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/orders/:id/approve"
        element={
          <ShellRoute permission="sales_orders:approve">
            <OrderApprovalPage />
          </ShellRoute>
        }
      />
      <Route
        path="/sales/orders/:id/stock-check"
        element={
          <ShellRoute permission="sales_orders:read">
            <StockAvailabilityPreviewPage />
          </ShellRoute>
        }
      />
      <Route
        path="/invoices"
        element={
          <ShellRoute permission="invoices:read">
            <InvoicesPage />
          </ShellRoute>
        }
      />
      <Route
        path="/invoices/:id"
        element={
          <ShellRoute permission="invoices:read">
            <InvoiceDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/invoices/:id/pdf"
        element={
          <ShellRoute permission="invoices:read">
            <InvoicePdfPreviewPage />
          </ShellRoute>
        }
      />
      <Route
        path="/dispatches"
        element={
          <ShellRoute permission="dispatches:read">
            <DispatchesPage />
          </ShellRoute>
        }
      />

      {/* Phase 6 Production Costing, Expenses, Payments & Receivables */}
      <Route
        path="/costing"
        element={
          <ShellRoute permission="costing:read">
            <ProductionCostingDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/costing/runs/:runId"
        element={
          <ShellRoute permission="costing:read">
            <RunCostDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/costing/expenses"
        element={
          <ShellRoute permission="costing:read">
            <ProductionExpensesPage />
          </ShellRoute>
        }
      />
      <Route
        path="/costing/runs/:runId/expenses/new"
        element={
          <ShellRoute permission="expenses:manage">
            <AddProductionExpensePage />
          </ShellRoute>
        }
      />
      <Route
        path="/payments"
        element={
          <ShellRoute permission="payments:read">
            <PaymentDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/payments/new"
        element={
          <ShellRoute permission="payments:manage">
            <RecordPaymentPage />
          </ShellRoute>
        }
      />
      <Route
        path="/payments/history"
        element={
          <ShellRoute permission="payments:read">
            <PaymentHistoryPage />
          </ShellRoute>
        }
      />
      <Route
        path="/invoices/:id/payments"
        element={
          <ShellRoute permission="invoices:read">
            <InvoicePaymentDetailPage />
          </ShellRoute>
        }
      />
      <Route
        path="/receivables"
        element={
          <ShellRoute permission="receivables:read">
            <ReceivablesPage />
          </ShellRoute>
        }
      />
      <Route
        path="/receivables/ageing"
        element={
          <ShellRoute permission="receivables:read">
            <ReceivablesAgeingPage />
          </ShellRoute>
        }
      />
      <Route
        path="/customers/:customerId/ledger"
        element={
          <ShellRoute permission="receivables:read">
            <CustomerLedgerPage />
          </ShellRoute>
        }
      />
      <Route
        path="/customers/:customerId/statement"
        element={
          <ShellRoute permission="receivables:read">
            <CustomerStatementPage />
          </ShellRoute>
        }
      />

      {/* Phase 7 Owner Dashboard, Auditor Portal & Audit Reports */}
      <Route
        path="/owner"
        element={
          <ShellRoute permission="owner_dashboard:view">
            <OwnerDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/auditor"
        element={
          <ShellRoute permission="reports:view">
            <AuditorDashboardPage />
          </ShellRoute>
        }
      />
      <Route
        path="/reports/exports"
        element={
          <ShellRoute permission="reports:export">
            <ReportExportCenterPage />
          </ShellRoute>
        }
      />
      <Route path="/reports/sales" element={<ShellRoute permission="reports:view"><AuditReportPage mode="sales" /></ShellRoute>} />
      <Route path="/reports/sales/customers" element={<ShellRoute permission="reports:view"><AuditReportPage mode="sales_customers" /></ShellRoute>} />
      <Route path="/reports/sales/products" element={<ShellRoute permission="reports:view"><AuditReportPage mode="sales_products" /></ShellRoute>} />
      <Route path="/reports/gst" element={<ShellRoute permission="reports:view"><AuditReportPage mode="gst_outward" /></ShellRoute>} />
      <Route path="/reports/gst/hsn" element={<ShellRoute permission="reports:view"><AuditReportPage mode="gst_hsn" /></ShellRoute>} />
      <Route path="/reports/purchases" element={<ShellRoute permission="reports:view"><AuditReportPage mode="purchases" /></ShellRoute>} />
      <Route path="/reports/stock/raw-materials" element={<ShellRoute permission="reports:view"><AuditReportPage mode="stock_raw" /></ShellRoute>} />
      <Route path="/reports/stock/packaging" element={<ShellRoute permission="reports:view"><AuditReportPage mode="stock_packaging" /></ShellRoute>} />
      <Route path="/reports/stock/finished-goods" element={<ShellRoute permission="reports:view"><AuditReportPage mode="stock_finished" /></ShellRoute>} />
      <Route path="/reports/stock/ledger" element={<ShellRoute permission="reports:view"><AuditReportPage mode="stock_ledger" /></ShellRoute>} />
      <Route path="/reports/production" element={<ShellRoute permission="reports:view"><AuditReportPage mode="production" /></ShellRoute>} />
      <Route path="/reports/production/variance" element={<ShellRoute permission="reports:view"><AuditReportPage mode="production_variance" /></ShellRoute>} />
      <Route path="/reports/production/costing" element={<ShellRoute permission="reports:view"><AuditReportPage mode="production_costing" /></ShellRoute>} />
      <Route path="/reports/payments" element={<ShellRoute permission="reports:view"><AuditReportPage mode="payments" /></ShellRoute>} />
      <Route path="/reports/receivables" element={<ShellRoute permission="reports:view"><AuditReportPage mode="receivables" /></ShellRoute>} />
      <Route path="/reports/receivables/ageing" element={<ShellRoute permission="reports:view"><AuditReportPage mode="receivables_ageing" /></ShellRoute>} />

      <Route
        path="/unauthorized"
        element={
          <ShellRoute>
            <UnauthorizedPage />
          </ShellRoute>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </OfflineSyncProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
