import client, { unwrap } from "./client";
import type { DouyinAccount, QrcodeStartData, QrcodeStatusData } from "@/types/douyin";

export async function startDouyinQrcode() {
  return unwrap<QrcodeStartData>(
    client.post("/douyin/qrcode/start", null, { timeout: 120000 })
  );
}

export async function pollDouyinQrcode(sessionId: string) {
  return unwrap<QrcodeStatusData>(
    client.get("/douyin/qrcode/status", { params: { session_id: sessionId } })
  );
}

export async function cancelDouyinQrcode(sessionId: string) {
  return unwrap<{ success: boolean }>(
    client.post("/douyin/qrcode/cancel", null, { params: { session_id: sessionId } })
  );
}

export async function getDouyinAccount() {
  return unwrap<DouyinAccount>(client.get("/douyin/account"));
}

export async function unbindDouyin() {
  return unwrap<{ success: boolean }>(client.post("/douyin/unbind"));
}
