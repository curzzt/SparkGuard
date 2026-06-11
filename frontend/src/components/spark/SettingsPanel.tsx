import { useEffect, useState } from "react";
import { Save, SlidersHorizontal } from "lucide-react";
import Button from "@/components/ui/Button";
import GlassCard from "@/components/ui/GlassCard";
import { Field, Input, TextArea } from "@/components/ui/Input";
import { SkeletonRows } from "@/components/ui/Skeleton";
import Switch from "@/components/ui/Switch";
import { toast } from "@/components/ui/toast";
import type { SparkSettings } from "@/types/spark";

interface SettingsPanelProps {
  settings?: SparkSettings;
  loading?: boolean;
  onSave: (data: Partial<SparkSettings>) => Promise<unknown>;
}

export default function SettingsPanel({ settings, loading, onSave }: SettingsPanelProps) {
  const [executeTime, setExecuteTime] = useState("09:00");
  const [defaultTemplate, setDefaultTemplate] = useState("");
  const [randomEnabled, setRandomEnabled] = useState(false);
  const [dailyLimit, setDailyLimit] = useState(10);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setExecuteTime(settings.execute_time || "09:00");
      setDefaultTemplate(settings.default_template || "");
      setRandomEnabled(settings.random_template_enabled);
      setDailyLimit(settings.daily_limit);
    }
  }, [settings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave({
        execute_time: executeTime,
        default_template: defaultTemplate,
        random_template_enabled: randomEnabled,
        daily_limit: dailyLimit,
      });
      toast.success("设置已保存");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <GlassCard
      title={
        <>
          <SlidersHorizontal size={15} strokeWidth={1.5} className="text-spark-soft" />
          续航参数
        </>
      }
      className="rise-in"
      style={{ animationDelay: "0.16s" }}
    >
      {loading ? (
        <SkeletonRows rows={4} />
      ) : (
        <div className="flex flex-col gap-4">
          <Field label="每日执行时间">
            <Input
              type="time"
              value={executeTime}
              onChange={(e) => setExecuteTime(e.target.value)}
              className="font-hud"
              aria-label="每日执行时间"
            />
          </Field>

          <Field label="默认消息模板" hint="未配置专属模板的对象将使用此内容">
            <TextArea
              value={defaultTemplate}
              onChange={(e) => setDefaultTemplate(e.target.value)}
              placeholder="例如：续火花啦，今天也要保持联系！"
            />
          </Field>

          <div className="flex items-center justify-between rounded-ctl border border-line bg-white/[0.03] px-3.5 py-3">
            <div className="flex flex-col">
              <span className="text-sm text-ink">随机模板</span>
              <span className="text-xs text-ink-dim">从模板池中随机挑选消息</span>
            </div>
            <Switch checked={randomEnabled} onChange={setRandomEnabled} size="sm" label="随机模板开关" />
          </div>

          <Field label="每日最多执行对象数">
            <Input
              type="number"
              min={1}
              max={100}
              value={dailyLimit}
              onChange={(e) => setDailyLimit(Math.min(Math.max(Number.parseInt(e.target.value, 10) || 1, 1), 100))}
              className="font-hud"
              aria-label="每日最多执行对象数"
            />
          </Field>

          <Button
            variant="primary"
            block
            loading={saving}
            icon={<Save size={15} strokeWidth={1.5} />}
            onClick={() => void handleSave()}
          >
            保存设置
          </Button>
        </div>
      )}
    </GlassCard>
  );
}
