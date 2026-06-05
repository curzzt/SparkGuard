import { Form, Input, Modal, Switch } from "antd";
import { useEffect } from "react";
import type { SparkTarget } from "@/types/spark";

interface TargetFormModalProps {
  open: boolean;
  initial?: SparkTarget | null;
  onCancel: () => void;
  onSubmit: (values: Partial<SparkTarget>) => Promise<void>;
}

export default function TargetFormModal({ open, initial, onCancel, onSubmit }: TargetFormModalProps) {
  const [form] = Form.useForm();

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        nickname: initial?.nickname || "",
        remark: initial?.remark || "",
        receiver_id: initial?.receiver_id || "",
        custom_template: initial?.custom_template || "",
        enabled: initial?.enabled ?? true,
      });
    } else {
      form.resetFields();
    }
  }, [open, initial, form]);

  return (
    <Modal
      title={initial ? "编辑续火花对象" : "新增续火花对象"}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={onSubmit}>
        <Form.Item name="nickname" label="昵称" rules={[{ required: true, message: "请输入昵称" }]}>
          <Input />
        </Form.Item>
        <Form.Item name="remark" label="备注">
          <Input />
        </Form.Item>
        <Form.Item
          name="receiver_id"
          label="私信会话显示名"
          extra="与抖音私信列表里该好友的名称一致，留空则使用上方昵称"
        >
          <Input placeholder="默认与昵称相同" />
        </Form.Item>
        <Form.Item name="custom_template" label="消息模板">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item name="enabled" label="启用" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
