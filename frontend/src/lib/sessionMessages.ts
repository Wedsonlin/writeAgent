export function messagesForDisplay(streamMessages: unknown[], persistedMessages: unknown[]): unknown[] {
  return streamMessages.length > 0 ? streamMessages : persistedMessages;
}
