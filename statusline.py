import json
import re
import sys
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEBUG_MODE = False
DEBUG_LOG = Path(__file__).with_name("statusline_debug.log")

### ANSI Helpers ###
R = "\033[0m"
D = "\033[2m"

FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_WHITE = "\033[37m"

NUM_COLOR = FG_WHITE
DOT = f"{D}·{R}"
DOT_SEP = f" {DOT} "

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


### Utilities ###


def _visible_width(s: str) -> int:
    """Calculate the printable width of a string in terminal cells."""
    clean = ANSI_ESCAPE_RE.sub("", s)
    width = 0
    for ch in clean:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        else:
            width += 1
    return width


def _align_line(left: str, right: str, total_width: int) -> str:
    """Aligns 'left' to the left margin and 'right' to the right margin."""
    v_left = _visible_width(left)
    v_right = _visible_width(right)
    pad = total_width - v_left - v_right
    if pad > 0:
        return f"{left}{' ' * pad}{right}"
    return f"{left} {right}"


def _format_usage_gauge(
    pct: float,
    bar_len: int = 10,
    health_pct: float | None = None,
) -> str:
    """Renders a usage gauge using ● for full, ○ for half, and · for empty."""
    step = 100.0 / bar_len
    half_step = step / 2.0

    check_pct = pct if health_pct is None else health_pct
    if check_pct < 25.0:
        color = FG_RED
    elif check_pct < 50.0:
        color = FG_YELLOW
    else:
        color = ""

    bar = []
    for i in range(bar_len):
        slot = i * step
        if pct >= slot + step:
            bar.append("●")
        elif pct >= slot + half_step:
            bar.append("○")
        else:
            bar.append("·")

    rendered = "".join(bar)
    if color:
        return f"{color}{rendered}{R}"
    return rendered


### Line 1 (Top Left): [vim_mode] · agent_state · [cycle_mode] ###


def _format_vim_mode(mode: str) -> str:
    """Returns styled vim mode indicator, or empty string for NORMAL/unspecified."""
    mode_clean = mode.strip().upper()
    if mode_clean in ("", "NORMAL"):
        return ""
    return f"-- {mode_clean} --"


def _format_agent_state(state: str) -> str:
    state_map = {
        "idle": f"{D}◇ Idle{R}",
        "working": f"{FG_BLUE}◈ Working...{R}",
        "tool_use": f"{FG_YELLOW}⚒ Tool{R}",
        "error": f"{FG_RED}⚠︎ Error{R}",
    }
    return state_map.get(state, f"{D}{state.replace('_', ' ').title()}...{R}")


def _format_cycle_mode(cycle_mode: str | None) -> str:
    """Formats the cycle_mode badge, or empty string for default/unspecified."""
    if not cycle_mode:
        return ""
    mode_clean = cycle_mode.strip().lower()
    mode_colors = {
        "accept-edits": FG_GREEN,
        "auto": FG_YELLOW,
        "plan": FG_BLUE,
    }
    if mode_clean in mode_colors:
        return f"{mode_colors[mode_clean]}{mode_clean}{R}"
    return ""


def _build_left_section(
    vim_badge: str,
    agent_state: str,
    cycle_mode_badge: str,
) -> str:
    parts = []
    if vim_badge:
        parts.append(vim_badge)
    if agent_state:
        parts.append(agent_state)
    if cycle_mode_badge:
        parts.append(cycle_mode_badge)
    return DOT_SEP.join(parts)


### Line 1 (Top Right): [optional metrics] · context ###


def _format_optional_metrics(tasks: int, subagents: int, artifacts: int) -> list[str]:
    metrics = []
    if artifacts > 0:
        metrics.append(f"{D}artifacts{R} {NUM_COLOR}{artifacts}{R}")
    if subagents > 0:
        metrics.append(f"{D}subagents{R} {NUM_COLOR}{subagents}{R}")
    if tasks > 0:
        metrics.append(f"{D}tasks{R} {NUM_COLOR}{tasks}{R}")
    return metrics


def _format_token_count(tokens: int) -> str:
    """Formats token count: 1-999 as-is, 1k-999.9k (max 1 dec), 1m+ (max 2 dec)."""
    if tokens >= 1_000_000:
        s = f"{tokens / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{s}m"
    if tokens >= 1_000:
        s = f"{tokens / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(tokens)


