import json
import re
import sys
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEBUG_MODE = False
DEBUG_LOG = Path(__file__).with_name("statusline_debug.log")

### ANSI Styles ###
RESET = "\033[0m"
DIM = "\033[2m"

FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_WHITE = "\033[37m"

NUM_COLOR = FG_WHITE
DOT = f"{DIM}·{RESET}"
DOT_SEP = f" {DOT} "

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


### Utilities ###


def _visible_width(s: str) -> int:
    """Calculates the visible width of a string in terminal cells."""
    clean = ANSI_ESCAPE_RE.sub("", s)
    width = 0
    for ch in clean:
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        elif unicodedata.category(ch) != "Mn":
            width += 1
    return width


def _align_line(left: str, right: str, terminal_width: int) -> str:
    """Aligns left and right text across the line."""
    v_left = _visible_width(left)
    v_right = _visible_width(right)
    pad = max(1, terminal_width - v_left - v_right)
    return f"{left}{' ' * pad}{right}"


def _format_usage_gauge(pct: float, bar_len: int) -> str:
    """Formats a usage gauge using ● for full, ○ for half, and · for empty."""
    step = 100.0 / bar_len
    half_step = step / 2.0

    bar = []
    for i in range(bar_len):
        slot = i * step
        if pct >= slot + step:
            bar.append("●")
        elif pct >= slot + half_step:
            bar.append("○")
        else:
            bar.append("·")

    return "".join(bar)


def _color_context_gauge(gauge: str, used_pct: float) -> str:
    """Colors a context gauge based on used percentage."""
    if used_pct > 75.0:
        return f"{FG_RED}{gauge}{RESET}"
    if used_pct > 50.0:
        return f"{FG_YELLOW}{gauge}{RESET}"
    return gauge


def _color_quota_gauge(gauge: str, rem_pct: float) -> str:
    """Colors a quota gauge based on remaining percentage."""
    if rem_pct < 25.0:
        return f"{FG_RED}{gauge}{RESET}"
    if rem_pct < 50.0:
        return f"{FG_YELLOW}{gauge}{RESET}"
    return gauge


### Line 1 (Top Left): [vim_mode] · agent_state · [cycle_mode] ###


def _format_vim_mode(mode: str) -> str:
    """Formats the vim mode indicator."""
    mode_clean = mode.strip().upper()
    if mode_clean in ("", "NORMAL"):
        return ""
    return f"-- {mode_clean} --"


def _format_agent_state(state: str) -> str:
    """Formats the agent state indicator."""
    state_map = {
        "idle": f"{DIM}◇ Idle{RESET}",
        "working": f"{FG_BLUE}◈ Working...{RESET}",
        "tool_use": f"{FG_YELLOW}⚒ Tool{RESET}",
        "reviewing": f"{FG_YELLOW}⌕ Review{RESET}",
        "error": f"{FG_RED}⚠︎ Error{RESET}",
    }
    if state in state_map:
        return state_map[state]
    return f"{DIM}{state.replace('_', ' ').title()}...{RESET}"


def _format_cycle_mode(cycle_mode: str) -> str:
    """Formats the cycle mode indicator."""
    mode_clean = cycle_mode.strip().lower()
    mode_colors = {
        "accept-edits": FG_GREEN,
        "auto": FG_YELLOW,
        "plan": FG_BLUE,
    }
    if mode_clean in mode_colors:
        return f"{mode_colors[mode_clean]}{mode_clean}{RESET}"
    return ""


def _build_top_left_section(
    vim_mode: str,
    agent_state: str,
    cycle_mode: str,
) -> str:
    """Builds the top-left section from active indicators."""
    parts = []
    if vim_mode:
        parts.append(vim_mode)
    if agent_state:
        parts.append(agent_state)
    if cycle_mode:
        parts.append(cycle_mode)
    return DOT_SEP.join(parts)


### Line 1 (Top Right): [optional_metrics] · context ###


def _format_optional_metrics(tasks: int, subagents: int, artifacts: int) -> list[str]:
    """Formats optional metric indicators, displaying them only if nonzero."""
    metrics = []
    if artifacts > 0:
        metrics.append(f"{DIM}artifacts{RESET} {NUM_COLOR}{artifacts}{RESET}")
    if subagents > 0:
        metrics.append(f"{DIM}subagents{RESET} {NUM_COLOR}{subagents}{RESET}")
    if tasks > 0:
        metrics.append(f"{DIM}tasks{RESET} {NUM_COLOR}{tasks}{RESET}")
    return metrics


def _format_token_count(tokens: int) -> str:
    """Formats token count: 1-999 as-is, 1k-999.9k (max 1 decimal), 1M+ (max 2 decimals)."""
    if tokens >= 999_950:
        s = f"{tokens / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{s}M"
    if tokens >= 1_000:
        s = f"{tokens / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(tokens)


def _format_context_metric(used_pct: float, total_tokens: int) -> str:
    """Formats the context window metric (token count, gauge, percentage)."""
    bar = _color_context_gauge(_format_usage_gauge(used_pct, bar_len=10), used_pct)
    tokens_fmt = _format_token_count(total_tokens)
    pct_fmt = f"{used_pct:.1f}%"
    return f"{DIM}ctx{RESET} {NUM_COLOR}{tokens_fmt}{RESET} {bar} {NUM_COLOR}{pct_fmt}{RESET}"


