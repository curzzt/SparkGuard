export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface User {
  id: number;
  phone: string;
  status: string;
  created_at?: string;
}

export interface AuthData {
  user: User;
  access_token: string;
  token_type: string;
  expires_in: number;
}