def _format_context_metric(used_pct: float, total_tokens: int = 0) -> str:
    """Formats the context gauge, token count, and percentage string."""
    remaining_pct = 100.0 - used_pct
    bar = _format_usage_gauge(used_pct, bar_len=10, health_pct=remaining_pct)
    tokens_fmt = _format_token_count(total_tokens)
    pct_fmt = f"{used_pct:.1f}%"
    return f"{D}ctx{R} {NUM_COLOR}{tokens_fmt}{R} {bar} {NUM_COLOR}{pct_fmt}{R}"


def _build_right_section(
    optional_metrics: list[str],
    context_metric: str,
) -> str:
    return DOT_SEP.join(optional_metrics + [context_metric])


### Line 2 (Bottom Left): model ###


def _format_model_name(model_name: str) -> str:
    if not model_name:
        return ""
    return f"{D}{model_name}{R}"


### Line 2 (Bottom Right): quota ###


def _format_quota_section(model_name: str, quota_data: Mapping[str, Any] | None) -> str:
    """Formats the quota section based on model pool (gemini or claude/gpt)."""
    if not quota_data:
        return ""

    model_lower = model_name.lower()
    if "gemini" in model_lower:
        pool_label = "gemini"
        key_5h = "gemini-5h"
        key_7d = "gemini-weekly"
    elif "claude" in model_lower or "gpt" in model_lower:
        pool_label = "claude/gpt"
        key_5h = "3p-5h"
        key_7d = "3p-weekly"
    else:
        return ""

    b_5h = quota_data.get(key_5h) or {}
    b_7d = quota_data.get(key_7d) or {}
    if not b_5h and not b_7d:
        return ""

    rem_5h = float(b_5h.get("remaining_fraction", 0.0)) * 100.0
    bar_5h = _format_usage_gauge(rem_5h, bar_len=5, health_pct=rem_5h)
    res = f"{D}quota ({pool_label}) 5h{R} {bar_5h} {NUM_COLOR}{rem_5h:.1f}%{R}"

    if b_7d:
        rem_7d = float(b_7d.get("remaining_fraction", 0.0)) * 100.0
        if rem_7d < 50.0:
            bar_7d = _format_usage_gauge(rem_7d, bar_len=5, health_pct=rem_7d)
            res += f" {D}7d{R} {bar_7d} {NUM_COLOR}{rem_7d:.1f}%{R}"

    if "gemini 4 argon" in model_lower:
        b_argon = quota_data.get("gemini-argon-wtu-weekly")
        if b_argon:
            rem_argon = float(b_argon.get("remaining_fraction", 0.0)) * 100.0
            if rem_argon < 50.0:
                bar_argon = _format_usage_gauge(
                    rem_argon, bar_len=5, health_pct=rem_argon
                )
                res += f" {D}argon 7d{R} {bar_argon} {NUM_COLOR}{rem_argon:.1f}%{R}"

    return res


### Render Statusline ###


def render_statusline(data: Mapping[str, Any]) -> str:
    """Pure rendering function converting session telemetry dictionary to statusline string."""
    cols = data.get("terminal_width", 80)
    vim_badge = _format_vim_mode((data.get("vim") or {}).get("mode", ""))
    model_name = (data.get("model") or {}).get("display_name", "")

    ctx_obj = data.get("context_window") or {}
    used_pct = float(ctx_obj.get("used_percentage", 0.0))
    total_tokens = int(ctx_obj.get("total_input_tokens", 0))

    optional_metrics = _format_optional_metrics(
        tasks=data.get("task_count", 0),
        subagents=len(data.get("subagents") or []),
        artifacts=data.get("artifact_count", 0),
    )

    top_left = _build_left_section(
        vim_badge,
        _format_agent_state(data.get("agent_state", "idle")),
        _format_cycle_mode(data.get("cycle_mode")),
    )
    top_right = _build_right_section(
        optional_metrics,
        _format_context_metric(used_pct, total_tokens),
    )

    bottom_left = _format_model_name(model_name)
    bottom_right = _format_quota_section(model_name, data.get("quota"))

    line1 = _align_line(top_left, top_right, cols)
    line2 = _align_line(bottom_left, bottom_right, cols)
    return f"{line1}\n{line2}\n"


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}

    if DEBUG_MODE and data:
        with DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2) + "\n\n")

    sys.stdout.write(render_statusline(data))


if __name__ == "__main__":
    main()
