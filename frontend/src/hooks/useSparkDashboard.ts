import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getDouyinAccount } from "@/api/douyin";
import {
  batchEnableTargets,
  getRecords,
  getSettings,
  getTargets,
  getTodayStatus,
  runNow,
  skipToday,
  updateSettings,
} from "@/api/spark";

export function useSparkDashboard() {
  const queryClient = useQueryClient();

  const queryOpts = { retry: false, refetchOnWindowFocus: false as const };

  const accountQuery = useQuery({ queryKey: ["douyin-account"], queryFn: getDouyinAccount, ...queryOpts });
  const settingsQuery = useQuery({ queryKey: ["spark-settings"], queryFn: getSettings, ...queryOpts });
  const targetsQuery = useQuery({ queryKey: ["spark-targets"], queryFn: getTargets, ...queryOpts });
  const todayQuery = useQuery({ queryKey: ["spark-today"], queryFn: getTodayStatus, ...queryOpts });
  const recordsQuery = useQuery({
    queryKey: ["spark-records"],
    queryFn: () => getRecords(7, 1, 20),
    ...queryOpts,
  });

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ["douyin-account"] });
    queryClient.invalidateQueries({ queryKey: ["spark-settings"] });
    queryClient.invalidateQueries({ queryKey: ["spark-targets"] });
    queryClient.invalidateQueries({ queryKey: ["spark-today"] });
    queryClient.invalidateQueries({ queryKey: ["spark-records"] });
  };

  const saveSettingsMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spark-settings"] });
    },
  });

  const runNowMutation = useMutation({
    mutationFn: runNow,
    onSuccess: () => refreshAll(),
  });

  const skipTodayMutation = useMutation({
    mutationFn: skipToday,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spark-settings"] });
      queryClient.invalidateQueries({ queryKey: ["spark-today"] });
    },
  });

  const batchEnableMutation = useMutation({
    mutationFn: batchEnableTargets,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["spark-targets"] }),
  });

  return {
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
  };
}
