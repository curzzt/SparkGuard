import { useEffect } from "react";
import { Layout } from "antd";
import { useNavigate } from "react-router-dom";
import AppHeader from "@/components/layout/AppHeader";
import AccountStatusBlock from "@/components/spark/AccountStatusBlock";
import AutoSparkSettingsBlock from "@/components/spark/AutoSparkSettingsBlock";
import TodayStatusBlock from "@/components/spark/TodayStatusBlock";
import TargetListBlock from "@/components/spark/TargetListBlock";
import RecordListBlock from "@/components/spark/RecordListBlock";
import { useAuth } from "@/hooks/useAuth";
import { useSparkDashboard } from "@/hooks/useSparkDashboard";

const { Content } = Layout;

export default function SparkDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
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
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader onLogout={() => navigate("/login")} />
      <Content className="page-container">
        <AccountStatusBlock
          userPhone={user?.phone}
          account={accountQuery.data}
          onChanged={refreshAll}
        />
        <AutoSparkSettingsBlock
          settings={settingsQuery.data}
          loading={settingsQuery.isLoading}
          onSave={(data) => saveSettingsMutation.mutateAsync(data)}
          onRunNow={() => runNowMutation.mutateAsync()}
          onSkipToday={() => skipTodayMutation.mutateAsync()}
          runLoading={runNowMutation.isPending}
        />
        <TodayStatusBlock status={todayQuery.data} loading={todayQuery.isLoading} />
        <TargetListBlock
          targets={targetsQuery.data?.items || []}
          loading={targetsQuery.isLoading}
          onChanged={refreshAll}
          onBatchEnable={(ids) => batchEnableMutation.mutateAsync(ids)}
        />
        <RecordListBlock records={recordsQuery.data?.items || []} loading={recordsQuery.isLoading} />
      </Content>
    </Layout>
  );
}
