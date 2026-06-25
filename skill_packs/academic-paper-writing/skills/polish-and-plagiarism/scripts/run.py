from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

for parent in Path(__file__).resolve().parents:
    if (parent / "tools").is_dir():
        sys.path.insert(0, str(parent))
        break

from diff_check import detect_polish_issues
from tools.document_export import DocumentExportError, export_markdown_document
from validate import (
    ContractError,
    compute_quality_checks,
    extract_polished_markdown,
    validate_blocking_contract,
)

Issue = dict[str, Any]


def main() -> int:
    args = _parse()
    data = _hydrate_formatted_draft(_load(args.input), Path(args.input))
    try:
        markdown = extract_polished_markdown(data)
        context = validate_blocking_contract(data, markdown)
        issues = detect_polish_issues(
            context["formatted_markdown"],
            markdown,
            context["constraints"],
        )
        issues.extend(context["protected_claim_issues"])
        if data.get("_used_formatted_fallback"):
            issues.append(
                {
                    "code": "formatted_markdown_fallback",
                    "severity": "warning",
                    "field": "polished_markdown",
                    "message": "polished_markdown was omitted; preserved formatted_draft.markdown for final export",
                }
            )
        if data.get("_auto_polish_log"):
            issues.append(
                {
                    "code": "auto_polish_log",
                    "severity": "warning",
                    "field": "polish_log",
                    "message": "polish_log was omitted; generated a conservative log entry for the supplied polished_markdown",
                }
            )
        template_profile = _template_profile_from_data(data)
        template_source_path = _template_source_path_from_data(data)
        export = export_markdown_document(
            markdown,
            Path(args.output).with_suffix(""),
            template_profile=template_profile,
            template_source_path=template_source_path,
        )
    except ContractError as exc:
        _write(args.output, {"artifact_type": "polished_draft", "error": {"message": str(exc), "fields": exc.fields}})
        return 1
    except DocumentExportError as exc:
        _write(args.output, {"artifact_type": "polished_draft", "error": {"message": str(exc), "fields": ["polished_draft.docx_path"]}})
        return 1

    markdown_path = str(Path(args.output).with_suffix(".md"))
    Path(markdown_path).write_text(markdown, encoding="utf-8")
    polish_log = context["polish_log"]
    polished = {
        "markdown": markdown,
        "markdown_path": markdown_path,
        "docx_path": export["docx_path"],
        "pdf_path": export["pdf_path"],
        "export_status": export["export_status"],
        "template_profile": export["template_profile"],
        "template_source_path": export["template_source_path"],
        "template_conformance_report": export["template_conformance_report"],
        "polish_log": polish_log,
        "plagiarism_optimization": context["plagiarism_optimization"],
        "polish_report": _polish_report(polish_log, context["plagiarism_optimization"], issues, export["export_status"]),
        "issues": issues,
        "quality_checks": compute_quality_checks(issues, polish_log, export["export_status"]),
        "source_formatted_path": context["source_formatted_path"],
    }
    _write(args.output, {"artifact_type": "polished_draft", "polished_draft": polished})
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hydrate_formatted_draft(data: dict[str, Any], input_path: Path) -> dict[str, Any]:
    if isinstance(data.get("formatted_draft"), dict):
        return data
    raw_path = data.get("formatted_draft_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return data

    candidates = []
    formatted_path = Path(raw_path)
    candidates.append(formatted_path)
    if not formatted_path.is_absolute():
        candidates.append(Path.cwd() / formatted_path)
        candidates.append(input_path.parent / formatted_path)

    for candidate in candidates:
        if not candidate.exists():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            data["formatted_draft"] = payload.get("formatted_draft") or payload
            break

    if data.get("polished_markdown"):
        if not data.get("polish_log") and isinstance(data.get("formatted_draft_path"), str):
            data["polish_log"] = [
                {
                    "section": "全文",
                    "change_type": "语言润色记录补全",
                    "reason": "输入包含 polished_markdown 但缺少 polish_log；脚本补充保守日志以记录已提供终稿文本并继续导出校验。",
                }
            ]
            data["_auto_polish_log"] = True
        data.setdefault("plagiarism_optimization", [])
        return data

    formatted_markdown = _formatted_body(data).get("markdown")
    if isinstance(formatted_markdown, str) and formatted_markdown.strip():
        data["accept_formatted_without_changes"] = True
        data["_used_formatted_fallback"] = True
        data.setdefault(
            "polish_log",
            [
                {
                    "section": "全文",
                    "change_type": "格式保持型终稿导出",
                    "reason": "未收到 LLM 润色后的 polished_markdown，保留格式化稿正文并执行最终 DOCX/PDF 导出与规范校验。",
                }
            ],
        )
        data.setdefault(
            "plagiarism_optimization",
            [
                {
                    "section": "全文",
                    "suggestion": "未接入商业查重报告；建议人工复核重复表达较高的定义性段落和系统列表段落。",
                }
            ],
        )
    return data


def _write(path: str, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _formatted_body(data: dict[str, Any]) -> dict[str, Any]:
    formatted = data.get("formatted_draft")
    if not isinstance(formatted, dict):
        return {}
    nested = formatted.get("formatted_draft")
    return nested if isinstance(nested, dict) else formatted


def _template_profile_from_data(data: dict[str, Any]) -> str | None:
    formatted = _formatted_body(data)
    value = formatted.get("template_profile")
    if isinstance(value, str) and value.strip():
        return value.strip()
    constraints = data.get("formatting_constraints")
    if isinstance(constraints, dict):
        value = constraints.get("template_profile")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _template_source_path_from_data(data: dict[str, Any]) -> str | None:
    formatted = _formatted_body(data)
    value = formatted.get("template_source_path")
    if isinstance(value, str) and value.strip():
        return value.strip()
    constraints = data.get("formatting_constraints")
    if isinstance(constraints, dict):
        value = constraints.get("template_source_path")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _polish_report(
    polish_log: list[dict[str, Any]],
    plagiarism_optimization: list[Any],
    issues: list[Issue],
    export_status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "total_polish_changes": len(polish_log),
        "total_similarity_suggestions": len(plagiarism_optimization),
        "warnings": sum(1 for issue in issues if issue.get("severity") == "warning"),
        "errors": sum(1 for issue in issues if issue.get("severity") == "error"),
        "export_status": export_status,
    }


if __name__ == "__main__":
    raise SystemExit(main())
