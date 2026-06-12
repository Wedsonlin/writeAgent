import { buildToolCallDisplay } from "../lib/toolDisplay";
import type { ToolCallSummary } from "./MessageBubble";
import { ToolDisplayView, ToolGlyph, ToolHeader } from "./ToolDisplayView";

const chevron = (
  <svg className="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

interface Props {
  toolCall: ToolCallSummary;
}

export function ToolCallCard({ toolCall }: Props) {
  const display = buildToolCallDisplay(toolCall);
  return (
    <details className={`tool-card ${display.kind}`}>
      <summary>
        <ToolHeader display={display} icon={<ToolGlyph name={display.toolName} />} />
        {chevron}
      </summary>
      <ToolDisplayView display={display} rawLabel="查看参数 JSON" />
    </details>
  );
}
