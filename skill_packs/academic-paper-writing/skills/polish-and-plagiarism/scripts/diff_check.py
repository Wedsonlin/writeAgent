from __future__ import annotations

import re
from collections import Counter
from typing import Any

from validate import Issue, PolishConstraints

_HEADING_LINE_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
_CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")
_BIBLIOGRAPHY_HEADING = "## 参考文献"
_REPETITIVE_NGRAM_MIN_LEN = 20

_INFORMAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("其实", re.compile(r"其实")),
    ("挺", re.compile(r"挺")),
    ("超级", re.compile(r"超级")),
    ("蛮", re.compile(r"蛮")),
    ("搞定", re.compile(r"搞定")),
    ("说白了", re.compile(r"说白了")),
    ("我觉得", re.compile(r"我觉得")),
    ("非常非常好", re.compile(r"非常非常好")),
    ("然后呢", re.compile(r"然后呢")),
    ("话说回来", re.compile(r"话说回来")),
    ("总之呢", re.compile(r"总之呢")),
    ("咱们", re.compile(r"咱们")),
    ("颠覆性", re.compile(r"颠覆性")),
    ("革命性", re.compile(r"革命性")),
    ("最强", re.compile(r"最强")),
)


def detect_polish_issues(
    formatted_markdown: str | None,
    polished_markdown: str,
    constraints: PolishConstraints,
) -> list[Issue]:
    issues: list[Issue] = []
    if formatted_markdown:
        issues.extend(detect_structure_diff_issues(formatted_markdown, polished_markdown, constraints))
    issues.extend(detect_informal_tone(polished_markdown))
    issues.extend(detect_repetitive_phrasing(polished_markdown, formatted_markdown))
    return issues


def detect_structure_diff_issues(
    formatted_markdown: str,
    polished_markdown: str,
    constraints: PolishConstraints,
) -> list[Issue]:
    issues: list[Issue] = []
    if constraints.preserve_headings:
        issues.extend(_detect_heading_diff(formatted_markdown, polished_markdown))
    if constraints.preserve_citations:
        issues.extend(_detect_citation_marker_diff(formatted_markdown, polished_markdown))
        issues.extend(_detect_bibliography_diff(formatted_markdown, polished_markdown))
    return issues


def detect_informal_tone(markdown: str) -> list[Issue]:
    body = split_body(markdown)
    matches: list[str] = []
    for label, pattern in _INFORMAL_PATTERNS:
        if pattern.search(body):
            matches.append(label)
    if "！" in body:
        matches.append("exclamation mark")
    if not matches:
        return []
    return [
        {
            "code": "informal_tone",
            "severity": "warning",
            "field": "polished_markdown",
            "message": "informal or non-academic expressions detected: " + ", ".join(matches),
        }
    ]


def detect_repetitive_phrasing(
    polished_markdown: str,
    formatted_markdown: str | None = None,
    *,
    min_len: int = _REPETITIVE_NGRAM_MIN_LEN,
) -> list[Issue]:
    polished_body = split_body(polished_markdown)
    formatted_body = split_body(formatted_markdown) if formatted_markdown else ""
    polished_counts = _repeated_sentence_counts(polished_body, min_len)
    formatted_counts = _repeated_sentence_counts(formatted_body, min_len) if formatted_body else Counter()

    issues: list[Issue] = []
    for fragment, polished_count in sorted(polished_counts.items(), key=lambda item: (-item[1], -len(item[0]))):
        if polished_count < 2:
            continue
        formatted_count = formatted_counts.get(fragment, 0)
        if polished_count <= formatted_count:
            continue
        preview = fragment[:40] + ("…" if len(fragment) > 40 else "")
        issues.append(
            {
                "code": "repetitive_phrasing",
                "severity": "warning",
                "field": "polished_markdown",
                "message": (
                    f"repeated sentence fragment of {len(fragment)} characters appears {polished_count} times "
                    f"(formatted draft had {formatted_count}): {preview!r}"
                ),
            }
        )
    return issues


