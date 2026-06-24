from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_seed_bib(tmp_path: Path) -> Path:
    bib_path = tmp_path / "seed.bib"
    bib_path.write_text(
        """@misc{yao2022react,
  author = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  title = {ReAct: Synergizing Reasoning and Acting in Language Models},
  year = {2022},
  eprint = {2210.03629},
  archivePrefix = {arXiv}
}
""",
        encoding="utf-8",
    )
    return bib_path


def _write_two_seed_bib(tmp_path: Path) -> Path:
    bib_path = tmp_path / "seed-two.bib"
    bib_path.write_text(
        """@inproceedings{zero2020,
  author = {Rajbhandari, Samyam and Rasley, Jeff},
  title = {ZeRO: Memory Optimizations Toward Training Trillion Parameter Models},
  booktitle = {SC},
  year = {2020},
  url = {https://arxiv.org/abs/1910.02054}
}

@inproceedings{vllm2023,
  author = {Kwon, Woosuk and Li, Zhuohan},
  title = {Efficient Memory Management for Large Language Model Serving with PagedAttention},
  booktitle = {SOSP},
  year = {2023},
  url = {https://arxiv.org/abs/2309.06180}
}
""",
        encoding="utf-8",
    )
    return bib_path


def _run_literature_script(repo_root: Path, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "scripts" / "run.py"),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_literature_review_builds_report_from_asset_input(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    source["source_map"][0]["main_finding"] = "ReAct combines reasoning and acting for tool-use agents."
    source["source_map"][0]["main_finding_zh"] = "ReAct 将推理与行动结合，为工具调用型 Agent 提供基础范式。"
    source["source_map"][0]["abstract_zh"] = "该文献提出 ReAct 框架，将语言模型的推理轨迹与外部行动交替组织起来。"
    source["source_map"][0]["key_claims"] = ["ReAct combines reasoning and acting for tool-use agents."]
    source["source_map"][0]["key_claims_zh"] = ["ReAct 将推理与行动结合，为工具调用型 Agent 提供基础范式。"]
    source["landscape"]["clusters"][0]["name"] = "LLM agent architecture and tool use"
    source["landscape"]["clusters"][0]["name_zh"] = "LLM 智能体架构与工具调用"
    source["landscape"]["clusters"][0]["summary"] = "This cluster covers ReAct, tool use, and multi-step planning."
    source["landscape"]["clusters"][0]["summary_zh"] = "该主题簇围绕 ReAct、工具调用与多步规划等核心机制展开。"
    source["landscape"]["consensus"] = ["Tool use and multi-step planning are core capabilities of LLM agents."]
    source["landscape"]["consensus_zh"] = ["工具调用与多步规划是 LLM 智能体的核心能力。"]
    source["landscape"]["controversies"] = ["Agents may use built-in tools or open reusable skills."]
    source["landscape"]["controversies_zh"] = ["Agent 应使用紧耦合内置工具，还是开放可复用 Skill，仍存在路径分歧。"]
    source["landscape"]["research_gaps"] = ["End-to-end academic writing agent systems are still immature."]
    source["landscape"]["research_gaps_zh"] = ["面向学术写作场景的端到端 Agent 系统尚不成熟。"]
    source["landscape"]["timeline_summary"] = "ReAct popularized tool-augmented reasoning in 2022."
    source["landscape"]["timeline_summary_zh"] = "2022 年 ReAct 推动工具增强推理范式，随后 Skill 化机制提升了能力复用性。"
    source["paper_reading_cards"] = [
        {
            "paper_id": "yao2022react",
            "source_urls": ["https://arxiv.org/abs/2210.03629"],
            "source_artifact_ids": ["extract-react"],
            "reading_status": "read",
            "research_problem_zh": "语言模型如何在推理过程中调用外部工具。",
            "method_zh": "交替生成推理轨迹和任务动作。",
            "main_claims_zh": ["ReAct 将推理与行动结合，为工具调用型 Agent 提供基础范式。"],
            "evidence_zh": ["论文摘要和案例展示了推理轨迹与外部行动的交替机制。"],
            "limitations_zh": [],
            "relevance_to_arguments": [
                {
                    "core_argument_index": 0,
                    "stance": "supports",
                    "support_strength": "moderate",
                    "evidence_summary_zh": "支撑大脑决策 + 工具调用模式。",
                }
            ],
            "relevance_to_innovations": [
                {
                    "innovation_index": 0,
                    "stance": "background",
                    "support_strength": "moderate",
                    "evidence_summary_zh": "为 Skill 工具调用架构提供上游范式。",
                }
            ],
        }
    ]
    bib_path = _write_seed_bib(tmp_path)
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    result = _run_literature_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    report = payload["literature_report"]

    assert payload["artifact_type"] == "literature_report"
    assert report["citation_style"] == source["citation_style"]
    assert [paper["id"] for paper in report["papers"]] == ["yao2022react"]
    assert report["research_landscape"]["clusters"][0]["name"] == "LLM 智能体架构与工具调用"
    assert report["research_landscape"]["clusters"][0]["summary"] == "该主题簇围绕 ReAct、工具调用与多步规划等核心机制展开。"
    assert report["research_landscape"]["timeline_summary"] == "2022 年 ReAct 推动工具增强推理范式，随后 Skill 化机制提升了能力复用性。"
    assert report["consensus"] == ["工具调用与多步规划是 LLM 智能体的核心能力。"]
    assert report["controversies"] == ["Agent 应使用紧耦合内置工具，还是开放可复用 Skill，仍存在路径分歧。"]
    assert report["research_gaps"] == ["面向学术写作场景的端到端 Agent 系统尚不成熟。"]
    assert report["papers"][0]["abstract"] == "该文献提出 ReAct 框架，将语言模型的推理轨迹与外部行动交替组织起来。"
    assert report["papers"][0]["key_claims"] == ["ReAct 将推理与行动结合，为工具调用型 Agent 提供基础范式。"]
    assert len(report["formatted_bibliography"]["gb7714"]) == 1
    assert len(report["formatted_bibliography"]["apa"]) == 1
    assert "unmapped_papers" not in report
    assert set(report["report_sections"]) == {
        "task_alignment",
        "research_status",
        "field_context",
        "core_literature_viewpoints",
        "argument_support_matrix",
        "innovation_support_matrix",
        "research_gaps",
        "supplement_search_summary",
        "references",
    }
    assert payload["literature_report_markdown_path"] == str(output_path.with_suffix(".md"))
    markdown = output_path.with_suffix(".md").read_text(encoding="utf-8")
    assert payload["literature_report_markdown"] == markdown
    assert "## 研究现状" in markdown
    assert "## 领域脉络" in markdown
    assert "## 核心文献观点" in markdown
    assert "## 任务书对齐目标" in markdown
    assert "## 论点与创新点支撑矩阵" in markdown
    assert "## 研究缺口" in markdown
    assert "## 参考文献" in markdown
    assert "### GB/T 7714" in markdown
    assert "### APA" in markdown
    assert "This cluster covers ReAct" not in markdown
    assert "Tool use and multi-step planning" not in markdown


def test_literature_review_uses_reading_cards_to_build_support_matrices(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    bib_path = _write_two_seed_bib(tmp_path)
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    source["writing_task"]["topic"] = "大模型时代 AI Infrastructure 综述"
    source["writing_task"]["core_arguments"] = [
        "训练基础设施和推理基础设施正在分化。",
        "AI Infra 评价指标需要从峰值算力转向综合效率。",
    ]
    source["writing_task"]["innovation_points"] = [
        "对比训练基础设施与推理基础设施的目标差异。",
        "总结 AI Infra 的典型评价指标与工程权衡。",
    ]
    source["source_map"] = []
    source["paper_reading_cards"] = [
        {
            "paper_id": "zero2020",
            "source_urls": ["https://arxiv.org/abs/1910.02054"],
            "source_artifact_ids": ["extract-zero"],
            "reading_status": "read",
            "research_problem_zh": "大模型训练中的显存冗余如何降低。",
            "method_zh": "将优化器状态、梯度和参数在数据并行进程间分片。",
            "main_claims_zh": ["ZeRO 通过分片优化器状态、梯度和参数降低显存冗余，使训练侧基础设施更关注显存优化与扩展性。"],
            "evidence_zh": ["论文围绕 trillion-parameter training 的显存优化目标展开。"],
            "limitations_zh": ["主要聚焦训练侧，不覆盖在线推理 SLO。"],
            "relevance_to_arguments": [
                {
                    "core_argument_index": 0,
                    "stance": "supports",
                    "support_strength": "strong",
                    "evidence_summary_zh": "直接说明训练侧瓶颈集中在显存优化与扩展性。",
                }
            ],
            "relevance_to_innovations": [
                {
                    "innovation_index": 0,
                    "stance": "supports",
                    "support_strength": "strong",
                    "evidence_summary_zh": "可用于训练/推理目标差异对比中的训练侧代表系统。",
                }
            ],
        },
        {
            "paper_id": "vllm2023",
            "source_urls": ["https://arxiv.org/abs/2309.06180"],
            "source_artifact_ids": ["extract-vllm"],
            "reading_status": "read",
            "research_problem_zh": "LLM 推理服务中的 KV Cache 内存如何高效管理。",
            "method_zh": "提出 PagedAttention，将 KV Cache 按页管理以减少浪费并提升吞吐。",
            "main_claims_zh": ["vLLM 通过 PagedAttention 优化 KV Cache 管理，表明推理基础设施更关注吞吐、延迟和内存利用率。"],
            "evidence_zh": ["论文将服务吞吐和内存效率作为核心评价对象。"],
            "limitations_zh": ["主要面向推理服务，不讨论训练集群通信效率。"],
            "relevance_to_arguments": [
                {
                    "core_argument_index": 1,
                    "stance": "supports",
                    "support_strength": "strong",
                    "evidence_summary_zh": "直接支撑以吞吐、延迟、内存利用率为代表的综合效率指标。",
                }
            ],
            "relevance_to_innovations": [
                {
                    "innovation_index": 1,
                    "stance": "supports",
                    "support_strength": "strong",
                    "evidence_summary_zh": "可用于总结推理侧性能/成本权衡。",
                }
            ],
        },
    ]
    source["landscape"] = {
        "keywords": ["AI Infrastructure", "分布式训练", "推理服务"],
        "clusters": [
            {"name": "训练基础设施", "summary": "训练侧强调显存优化、分布式并行和扩展性。", "paper_ids": ["zero2020"]},
            {"name": "推理基础设施", "summary": "推理侧强调 KV Cache、吞吐、延迟和单位成本。", "paper_ids": ["vllm2023"]},
        ],
        "consensus": ["训练与推理基础设施围绕不同瓶颈形成了分化的优化路径。"],
        "controversies": ["训练侧指标与推理侧指标难以用单一峰值算力指标统一衡量。"],
        "research_gaps": ["仍需统一框架解释训练、推理与运维治理之间的工程权衡。"],
        "timeline_summary": "2020 年前后训练扩展系统成熟，2023 年后推理服务系统快速发展。",
    }
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    result = _run_literature_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    report = payload["literature_report"]
    markdown = output_path.with_suffix(".md").read_text(encoding="utf-8")
    sections = report["report_sections"]

    assert sections["task_alignment"]["core_arguments"] == source["writing_task"]["core_arguments"]
    assert sections["task_alignment"]["innovation_points"] == source["writing_task"]["innovation_points"]
    assert sections["argument_support_matrix"][0]["supporting_papers"] == ["zero2020"]
    assert sections["argument_support_matrix"][1]["supporting_papers"] == ["vllm2023"]
    assert sections["innovation_support_matrix"][0]["supporting_papers"] == ["zero2020"]
    assert sections["innovation_support_matrix"][1]["supporting_papers"] == ["vllm2023"]
    assert report["papers"][0]["key_claims"] != report["papers"][1]["key_claims"]
    assert "ZeRO 通过分片优化器状态" in markdown
    assert "vLLM 通过 PagedAttention" in markdown
    assert "核心论点 1" in markdown
    assert "创新点 1" in markdown
    assert "该文献围绕" not in markdown


def test_literature_review_downgrades_ungrounded_source_map_evidence(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    bib_path = _write_seed_bib(tmp_path)
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    source["paper_reading_cards"] = []
    source["source_map"][0]["evidence_strength"] = "moderate"
    source["source_map"][0]["source_urls"] = []
    source["source_map"][0]["source_artifact_ids"] = []
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    result = _run_literature_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))["literature_report"]
    assert report["papers"][0]["evidence_strength"] == "weak"
    assert report["papers"][0]["provenance"]["status"] == "ungrounded_source_map"


def test_literature_review_accepts_task_book_keywords_and_extra_paper_metadata(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    bib_path = _write_seed_bib(tmp_path)
    source["task_book_markdown"] = "# 论文写作任务书\n\n研究方向关键词：Agent Skills；学术写作智能体"
    source["research_keywords"] = ["Agent Skills", "学术写作智能体"]
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    source["extra_references"] = [
        {
            "id": "skill2024",
            "type": "paper",
            "title": "Reusable Skills for Academic Writing Agents",
            "authors": ["Chen, Ming", "Li, Hua"],
            "year": 2024,
            "venue": "Journal of AI Writing Systems",
            "doi": "10.1234/example.2024.1",
            "url": "https://example.org/skill2024",
            "abstract": "This paper studies reusable skills for academic writing agents.",
            "source_kind": "search_evidence",
        }
    ]
    source["paper_reading_cards"] = [
        {
            "paper_id": "yao2022react",
            "source_urls": ["https://arxiv.org/abs/2210.03629"],
            "source_artifact_ids": ["extract-react"],
            "reading_status": "read",
            "research_problem_zh": "语言模型如何调用外部工具。",
            "method_zh": "交替组织推理轨迹与外部动作。",
            "main_claims_zh": ["ReAct 为工具调用型 Agent 提供基础范式。"],
            "evidence_zh": ["摘要描述了 reasoning 与 acting 的协同。"],
            "limitations_zh": [],
            "relevance_to_arguments": [{"core_argument_index": 0, "stance": "supports", "support_strength": "moderate", "evidence_summary_zh": "支撑工具调用模式。"}],
            "relevance_to_innovations": [],
        },
        {
            "paper_id": "skill2024",
            "source_urls": ["https://example.org/skill2024"],
            "source_artifact_ids": ["extract-skill2024"],
            "reading_status": "read",
            "research_problem_zh": "如何复用技能以支持学术写作智能体。",
            "method_zh": "提出可复用 Skill 组件并评估写作工作流。",
            "main_claims_zh": ["可复用 Skill 为学术写作智能体提供了模块化能力基础。"],
            "evidence_zh": ["摘要描述了可复用技能对写作工作流的支持。"],
            "limitations_zh": [],
            "relevance_to_arguments": [{"core_argument_index": 0, "stance": "supports", "support_strength": "moderate", "evidence_summary_zh": "支撑 Skill 工具调用模式。"}],
            "relevance_to_innovations": [],
        },
    ]
    source["source_map"].append(
        {
            "paper_id": "skill2024",
            "research_question": "如何复用技能以支持学术写作智能体。",
            "core_method": "提出可复用 Skill 组件并评估写作工作流。",
            "main_finding": "可复用 Skill 能降低复杂写作任务的流程负担。",
            "key_claims": ["可复用 Skill 为学术写作智能体提供了模块化能力基础。"],
            "evidence_strength": "moderate",
            "limitations": [],
            "alignment_to_core": [{"core_argument_index": 0, "stance": "supports", "note": "支撑 Skill 工具调用模式。"}],
            "provenance": {"main_finding": "abstract"},
        }
    )
    source["landscape"]["clusters"][0]["paper_ids"].append("skill2024")
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    result = _run_literature_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))["literature_report"]
    assert "Agent Skills" in report["keywords"]
    assert "学术写作智能体" in report["keywords"]
    assert [paper["id"] for paper in report["papers"]] == ["yao2022react", "skill2024"]
    assert report["papers"][1]["source_kind"] == "search_evidence"
    assert len(report["formatted_bibliography"]["gb7714"]) == 2
    assert len(report["report_sections"]["references"]["gb7714"]) == 2
    assert len(report["report_sections"]["references"]["apa"]) == 2


def test_literature_review_derives_keywords_from_task_book_when_research_keywords_missing(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    bib_path = _write_seed_bib(tmp_path)
    source.pop("research_keywords", None)
    source["task_book_markdown"] = "# 论文写作任务书\n\n研究方向关键词：检索增强生成；学术写作智能体"
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    result = _run_literature_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))["literature_report"]
    assert "检索增强生成" in report["keywords"]
    assert "学术写作智能体" in report["keywords"]


def test_literature_review_reports_unmapped_papers_without_crashing(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    bib_path = _write_seed_bib(tmp_path)
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    source["source_map"] = []
    source["paper_reading_cards"] = []
    source["landscape"]["clusters"] = []
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    result = _run_literature_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))["literature_report"]
    assert report["unmapped_papers"] == ["yao2022react"]
    assert report["papers"][0]["key_claims"] == []
    assert report["papers"][0]["evidence_strength"] == "weak"
    assert report["papers"][0]["provenance"]["status"] == "unmapped"
    markdown = output_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "未映射文献" in markdown
    assert "yao2022react" in markdown
