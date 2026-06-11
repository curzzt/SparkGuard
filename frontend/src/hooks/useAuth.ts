import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/api/auth";
import { isDevAuthBypassEnabled, useAuthStore } from "@/store/authStore";

export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthStore((s) => s._hasHydrated);
  const setAuth = useAuthStore((s) => s.setAuth);
  const setUser = useAuthStore((s) => s.setUser);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: hasHydrated && !!accessToken && !isDevAuthBypassEnabled(),
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (meQuery.data) {
      setUser(meQuery.data);
    }
  }, [meQuery.data, setUser]);

  return {
    accessToken,
    user: meQuery.data || user,
    hasHydrated,
    isAuthenticated: !!accessToken,
    setAuth,
    setUser,
    clearAuth,
    meQuery,
  };
}
