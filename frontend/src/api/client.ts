import axios from "axios";
import type { ApiResponse } from "@/types/auth";
import { isDevAuthBypassEnabled, useAuthStore } from "@/store/authStore";

const client = axios.create({
  baseURL: "/api",
  timeout: 5000,
});

client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse<unknown>;
    if (data.code !== 0) {
      return Promise.reject(new Error(data.message || "请求失败"));
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401 && !isDevAuthBypassEnabled()) {
      useAuthStore.getState().clearAuth();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    const message = error.response?.data?.message || error.message || "网络错误";
    return Promise.reject(new Error(message));
  }
);

export default client;

export async function unwrap<T>(promise: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  const response = await promise;
  return response.data.data;
}
