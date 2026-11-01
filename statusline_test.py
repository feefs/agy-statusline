import unittest

from statusline import (
    ANSI_ESCAPE_RE,
    _align_line,
    _build_top_left_section,
    _build_top_right_section,
    _color_context_gauge,
    _color_quota_gauge,
    _format_agent_state,
    _format_context_metric,
    _format_cycle_mode,
    _format_model_name,
    _format_optional_metrics,
    _format_quota_section,
    _format_token_count,
    _format_usage_gauge,
    _format_vim_mode,
    _visible_width,
    render_statusline,
)


def strip_ansi(s: str) -> str:
    return ANSI_ESCAPE_RE.sub("", s)


class TestStatusline(unittest.TestCase):
    """Direct in-memory unit tests ordered to match displayed statusline flow."""

    # ── Utilities ──

    def test_visible_width(self):
        self.assertEqual(_visible_width("\033[32m● READY\033[0m"), 7)
        self.assertEqual(_visible_width("ctx 3.5k ●○········ 16.5%"), 25)
        self.assertEqual(_visible_width("你好"), 4)

    def test_align_line(self):
        line = _align_line("left", "right", 20)
        self.assertEqual(len(line), 20)
        self.assertEqual(line, "left           right")

    def test_format_usage_gauge(self):
        # 10-bar tests
        self.assertEqual(_format_usage_gauge(0.0, bar_len=10), "··········")
        self.assertEqual(_format_usage_gauge(5.0, bar_len=10), "○·········")
        self.assertEqual(_format_usage_gauge(16.5, bar_len=10), "●○········")
        self.assertEqual(_format_usage_gauge(100.0, bar_len=10), "●●●●●●●●●●")

        # 5-bar quota tests (20% full, 10% half)
        self.assertEqual(_format_usage_gauge(75.0, bar_len=5), "●●●○·")
        self.assertEqual(_format_usage_gauge(85.0, bar_len=5), "●●●●·")
        self.assertEqual(_format_usage_gauge(90.0, bar_len=5), "●●●●○")

    def test_color_context_gauge(self):
        self.assertEqual(_color_context_gauge("●○········", 16.5), "●○········")
        self.assertEqual(_color_context_gauge("●●●●●·····", 50.0), "●●●●●·····")
        self.assertIn("\033[33m", _color_context_gauge("●●●●●●····", 60.0))
        self.assertIn("\033[31m", _color_context_gauge("●●●●●●●●··", 80.0))

    def test_color_quota_gauge(self):
        self.assertEqual(_color_quota_gauge("●●●○·", 75.0), "●●●○·")
        self.assertEqual(_color_quota_gauge("●●○··", 50.0), "●●○··")
        self.assertIn("\033[33m", _color_quota_gauge("●●···", 40.0))
        self.assertIn("\033[31m", _color_quota_gauge("●····", 20.0))

    # ── Line 1 (Top Left): [vim_mode] · agent_state · [cycle_mode] ──

    def test_format_vim_mode(self):
        self.assertEqual(_format_vim_mode(""), "")
        self.assertEqual(_format_vim_mode("NORMAL"), "")
        self.assertEqual(_format_vim_mode("insert"), "-- INSERT --")
        self.assertEqual(_format_vim_mode("visual line"), "-- VISUAL LINE --")

    def test_format_agent_state(self):
        self.assertEqual(strip_ansi(_format_agent_state("idle")), "◇ Idle")
        self.assertEqual(strip_ansi(_format_agent_state("working")), "◈ Working...")
        self.assertEqual(strip_ansi(_format_agent_state("tool_use")), "⚒ Tool")
        self.assertEqual(strip_ansi(_format_agent_state("reviewing")), "⌕ Review")
        self.assertEqual(strip_ansi(_format_agent_state("error")), "⚠︎ Error")
        self.assertEqual(
            strip_ansi(_format_agent_state("custom_state")), "Custom State..."
        )

    def test_format_cycle_mode(self):
        self.assertEqual(_format_cycle_mode(""), "")
        self.assertEqual(_format_cycle_mode("default"), "")
        self.assertEqual(strip_ansi(_format_cycle_mode("accept-edits")), "accept-edits")
        self.assertEqual(strip_ansi(_format_cycle_mode("auto")), "auto")
        self.assertEqual(strip_ansi(_format_cycle_mode("plan")), "plan")

    def test_build_top_left_section(self):
        self.assertEqual(
            strip_ansi(_build_top_left_section("", "◇ Idle", "")), "◇ Idle"
        )
        self.assertEqual(
            strip_ansi(
                _build_top_left_section("-- VISUAL --", "◈ Working...", "auto")
            ),
            "-- VISUAL -- · ◈ Working... · auto",
        )

    # ── Line 1 (Top Right): [optional metrics] · context ──

    def test_format_optional_metrics(self):
        self.assertEqual(_format_optional_metrics(0, 0, 0), [])
        metrics = [strip_ansi(m) for m in _format_optional_metrics(1, 2, 3)]
        self.assertEqual(metrics, ["artifacts 3", "subagents 2", "tasks 1"])

    def test_format_token_count(self):
        # 1 - 999
        self.assertEqual(_format_token_count(0), "0")
        self.assertEqual(_format_token_count(542), "542")
        self.assertEqual(_format_token_count(999), "999")
        # 1,000 - 999,999 (max 1 decimal)
        self.assertEqual(_format_token_count(1_000), "1k")
        self.assertEqual(_format_token_count(1_200), "1.2k")
        self.assertEqual(_format_token_count(3_500), "3.5k")
        self.assertEqual(_format_token_count(10_500), "10.5k")
        self.assertEqual(_format_token_count(192_900), "192.9k")
        # 1,000,000+ (max 2 decimals)
        self.assertEqual(_format_token_count(1_000_000), "1m")
        self.assertEqual(_format_token_count(1_450_000), "1.45m")
        self.assertEqual(_format_token_count(1_500_000), "1.5m")

    def test_format_context_metric(self):
        self.assertEqual(
            strip_ansi(_format_context_metric(16.5, 3500)),
            "ctx 3.5k ●○········ 16.5%",
        )

    def test_build_top_right_section(self):
        opt = ["artifacts 3", "subagents 2", "tasks 1"]
        ctx = "ctx 3.5k ●○········ 16.5%"

        self.assertEqual(
            strip_ansi(_build_top_right_section(opt, ctx, max_width=80)),
            "artifacts 3 · subagents 2 · tasks 1 · ctx 3.5k ●○········ 16.5%",
        )
        # Drop artifacts (full width is 63)
        self.assertEqual(
            strip_ansi(_build_top_right_section(opt, ctx, max_width=62)),
            "subagents 2 · tasks 1 · ctx 3.5k ●○········ 16.5%",
        )
        # Drop artifacts and subagents (2-metric width is 49)
        self.assertEqual(
            strip_ansi(_build_top_right_section(opt, ctx, max_width=48)),
            "tasks 1 · ctx 3.5k ●○········ 16.5%",
        )
        # Drop all optional metrics (1-metric width is 35); context always stays
        self.assertEqual(
            strip_ansi(_build_top_right_section(opt, ctx, max_width=34)),
            "ctx 3.5k ●○········ 16.5%",
        )
        self.assertEqual(
            strip_ansi(_build_top_right_section(opt, ctx, max_width=10)),
            "ctx 3.5k ●○········ 16.5%",
        )

    # ── Line 2 (Bottom Left): model ──

    def test_format_model_name(self):
        self.assertEqual(_format_model_name(""), "")
        self.assertEqual(
            strip_ansi(_format_model_name("Gemini 3.8 Flash (High)")),
            "Gemini 3.8 Flash (High)",
        )

    # ── Line 2 (Bottom Right): quota ──

    def test_format_quota_section(self):
        # Unknown model or missing quota buckets return empty string
        self.assertEqual(
            _format_quota_section("Unknown Model", {"gemini-5h": {}}, max_width=80),
            "",
        )
        self.assertEqual(
            _format_quota_section("Gemini 3.8 Flash (High)", {}, max_width=80),
            "",
        )

        # All healthy (>= 50%): only 5h is shown
        healthy_quota = {
            "3p-5h": {"remaining_fraction": 0.80},
            "3p-weekly": {"remaining_fraction": 0.65},
            "gemini-5h": {"remaining_fraction": 0.75},
            "gemini-weekly": {"remaining_fraction": 0.90},
            "gemini-argon-wtu-weekly": {"remaining_fraction": 0.85},
        }
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 3.8 Flash (High)", healthy_quota, max_width=80
                )
            ),
            "quota (gemini) 5h ●●●○· 75.0%",
        )
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", healthy_quota, max_width=80
                )
            ),
            "quota (gemini) 5h ●●●○· 75.0%",
        )
        self.assertEqual(
            strip_ansi(
                _format_quota_section("Claude 3.7 Sonnet", healthy_quota, max_width=80)
            ),
            "quota (claude/gpt) 5h ●●●●· 80.0%",
        )

        # Argon < 50%, 7d >= 50%: shows 5h and argon 7d (omits 7d)
        argon_low_quota = {
            "gemini-5h": {"remaining_fraction": 0.936},
            "gemini-weekly": {"remaining_fraction": 0.909},
            "gemini-argon-wtu-weekly": {"remaining_fraction": 0.434},
        }
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", argon_low_quota, max_width=80
                )
            ),
            "quota (gemini) 5h ●●●●○ 93.6% argon 7d ●●··· 43.4%",
        )

        # Both 7d < 50% and argon < 50%: shows 5h, 7d, and argon 7d
        both_low_quota = {
            "gemini-5h": {"remaining_fraction": 0.60},
            "gemini-weekly": {"remaining_fraction": 0.40},
            "gemini-argon-wtu-weekly": {"remaining_fraction": 0.20},
        }
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", both_low_quota, max_width=80
                )
            ),
            "quota (gemini) 5h ●●●·· 60.0% 7d ●●··· 40.0% argon 7d ●···· 20.0%",
        )

        # Claude/GPT 7d < 50%: shows 5h and 7d
        claude_low_7d = {
            "3p-5h": {"remaining_fraction": 1.0},
            "3p-weekly": {"remaining_fraction": 0.35},
        }
        self.assertEqual(
            strip_ansi(
                _format_quota_section("Claude 3.7 Sonnet", claude_low_7d, max_width=80)
            ),
            "quota (claude/gpt) 5h ●●●●● 100.0% 7d ●○··· 35.0%",
        )

        # Narrow width filtering: drops highest quota items one by one, keeping original order
        # Full 3-item string has width 65; 2-item string has width 50; 1-item string has width 35
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", both_low_quota, max_width=64
                )
            ),
            "quota (gemini) 7d ●●··· 40.0% argon 7d ●···· 20.0%",
        )
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", both_low_quota, max_width=49
                )
            ),
            "quota (gemini) argon 7d ●···· 20.0%",
        )
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", both_low_quota, max_width=10
                )
            ),
            "quota (gemini) argon 7d ●···· 20.0%",
        )

        # When 5h is lowest (15%) and 7d is highest (40%), drops 7d first then argon 7d (30%)
        low_5h_quota = {
            "gemini-5h": {"remaining_fraction": 0.15},
            "gemini-weekly": {"remaining_fraction": 0.40},
            "gemini-argon-wtu-weekly": {"remaining_fraction": 0.30},
        }
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", low_5h_quota, max_width=64
                )
            ),
            "quota (gemini) 5h ○···· 15.0% argon 7d ●○··· 30.0%",
        )
        self.assertEqual(
            strip_ansi(
                _format_quota_section(
                    "Gemini 4 Argon (High)", low_5h_quota, max_width=49
                )
            ),
            "quota (gemini) 5h ○···· 15.0%",
        )

    # ── Render Statusline ──

    def test_render_statusline_mockup_example(self):
        payload = {
            "vim": {"mode": "VISUAL"},
            "agent_state": "working",
            "cycle_mode": "auto",
            "model": {"display_name": "Gemini 3.8 Flash (High)"},
            "artifact_count": 3,
            "subagents": [{"id": "1"}, {"id": "2"}],
            "task_count": 1,
            "context_window": {
                "total_input_tokens": 3500,
                "used_percentage": 16.5,
            },
            "quota": {
                "gemini-5h": {"remaining_fraction": 0.75},
                "gemini-weekly": {"remaining_fraction": 0.45},
            },
            "terminal_width": 115,
        }
        output = strip_ansi(render_statusline(payload))
        lines = output.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("-- VISUAL -- · ◈ Working... · auto"))
        self.assertTrue(
            lines[0].endswith(
                "artifacts 3 · subagents 2 · tasks 1 · ctx 3.5k ●○········ 16.5%"
            )
        )
        self.assertTrue(lines[1].startswith("Gemini 3.8 Flash (High)"))
        self.assertTrue(
            lines[1].endswith("quota (gemini) 5h ●●●○· 75.0% 7d ●●··· 45.0%")
        )

    def test_render_statusline_minimal_payload(self):
        payload = {
            "agent_state": "idle",
            "model": {"display_name": "Gemini 4 Argon (High)"},
            "context_window": {
                "total_input_tokens": 178976,
                "used_percentage": 17.1,
            },
            "quota": {
                "gemini-5h": {"remaining_fraction": 0.926},
                "gemini-weekly": {"remaining_fraction": 0.907},
                "gemini-argon-wtu-weekly": {"remaining_fraction": 0.434},
            },
            "terminal_width": 100,
        }
        output = strip_ansi(render_statusline(payload))
        lines = output.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            "◇ Idle                                                                     ctx 179k ●○········ 17.1%",
        )
        self.assertEqual(
            lines[1],
            "Gemini 4 Argon (High)                             quota (gemini) 5h ●●●●○ 92.6% argon 7d ●●··· 43.4%",
        )

    def test_render_statusline_narrow_terminal(self):
        payload = {
            "vim": {"mode": "VISUAL"},
            "agent_state": "working",
            "cycle_mode": "auto",
            "model": {"display_name": "Gemini 4 Argon (High)"},
            "artifact_count": 3,
            "subagents": [{"id": "1"}, {"id": "2"}],
            "task_count": 1,
            "context_window": {
                "total_input_tokens": 3500,
                "used_percentage": 16.5,
            },
            "quota": {
                "gemini-5h": {"remaining_fraction": 0.60},
                "gemini-weekly": {"remaining_fraction": 0.40},
                "gemini-argon-wtu-weekly": {"remaining_fraction": 0.20},
            },
            # Width 75:
            # Line 1 left is 34 -> max_width 40 -> keeps only "tasks 1 · ctx ..." (width 35)
            # Line 2 left is 21 -> max_width 53 -> drops 5h (60%), keeps "7d ... argon 7d ..." (width 50)
            "terminal_width": 75,
        }
        lines = strip_ansi(render_statusline(payload)).splitlines()
        self.assertEqual(
            lines[0],
            "-- VISUAL -- · ◈ Working... · auto      tasks 1 · ctx 3.5k ●○········ 16.5%",
        )
        self.assertEqual(
            lines[1],
            "Gemini 4 Argon (High)    quota (gemini) 7d ●●··· 40.0% argon 7d ●···· 20.0%",
        )

        # Width 60:
        # Line 1 left is 34 -> max_width 25 -> drops all optional metrics, keeps only "ctx ..." (width 25)
        # Line 2 left is 21 -> max_width 38 -> drops 5h and 7d, keeps only "argon 7d ..." (width 35)
        payload["terminal_width"] = 60
        lines = strip_ansi(render_statusline(payload)).splitlines()
        self.assertEqual(
            lines[0],
            "-- VISUAL -- · ◈ Working... · auto ctx 3.5k ●○········ 16.5%",
        )
        self.assertEqual(
            lines[1],
            "Gemini 4 Argon (High)    quota (gemini) argon 7d ●···· 20.0%",
        )


if __name__ == "__main__":
    unittest.main()
