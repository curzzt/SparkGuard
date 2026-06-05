import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";

export function useAuth() {
  const { accessToken, user, setAuth, setUser, clearAuth } = useAuthStore();

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: !!accessToken,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.data) {
      setUser(meQuery.data);
    }
  }, [meQuery.data, setUser]);

  return {
    accessToken,
    user: meQuery.data || user,
    isAuthenticated: !!accessToken,
    setAuth,
    clearAuth,
    meQuery,
  };
}
