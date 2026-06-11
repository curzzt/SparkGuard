import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types/auth";

interface AuthState {
  accessToken: string | null;
  user: User | null;
  _hasHydrated: boolean;
  setAuth: (token: string, user: User) => void;
  setUser: (user: User) => void;
  clearAuth: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      _hasHydrated: false,
      setAuth: (accessToken, user) => set({ accessToken, user }),
      setUser: (user) => set({ user }),
      clearAuth: () => set({ accessToken: null, user: null }),
      setHasHydrated: (value) => set({ _hasHydrated: value }),
    }),
    {
      name: "sparkguard-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
      }),
      onRehydrateStorage: () => () => {
        useAuthStore.getState().setHasHydrated(true);
      },
    }
  )
);

if (useAuthStore.persist.hasHydrated()) {
  useAuthStore.getState().setHasHydrated(true);
} else {
  useAuthStore.persist.onFinishHydration(() => {
    useAuthStore.getState().setHasHydrated(true);
  });
}

export function isDevAuthBypassEnabled(): boolean {
  return import.meta.env.DEV && String(import.meta.env.VITE_DEV_BYPASS_AUTH).toLowerCase() === "true";
}
