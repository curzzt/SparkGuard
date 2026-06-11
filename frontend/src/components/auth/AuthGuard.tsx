import { Navigate, Outlet } from "react-router-dom";
import { Spin } from "antd";
import { useAuth } from "@/hooks/useAuth";
import { isDevAuthBypassEnabled } from "@/store/authStore";

export default function AuthGuard() {
  const { accessToken, user, hasHydrated, clearAuth, meQuery } = useAuth();

  if (isDevAuthBypassEnabled()) {
    return <Outlet />;
  }

  if (!hasHydrated) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  if (meQuery.isPending && !user) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (meQuery.isError && !user) {
    clearAuth();
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
