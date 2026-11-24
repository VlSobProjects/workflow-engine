"""The report document: the engine's shell, styles and viewer around one embedded model. See ADR 022 §4.

The template is the engine's own and is not replaceable. The document carries everything it needs and
names nothing outside itself, so it opens from a disk or a static host with no network.
"""

from __future__ import annotations

import html
import json
from importlib.resources import files
from string import Template
from typing import cast

REPORT_FILE_NAME = "report.html"

_VIEWER = files("workflow_engine.report").joinpath("viewer")


def _asset(name: str) -> str:
    return _VIEWER.joinpath(name).read_text(encoding="utf-8")


def data_block(model: dict[str, object]) -> str:
    """The model as the text of a `<script type="application/json">` element.

    Every `<` is written as its JSON escape, which covers the two sequences that would end or comment
    out the element, `</` and `<!--`, wherever a value or a name carries them. JSON reads the escape
    back as the same character.
    """
    return json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def render_document(model: dict[str, object]) -> str:
    session = cast(dict[str, object], model["session"])
    title = f"{session['flow_id']} · {session['status']} · workflow-engine report"
    return Template(_asset("shell.html")).substitute(
        title=html.escape(title),
        style=_asset("report.css"),
        data=data_block(model),
        script=_asset("report.js"),
    )
