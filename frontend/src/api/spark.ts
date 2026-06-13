import client, { unwrap } from "./client";
import type { SparkRecord, SparkSettings, SparkTarget, TodayStatus } from "@/types/spark";

export async function getTargets() {
  return unwrap<{ items: SparkTarget[]; total: number }>(client.get("/spark/targets"));
}

export async function createTarget(data: Partial<SparkTarget>) {
  return unwrap<SparkTarget>(client.post("/spark/targets", data));
}

export async function updateTarget(id: number, data: Partial<SparkTarget>) {
  return unwrap<SparkTarget>(client.put(`/spark/targets/${id}`, data));
}

export async function deleteTarget(id: number) {
  return unwrap<{ success: boolean }>(client.delete(`/spark/targets/${id}`));
}

export async function batchEnableTargets(ids: number[]) {
  return unwrap<{ success: boolean }>(client.post("/spark/targets/batch-enable", { ids }));
}

export async function batchDisableTargets(ids: number[]) {
  return unwrap<{ success: boolean }>(client.post("/spark/targets/batch-disable", { ids }));
}

export async function getSettings() {
  return unwrap<SparkSettings>(client.get("/spark/settings"));
}

export async function updateSettings(data: Partial<SparkSettings>) {
  return unwrap<SparkSettings>(client.put("/spark/settings", data));
}

export async function runNow() {
  return unwrap<{ job_status: string; message: string }>(
    client.post("/spark/run-now", null, { timeout: 300000 })
  );
}

export async function skipToday() {
  return unwrap<{ skip_today: boolean }>(client.post("/spark/skip-today"));
}

export async function getTodayStatus() {
  return unwrap<TodayStatus>(client.get("/spark/today-status"));
}

export async function getRecords(days = 7, page = 1, page_size = 20) {
  return unwrap<{ items: SparkRecord[]; total: number }>(
    client.get("/spark/records", { params: { days, page, page_size } })
  );
}