def _build_top_right_section(
    optional_metrics: list[str],
    context_metric: str,
    max_width: int,
) -> str:
    """Builds the top-right section, dropping optional metrics to fit max_width cells."""
    # Prepend optional metrics right-to-left until max_width is reached
    res = context_metric
    used_width = _visible_width(res)
    sep_width = _visible_width(DOT_SEP)

    for metric in reversed(optional_metrics):
        next_width = used_width + sep_width + _visible_width(metric)
        if next_width > max_width:
            break
        res = f"{metric}{DOT_SEP}{res}"
        used_width = next_width

    return res


### Line 2 (Bottom Left): model ###


def _format_model_name(model_name: str) -> str:
    """Formats the model name."""
    if not model_name:
        return ""
    return f"{DIM}{model_name}{RESET}"


### Line 2 (Bottom Right): quota ###


def _format_quota_section(
    model_name: str,
    quota_data: Mapping[str, Any],
    max_width: int,
) -> str:
    """Formats the model quota section, dropping highest quotas to fit max_width cells."""
    # Determine quota label and bucket keys from the model name
    model_lower = model_name.lower()
    if "gemini" in model_lower:
        quota_label = "gemini"
        key_5h = "gemini-5h"
        key_7d = "gemini-weekly"
    elif "claude" in model_lower or "gpt" in model_lower:
        quota_label = "claude/gpt"
        key_5h = "3p-5h"
        key_7d = "3p-weekly"
    else:
        return ""

    b_5h = quota_data.get(key_5h) or {}
    b_7d = quota_data.get(key_7d) or {}
    if not b_5h and not b_7d:
        return ""

    # Collect active quota buckets (always 5h; 7d and argon 7d only if < 50%)
    rem_5h = float(b_5h.get("remaining_fraction") or 0.0) * 100.0
    bar_5h = _color_quota_gauge(_format_usage_gauge(rem_5h, bar_len=5), rem_5h)
    items = [(rem_5h, f"{DIM}5h{RESET} {bar_5h} {NUM_COLOR}{rem_5h:.1f}%{RESET}")]

    if b_7d:
        rem_7d = float(b_7d.get("remaining_fraction") or 0.0) * 100.0
        if rem_7d < 50.0:
            bar_7d = _color_quota_gauge(_format_usage_gauge(rem_7d, bar_len=5), rem_7d)
            items.append(
                (rem_7d, f"{DIM}7d{RESET} {bar_7d} {NUM_COLOR}{rem_7d:.1f}%{RESET}")
            )

    if "gemini 4 argon" in model_lower:
        b_argon = quota_data.get("gemini-argon-wtu-weekly")
        if b_argon:
            rem_argon = float(b_argon.get("remaining_fraction") or 0.0) * 100.0
            if rem_argon < 50.0:
                bar_argon = _color_quota_gauge(
                    _format_usage_gauge(rem_argon, bar_len=5), rem_argon
                )
                items.append(
                    (
                        rem_argon,
                        f"{DIM}argon 7d{RESET} {bar_argon} {NUM_COLOR}{rem_argon:.1f}%{RESET}",
                    )
                )

    # Iteratively remove the highest-percentage quota until the section fits
    prefix = f"{DIM}quota ({quota_label}){RESET}"
    used_width = _visible_width(prefix)
    for _, text in items:
        used_width += 1 + _visible_width(text)

    while len(items) > 1 and used_width > max_width:
        max_idx = 0
        for i in range(1, len(items)):
            if items[i][0] >= items[max_idx][0]:
                max_idx = i
        _, removed_text = items.pop(max_idx)
        used_width -= 1 + _visible_width(removed_text)

    parts = [prefix]
    for _, text in items:
        parts.append(text)
    return " ".join(parts)


### Render Status Line ###


def render_statusline(data: Mapping[str, Any]) -> str:
    """Renders the status line from the session state."""
    terminal_width = data.get("terminal_width") or 80
    vim_mode = _format_vim_mode((data.get("vim") or {}).get("mode") or "")
    model_name = (data.get("model") or {}).get("display_name") or ""

    ctx_obj = data.get("context_window") or {}
    used_pct = float(ctx_obj.get("used_percentage") or 0.0)
    total_tokens = int(ctx_obj.get("total_input_tokens") or 0)

    optional_metrics = _format_optional_metrics(
        tasks=data.get("task_count") or 0,
        subagents=len(data.get("subagents") or []),
        artifacts=data.get("artifact_count") or 0,
    )

    top_left = _build_top_left_section(
        vim_mode,
        _format_agent_state(data.get("agent_state") or "idle"),
        _format_cycle_mode(data.get("cycle_mode") or ""),
    )
    top_right_max_width = terminal_width - _visible_width(top_left) - 1
    top_right = _build_top_right_section(
        optional_metrics,
        _format_context_metric(used_pct, total_tokens),
        max_width=top_right_max_width,
    )

    bottom_left = _format_model_name(model_name)
    bottom_right_max_width = terminal_width - _visible_width(bottom_left) - 1
    bottom_right = _format_quota_section(
        model_name,
        data.get("quota") or {},
        max_width=bottom_right_max_width,
    )

    line1 = _align_line(top_left, top_right, terminal_width)
    line2 = _align_line(bottom_left, bottom_right, terminal_width)
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
