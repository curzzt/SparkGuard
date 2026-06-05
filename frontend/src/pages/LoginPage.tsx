import { useEffect, useState } from "react";
import { Button, Card, Form, Input, Tabs, message } from "antd";
import { useNavigate } from "react-router-dom";
import { login, register } from "@/api/auth";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("login");

  useEffect(() => {
    document.title = "登录 - 火花续航";
  }, []);

  const handleLogin = async (values: { phone: string; password: string }) => {
    setLoading(true);
    try {
      const data = await login(values.phone, values.password);
      setAuth(data.access_token, data.user);
      message.success("登录成功");
      navigate("/");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: {
    phone: string;
    password: string;
    password_confirm: string;
  }) => {
    setLoading(true);
    try {
      const data = await register(values.phone, values.password, values.password_confirm);
      setAuth(data.access_token, data.user);
      message.success("注册成功");
      navigate("/");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "注册失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Card title="火花续航" style={{ width: 420 }}>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            {
              key: "login",
              label: "登录",
              children: (
                <Form layout="vertical" onFinish={handleLogin}>
                  <Form.Item name="phone" label="手机号" rules={[{ required: true, message: "请输入手机号" }]}>
                    <Input placeholder="13800138000" />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
                    <Input.Password />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: "register",
              label: "注册",
              children: (
                <Form layout="vertical" onFinish={handleRegister}>
                  <Form.Item name="phone" label="手机号" rules={[{ required: true, message: "请输入手机号" }]}>
                    <Input placeholder="13800138000" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    label="密码"
                    rules={[{ required: true, message: "至少8位含字母数字" }]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Form.Item
                    name="password_confirm"
                    label="确认密码"
                    dependencies={["password"]}
                    rules={[
                      { required: true, message: "请确认密码" },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue("password") === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error("两次密码不一致"));
                        },
                      }),
                    ]}
                  >
                    <Input.Password />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    注册
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
