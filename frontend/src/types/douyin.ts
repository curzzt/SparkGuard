export interface DouyinAccount {
  bound: boolean;
  auth_method?: string;
  open_id?: string;
  nickname?: string;
  avatar_url?: string;
  auth_status?: string;
  session_valid?: boolean;
}

export interface QrcodeStartData {
  session_id: string;
  status: string;
  qrcode_image: string | null;
  expires_in: number;
  already_logged_in?: boolean;
}

export interface QrcodeStatusData {
  status: string;
  bound: boolean;
  nickname?: string;
  avatar_url?: string;
  message?: string;
  qrcode_image?: string | null;
}
