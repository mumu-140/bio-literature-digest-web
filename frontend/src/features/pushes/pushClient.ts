import { request } from "../../dataClient";

export type PaperPushItem = {
  id: number;
  batch_id: string;
  paper_id: number;
  canonical_key: string;
  recipient_user_id: number;
  sent_by_user_id: number;
  note: string;
  is_read: boolean;
  pushed_at: string;
  read_at?: string | null;
  email_notification_status: "not_requested" | "pending" | "retrying" | "sent" | "failed";
  email_notification_error: string;
  email_notification_sent_at?: string | null;
  title_en: string;
  title_zh: string;
  journal: string;
  publish_date: string;
  article_url: string;
  sender_name: string;
  recipient_name: string;
};

export async function listPushes(targetUserId?: string) {
  const suffix = targetUserId ? `?user_id=${targetUserId}` : "";
  return request<PaperPushItem[]>(`/api/pushes${suffix}`);
}

export async function updatePush(pushId: number, isRead: boolean) {
  return request<PaperPushItem>(`/api/pushes/${pushId}`, {
    method: "PATCH",
    body: JSON.stringify({ is_read: isRead }),
  });
}

export type PaperPushBatchPayload = {
  paper_ids: number[];
  recipient_user_ids: number[];
  note: string;
  send_email_notification: boolean;
};

export type PaperPushBatchResult = {
  batch_id: string;
  paper_count: number;
  recipient_count: number;
  created_count: number;
  email_queued_count: number;
  items: Array<{
    push_id: number;
    paper_id: number;
    recipient_user_id: number;
    email_notification_status: PaperPushItem["email_notification_status"];
  }>;
};

export async function createPushBatch(payload: PaperPushBatchPayload) {
  return request<PaperPushBatchResult>("/api/admin/pushes/batch", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createPush(payload: { paper_id: number; recipient_user_id: number; note: string; send_email_notification: boolean }) {
  return request<PaperPushItem>("/api/admin/pushes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
