import { buildToolResultDisplay } from "../lib/toolDisplay";
import { ToolDisplayView, ToolGlyph, ToolHeader } from "./ToolDisplayView";

interface Props {
  content: string;
  name?: string;
  parsed?: unknown;
}

export function ToolResultCard({ content, name, parsed }: Props) {
  const display = buildToolResultDisplay({ name, content, parsed });

  return (
    <article className={`tool-result-card ${display.kind}`}>
      <div className="tool-result-header">
        <ToolHeader display={display} icon={<ToolGlyph name={display.toolName} />} />
      </div>
      <ToolDisplayView display={display} rawLabel="查看原始结果" />
    </article>
  );
}
