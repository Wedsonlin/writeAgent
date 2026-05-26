"""Publish the pipeline artifacts from .writeagent/ into case/ as stage deliverables.

Outputs::

    case/01-论文写作任务书.json    <- state.writing_task
    case/01-论文写作任务书.md      <- .writeagent/outputs/01-论文写作任务书.md
    case/02-文献梳理报告.json      <- state.literature_report
    case/02-文献梳理报告.md        <- .writeagent/outputs/02-文献梳理报告.md
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
WORKSPACE = REPO / ".writeagent"
STATE = WORKSPACE / "state.json"
OUTPUTS = WORKSPACE / "outputs"
CASE = REPO / "case"


def publish() -> None:
    if not STATE.exists():
        raise SystemExit(f"missing {STATE}; run examples/run_skill1_then_skill2.py first")
    state = json.loads(STATE.read_text(encoding="utf-8"))

    if "writing_task" in state:
        target = CASE / "01-论文写作任务书.json"
        target.write_text(
            json.dumps(state["writing_task"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {target.relative_to(REPO)}")

    if "literature_report" in state:
        target = CASE / "02-文献梳理报告.json"
        target.write_text(
            json.dumps(state["literature_report"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {target.relative_to(REPO)}")

    for src_name, dst_name in [
        ("01-论文写作任务书.md", "01-论文写作任务书.md"),
        ("02-文献梳理报告.md", "02-文献梳理报告.md"),
    ]:
        src = OUTPUTS / src_name
        if src.exists():
            dst = CASE / dst_name
            shutil.copy2(src, dst)
            print(f"wrote {dst.relative_to(REPO)}")


if __name__ == "__main__":
    publish()
