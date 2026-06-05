import client, { unwrap } from "./client";
import type { AuthData, User } from "@/types/auth";

export async function register(phone: string, password: string, password_confirm: string) {
  return unwrap<AuthData>(
    client.post("/auth/register", { phone, password, password_confirm })
  );
}

export async function login(phone: string, password: string) {
  return unwrap<AuthData>(client.post("/auth/login", { phone, password }));
}

export async function getMe() {
  return unwrap<User>(client.get("/auth/me"));
}

export async function logout() {
  return unwrap<{ success: boolean }>(client.post("/auth/logout"));
}