def split_body(markdown: str) -> str:
    body, _ = split_body_and_bibliography(markdown)
    return body


def split_body_and_bibliography(markdown: str) -> tuple[str, str | None]:
    marker_index = markdown.find(_BIBLIOGRAPHY_HEADING)
    if marker_index < 0:
        return markdown, None
    return markdown[:marker_index], markdown[marker_index:]


def extract_heading_lines(markdown: str) -> list[str]:
    return [line.rstrip() for line in _HEADING_LINE_RE.findall(markdown)]


def extract_citation_markers(text: str) -> Counter[int]:
    return Counter(int(match.group(1)) for match in _CITATION_MARKER_RE.finditer(text))


def extract_bibliography_entry_lines(markdown: str) -> list[str]:
    _, bibliography = split_body_and_bibliography(markdown)
    if bibliography is None:
        return []
    lines = bibliography.splitlines()
    if not lines:
        return []
    start = 1 if lines[0].strip() == _BIBLIOGRAPHY_HEADING else 0
    entries = [_normalize_bibliography_line(line) for line in lines[start:] if line.strip()]
    return entries


def _detect_heading_diff(formatted_markdown: str, polished_markdown: str) -> list[Issue]:
    formatted_headings = extract_heading_lines(formatted_markdown)
    polished_headings = extract_heading_lines(polished_markdown)
    if formatted_headings == polished_headings:
        return []
    return [
        {
            "code": "heading_structure_changed",
            "severity": "warning",
            "field": "polished_markdown",
            "message": (
                "heading lines differ from formatted_draft.markdown "
                f"(formatted={len(formatted_headings)}, polished={len(polished_headings)})"
            ),
        }
    ]


def _detect_citation_marker_diff(formatted_markdown: str, polished_markdown: str) -> list[Issue]:
    formatted_markers = extract_citation_markers(split_body(formatted_markdown))
    polished_markers = extract_citation_markers(split_body(polished_markdown))
    if formatted_markers == polished_markers:
        return []

    missing = sorted(index for index, count in formatted_markers.items() if polished_markers[index] < count)
    extra = sorted(index for index, count in polished_markers.items() if formatted_markers[index] < count)
    details: list[str] = []
    if missing:
        details.append(f"missing markers: {', '.join(f'[{index}]' for index in missing)}")
    if extra:
        details.append(f"unexpected markers: {', '.join(f'[{index}]' for index in extra)}")
    return [
        {
            "code": "citation_marker_changed",
            "severity": "warning",
            "field": "polished_markdown",
            "message": "in-text citation markers differ from formatted draft" + (
                f" ({'; '.join(details)})" if details else ""
            ),
        }
    ]


def _detect_bibliography_diff(formatted_markdown: str, polished_markdown: str) -> list[Issue]:
    formatted_entries = extract_bibliography_entry_lines(formatted_markdown)
    polished_entries = extract_bibliography_entry_lines(polished_markdown)
    if not formatted_entries and not polished_entries:
        return []
    if Counter(formatted_entries) == Counter(polished_entries):
        return []
    return [
        {
            "code": "bibliography_changed",
            "severity": "warning",
            "field": "polished_markdown",
            "message": (
                "bibliography entry lines differ from formatted draft "
                f"(formatted={len(formatted_entries)}, polished={len(polished_entries)})"
            ),
        }
    ]


def _normalize_bibliography_line(line: str) -> str:
    return re.sub(r"\s+", "", line.strip())


def _normalize_for_ngrams(text: str) -> str:
    collapsed = re.sub(r"\s+", "", text)
    return re.sub(r"[#*`_\[\]()（）【】]", "", collapsed)


def _repeated_sentence_counts(text: str, min_len: int) -> Counter[str]:
    counts: Counter[str] = Counter()
    for fragment in re.split(r"[。；\n]+", text):
        normalized = _normalize_for_ngrams(fragment)
        if len(normalized) >= min_len:
            counts[normalized] += 1
    return counts
