import { useEffect, useRef } from "react";
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

  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = () => {
    stopPolling();
    let ticks = 0;
    pollRef.current = window.setInterval(() => {
      void (async () => {
        ticks += 1;
        queryClient.invalidateQueries({ queryKey: ["spark-records"] });
        queryClient.invalidateQueries({ queryKey: ["spark-targets"] });
        try {
          const status = await queryClient.fetchQuery({
            queryKey: ["spark-today"],
            queryFn: getTodayStatus,
          });
          if (ticks >= 2 && status.job_status !== "running") {
            stopPolling();
          }
        } catch {
          /* 轮询期间忽略瞬时错误 */
        }
        if (ticks >= 40) {
          stopPolling();
        }
      })();
    }, 3000);
  };

  useEffect(() => stopPolling, []);

  const saveSettingsMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["spark-settings"] });
    },
  });

  const runNowMutation = useMutation({
    mutationFn: runNow,
    onSuccess: () => {
      refreshAll();
      startPolling();
    },
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
