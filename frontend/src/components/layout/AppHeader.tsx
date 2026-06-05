import { Button, Layout, Space, Typography } from "antd";
import { logout } from "@/api/auth";
import { useAuth } from "@/hooks/useAuth";

const { Header } = Layout;
const { Text } = Typography;

interface AppHeaderProps {
  onLogout?: () => void;
}

export default function AppHeader({ onLogout }: AppHeaderProps) {
  const { user, clearAuth } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      clearAuth();
      onLogout?.();
    }
  };

  return (
    <Header style={{ background: "#fff", padding: "0 24px", display: "flex", justifyContent: "space-between" }}>
      <Typography.Title level={4} style={{ margin: 0, lineHeight: "64px" }}>
        火花续航
      </Typography.Title>
      <Space>
        <Text>{user?.phone}</Text>
        <Button onClick={handleLogout}>退出</Button>
      </Space>
    </Header>
  );
}
