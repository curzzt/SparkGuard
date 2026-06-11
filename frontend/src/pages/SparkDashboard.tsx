import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppHeader from "@/components/layout/AppHeader";
import SparkBackground from "@/components/layout/SparkBackground";
import AccountStatusModal from "@/components/spark/AccountStatusModal";
import MissionControl from "@/components/spark/MissionControl";
import RecordListBlock from "@/components/spark/RecordListBlock";
import SettingsPanel from "@/components/spark/SettingsPanel";
import TargetListBlock from "@/components/spark/TargetListBlock";
import { useSparkDashboard } from "@/hooks/useSparkDashboard";

export default function SparkDashboard() {
  const navigate = useNavigate();
  const [accountOpen, setAccountOpen] = useState(false);
  const {
    accountQuery,
    settingsQuery,
    targetsQuery,
    todayQuery,
    recordsQuery,
    saveSettingsMutation,
    runNowMutation,
    skipTodayMutation,
    batchEnableMutation,
    refreshAll,
  } = useSparkDashboard();

  useEffect(() => {
    document.title = "火花续航面板";
  }, []);

  return (
    <div className="bg-noise relative min-h-screen">
      <SparkBackground />
      <div className="relative z-10">
        <AppHeader
          account={accountQuery.data}
          onAccountClick={() => setAccountOpen(true)}
          onLogout={() => navigate("/login")}
        />
        <main className="mx-auto flex w-full max-w-[1200px] flex-col gap-5 px-6 pb-14 pt-6">
          <div className="rise-in">
            <MissionControl
              settings={settingsQuery.data}
              status={todayQuery.data}
              loading={
                (settingsQuery.isLoading && !settingsQuery.isError) || (todayQuery.isLoading && !todayQuery.isError)
              }
              onToggleEnabled={(enabled) => saveSettingsMutation.mutateAsync({ enabled })}
              onRunNow={() => runNowMutation.mutateAsync()}
              onSkipToday={() => skipTodayMutation.mutateAsync()}
              runLoading={runNowMutation.isPending}
            />
          </div>

          <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <TargetListBlock
                targets={targetsQuery.data?.items || []}
                loading={targetsQuery.isLoading && !targetsQuery.isError}
                accountBound={accountQuery.data?.bound === true}
                onChanged={refreshAll}
                onBatchEnable={(ids) => batchEnableMutation.mutateAsync(ids)}
              />
            </div>
            <SettingsPanel
              settings={settingsQuery.data}
              loading={settingsQuery.isLoading && !settingsQuery.isError}
              onSave={(data) => saveSettingsMutation.mutateAsync(data)}
            />
          </div>

          <RecordListBlock
            records={recordsQuery.data?.items || []}
            loading={recordsQuery.isLoading && !recordsQuery.isError}
          />
        </main>
      </div>

      <AccountStatusModal
        open={accountOpen}
        account={accountQuery.data}
        onClose={() => setAccountOpen(false)}
        onChanged={refreshAll}
      />
    </div>
  );
}
