import { Avatar, Button, Card, Descriptions, Modal, Space, Spin, Tag, message } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";
import { cancelDouyinQrcode, pollDouyinQrcode, startDouyinQrcode, unbindDouyin } from "@/api/douyin";
import type { DouyinAccount } from "@/types/douyin";

interface AccountStatusBlockProps {
  userPhone?: string;
  account?: DouyinAccount;
  onChanged: () => void;
}

export default function AccountStatusBlock({ userPhone, account, onChanged }: AccountStatusBlockProps) {
  const [qrOpen, setQrOpen] = useState(false);
  const [qrImage, setQrImage] = useState<string | null>(null);
  const [qrStatus, setQrStatus] = useState<string>("pending");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const startSeqRef = useRef(0);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const applyQrcodeImage = useCallback((base64: string | null | undefined) => {
    if (base64) {
      setQrImage(`data:image/png;base64,${base64}`);
    }
  }, []);

  const handlePoll = useCallback(
    async (sid: string) => {
      try {
        const data = await pollDouyinQrcode(sid);
        setQrStatus(data.status);
        if (data.qrcode_image) {
          applyQrcodeImage(data.qrcode_image);
        }
        if (data.status === "confirmed" && data.bound) {
          stopPoll();
          message.success("抖音账号关联成功");
          setQrOpen(false);
          onChanged();
        } else if (data.status === "expired") {
          stopPoll();
          message.warning(data.message || "二维码已过期");
        }
      } catch (e) {
        stopPoll();
        message.error(e instanceof Error ? e.message : "查询扫码状态失败");
      }
    },
    [applyQrcodeImage, onChanged, stopPoll]
  );

  const startQrcodeFlow = useCallback(async () => {
    stopPoll();
    const seq = ++startSeqRef.current;
    setLoading(true);
    setQrStatus("pending");
    setQrImage(null);
    setQrOpen(true);
    try {
      const data = await startDouyinQrcode();
      if (seq !== startSeqRef.current) {
        return;
      }
      if (data.already_logged_in || data.status === "confirmed") {
        message.success("抖音账号已关联");
        setQrOpen(false);
        onChanged();
        return;
      }
      if (!data.qrcode_image) {
        message.error("未能获取二维码，请重试");
        setQrOpen(false);
        return;
      }
      sessionIdRef.current = data.session_id;
      setSessionId(data.session_id);
      applyQrcodeImage(data.qrcode_image);
      pollRef.current = setInterval(() => {
        const sid = sessionIdRef.current;
        if (sid) {
          void handlePoll(sid);
        }
      }, 2000);
      void handlePoll(data.session_id);
    } catch (e) {
      if (seq === startSeqRef.current) {
        message.error(e instanceof Error ? e.message : "获取二维码失败");
        setQrOpen(false);
      }
    } finally {
      if (seq === startSeqRef.current) {
        setLoading(false);
      }
    }
  }, [applyQrcodeImage, handlePoll, onChanged, stopPoll]);

  useEffect(() => {
    return () => stopPoll();
  }, [stopPoll]);

  const handleQrClose = async () => {
    stopPoll();
    if (sessionId) {
      try {
        await cancelDouyinQrcode(sessionId);
      } catch {
        /* ignore */
      }
    }
    setQrOpen(false);
    sessionIdRef.current = null;
    setSessionId(null);
    setQrImage(null);
  };

  const handleUnbind = async () => {
    try {
      await unbindDouyin();
      message.success("已解绑");
      onChanged();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "解绑失败");
    }
  };

  const authStatusColor =
    account?.auth_status === "active" ? "success" : account?.auth_status === "expired" ? "warning" : "default";

  const qrStatusText =
    qrStatus === "scanned"
      ? "已扫描，请在手机抖音上点击确认登录"
      : qrStatus === "pending"
        ? "请使用手机抖音扫一扫"
        : qrStatus === "expired"
          ? "二维码已过期，请关闭后重新获取"
          : "";

  return (
    <>
      <Card className="block-card" title="账号状态">
        <Descriptions column={1}>
          <Descriptions.Item label="登录用户">{userPhone || "-"}</Descriptions.Item>
          {account?.bound ? (
            <>
              <Descriptions.Item label="抖音">
                <Space>
                  <Tag color="success">已关联</Tag>
                  <span>{account.nickname || "-"}</span>
                  {account.avatar_url && <Avatar src={account.avatar_url} size="small" />}
                  <Tag color={authStatusColor}>
                    登录态：{account.auth_status === "active" ? "有效" : account.auth_status}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="操作">
                <Space>
                  <Button loading={loading} onClick={() => void startQrcodeFlow()}>
                    重新扫码关联
                  </Button>
                  <Button danger onClick={handleUnbind}>
                    解绑
                  </Button>
                </Space>
              </Descriptions.Item>
            </>
          ) : (
            <Descriptions.Item label="抖音">
              <Space>
                <Tag>未关联</Tag>
                <Button type="primary" loading={loading} onClick={() => void startQrcodeFlow()}>
                  扫码关联抖音号
                </Button>
              </Space>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Modal
        title="扫码关联抖音号"
        open={qrOpen}
        onCancel={() => void handleQrClose()}
        footer={[
          <Button key="refresh" onClick={() => void startQrcodeFlow()}>
            刷新二维码
          </Button>,
          <Button key="close" onClick={() => void handleQrClose()}>
            关闭
          </Button>,
        ]}
        destroyOnClose
      >
        <div style={{ textAlign: "center", minHeight: 280 }}>
          {qrImage ? (
            <img src={qrImage} alt="抖音登录二维码" style={{ maxWidth: 260, margin: "0 auto" }} />
          ) : (
            <Spin />
          )}
          <p style={{ marginTop: 16, color: "#666" }}>{qrStatusText}</p>
          <p style={{ color: "#999", fontSize: 12 }}>
            打开抖音 App → 我 → 扫一扫 → 扫描上方二维码 → 在手机上确认登录
          </p>
        </div>
      </Modal>
    </>
  );
}
