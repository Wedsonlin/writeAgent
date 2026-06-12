export type ToolDisplayKind =
  | "artifact"
  | "delegation"
  | "execution"
  | "file"
  | "generic"
  | "message"
  | "progress"
  | "todo";

export type ToolDisplayTone = "danger" | "neutral" | "running" | "success" | "warning";

export interface ToolDisplayField {
  label: string;
  value: string;
  mono?: boolean;
}

export interface ToolDisplayTodo {
  content: string;
  status: string;
  statusLabel: string;
  tone: ToolDisplayTone;
}

export interface ToolDisplayModel {
  kind: ToolDisplayKind;
  toolName: string;
  title: string;
  summary: string;
  statusLabel?: string;
  statusTone?: ToolDisplayTone;
  keyValues: ToolDisplayField[];
  todos: ToolDisplayTodo[];
  paths: string[];
  markdown?: string;
  rawText: string;
}

export interface ToolDisplayInput {
  name?: string;
  content?: unknown;
  parsed?: unknown;
}

export interface ToolCallDisplayInput {
  name?: string;
  args?: unknown;
}

const toolLabels: Record<string, string> = {
  ask_user: "请求用户补充",
  delegate_to_agent: "委派 Agent",
  execute_bash: "脚本执行",
  inspect_progress: "查看进度",
  read_file: "读取文件",
  task: "子 Agent 任务",
  update_artifact_manifest: "登记产物",
  update_progress: "更新进度",
  write_file: "写入文件",
  write_todos: "待办事项",
};

const stageLabels: Record<string, string> = {
  academic_formatting: "学术格式化",
  content_generation: "正文生成",
  literature_review: "文献梳理",
  paper_outline: "论文大纲",
  polish_and_plagiarism: "润色查重",
  requirement_analysis: "需求分析",
};

