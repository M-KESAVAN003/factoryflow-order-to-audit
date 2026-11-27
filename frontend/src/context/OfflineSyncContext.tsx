import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useAuth } from "./AuthContext";
import { listOfflineOrders } from "../lib/offlineDb";
import {
  applyServiceWorkerUpdate,
  registerFactoryFlowServiceWorker,
} from "../lib/pwa";
import {
  createLocalOfflineOrder,
  loadOfflineMasterCache,
  markConflictResolved,
  syncMasterDataFromServer,
  syncPendingOfflineOrders,
  syncSingleOfflineOrder,
} from "../lib/syncEngine";
import {
  CachedCustomerMin,
  CachedProductMin,
  OfflineOrderRecord,
  PwaNetworkState,
} from "../types/offline";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

interface OfflineSyncContextValue {
  isOnline: boolean;
  networkState: PwaNetworkState;
  syncing: boolean;
  lastMasterSyncAt: string | null;
  lastOrderSyncMessage: string | null;
  customers: CachedCustomerMin[];
  products: CachedProductMin[];
  offlineOrders: OfflineOrderRecord[];
  pendingCount: number;
  failedCount: number;
  needsReviewCount: number;
  syncedCount: number;
  updateAvailable: boolean;
  installPromptAvailable: boolean;
  promptInstall: () => Promise<boolean>;
  applyAppUpdate: () => void;
  refreshOfflineState: () => Promise<void>;
  syncMasterData: () => Promise<void>;
  createOfflineOrder: (params: {
    customerId: string;
    productId: string;
    quantity: string;
    notes?: string | null;
  }) => Promise<OfflineOrderRecord>;
  syncNow: (includeFailed?: boolean) => Promise<void>;
  retryOrder: (localOrderId: string) => Promise<OfflineOrderRecord>;
  resolveOrderConflict: (localOrderId: string) => Promise<void>;
}

const OfflineSyncContext = createContext<OfflineSyncContextValue | undefined>(undefined);

