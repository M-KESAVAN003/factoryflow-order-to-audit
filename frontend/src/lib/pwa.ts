export interface PwaRegistrationHandlers {
  onUpdateAvailable?: (registration: ServiceWorkerRegistration) => void;
  onSyncMessage?: () => void;
}

let activeWaitingWorker: ServiceWorker | null = null;

export function supportsServiceWorker(): boolean {
  return typeof navigator !== "undefined" && "serviceWorker" in navigator;
}

export function supportsBackgroundSync(): boolean {
  return (
    typeof window !== "undefined" &&
    "ServiceWorkerRegistration" in window &&
    "sync" in (window.ServiceWorkerRegistration?.prototype ?? {})
  );
}

export async function registerFactoryFlowServiceWorker(
  handlers?: PwaRegistrationHandlers
): Promise<ServiceWorkerRegistration | null> {
  if (!supportsServiceWorker()) {
    return null;
  }
  try {
    const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    if (reg.waiting) {
      activeWaitingWorker = reg.waiting;
      handlers?.onUpdateAvailable?.(reg);
    }
    reg.addEventListener("updatefound", () => {
      const installing = reg.installing;
      if (!installing) return;
      installing.addEventListener("statechange", () => {
        if (installing.state === "installed" && navigator.serviceWorker.controller) {
          activeWaitingWorker = installing;
          handlers?.onUpdateAvailable?.(reg);
        }
      });
    });

    navigator.serviceWorker.addEventListener("message", (event) => {
      if (event.data && event.data.type === "SYNC_PENDING_ORDERS") {
        handlers?.onSyncMessage?.();
      }
    });
    return reg;
  } catch {
    return null;
  }
}

export function applyServiceWorkerUpdate(): void {
  if (activeWaitingWorker) {
    activeWaitingWorker.postMessage({ type: "SKIP_WAITING" });
  }
  if (typeof window !== "undefined") {
    window.location.reload();
  }
}

export async function requestBackgroundOrderSync(): Promise<boolean> {
  if (!supportsServiceWorker()) return false;
  try {
    const reg = await navigator.serviceWorker.ready;
    const syncReg = reg as ServiceWorkerRegistration & {
      sync?: { register: (tag: string) => Promise<void> };
    };
    if (syncReg.sync && typeof syncReg.sync.register === "function") {
      await syncReg.sync.register("factoryflow-order-sync");
      return true;
    }
  } catch {
    // Graceful fallback to foreground synchronization
  }
  return false;
}