export function buildToolCallDisplay(toolCall: ToolCallDisplayInput): ToolDisplayModel {
  const toolName = toolCall.name ?? "tool_call";
  const args = asRecord(toolCall.args);
  const rawText = stringifyRaw(toolCall.args ?? {});

  if (toolName === "write_todos" && Array.isArray(args?.todos)) {
    const todos = normalizeTodos(args.todos);
    return model({
      kind: "todo",
      toolName,
      title: "更新待办事项",
      summary: `${todos.length} 项任务将同步到执行计划`,
      todos,
      rawText,
    });
  }

  if (toolName === "execute_bash") {
    const command = stringValue(args?.command);
    const purpose = stringValue(args?.purpose);
    return model({
      kind: "execution",
      toolName,
      title: "脚本执行",
      summary: compactText(purpose ?? command ?? "准备运行受控命令", 140),
      keyValues: [
        field("用途", purpose),
        field("命令", command, true),
        field("工作目录", stringValue(args?.cwd), true),
        field("超时", numberValue(args?.timeout_sec) ? `${numberValue(args?.timeout_sec)}s` : undefined),
      ],
      paths: uniquePaths(extractPathLikeValues(args)),
      rawText,
    });
  }

  if (toolName === "update_progress") {
    const stageId = stringValue(args?.stage_id);
    const status = stringValue(args?.status);
    return model({
      kind: "progress",
      toolName,
      title: "更新工作流进度",
      summary: [stageId ? labelForStage(stageId) : null, status ? normalizeTodoStatus(status).label : null]
        .filter(Boolean)
        .join(" · ") || "同步阶段状态",
      keyValues: [
        field("阶段", stageId ? labelForStage(stageId) : undefined),
        field("状态", status ? normalizeTodoStatus(status).label : undefined),
        field("阻塞原因", stringValue(args?.blocked_reason)),
      ],
      paths: uniquePaths([
        ...stringArray(args?.input_artifacts),
        ...stringArray(args?.output_artifacts),
      ]),
      rawText,
    });
  }

  if (toolName === "update_artifact_manifest") {
    return model({
      kind: "artifact",
      toolName,
      title: "登记产物",
      summary: compactText(stringValue(args?.summary) ?? stringValue(args?.path) ?? "更新产物清单", 140),
      keyValues: [
        field("产物", stringValue(args?.artifact_id)),
        field("类型", stringValue(args?.artifact_type)),
        field("阶段", stringValue(args?.stage_id) ? labelForStage(String(args?.stage_id)) : undefined),
        field("创建者", stringValue(args?.created_by)),
      ],
      paths: uniquePaths([stringValue(args?.path), ...stringArray(args?.depends_on)]),
      rawText,
    });
  }

  if (toolName === "task" || toolName === "delegate_to_agent") {
    const receiver = stringValue(args?.subagent_type) ?? stringValue(args?.receiver_agent_id) ?? stringValue(args?.capability);
    const instruction = stringValue(args?.description) ?? stringValue(args?.instruction);
    return model({
      kind: "delegation",
      toolName,
      title: toolName === "task" ? "委派子 Agent" : "远程委派",
      summary: compactText(instruction ?? receiver ?? "交给 Agent 处理", 160),
      keyValues: [
        field("目标", receiver),
        field("任务 ID", stringValue(args?.task_id)),
        field("上下文", stringValue(args?.context_id)),
      ],
      paths: uniquePaths(extractPathLikeValues(args)),
      rawText,
    });
  }

  if (toolName === "read_file" || toolName === "write_file") {
    const filePath = stringValue(args?.file_path);
    const content = stringValue(args?.content);
    return model({
      kind: "file",
      toolName,
      title: toolName === "read_file" ? "读取文件" : "写入文件",
      summary: compactText(filePath ?? "文件操作", 140),
      keyValues: [
        field("路径", filePath, true),
        field("限制", numberValue(args?.limit) ? `${numberValue(args?.limit)} 行` : undefined),
        field("内容长度", content ? `${content.length} 字符` : undefined),
      ],
      paths: uniquePaths([filePath]),
      rawText,
    });
  }

  return model({
    kind: "generic",
    toolName,
    title: labelForTool(toolName),
    summary: summarizeRecord(args) || "查看结构化参数",
    keyValues: scalarFields(args),
    paths: uniquePaths(extractPathLikeValues(args)),
    rawText,
  });
}

export function buildToolResultDisplay(result: ToolDisplayInput): ToolDisplayModel {
  const toolName = result.name ?? "tool";
  const rawText = stringifyRaw(result.content ?? "");
  const parsed = result.parsed ?? parseJsonText(textValue(result.content));
  const text = textValue(result.content);
  const todos = parseTodosFromResult(toolName, parsed, text);

  if (todos.length > 0) {
    return model({
      kind: "todo",
      toolName,
      title: "待办事项已更新",
      summary: `${todos.length} 项任务：${summarizeTodoCounts(todos)}`,
      statusLabel: "已同步",
      statusTone: "success",
      todos,
      rawText,
    });
  }

  const parsedRecord = asRecord(parsed);
  if (toolName === "execute_bash" || looksLikeExecutionResult(parsedRecord)) {
    return executionResultDisplay(toolName, parsedRecord, rawText);
  }

  if (parsedRecord?.stage && typeof parsedRecord.stage === "object") {
    return progressUpdateDisplay(toolName, parsedRecord, rawText);
  }

  if (Array.isArray(parsedRecord?.completed_stages) || Array.isArray(parsedRecord?.pending_stages)) {
    return progressSnapshotDisplay(toolName, parsedRecord, rawText);
  }

  if (parsedRecord?.artifact && typeof parsedRecord.artifact === "object") {
    return artifactResultDisplay(toolName, parsedRecord, rawText);
  }

  if (toolName === "task" || toolName === "delegate_to_agent") {
    const markdown = extractToolMessageMarkdown(text) ?? text;
    return model({
      kind: "delegation",
      toolName,
      title: "子 Agent 返回",
      summary: compactText(firstMeaningfulLine(markdown) ?? "任务返回了结果摘要", 140),
      statusLabel: "已返回",
      statusTone: "success",
      markdown,
      paths: uniquePaths(extractPathsFromText(markdown)),
      rawText,
    });
  }

  if (parsedRecord) {
    return model({
      kind: "generic",
      toolName,
      title: `${labelForTool(toolName)}结果`,
      summary: summarizeRecord(parsedRecord) || "返回结构化数据",
      statusLabel: resultStatusLabel(parsedRecord),
      statusTone: resultStatusTone(parsedRecord),
      keyValues: scalarFields(parsedRecord),
      paths: uniquePaths(extractPathLikeValues(parsedRecord)),
      rawText,
    });
  }

  const simpleFilePath = extractSinglePathFromText(text);
  return model({
    kind: simpleFilePath ? "file" : "message",
    toolName,
    title: `${labelForTool(toolName)}结果`,
    summary: compactText(firstMeaningfulLine(text) ?? "工具返回文本结果", 140),
    statusLabel: /error|failed|失败/i.test(text) ? "需关注" : undefined,
    statusTone: /error|failed|失败/i.test(text) ? "warning" : undefined,
    markdown: text.length > 0 && text.length < 4000 ? text : undefined,
    paths: uniquePaths(simpleFilePath ? [simpleFilePath] : extractPathsFromText(text)),
    rawText,
  });
}

