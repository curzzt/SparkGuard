import { useEffect, useState } from "react";
import { Button, Card, Input, InputNumber, Space, Switch, TimePicker, message } from "antd";
import dayjs from "dayjs";
import type { SparkSettings } from "@/types/spark";

interface AutoSparkSettingsBlockProps {
  settings?: SparkSettings;
  loading?: boolean;
  onSave: (data: Partial<SparkSettings>) => Promise<unknown>;
  onRunNow: () => Promise<unknown>;
  onSkipToday: () => Promise<unknown>;
  runLoading?: boolean;
}

export default function AutoSparkSettingsBlock({
  settings,
  loading,
  onSave,
  onRunNow,
  onSkipToday,
  runLoading,
}: AutoSparkSettingsBlockProps) {
  const [enabled, setEnabled] = useState(false);
  const [executeTime, setExecuteTime] = useState(dayjs("09:00", "HH:mm"));
  const [defaultTemplate, setDefaultTemplate] = useState("");
  const [randomEnabled, setRandomEnabled] = useState(false);
  const [dailyLimit, setDailyLimit] = useState(10);

  useEffect(() => {
    if (settings) {
      setEnabled(settings.enabled);
      setExecuteTime(dayjs(settings.execute_time, "HH:mm"));
      setDefaultTemplate(settings.default_template || "");
      setRandomEnabled(settings.random_template_enabled);
      setDailyLimit(settings.daily_limit);
    }
  }, [settings]);

  const handleSave = async () => {
    try {
      await onSave({
        enabled,
        execute_time: executeTime.format("HH:mm"),
        default_template: defaultTemplate,
        random_template_enabled: randomEnabled,
        daily_limit: dailyLimit,
      });
      message.success("设置已保存");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    }
  };

  const handleRunNow = async () => {
    try {
      await onRunNow();
      message.success("任务已触发");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "执行失败");
    }
  };

  const handleSkipToday = async () => {
    try {
      await onSkipToday();
      message.success("已跳过今日");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  return (
    <Card className="block-card" title="自动续火花开关" loading={loading}>
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Space wrap>
          <span>开启自动续火花</span>
          <Switch checked={enabled} onChange={setEnabled} />
          <span>执行时间</span>
          <TimePicker value={executeTime} format="HH:mm" onChange={(v) => v && setExecuteTime(v)} />
        </Space>
        <Space wrap style={{ width: "100%" }}>
          <span>默认模板</span>
          <Input style={{ width: 320 }} value={defaultTemplate} onChange={(e) => setDefaultTemplate(e.target.value)} />
          <span>随机模板</span>
          <Switch checked={randomEnabled} onChange={setRandomEnabled} />
        </Space>
        <Space wrap>
          <span>每日上限</span>
          <InputNumber min={1} max={100} value={dailyLimit} onChange={(v) => setDailyLimit(v || 10)} />
          <Button type="primary" onClick={handleSave}>
            保存
          </Button>
          <Button loading={runLoading} onClick={handleRunNow}>
            立即执行
          </Button>
          <Button onClick={handleSkipToday}>跳过今日</Button>
        </Space>
      </Space>
    </Card>
  );
}
