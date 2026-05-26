# APA 7 引用格式速查

`citation_formatter.format_apa` 覆盖以下主要条目类型，遵循 APA 第 7 版规范。

## 基本结构

```
Author, A. A., Author, B. B., & Author, C. C. (Year). Title of work. *Source*, vol(issue), pages. https://doi.org/xxxx
```

## 作者规则

- 全部作者使用 `Last, F. M.` 形式。
- 两位作者用 `&` 连接：`Smith, J., & Doe, A.`。
- 3 位及以上：前 N-1 个用逗号分隔，最后一个前加 `, &`：`Smith, J., Doe, A., & Lee, B.`。
- 超过 20 位作者：列出前 19 个 + `... ` + 最后一个。

## 题目大小写

- 期刊文章题目使用 sentence case（仅首字母大写）。
- 期刊名 / 书名使用 title case，并以斜体表示（Markdown 中以 `*...*` 包裹）。

## 示例

期刊：

```
Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). ReAct: Synergizing reasoning and acting in language models. *arXiv preprint arXiv:2210.03629*. https://doi.org/10.48550/arXiv.2210.03629
```

会议：

```
Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., ... Wen, J. (2024). A survey on large language model based autonomous agents. *Findings of ACL*.
```

报告 / 网页：

```
Anthropic. (2025). *Skills specification*. https://docs.anthropic.com/skills
```

## 边界情况

- 无年份：用 `(n.d.)`。
- 无 DOI 但有 URL：用 URL 替代 DOI。
- 中文文献：保留中文作者顺序，姓在前；机构作者直接写名称。