export function labelForTool(name: string): string {
  return toolLabels[name] ?? name;
}

export function labelForStage(stageId: string): string {
  return stageLabels[stageId] ?? stageId;
}

export function normalizeTodoStatus(status: unknown): { label: string; tone: ToolDisplayTone } {
  const value = String(status ?? "").toLowerCase();
  if (["completed", "complete", "done", "success", "ok"].includes(value)) {
    return { label: "已完成", tone: "success" };
  }
  if (["in_progress", "running", "active", "processing"].includes(value)) {
    return { label: "进行中", tone: "running" };
  }
  if (["blocked", "awaiting", "waiting"].includes(value)) {
    return { label: "等待处理", tone: "warning" };
  }
  if (["failed", "failure", "error"].includes(value)) {
    return { label: "失败", tone: "danger" };
  }
  if (["cancelled", "canceled", "skipped"].includes(value)) {
    return { label: "已跳过", tone: "neutral" };
  }
  return { label: value === "pending" || !value ? "待处理" : String(status), tone: "neutral" };
}

function executionResultDisplay(
  toolName: string,
  parsed: Record<string, unknown> | null,
  rawText: string,
): ToolDisplayModel {
  const status = stringValue(parsed?.status);
  const exitCode = numberValue(parsed?.exit_code);
  const durationMs = numberValue(parsed?.duration_ms);
  const writtenFiles = stringArray(parsed?.written_files);
  const stderr = stringValue(parsed?.stderr);
  const stdout = stringValue(parsed?.stdout);
  const tone = status === "ok" ? "success" : status === "timeout" ? "warning" : "danger";
  const statusLabel = status === "ok" ? "执行成功" : status === "timeout" ? "执行超时" : "执行失败";
  const outputPreview = [stdout, stderr].filter(Boolean).join("\n\n").trim();
  return model({
    kind: "execution",
    toolName,
    title: "脚本执行结果",
    summary: [
      statusLabel,
      durationMs != null ? formatDuration(durationMs) : null,
      writtenFiles.length > 0 ? `写入 ${writtenFiles.length} 个文件` : null,
    ]
      .filter(Boolean)
      .join(" · "),
    statusLabel,
    statusTone: tone,
    keyValues: [
      field("退出码", exitCode == null ? undefined : String(exitCode)),
      field("耗时", durationMs == null ? undefined : formatDuration(durationMs)),
      field("工作目录", stringValue(parsed?.cwd), true),
      field("命令", stringValue(parsed?.command), true),
    ],
    markdown: outputPreview ? codeBlock(outputPreview) : undefined,
    paths: uniquePaths(writtenFiles),
    rawText,
  });
}