export function OfflineSyncProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  const [syncing, setSyncing] = useState(false);
  const [customers, setCustomers] = useState<CachedCustomerMin[]>([]);
  const [products, setProducts] = useState<CachedProductMin[]>([]);
  const [offlineOrders, setOfflineOrders] = useState<OfflineOrderRecord[]>([]);
  const [lastMasterSyncAt, setLastMasterSyncAt] = useState<string | null>(null);
  const [lastOrderSyncMessage, setLastOrderSyncMessage] = useState<string | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);

  const syncLockRef = useRef(false);

  const refreshOfflineState = useCallback(async () => {
    const [cache, orders] = await Promise.all([
      loadOfflineMasterCache(),
      user ? listOfflineOrders(user.id) : Promise.resolve([]),
    ]);
    setCustomers(cache.customers);
    setProducts(cache.products);
    setLastMasterSyncAt(cache.lastMasterSyncAt);
    setOfflineOrders(orders);
  }, [user]);

  const syncNow = useCallback(
    async (includeFailed = false) => {
      if (!user || !navigator.onLine || syncLockRef.current) return;
      syncLockRef.current = true;
      setSyncing(true);
      try {
        const results = await syncPendingOfflineOrders(user.id, includeFailed);
        await refreshOfflineState();
        if (results.length > 0) {
          const okCount = results.filter(
            (r) => r.syncStatus === "SYNCED" || r.syncStatus === "NEEDS_REVIEW"
          ).length;
          const failCount = results.filter(
            (r) => r.syncStatus === "SYNC_FAILED" || r.syncStatus === "CONFLICT"
          ).length;
          setLastOrderSyncMessage(
            failCount > 0
              ? `Synced ${okCount} order(s), ${failCount} failed.`
              : `Synchronized ${okCount} offline order(s).`
          );
        }
      } finally {
        syncLockRef.current = false;
        setSyncing(false);
      }
    },
    [user, refreshOfflineState]
  );

  const syncMasterData = useCallback(async () => {
    if (!navigator.onLine) {
      throw new Error("Cannot refresh customer and product pricing while offline.");
    }
    const res = await syncMasterDataFromServer();
    setCustomers(res.customers);
    setProducts(res.products);
    setLastMasterSyncAt(res.syncedAt);
  }, []);

  const createOfflineOrder = useCallback(
    async (params: {
      customerId: string;
      productId: string;
      quantity: string;
      notes?: string | null;
    }) => {
      if (!user) throw new Error("Must be authenticated to save offline orders.");
      const customer = customers.find((c) => c.id === params.customerId);
      const product = products.find((p) => p.id === params.productId);
      if (!customer || !product) {
        throw new Error("Select a synchronized customer and active cached product.");
      }
      const created = await createLocalOfflineOrder({
        salesmanId: user.id,
        customer,
        product,
        quantity: params.quantity,
        notes: params.notes,
      });
      await refreshOfflineState();
      return created;
    },
    [user, customers, products, refreshOfflineState]
  );

  const retryOrder = useCallback(
    async (localOrderId: string) => {
      if (!navigator.onLine) {
        throw new Error("Internet connection required to retry order sync.");
      }
      setSyncing(true);
      try {
        const res = await syncSingleOfflineOrder(localOrderId);
        await refreshOfflineState();
        return res;
      } finally {
        setSyncing(false);
      }
    },
    [refreshOfflineState]
  );

  const resolveOrderConflict = useCallback(
    async (localOrderId: string) => {
      await markConflictResolved(localOrderId);
      await refreshOfflineState();
    },
    [refreshOfflineState]
  );

  useEffect(() => {
    void refreshOfflineState();
  }, [refreshOfflineState]);

  useEffect(() => {
    void registerFactoryFlowServiceWorker({
      onUpdateAvailable: () => setUpdateAvailable(true),
      onSyncMessage: () => {
        void syncNow(false);
      },
    });
  }, [syncNow]);

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true);
      void syncNow(false);
    };
    const onOffline = () => {
      setIsOnline(false);
    };
    const onInstallPrompt = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e as BeforeInstallPromptEvent);
    };

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("beforeinstallprompt", onInstallPrompt);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("beforeinstallprompt", onInstallPrompt);
    };
  }, [syncNow]);

  // Automatic sync on app launch / user load when pending orders already exist
  useEffect(() => {
    if (user && isOnline) {
      const hasPending = offlineOrders.some((o) => o.syncStatus === "PENDING_SYNC");
      if (hasPending && !syncLockRef.current) {
        void syncNow(false);
      }
    }
  }, [user, isOnline, offlineOrders, syncNow]);

  const pendingCount = useMemo(
    () => offlineOrders.filter((o) => o.syncStatus === "PENDING_SYNC" || o.syncStatus === "SYNCING").length,
    [offlineOrders]
  );
  const failedCount = useMemo(
    () => offlineOrders.filter((o) => o.syncStatus === "SYNC_FAILED" || o.syncStatus === "CONFLICT").length,
    [offlineOrders]
  );
  const needsReviewCount = useMemo(
    () => offlineOrders.filter((o) => o.syncStatus === "NEEDS_REVIEW").length,
    [offlineOrders]
  );
  const syncedCount = useMemo(
    () => offlineOrders.filter((o) => o.syncStatus === "SYNCED").length,
    [offlineOrders]
  );

  const networkState: PwaNetworkState = useMemo(() => {
    if (syncing) return "SYNCING";
    if (!isOnline) return "OFFLINE";
    if (failedCount > 0) return "SYNC_FAILED";
    if (pendingCount > 0) return "PENDING";
    return "ONLINE";
  }, [syncing, isOnline, failedCount, pendingCount]);

  const promptInstall = useCallback(async () => {
    if (!installEvent) return false;
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    setInstallEvent(null);
    return choice.outcome === "accepted";
  }, [installEvent]);

  return (
    <OfflineSyncContext.Provider
      value={{
        isOnline,
        networkState,
        syncing,
        lastMasterSyncAt,
        lastOrderSyncMessage,
        customers,
        products,
        offlineOrders,
        pendingCount,
        failedCount,
        needsReviewCount,
        syncedCount,
        updateAvailable,
        installPromptAvailable: Boolean(installEvent),
        promptInstall,
        applyAppUpdate: applyServiceWorkerUpdate,
        refreshOfflineState,
        syncMasterData,
        createOfflineOrder,
        syncNow,
        retryOrder,
        resolveOrderConflict,
      }}
    >
      {children}
    </OfflineSyncContext.Provider>
  );
}

export function useOfflineSync(): OfflineSyncContextValue {
  const ctx = useContext(OfflineSyncContext);
  if (!ctx) {
    throw new Error("useOfflineSync must be used inside OfflineSyncProvider");
  }
  return ctx;
}
