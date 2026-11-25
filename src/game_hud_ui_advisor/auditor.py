"""Inert, root-jailed static heuristic auditor for local game UI/HUD files."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MAX_AUDIT_BYTES = 1_000_000
ALLOWED_AUDIT_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".jsx", ".tsx"}

_FONT_SIZE_PX_RE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)\s*px", re.IGNORECASE)
_OVERLAY_POS_RE = re.compile(r"position\s*:\s*(?:fixed|absolute)|\bfixed\s+inset-0\b", re.IGNORECASE)
_POINTER_NONE_RE = re.compile(r"pointer-events\s*:\s*none|\bpointer-events-none\b", re.IGNORECASE)
_USER_SELECT_NONE_RE = re.compile(r"user-select\s*:\s*none|-webkit-user-select\s*:\s*none|\bselect-none\b", re.IGNORECASE)
_MOTION_RE = re.compile(r"@keyframes|\banimation\s*:|\btransition\s*:|\banimate-", re.IGNORECASE)
_REDUCED_MOTION_RE = re.compile(r"prefers-reduced-motion|\bmotion-reduce:", re.IGNORECASE)
_FOCUS_STYLE_RE = re.compile(r":focus(?:-visible)?\b|\bfocus-visible:", re.IGNORECASE)
_INTERACTIVE_CONTROL_RE = re.compile(r"<(?:button|input|select|textarea)\b|\bonClick\s*=|\baddEventListener\s*\(\s*['\"]click['\"]", re.IGNORECASE)
_BACKDROP_BLUR_RE = re.compile(r"backdrop-filter\s*:[^;]*blur\(|\bbackdrop-blur(?:-sm|-md|-lg|-xl)?\b", re.IGNORECASE)
_RESPONSIVE_HINT_RE = re.compile(r"@media|clamp\(|minmax\(|env\(\s*safe-area-inset", re.IGNORECASE)
_TABULAR_NUMS_RE = re.compile(r"tabular-nums", re.IGNORECASE)
_TEXT_LEGIBILITY_RE = re.compile(r"text-shadow|-webkit-text-stroke|drop-shadow", re.IGNORECASE)
_ARIA_LIVE_RE = re.compile(r"aria-live\s*=", re.IGNORECASE)


class _HtmlHudSignals(HTMLParser):
    """Collect structural HTML HUD signals without executing scripts or echoing copy."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_viewport = False
        self.images_without_alt: list[int] = []
        self.interactive_count = 0
        self.aria_live_count = 0
        self.inline_css_chunks: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.casefold(): v for k, v in attrs}
        line = self.getpos()[0]
        tag_lower = tag.casefold()
        if tag_lower == "style":
            self._in_style = True
        elif tag_lower == "meta" and (values.get("name") or "").casefold() == "viewport":
            self.has_viewport = True
        elif tag_lower == "img" and "alt" not in values:
            self.images_without_alt.append(line)
        elif tag_lower in {"button", "input", "select", "textarea"}:
            self.interactive_count += 1
        if "aria-live" in values:
            self.aria_live_count += 1
        style = values.get("style")
        if style:
            self.inline_css_chunks.append(style)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.inline_css_chunks.append(data)


