import shutil
import sys
import time

from statusline import render_statusline

FRAMES = [
    # Frame 1: Hero frame with INSERT mode, working state, accept-edits (green),
    # subagents, yellow context (> 50%), and red Argon 7d quota (< 25%).
    {
        "vim": {"mode": "INSERT"},
        "agent_state": "working",
        "cycle_mode": "accept-edits",
        "model": {"display_name": "Gemini 4 Argon (High)"},
        "artifact_count": 0,
        "subagents": [{"id": "1"}, {"id": "2"}],
        "task_count": 0,
        "context_window": {
            "total_input_tokens": 582000,
            "used_percentage": 55.5,
        },
        "quota": {
            "gemini-5h": {"remaining_fraction": 0.840},
            "gemini-weekly": {"remaining_fraction": 0.910},
            "gemini-argon-wtu-weekly": {"remaining_fraction": 0.200},
        },
    },
    # Frame 2: Reviewing state in auto mode, artifacts & tasks, and yellow
    # 7d quota (< 50%).
    {
        "vim": {"mode": "NORMAL"},
        "agent_state": "reviewing",
        "cycle_mode": "auto",
        "model": {"display_name": "Claude Opus 5.5 (Medium)"},
        "artifact_count": 3,
        "subagents": [],
        "task_count": 1,
        "context_window": {
            "total_input_tokens": 284500,
            "used_percentage": 27.1,
        },
        "quota": {
            "3p-5h": {"remaining_fraction": 0.750},
            "3p-weekly": {"remaining_fraction": 0.350},
        },
    },
    # Frame 3: Tool execution in VISUAL and plan mode, artifacts only,
    # red context (> 75%), and red 5h quota (< 25%).
    {
        "vim": {"mode": "VISUAL"},
        "agent_state": "tool_use",
        "cycle_mode": "plan",
        "model": {"display_name": "Gemini 3.8 Flash (Low)"},
        "artifact_count": 1,
        "subagents": [],
        "task_count": 0,
        "context_window": {
            "total_input_tokens": 825000,
            "used_percentage": 78.7,
        },
        "quota": {
            "gemini-5h": {"remaining_fraction": 0.200},
            "gemini-weekly": {"remaining_fraction": 0.850},
        },
    },
    # Frame 4: Minimal idle state with healthy quotas (>= 50%) and no
    # optional metrics.
    {
        "vim": {"mode": "NORMAL"},
        "agent_state": "idle",
        "cycle_mode": "default",
        "model": {"display_name": "Claude Sonnet 5.5 (High)"},
        "artifact_count": 0,
        "subagents": [],
        "task_count": 0,
        "context_window": {
            "total_input_tokens": 123587,
            "used_percentage": 11.8,
        },
        "quota": {
            "3p-5h": {"remaining_fraction": 0.951},
            "3p-weekly": {"remaining_fraction": 0.984},
        },
    },
]


def main() -> None:
    terminal_width = shutil.get_terminal_size((100, 2)).columns
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        for i, state in enumerate(FRAMES):
            payload = dict(state, terminal_width=terminal_width)
            rendered = render_statusline(payload).rstrip("\n")
            sys.stdout.write(f"\033[H\033[2J{rendered}")
            sys.stdout.flush()
            # Sleep 3.0s per frame, with an extra buffer on the final frame so the
            # script doesn't exit to the shell prompt before statusline.tape finishes.
            if i < len(FRAMES) - 1:
                time.sleep(3.0)
            else:
                time.sleep(3.5)
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
