import { useCallback, useEffect, useRef, useState } from "react";
import { QrCode, RefreshCw, Unlink } from "lucide-react";
import { cancelDouyinQrcode, pollDouyinQrcode, startDouyinQrcode, unbindDouyin } from "@/api/douyin";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import { toast } from "@/components/ui/toast";
import type { DouyinAccount } from "@/types/douyin";

interface AccountStatusModalProps {
  open: boolean;
  account?: DouyinAccount;
  onClose: () => void;
  onChanged: () => void;
}

export default function AccountStatusModal({ open, account, onClose, onChanged }: AccountStatusModalProps) {
  const [qrMode, setQrMode] = useState(false);
  const [qrImage, setQrImage] = useState<string | null>(null);
  const [qrStatus, setQrStatus] = useState<string>("pending");
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

  const resetQr = useCallback(async () => {
    stopPoll();
    const sid = sessionIdRef.current;
    sessionIdRef.current = null;
    if (sid) {
      try {
        await cancelDouyinQrcode(sid);
      } catch {
        /* ignore */
      }
    }
    setQrMode(false);
    setQrImage(null);
    setQrStatus("pending");
  }, [stopPoll]);

  const handlePoll = useCallback(
    async (sid: string) => {
      try {
        const data = await pollDouyinQrcode(sid);
        setQrStatus(data.status);
        if (data.qrcode_image) {
          setQrImage(`data:image/png;base64,${data.qrcode_image}`);
        }
        if (data.status === "confirmed" && data.bound) {
          stopPoll();
          toast.success("抖音账号关联成功");
          void resetQr();
          onChanged();
          onClose();
        } else if (data.status === "expired") {
          stopPoll();
          toast.warning(data.message || "二维码已过期");
        } else if (data.status === "error") {
          stopPoll();
          toast.error(data.message || "二维码获取失败，请重试");
        }
      } catch (e) {
        stopPoll();
        toast.error(e instanceof Error ? e.message : "查询扫码状态失败");
      }
    },
    [onChanged, onClose, resetQr, stopPoll]
  );

  const startQrcodeFlow = useCallback(async () => {
    stopPoll();
    const seq = ++startSeqRef.current;
    setLoading(true);
    setQrStatus("pending");
    setQrImage(null);
    setQrMode(true);
    try {
      const data = await startDouyinQrcode();
      if (seq !== startSeqRef.current) return;
      if (data.already_logged_in || data.status === "confirmed") {
        toast.success("抖音账号已关联");
        void resetQr();
        onChanged();
        onClose();
        return;
      }
      sessionIdRef.current = data.session_id;
      setQrStatus(data.status || "loading");
      if (data.qrcode_image) {
        setQrImage(`data:image/png;base64,${data.qrcode_image}`);
      }
      pollRef.current = setInterval(() => {
        const sid = sessionIdRef.current;
        if (sid) {
          void handlePoll(sid);
        }
      }, 2000);
      void handlePoll(data.session_id);
    } catch (e) {
      if (seq === startSeqRef.current) {
        toast.error(e instanceof Error ? e.message : "获取二维码失败");
        setQrMode(false);
      }
    } finally {
      if (seq === startSeqRef.current) {
        setLoading(false);
      }
    }
  }, [handlePoll, onChanged, onClose, resetQr, stopPoll]);

  useEffect(() => {
    return () => stopPoll();
  }, [stopPoll]);

  useEffect(() => {
    if (!open) {
      void resetQr();
    }
  }, [open, resetQr]);

  const handleUnbind = async () => {
    try {
      await unbindDouyin();
      toast.success("已解绑");
      onChanged();
      onClose();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "解绑失败");
    }
  };

  const qrStatusText =
    qrStatus === "loading"
      ? "正在生成二维码，请稍候…"
      : qrStatus === "scanned"
        ? "已扫描，请在手机抖音上点击确认登录"
        : qrStatus === "expired"
          ? "二维码已过期，请刷新重试"
          : "请使用手机抖音扫一扫";

  return (
    <Modal
      open={open}
      title={qrMode ? "扫码关联抖音号" : "抖音账号"}
      onClose={() => {
        void resetQr();
        onClose();
      }}
      footer={
        qrMode ? (
          <>
            <Button size="sm" loading={loading} icon={<RefreshCw size={14} strokeWidth={1.5} />} onClick={() => void startQrcodeFlow()}>
              刷新二维码
            </Button>
            <Button size="sm" variant="ghost" onClick={() => void resetQr()}>
              返回
            </Button>
          </>
        ) : account?.bound ? (
          <>
            <Button size="sm" loading={loading} icon={<QrCode size={14} strokeWidth={1.5} />} onClick={() => void startQrcodeFlow()}>
              重新扫码关联
            </Button>
            <Button size="sm" variant="danger" icon={<Unlink size={14} strokeWidth={1.5} />} onClick={() => void handleUnbind()}>
              解绑
            </Button>
          </>
        ) : (
          <Button
            size="sm"
            variant="primary"
            loading={loading}
            icon={<QrCode size={14} strokeWidth={1.5} />}
            onClick={() => void startQrcodeFlow()}
          >
            扫码关联抖音号
          </Button>
        )
      }
    >
      {qrMode ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-4 text-center">
          {qrImage ? (
            <div className="scanline rounded-ctl border border-volt/30 bg-white p-2.5 shadow-glow-volt">
              <img src={qrImage} alt="抖音登录二维码" className="block h-56 w-56" />
            </div>
          ) : (
            <Spinner />
          )}
          <p className="m-0 text-sm text-ink-mid">{qrStatusText}</p>
          <p className="m-0 text-xs text-ink-dim">打开抖音 App → 我 → 扫一扫 → 扫描上方二维码 → 在手机上确认登录</p>
        </div>
      ) : account?.bound ? (
        <div className="flex items-center gap-4">
          {account.avatar_url ? (
            <img
              src={account.avatar_url}
              alt="抖音头像"
              className="h-14 w-14 rounded-full border border-volt/40 shadow-glow-volt"
            />
          ) : (
            <div className="flex h-14 w-14 items-center justify-center rounded-full border border-line-bright bg-white/[0.05]">
              <QrCode size={22} strokeWidth={1.5} className="text-ink-dim" />
            </div>
          )}
          <div className="flex flex-col gap-1">
            <span className="text-base font-semibold text-ink">{account.nickname || "未知昵称"}</span>
            <span className="flex items-center gap-2 text-xs">
              {account.auth_status === "active" ? (
                <>
                  <span className="pulse-dot" style={{ width: 6, height: 6 }} />
                  <span className="text-volt-soft">登录态有效</span>
                </>
              ) : (
                <span className="text-ember">登录态：{account.auth_status || "未知"}，建议重新扫码</span>
              )}
            </span>
          </div>
        </div>
      ) : (
        <div className="flex min-h-[140px] flex-col items-center justify-center gap-2 text-center">
          <p className="m-0 text-sm text-ink-mid">尚未关联抖音账号</p>
          <p className="m-0 text-xs text-ink-dim">关联后才能执行自动续火花与导入最近联系人</p>
        </div>
      )}
    </Modal>
  );
}
