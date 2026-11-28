import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterEach } from "vitest";

configure({ asyncUtilTimeout: 5000 });

function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key)! : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(String(key), String(value));
    },
  };
}

function ensureWebStorage(name: "localStorage" | "sessionStorage"): void {
  const g = globalThis as Record<string, unknown>;
  const existing = g[name] as Partial<Storage> | undefined;
  if (
    existing &&
    typeof existing.getItem === "function" &&
    typeof existing.setItem === "function" &&
    typeof existing.clear === "function"
  ) {
    return;
  }

  const winStorage =
    typeof window !== "undefined"
      ? (window[name] as Partial<Storage> | undefined)
      : undefined;
  const resolved: Storage =
    winStorage && typeof winStorage.getItem === "function"
      ? (winStorage as Storage)
      : createMemoryStorage();

  Object.defineProperty(globalThis, name, {
    value: resolved,
    configurable: true,
    writable: true,
  });
  if (typeof window !== "undefined" && window[name] !== resolved) {
    Object.defineProperty(window, name, {
      value: resolved,
      configurable: true,
      writable: true,
    });
  }
}

// Node 25+/26 exposes an unbacked global localStorage accessor when --localstorage-file
// is absent, which can shadow jsdom's Storage under Vitest 2.x. Restore real Storage here.
ensureWebStorage("localStorage");
ensureWebStorage("sessionStorage");

afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