function progressUpdateDisplay(
  toolName: string,
  parsed: Record<string, unknown>,
  rawText: string,
): ToolDisplayModel {
  const stage = parsed.stage as Record<string, unknown>;
  const stageId = stringValue(stage.stage_id);
  const status = stringValue(stage.status);
  const statusMeta = normalizeTodoStatus(status);
  const currentStage = stringValue(parsed.current_stage);
  return model({
    kind: "progress",
    toolName,
    title: "工作流进度已更新",
    summary: [
      stageId ? `${labelForStage(stageId)} → ${statusMeta.label}` : null,
      currentStage ? `下一阶段：${labelForStage(currentStage)}` : "流程已收束",
    ]
      .filter(Boolean)
      .join(" · "),
    statusLabel: statusMeta.label,
    statusTone: statusMeta.tone,
    keyValues: [
      field("阶段", stageId ? labelForStage(stageId) : undefined),
      field("状态", statusMeta.label),
      field("当前阶段", currentStage ? labelForStage(currentStage) : "无"),
      field("更新时间", stringValue(stage.updated_at)),
    ],
    paths: uniquePaths([
      ...stringArray(stage.input_artifacts),
      ...stringArray(stage.output_artifacts),
    ]),
    rawText,
  });
}

function progressSnapshotDisplay(
  toolName: string,
  parsed: Record<string, unknown>,
  rawText: string,
): ToolDisplayModel {
  const completed = stringArray(parsed.completed_stages);
  const pending = stringArray(parsed.pending_stages);
  const artifacts = Array.isArray(parsed.artifacts) ? parsed.artifacts : [];
  const currentStage = stringValue(parsed.current_stage);
  return model({
    kind: "progress",
    toolName,
    title: "当前工作流快照",
    summary: `已完成 ${completed.length} 阶段 · 待处理 ${pending.length} 阶段 · 产物 ${artifacts.length} 个`,
    statusLabel: currentStage ? "进行中" : pending.length === 0 ? "已完成" : undefined,
    statusTone: currentStage ? "running" : pending.length === 0 ? "success" : undefined,
    keyValues: [
      field("当前阶段", currentStage ? labelForStage(currentStage) : "无"),
      field("下一步", stringValue(parsed.next_recommended_action) ? labelForStage(String(parsed.next_recommended_action)) : "无"),
      field("阻塞原因", stringValue(parsed.blocked_reason)),
    ],
    paths: uniquePaths(extractPathLikeValues(parsed)),
    rawText,
  });
}

function artifactResultDisplay(
  toolName: string,
  parsed: Record<string, unknown>,
  rawText: string,
): ToolDisplayModel {
  const artifact = parsed.artifact as Record<string, unknown>;
  return model({
    kind: "artifact",
    toolName,
    title: "产物清单已更新",
    summary: compactText(stringValue(artifact.summary) ?? stringValue(artifact.path) ?? "产物已登记", 160),
    statusLabel: "已登记",
    statusTone: "success",
    keyValues: [
      field("产物", stringValue(artifact.artifact_id)),
      field("类型", stringValue(artifact.artifact_type)),
      field("阶段", stringValue(artifact.stage_id) ? labelForStage(String(artifact.stage_id)) : undefined),
      field("版本", numberValue(artifact.version) == null ? undefined : `v${numberValue(artifact.version)}`),
      field("创建者", stringValue(artifact.created_by)),
    ],
    paths: uniquePaths(extractPathLikeValues(artifact)),
    rawText,
  });
}

function parseTodosFromResult(toolName: string, parsed: unknown, text: string): ToolDisplayTodo[] {
  const record = asRecord(parsed);
  if (Array.isArray(record?.todos)) {
    return normalizeTodos(record.todos);
  }
  if (toolName === "write_todos" || /todo list|todos/i.test(text)) {
    return normalizeTodos(parseTodoObjectsFromText(text));
  }
  return [];
}

