import client, { unwrap } from "./client";
import type { DouyinAccount, DouyinRecentContactsData, QrcodeStartData, QrcodeStatusData } from "@/types/douyin";

export async function startDouyinQrcode() {
  return unwrap<QrcodeStartData>(
    client.post("/douyin/qrcode/start", null, { timeout: 120000 })
  );
}

export async function pollDouyinQrcode(sessionId: string) {
  return unwrap<QrcodeStatusData>(
    client.get("/douyin/qrcode/status", { params: { session_id: sessionId }, timeout: 30000 })
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

export async function getDouyinRecentContacts(limit = 10) {
  return unwrap<DouyinRecentContactsData>(
    client.get("/douyin/recent-contacts", { params: { limit }, timeout: 120000 })
  );
}

export async function unbindDouyin() {
  return unwrap<{ success: boolean }>(client.post("/douyin/unbind"));
}
