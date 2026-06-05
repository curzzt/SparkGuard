import { Navigate, Outlet } from "react-router-dom";
import { Spin } from "antd";
import { useAuth } from "@/hooks/useAuth";

const DEV_BYPASS = import.meta.env.DEV && import.meta.env.VITE_DEV_BYPASS_AUTH === "true";

export default function AuthGuard() {
  const { isAuthenticated, meQuery } = useAuth();

  if (DEV_BYPASS) {
    return <Outlet />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (meQuery.isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  return <Outlet />;
}