function normalizeTodos(rawTodos: unknown[]): ToolDisplayTodo[] {
  return rawTodos
    .map((raw) => asRecord(raw))
    .filter((raw): raw is Record<string, unknown> => Boolean(raw))
    .map((raw) => {
      const content = stringValue(raw.content) ?? stringValue(raw.title) ?? stringValue(raw.task) ?? "";
      const status = stringValue(raw.status) ?? "pending";
      const meta = normalizeTodoStatus(status);
      return {
        content,
        status,
        statusLabel: meta.label,
        tone: meta.tone,
      };
    })
    .filter((todo) => todo.content.length > 0);
}

function parseTodoObjectsFromText(text: string): Array<Record<string, string>> {
  const todos: Array<Record<string, string>> = [];
  const pattern = /\{['"]content['"]:\s*['"]([^'"]+)['"],\s*['"]status['"]:\s*['"]([^'"]+)['"]/g;
  for (const match of text.matchAll(pattern)) {
    todos.push({ content: match[1], status: match[2] });
  }
  return todos;
}

function summarizeTodoCounts(todos: ToolDisplayTodo[]): string {
  const counts = new Map<string, number>();
  for (const todo of todos) {
    counts.set(todo.statusLabel, (counts.get(todo.statusLabel) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([label, count]) => `${label} ${count}`)
    .join("，");
}

function resultStatusLabel(record: Record<string, unknown>): string | undefined {
  const status = stringValue(record.status);
  if (!status) {
    return undefined;
  }
  if (status === "ok" || status === "success") {
    return "成功";
  }
  if (status === "timeout") {
    return "超时";
  }
  if (status === "failed" || status === "error") {
    return "失败";
  }
  return status;
}

function resultStatusTone(record: Record<string, unknown>): ToolDisplayTone | undefined {
  const status = stringValue(record.status);
  if (status === "ok" || status === "success") {
    return "success";
  }
  if (status === "timeout") {
    return "warning";
  }
  if (status === "failed" || status === "error") {
    return "danger";
  }
  return undefined;
}

function looksLikeExecutionResult(record: Record<string, unknown> | null): boolean {
  return Boolean(record && ("exit_code" in record || "stdout" in record || "stderr" in record || "command" in record));
}

function scalarFields(record: Record<string, unknown> | null, limit = 6): ToolDisplayField[] {
  if (!record) {
    return [];
  }
  return Object.entries(record)
    .filter(([, value]) => value == null || ["boolean", "number", "string"].includes(typeof value))
    .slice(0, limit)
    .map(([key, value]) => field(humanizeKey(key), value == null ? "无" : String(value), looksLikePathOrCommand(String(value))))
    .filter((item): item is ToolDisplayField => Boolean(item));
}

function summarizeRecord(record: Record<string, unknown> | null): string {
  if (!record) {
    return "";
  }
  const preferred = ["summary", "message", "content", "description", "next_recommended_action"];
  for (const key of preferred) {
    const value = stringValue(record[key]);
    if (value) {
      return compactText(key === "next_recommended_action" ? `建议下一步：${labelForStage(value)}` : value, 160);
    }
  }
  const keys = Object.keys(record);
  return keys.length > 0 ? `包含 ${keys.length} 个字段：${keys.slice(0, 4).map(humanizeKey).join("、")}` : "";
}

function extractPathLikeValues(value: unknown): string[] {
  const paths: string[] = [];
  const visit = (item: unknown, key = "") => {
    if (typeof item === "string") {
      if (looksLikePath(item) || /path|file|artifact|output|input/i.test(key)) {
        paths.push(item);
      }
      return;
    }
    if (Array.isArray(item)) {
      item.forEach((entry) => visit(entry, key));
      return;
    }
    const record = asRecord(item);
    if (record) {
      Object.entries(record).forEach(([childKey, childValue]) => visit(childValue, childKey));
    }
  };
  visit(value);
  return paths;
}

function extractPathsFromText(text: string): string[] {
  const matches = text.match(/(?:\/|\.\w|[A-Za-z]:\\)[^\s`'"，。；;]+/g) ?? [];
  return matches.filter(looksLikePath);
}

function extractSinglePathFromText(text: string): string | null {
  const match = text.match(/(?:Updated file|Wrote file|Read file)\s+([^\s]+)/i);
  return match?.[1] ?? null;
}

function uniquePaths(paths: Array<string | null | undefined>): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const path of paths) {
    if (!path || seen.has(path)) {
      continue;
    }
    seen.add(path);
    result.push(path);
  }
  return result.slice(0, 12);
}

function extractToolMessageMarkdown(text: string): string | null {
  const match = text.match(/ToolMessage\(content=(['"])([\s\S]*?)\1,\s*name=/);
  if (!match) {
    return null;
  }
  return decodeEscapedText(match[2]);
}

function decodeEscapedText(text: string): string {
  return text
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\'/g, "'")
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, "\\");
}

function firstMeaningfulLine(text: string): string | null {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim().replace(/^[-*]\s+/, ""))
    .find((line) => line.length > 0) ?? null;
}

function compactText(text: string, maxLength = 120): string {
  const compacted = text.replace(/\s+/g, " ").trim();
  if (compacted.length <= maxLength) {
    return compacted;
  }
  return `${compacted.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms} ms`;
  }
  return `${(ms / 1000).toFixed(1)} s`;
}

function codeBlock(text: string): string {
  return `\`\`\`text\n${text}\n\`\`\``;
}

function field(label: string, value: unknown, mono = false): ToolDisplayField | null {
  if (value == null || value === "") {
    return null;
  }
  return { label, value: String(value), mono };
}

type ToolDisplayModelInput = Omit<Partial<ToolDisplayModel>, "keyValues" | "paths" | "todos"> &
  Pick<ToolDisplayModel, "kind" | "rawText" | "title" | "toolName"> & {
    keyValues?: Array<ToolDisplayField | null>;
    paths?: string[];
    todos?: ToolDisplayTodo[];
  };

function model(input: ToolDisplayModelInput): ToolDisplayModel {
  return {
    kind: input.kind,
    toolName: input.toolName,
    title: input.title,
    summary: input.summary ?? "",
    statusLabel: input.statusLabel,
    statusTone: input.statusTone,
    keyValues: (input.keyValues ?? []).filter((item): item is ToolDisplayField => Boolean(item)),
    todos: input.todos ?? [],
    paths: input.paths ?? [],
    markdown: input.markdown,
    rawText: input.rawText,
  };
}

function parseJsonText(text: string): unknown | undefined {
  if (!text.trim()) {
    return undefined;
  }
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function textValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (value == null) {
    return "";
  }
  return stringifyRaw(value);
}

function stringifyRaw(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function humanizeKey(key: string): string {
  const labels: Record<string, string> = {
    artifact_id: "产物",
    artifact_type: "类型",
    blocked_reason: "阻塞原因",
    command: "命令",
    content: "内容",
    created_by: "创建者",
    current_stage: "当前阶段",
    duration_ms: "耗时",
    exit_code: "退出码",
    file_path: "路径",
    next_recommended_action: "建议下一步",
    path: "路径",
    stage_id: "阶段",
    status: "状态",
    summary: "摘要",
    updated_at: "更新时间",
    version: "版本",
  };
  return labels[key] ?? key.replace(/_/g, " ");
}

function looksLikePathOrCommand(value: string): boolean {
  return looksLikePath(value) || value.includes(" --") || value.startsWith("python ");
}

function looksLikePath(value: string): boolean {
  return (
    value.includes("/") ||
    value.includes("\\") ||
    /\.(json|md|py|yaml|yml|txt|bib|csv|ts|tsx|js|mjs)$/i.test(value)
  );
}
