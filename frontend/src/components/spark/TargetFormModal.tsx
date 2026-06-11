import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { Field, Input, TextArea } from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";
import Switch from "@/components/ui/Switch";
import type { SparkTarget } from "@/types/spark";

interface TargetFormModalProps {
  open: boolean;
  initial?: SparkTarget | null;
  onCancel: () => void;
  onSubmit: (values: Partial<SparkTarget>) => Promise<void>;
}

export default function TargetFormModal({ open, initial, onCancel, onSubmit }: TargetFormModalProps) {
  const [nickname, setNickname] = useState("");
  const [remark, setRemark] = useState("");
  const [receiverId, setReceiverId] = useState("");
  const [customTemplate, setCustomTemplate] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [nicknameError, setNicknameError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setNickname(initial?.nickname || "");
      setRemark(initial?.remark || "");
      setReceiverId(initial?.receiver_id || "");
      setCustomTemplate(initial?.custom_template || "");
      setEnabled(initial?.enabled ?? true);
      setNicknameError(null);
    }
  }, [open, initial]);

  const handleSubmit = async () => {
    if (!nickname.trim()) {
      setNicknameError("请输入昵称");
      return;
    }
    setNicknameError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        nickname: nickname.trim(),
        remark,
        receiver_id: receiverId,
        custom_template: customTemplate,
        enabled,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      title={initial ? "编辑续火花对象" : "新增续火花对象"}
      onClose={onCancel}
      footer={
        <>
          <Button size="sm" variant="ghost" onClick={onCancel}>
            取消
          </Button>
          <Button size="sm" variant="primary" loading={submitting} onClick={() => void handleSubmit()}>
            {initial ? "保存" : "创建"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Field label="昵称" error={nicknameError}>
          <Input
            value={nickname}
            onChange={(e) => {
              setNickname(e.target.value);
              if (nicknameError) setNicknameError(null);
            }}
            placeholder="对方的昵称"
          />
        </Field>
        <Field label="备注">
          <Input value={remark} onChange={(e) => setRemark(e.target.value)} placeholder="可选" />
        </Field>
        <Field label="私信会话显示名" hint="与抖音私信列表里该好友的名称一致，留空则使用上方昵称">
          <Input value={receiverId} onChange={(e) => setReceiverId(e.target.value)} placeholder="默认与昵称相同" />
        </Field>
        <Field label="消息模板" hint="留空则使用全局默认模板">
          <TextArea value={customTemplate} onChange={(e) => setCustomTemplate(e.target.value)} />
        </Field>
        <div className="flex items-center justify-between rounded-ctl border border-line bg-white/[0.03] px-3.5 py-3">
          <span className="text-sm text-ink">启用该对象</span>
          <Switch checked={enabled} onChange={setEnabled} size="sm" label="启用该对象" />
        </div>
      </div>
    </Modal>
  );
}
