import shutil
import sys
import time

from statusline import render_statusline

FRAMES = [
    # 1. Hero frame: INSERT + working + accept-edits (green), subagents, yellow context (> 50%) and red Argon 7d quota (< 25%)
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
    # 2. Reviewing artifact in auto mode, artifacts & tasks, Claude Opus 5.5 with yellow 7d quota (< 50%)
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
    # 3. Tool execution in VISUAL + plan mode, artifacts only, red context (> 75%) and red quota (< 25%), Gemini 3.8 Flash
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
    # 4. Minimal idle state (healthy quotas >= 50%, no optional metrics), Claude Sonnet 5.5
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
    cols = shutil.get_terminal_size((100, 2)).columns
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        for i, state in enumerate(FRAMES):
            payload = dict(state, terminal_width=cols)
            rendered = render_statusline(payload).rstrip("\n")
            sys.stdout.write(f"\033[H\033[2J{rendered}")
            sys.stdout.flush()
            if i < len(FRAMES) - 1:
                time.sleep(3.5)
            else:
                time.sleep(4.0)
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
