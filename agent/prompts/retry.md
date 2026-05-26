# writeAgent · 失败重试提示词

某个 Skill 在运行时返回了非零退出码或抛出了异常。`retry_with_fallback` 节点负责：

1. 把 `retry_count` 自增 1。
2. 截断 stderr / stdout 末尾 500 字符写入 `history.message`。
3. 若 `retry_count <= MAX_RETRY (=2)`，回跳到失败的 Skill；否则终止流水线并把 `stage` 设为 `failed`。

## 排错优先级

- 网络 / 鉴权类错误（401 / 429 / Timeout）：直接重试。
- LLM 返回非法 JSON：在重试时给 Skill 注入"严格 JSON 模式"提示词。
- 输入文件缺失：尝试用 `state.references_dir` 列出的备选路径。
- 仍然失败：把错误信息汇总成"用户可读的故障描述"输出到 `state.error`。
