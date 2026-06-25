# Data and Results Writing

Do not invent data.

Survey papers:

- Follow the outline. Do not force "实验" or "结果分析" sections unless the outline requires them.
- Discuss evidence from literature as research status, comparison, limitation, or trend.

Empirical papers:

- Methods, experiments, datasets, metrics, and results require `research_data`, `experiment_notes`, or explicit user-provided data.
- If required data is missing, write the issue into `open_questions`.
- Do not fabricate performance improvements, p-values, sample sizes, benchmark names, or evaluation tables.

When data is present:

- Record every table, metric, dataset, or experiment in `data_used`.
- Separate observed results from interpretation.
- Cite literature only for background or comparison, not as a substitute for missing experiment results.
