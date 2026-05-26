# GB/T 7714-2015 引用格式速查

`citation_formatter.format_gb7714` 实现了下表的主要条目类型。本仓库聚焦最常
出现的 5 类（期刊、会议、专著、学位论文、预印本），未来如需扩展请同步更新代码。

## 基本结构

```
作者. 题名[文献类型标识]. 其他责任者. 版本项. 出版地: 出版者, 出版年: 引文页码.
```

## 文献类型标识

| 文献类型 | 标识 |
| --- | --- |
| 期刊（journal） | `[J]` |
| 会议（conference / inproceedings） | `[C]` |
| 专著（book / monograph） | `[M]` |
| 学位论文（thesis / dissertation） | `[D]` |
| 报告（report） | `[R]` |
| 电子资源 / 预印本（preprint） | `[EB/OL]` |
| 其他（misc） | `[Z]` |

## 作者规则

- 作者用「姓 名首字母大写」格式，例如 `Smith J`、`王小明`。
- 3 位以内全部列出；4 位及以上仅列出前 3 位 + 「等」。
- 中英文作者间用半角逗号分隔。

## 示例

期刊：

```
[1] Yao S, Zhao J, Yu D, et al. ReAct: Synergizing Reasoning and Acting in Language Models[J]. arXiv preprint arXiv:2210.03629, 2022.
```

会议：

```
[2] Wang L, Ma C, Feng X, et al. A Survey on Large Language Model based Autonomous Agents[C]. ACL Findings, 2024.
```

电子资源：

```
[3] Anthropic. Skills Specification[EB/OL]. (2025-06-15). https://docs.anthropic.com/skills.
```

## 边界情况

- 缺少 venue 时，省略出版项；只保留 `作者. 题名[标识]. 年份.`。
- 缺少作者（如机构作者）时，把机构名当成单一作者条目；不输出"等"后缀。
- arXiv 文献 type 取 `[EB/OL]`，venue 写 `arXiv preprint arXiv:xxxx.xxxxx`。
