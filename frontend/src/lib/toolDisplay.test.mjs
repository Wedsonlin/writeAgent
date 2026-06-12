import assert from "node:assert/strict";
import {
  buildToolCallDisplay,
  buildToolResultDisplay,
  normalizeTodoStatus,
} from "./toolDisplay.ts";

const todoResult = buildToolResultDisplay({
  name: "write_todos",
  content:
    "Updated todo list to [{'content': '构造 requirement_analysis 输入 JSON 并运行 Skill 脚本', 'status': 'in_progress'}, {'content': '基于写作任务生成 literature_review 输入 JSON 并运行脚本', 'status': 'pending'}]",
});

assert.equal(todoResult.kind, "todo");
assert.equal(todoResult.title, "待办事项已更新");
assert.equal(todoResult.todos.length, 2);
assert.deepEqual(
  todoResult.todos.map((todo) => [todo.content, todo.statusLabel]),
  [
    ["构造 requirement_analysis 输入 JSON 并运行 Skill 脚本", "进行中"],
    ["基于写作任务生成 literature_review 输入 JSON 并运行脚本", "待处理"],
  ],
);

const bashResult = buildToolResultDisplay({
  name: "execute_bash",
  content: JSON.stringify({
    status: "ok",
    exit_code: 0,
    stdout: "",
    stderr: "",
    duration_ms: 466,
    cwd: "C:\\repo",
    command:
      "python skill_packs/academic-paper-writing/skills/writing-requirement-analysis/scripts/run.py --input .writeagent/projects/default/artifacts/requirement_analysis_input.json --output .writeagent/projects/default/artifacts/requirement_analysis_output.json",
    written_files: [".writeagent\\projects\\default\\artifacts\\requirement_analysis_output.json"],
  }),
});

assert.equal(bashResult.kind, "execution");
assert.equal(bashResult.statusTone, "success");
assert.equal(bashResult.statusLabel, "执行成功");
assert.ok(bashResult.summary.includes("466 ms"));
assert.ok(bashResult.keyValues.some((item) => item.label === "退出码" && item.value === "0"));
assert.deepEqual(bashResult.paths, [".writeagent\\projects\\default\\artifacts\\requirement_analysis_output.json"]);

const progressResult = buildToolResultDisplay({
  name: "update_progress",
  content: JSON.stringify({
    status: "ok",
    stage: {
      stage_id: "literature_review",
      status: "completed",
      input_artifacts: ["/.writeagent/projects/default/artifacts/requirement_analysis_output.json"],
      output_artifacts: ["/.writeagent/projects/default/artifacts/literature_review_output.json"],
      blocked_reason: null,
      updated_at: "2026-06-09T03:32:20.985015+00:00",
    },
    current_stage: "paper_outline",
  }),
});

assert.equal(progressResult.kind, "progress");
assert.equal(progressResult.title, "工作流进度已更新");
assert.equal(progressResult.statusTone, "success");
assert.ok(progressResult.summary.includes("文献梳理"));
assert.ok(progressResult.paths.includes("/.writeagent/projects/default/artifacts/literature_review_output.json"));

const todoCall = buildToolCallDisplay({
  name: "write_todos",
  args: {
    todos: [
      { content: "生成论文大纲并运行 outline 脚本", status: "pending" },
      { content: "汇总最终中文论文 Markdown artifact 并更新进度", status: "pending" },
    ],
  },
});

assert.equal(todoCall.kind, "todo");
assert.equal(todoCall.title, "更新待办事项");
assert.equal(todoCall.todos.length, 2);

const bashCall = buildToolCallDisplay({
  name: "execute_bash",
  args: {
    command:
      "python /skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py --input /.writeagent/projects/default/artifacts/literature_review_input.json --output /.writeagent/projects/default/artifacts/literature_review_output.json",
    purpose: "Run literature review skill script",
    timeout_sec: 600,
  },
});

assert.equal(bashCall.kind, "execution");
assert.equal(bashCall.title, "脚本执行");
assert.ok(bashCall.summary.includes("Run literature review skill script"));
assert.ok(bashCall.keyValues.some((item) => item.label === "超时" && item.value === "600s"));

assert.equal(normalizeTodoStatus("in_progress").label, "进行中");
assert.equal(normalizeTodoStatus("completed").tone, "success");

console.log("toolDisplay tests passed");
