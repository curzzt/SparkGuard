import { Navigate, Outlet } from "react-router-dom";
import { FullScreenSpinner } from "@/components/ui/Spinner";
import { useAuth } from "@/hooks/useAuth";
import { isDevAuthBypassEnabled } from "@/store/authStore";

export default function AuthGuard() {
  const { accessToken, user, hasHydrated, clearAuth, meQuery } = useAuth();

  if (isDevAuthBypassEnabled()) {
    return <Outlet />;
  }

  if (!hasHydrated) {
    return <FullScreenSpinner />;
  }

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  if (meQuery.isPending && !user) {
    return <FullScreenSpinner />;
  }

  if (meQuery.isError && !user) {
    clearAuth();
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
