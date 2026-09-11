import { useState } from "react";

import { AuthUser, PaperItem } from "../../dataClient";
import { createPushBatch } from "../pushes/pushClient";
import { useAdminUsers } from "../shared/WorkbenchUi";
import { getPaperSelectionKey } from "./digestUtils";

const MAX_PUSH_COMBINATIONS = 200;

export type PushFeedback = {
  kind: "success" | "error";
  message: string;
};

type PushFormState = ReturnType<typeof usePushFormState>;

export function useDigestPush({
  user,
  loadedPapers,
  selectedKeys,
}: {
  user: AuthUser;
  loadedPapers: PaperItem[];
  selectedKeys: string[];
}) {
  const adminUsers = useAdminUsers(user.role === "admin");
  const form = usePushFormState();
  const actions = usePushActions({ user, loadedPapers, selectedKeys, form });
  const selectedPaperCount = loadedPapers.filter((paper) =>
    selectedKeys.includes(getPaperSelectionKey(paper)),
  ).length;
  return {
    adminUsers,
    ...form,
    ...actions,
    pushCombinationCount: selectedPaperCount * form.pushTargetUserIds.length,
    maxPushCombinations: MAX_PUSH_COMBINATIONS,
  };
}

function usePushFormState() {
  const [pushTargetUserIds, setPushTargetUserIds] = useState<string[]>([]);
  const [pushNote, setPushNote] = useState("");
  const [sendPushEmail, setSendPushEmail] = useState(true);
  const [pushFeedback, setPushFeedback] = useState<PushFeedback | null>(null);
  const [pushingPaperId, setPushingPaperId] = useState<number | null>(null);
  const [isBatchPushing, setIsBatchPushing] = useState(false);
  return {
    pushTargetUserIds,
    setPushTargetUserIds,
    pushNote,
    setPushNote,
    sendPushEmail,
    setSendPushEmail,
    pushFeedback,
    setPushFeedback,
    pushingPaperId,
    setPushingPaperId,
    isBatchPushing,
    setIsBatchPushing,
  };
}

function usePushActions({
  user,
  loadedPapers,
  selectedKeys,
  form,
}: {
  user: AuthUser;
  loadedPapers: PaperItem[];
  selectedKeys: string[];
  form: PushFormState;
}) {
  const selectedPapers = loadedPapers.filter((paper) =>
    selectedKeys.includes(getPaperSelectionKey(paper)),
  );
  return {
    isPushPending: form.isBatchPushing || form.pushingPaperId !== null,
    pushPaper: (paper: PaperItem) => submitPush({ user, form, papers: [paper], singlePaperId: paper.id }),
    pushSelectedPapers: () => submitPush({ user, form, papers: selectedPapers }),
  };
}

async function submitPush({
  user,
  form,
  papers,
  singlePaperId,
}: {
  user: AuthUser;
  form: PushFormState;
  papers: PaperItem[];
  singlePaperId?: number;
}) {
  if (user.role !== "admin") return;
  const recipientIds = form.pushTargetUserIds.map(Number);
  const errorMessage = validatePush(papers.length, recipientIds.length);
  if (errorMessage) {
    form.setPushFeedback({ kind: "error", message: errorMessage });
    return;
  }

  singlePaperId ? form.setPushingPaperId(singlePaperId) : form.setIsBatchPushing(true);
  form.setPushFeedback(null);
  try {
    const result = await createPushBatch({
      paper_ids: papers.map((paper) => paper.id),
      recipient_user_ids: recipientIds,
      note: form.pushNote,
      send_email_notification: form.sendPushEmail,
    });
    const emailText = result.email_queued_count
      ? "，" + String(result.email_queued_count) + " 封汇总邮件已进入队列"
      : "";
    form.setPushFeedback({
      kind: "success",
      message: "已创建 " + String(result.created_count) + " 条站内推送" + emailText + "。",
    });
  } catch (error) {
    form.setPushFeedback({
      kind: "error",
      message: error instanceof Error ? error.message : "批量推送失败，请稍后重试。",
    });
  } finally {
    form.setPushingPaperId(null);
    form.setIsBatchPushing(false);
  }
}

function validatePush(paperCount: number, recipientCount: number) {
  if (!paperCount) return "先选择要推送的文献。";
  if (!recipientCount) return "至少选择一名接收人。";
  if (paperCount * recipientCount > MAX_PUSH_COMBINATIONS) {
    return "本次推送超过 200 条，请减少文献或接收人。";
  }
  return "";
}
