from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import bibtexparser
from tools.search_knowledge import search_knowledge


def test_literature_review_real_invocation_from_stage1_output_and_seed_bib(tmp_path):
    repo_root = Path.cwd()
    skill1_json = repo_root / ".writeagent" / "output" / "skill1-real-argument-replay.json"
    skill1_md = repo_root / ".writeagent" / "output" / "skill1-real-argument-replay.md"
    seed_bib = repo_root / "case" / "references" / "seed.bib"
    assert skill1_json.exists()
    assert skill1_md.exists()
    assert seed_bib.exists()

    stage1 = json.loads(skill1_json.read_text(encoding="utf-8"))
    writing_task = stage1["writing_task"]
    writing_task["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": seed_bib.relative_to(repo_root).as_posix()}
    ]
    entries = bibtexparser.loads(seed_bib.read_text(encoding="utf-8")).entries
    assert len(entries) == 29
    paper_ids = [entry["ID"] for entry in entries]
    landscape = _landscape(paper_ids)
    input_payload = {
        "task_book_markdown": skill1_md.read_text(encoding="utf-8"),
        "task_book_markdown_path": skill1_md.relative_to(repo_root).as_posix(),
        "writing_task": writing_task,
        "research_keywords": ["AI Infrastructure", "分布式训练", "推理服务", "RAG 基础设施"],
        "citation_style": "GB/T 7714",
        "source_map": [],
        "paper_reading_cards": [],
        "landscape": landscape,
        "extra_references": [],
        "supplement_search_summary": {
            "status": "unavailable",
            "reason": "真实精读需要 search_knowledge/extract_sources；当前测试不使用模板化 source_map 冒充精读。",
            "uncovered_arguments": writing_task.get("core_arguments", []),
            "uncovered_innovations": writing_task.get("innovation_points", []),
        },
    }
    input_path = tmp_path / "skill2_real_input.json"
    output_path = tmp_path / "skill2_real_literature_report.json"
    input_path.write_text(json.dumps(input_payload, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
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

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    report = payload["literature_report"]
    markdown_path = Path(payload["literature_report_markdown_path"])
    assert payload["artifact_type"] == "literature_report"
    assert payload["literature_report_markdown"]
    assert markdown_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["literature_report_markdown"] == markdown

    assert len(report["papers"]) == 29
    assert len(report["formatted_bibliography"]["gb7714"]) == 29
    assert len(report["formatted_bibliography"]["apa"]) == 29
    assert len(report["report_sections"]["references"]["gb7714"]) == 29
    assert len(report["report_sections"]["references"]["apa"]) == 29
    assert len(report["unmapped_papers"]) == 29
    assert {paper["evidence_strength"] for paper in report["papers"]} == {"weak"}
    assert report["report_sections"]["task_alignment"]["core_arguments"] == writing_task["core_arguments"]
    assert report["report_sections"]["task_alignment"]["innovation_points"] == writing_task["innovation_points"]
    assert report["report_sections"]["supplement_search_summary"]["status"] == "unavailable"
    for heading in ["任务书对齐目标", "研究现状", "领域脉络", "核心文献观点", "论点与创新点支撑矩阵", "研究缺口", "参考文献", "GB/T 7714", "APA"]:
        assert heading in markdown
    assert "provides candidate evidence" not in markdown
    assert "AI infrastructure has evolved from single-point compute provisioning" not in markdown
    assert "Training-side and inference-side optimization" not in markdown
    assert "该文献围绕" not in markdown


class _UnavailableTavilyClient:
    is_available = False


def test_real_invocation_marks_search_unavailable_when_tavily_is_not_configured(tmp_path):

    result = search_knowledge(
        queries=["ZeRO Memory Optimizations Toward Training Trillion Parameter Models"],
        intent="academic_papers",
        stage_id="literature_review",
        artifact_root=tmp_path,
        manifest_path=tmp_path / "manifest.json",
        client=_UnavailableTavilyClient(),
    )

    assert result["status"] == "unavailable"
    assert "TAVILY_API_KEY" in result["reason"]
    assert "artifact" not in result


def _landscape(paper_ids: list[str]) -> dict:
    return {
        "keywords": ["AI Infrastructure", "分布式训练", "推理服务", "RAG 基础设施"],
        "clusters": [
            {
                "name": "分布式训练与模型扩展",
                "summary": "涵盖 ZeRO、DeepSpeed、Megatron-LM、GShard、Switch Transformer、Alpa 和 Pathways 等训练基础设施。",
                "paper_ids": paper_ids[:9],
            },
            {
                "name": "推理服务与运行时优化",
                "summary": "涵盖 Orca、vLLM、Sarathi、SpecInfer、SGLang、TensorRT-LLM 以及注意力/编译优化。",
                "paper_ids": paper_ids[9:20],
            },
            {
                "name": "编排、检索、可观测性与绿色 AI",
                "summary": "涵盖 Kubernetes、KServe、Slurm、RAG、ColBERT、FAISS、可观测性和可持续 AI。",
                "paper_ids": paper_ids[20:],
            },
        ],
        "consensus": ["AI Infrastructure 已经从单点算力供给演化为跨层协同系统工程。"],
        "controversies": ["训练侧与推理侧的优化目标、资源调度方式和评价指标存在显著差异。"],
        "research_gaps": ["现有文献仍缺少统一覆盖训练、推理、检索、治理和绿色计算的综合评价框架。"],
        "timeline_summary": "2018 年 Ray 代表通用分布式 AI 运行时，2020 年后 ZeRO/DeepSpeed/GShard 等推动大模型训练扩展，2022 年后 vLLM、Orca、SGLang 等强化推理基础设施。",
    }
