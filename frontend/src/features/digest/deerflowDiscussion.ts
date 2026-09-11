export const MAX_DEERFLOW_DISCUSSION_PAPERS = 10;

const DEFAULT_DEERFLOW_CHAT_URL = "https://deerflow.muaiword.com/workspace/chats/new";

export function buildDeerFlowDiscussionUrl(
  literatureKeys: string[],
  baseUrl = DEFAULT_DEERFLOW_CHAT_URL,
) {
  const normalizedKeys = Array.from(
    new Set(literatureKeys.map((key) => key.trim()).filter(Boolean)),
  );
  if (normalizedKeys.length === 0) {
    throw new Error("至少选择 1 篇文献后再讨论。");
  }
  if (normalizedKeys.length > MAX_DEERFLOW_DISCUSSION_PAPERS) {
    throw new Error(`一次最多选择 ${MAX_DEERFLOW_DISCUSSION_PAPERS} 篇文献讨论。`);
  }

  const url = new URL(baseUrl);
  for (const key of normalizedKeys) {
    url.searchParams.append("literature_key", key);
  }
  return url.toString();
}