def audit_local_game_ui_file(path: str, audit_root: Path) -> dict[str, Any]:
    """Review one explicitly selected local game UI/HUD file as inert text."""
    try:
        root = audit_root.resolve()
        selected = Path(path).resolve(strict=True)
        selected.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return {"status": "rejected", "reason": "path_outside_audit_root_or_unavailable"}

    suffix = selected.suffix.casefold()
    if not selected.is_file() or suffix not in ALLOWED_AUDIT_SUFFIXES:
        return {"status": "rejected", "reason": "expected_supported_ui_file"}

    try:
        if selected.stat().st_size > MAX_AUDIT_BYTES:
            return {"status": "rejected", "reason": "file_too_large"}
        raw = selected.read_bytes()
    except OSError:
        return {"status": "rejected", "reason": "file_unreadable"}

    if len(raw) > MAX_AUDIT_BYTES:
        return {"status": "rejected", "reason": "file_too_large"}

    text = raw.decode("utf-8", errors="replace")
    is_html = suffix in {".html", ".htm"}
    findings: list[dict[str, Any]] = []

    has_viewport = False
    has_aria_live = bool(_ARIA_LIVE_RE.search(text))
    interactive_present = bool(_INTERACTIVE_CONTROL_RE.search(text))
    analysis_text = text

    if is_html:
        parser = _HtmlHudSignals()
        try:
            parser.feed(text)
            parser.close()
        except Exception:
            return {"status": "rejected", "reason": "html_parse_error"}
        has_viewport = parser.has_viewport
        has_aria_live = has_aria_live or parser.aria_live_count > 0
        interactive_present = interactive_present or parser.interactive_count > 0
        analysis_text = text + "\n" + "\n".join(parser.inline_css_chunks)

        if not has_viewport:
            findings.append({
                "id": "missing_viewport_meta",
                "severity": "warning",
                "evidence": "No <meta name=\"viewport\"> tag found for responsive HUD scaling.",
            })
        for line in parser.images_without_alt[:50]:
            findings.append({
                "id": "image_missing_alt",
                "severity": "warning",
                "line": line,
                "evidence": "img element has no alt attribute.",
            })

    has_overlay = bool(_OVERLAY_POS_RE.search(analysis_text))
    has_pointer_passthrough = bool(_POINTER_NONE_RE.search(analysis_text))
    has_user_select_none = bool(_USER_SELECT_NONE_RE.search(analysis_text))
    has_motion = bool(_MOTION_RE.search(analysis_text))
    has_reduced_motion = bool(_REDUCED_MOTION_RE.search(analysis_text))
    has_visible_focus = bool(_FOCUS_STYLE_RE.search(analysis_text))
    has_responsive_hint = bool(_RESPONSIVE_HINT_RE.search(analysis_text))
    has_tabular_nums = bool(_TABULAR_NUMS_RE.search(analysis_text))
    has_text_legibility = bool(_TEXT_LEGIBILITY_RE.search(analysis_text))

    tiny_fonts: list[tuple[int, float]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in _FONT_SIZE_PX_RE.finditer(line):
            size_px = float(match.group(1))
            if size_px < 12.0:
                tiny_fonts.append((line_no, size_px))

    blur_count = len(_BACKDROP_BLUR_RE.findall(analysis_text))

    if has_overlay and not has_pointer_passthrough:
        findings.append({
            "id": "missing_pointer_events_passthrough",
            "severity": "warning",
            "evidence": "Positioned HUD overlay found without pointer-events: none; canvas input/raycasting may be blocked.",
        })

    if (has_overlay or is_html) and not has_user_select_none:
        findings.append({
            "id": "missing_user_select_none",
            "severity": "info",
            "evidence": "No user-select: none rule found; rapid gameplay drags may highlight HUD text.",
        })

    for line_no, size_px in tiny_fonts[:25]:
        findings.append({
            "id": "tiny_hud_font_size",
            "severity": "warning",
            "line": line_no,
            "evidence": f"Font size {size_px:g}px is under 12px; likely illegible in peripheral HUD zones.",
        })

    if has_motion and not has_reduced_motion:
        findings.append({
            "id": "missing_reduced_motion_fallback",
            "severity": "warning",
            "evidence": "Animations/transitions detected without a prefers-reduced-motion fallback.",
        })

    if interactive_present and not has_visible_focus:
        findings.append({
            "id": "missing_visible_focus_style",
            "severity": "warning",
            "evidence": "Interactive controls detected without :focus or :focus-visible styling for keyboard/gamepad nav.",
        })

    if blur_count >= 3:
        findings.append({
            "id": "excessive_backdrop_blur",
            "severity": "warning",
            "evidence": f"Found {blur_count} backdrop blur rules; stacking blurs can degrade WebGL/Three.js frame pacing.",
        })

    return {
        "status": "reviewed",
        "path": str(selected),
        "suffix": suffix,
        "bytes_read": len(raw),
        "findings": findings,
        "signals": {
            "viewport_meta": has_viewport if is_html else None,
            "pointer_events_passthrough_hint": has_pointer_passthrough,
            "user_select_none_hint": has_user_select_none,
            "safe_area_or_responsive_hint": has_responsive_hint,
            "reduced_motion_hint": has_reduced_motion,
            "visible_focus_hint": has_visible_focus,
            "aria_live_hint": has_aria_live,
            "tabular_nums_hint": has_tabular_nums,
            "text_legibility_hint": has_text_legibility,
            "backdrop_blur_count": blur_count,
            "tiny_font_count": len(tiny_fonts),
        },
        "limitations": [
            "Heuristic static source inspection only; external CSS, TypeScript modules, and WebGL scenes are not executed or resolved.",
            "Not a full WCAG or rendered-frame contrast audit; test visually inside the target game viewport.",
        ],
    }
