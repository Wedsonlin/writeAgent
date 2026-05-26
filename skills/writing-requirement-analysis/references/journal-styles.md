# 期刊风格画像知识库

`journal_match.py` 会解析下面的 YAML 块来匹配 `target_journal`。新增期刊时
只需在 YAML 中追加一个条目，无需改动代码。

## YAML 索引

```yaml
default:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-相关工作-方法/系统-实验/分析-讨论-结论-参考文献

计算机研究与发展:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要(中英)-引言-相关工作-方法-实验-讨论-结论-参考文献

软件学报:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要(中英)-引言-相关工作-方法-实验-结论-参考文献

中国科学:信息科学:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-方法-实验/案例-结论-参考文献

自动化学报:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-相关研究-方法-实验-结论-参考文献

电子学报:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-理论分析-实验-结论

CCF Transactions on Pervasive Computing and Interaction:
  citation_style: ACM
  tone: formal-en
  structure_hint: Abstract-Intro-Related Work-System-Evaluation-Discussion-Conclusion

ACM Transactions on Information Systems:
  citation_style: ACM
  tone: formal-en
  structure_hint: Abstract-Intro-Related Work-Method-Experiments-Discussion-Conclusion

IEEE Transactions on Knowledge and Data Engineering:
  citation_style: IEEE
  tone: formal-en
  structure_hint: Abstract-Intro-Related Work-Approach-Evaluation-Discussion-Conclusion

arXiv preprint:
  citation_style: APA
  tone: formal-en
  structure_hint: Abstract-Introduction-Background-Method-Results-Discussion-Conclusion

level::CCF-A:
  citation_style: ACM
  tone: formal-en
  structure_hint: Abstract-Introduction-Related Work-Method-Experiments-Discussion-Conclusion

level::CCF-B:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-相关工作-方法-实验-讨论-结论-参考文献

level::CCF-C:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-相关工作-方法-实验-结论-参考文献

level::中文核心:
  citation_style: GB/T 7714
  tone: formal-zh
  structure_hint: 摘要-引言-相关工作-方法-实验/分析-结论-参考文献
```

## 匹配规则

1. 先尝试 `name` 子串匹配（不区分大小写）。
2. 找不到时回退到 `level::<level>` 键。
3. 都不匹配则使用 `default`。

## 维护说明

- 期刊条目以**期刊正式名称**为键；中文期刊用中文，英文期刊用英文官方名。
- 三个字段：`citation_style`、`tone`、`structure_hint`。
- 结构提示仅给出顶层框架，不展开二级标题；具体大纲由 Skill 3 完成。
