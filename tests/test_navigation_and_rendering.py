import io
import unittest

from rich.console import Console
from textual.widgets import RichLog

from pathfinder_cli.app import (
    ATTENTION_ITEMS,
    COMMAND_HELP,
    HOME_ACTIONS,
    INVESTIGATION_CASES,
    MODULES,
    PROCESSING_SPINNER_FRAMES,
    ConversationEntry,
    PathfinderPrototypeApp,
)
from pathfinder_cli.theme import PALETTE


class _DummyInput:
    def __init__(self, value: str) -> None:
        self.value = value
        self.disabled = False

    def focus(self) -> None:
        return None


class _DummyKeyEvent:
    def __init__(self, key: str) -> None:
        self.key = key
        self.prevented = False
        self.stopped = False

    def prevent_default(self) -> None:
        self.prevented = True

    def stop(self) -> None:
        self.stopped = True


class _DummyStatic:
    def __init__(self) -> None:
        self.value = None

    def update(self, value) -> None:
        self.value = value


def _renderables_to_text(renderables: list[object], width: int = 140) -> str:
    console = Console(record=True, file=io.StringIO(), width=width, color_system=None, force_terminal=False)
    for renderable in renderables:
        console.print(renderable)
    return console.export_text(styles=False)


class ProcessPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_status_render_happens_after_processing_clears(self) -> None:
        app = PathfinderPrototypeApp()
        dummy_input = _DummyInput("")
        render_states: list[bool] = []

        app.query_one = lambda *args, **kwargs: dummy_input  # type: ignore[method-assign]
        app._mark_updated = lambda: None  # type: ignore[method-assign]
        app._refresh_chrome = lambda: None  # type: ignore[method-assign]

        async def _noop_animate_processing() -> None:
            return None

        app._animate_processing = _noop_animate_processing  # type: ignore[method-assign]

        def _record_render() -> None:
            render_states.append(app.processing)

        app._render_current_module = _record_render  # type: ignore[method-assign]

        await app._process_prompt("show me the agent status")

        self.assertGreaterEqual(len(render_states), 1)
        self.assertFalse(render_states[-1])
        self.assertFalse(app.processing)

    async def test_story_scope_selection_shows_resolving_then_planning(self) -> None:
        app = PathfinderPrototypeApp()
        dummy_input = _DummyInput("")
        messages: list[str] = []
        callback_called = {"count": 0}

        app.query_one = lambda *args, **kwargs: dummy_input  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        async def _fake_animate_processing(*args, **kwargs) -> None:
            messages.append(app.processing_message)

        app._animate_processing = _fake_animate_processing  # type: ignore[method-assign]

        def _callback() -> None:
            callback_called["count"] += 1

        await app._perform_selection_action("Resolving scope...", _callback)

        self.assertEqual(messages[:2], ["Resolving scope...", "Planning next step..."])
        self.assertEqual(callback_called["count"], 1)
        self.assertFalse(app.processing)

    async def test_natural_language_demo_prompts_open_visual_story_screens(self) -> None:
        app = PathfinderPrototypeApp()
        dummy_input = _DummyInput("")
        prompts = (
            (
                "show me where privileged activity has been spiking this week across identity, policy, connector, and response signals",
                "story_demo_activity_heatmap",
            ),
            (
                "break down today’s privileged access review queue by correlated risk, watch items, and stale approvals",
                "story_demo_queue_breakdown",
            ),
            (
                "map the full reachable privilege path for svc-backup-ops into production admin access, including the live session and approval mismatch",
                "story_demo_privilege_graph",
            ),
        )

        app.query_one = lambda *args, **kwargs: dummy_input  # type: ignore[method-assign]
        app._mark_updated = lambda: None  # type: ignore[method-assign]
        app._refresh_chrome = lambda: None  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        async def _noop_animate_processing(*args, **kwargs) -> None:
            return None

        app._animate_processing = _noop_animate_processing  # type: ignore[method-assign]

        for prompt, expected_scene in prompts:
            with self.subTest(prompt=prompt):
                await app._process_prompt(prompt)

                self.assertEqual(app.detail_view_key, expected_scene)
                self.assertTrue(app.detail_navigation_active)
                self.assertEqual(app.histories["pathfinder"][-1].kind, "story_scene")
                self.assertEqual(app.histories["pathfinder"][-1].action_key, expected_scene)


class MountBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_dashboard_opens_at_top_of_main_log(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)

        self.assertEqual(log.scroll_offset.y, 0)

    async def test_session_relatedness_scene_opens_at_top_of_log(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            app.detail_view_key = "story_session_relatedness"
            app._render_current_module()
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)

        self.assertEqual(log.scroll_offset.y, 0)

    async def test_session_relatedness_processing_does_not_force_scroll_to_top(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            app.detail_view_key = "story_session_relatedness"
            app._render_current_module()
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)
            log.scroll_end(animate=False, force=True, immediate=True)
            await pilot.pause()
            bottom_offset = log.scroll_offset.y

            app.processing = True
            app.processing_message = "Reviewing affected assets..."
            app._render_current_module()
            await pilot.pause()
            app.processing = False
            app.processing_message = ""

        self.assertGreater(bottom_offset, 0)
        self.assertNotEqual(log.scroll_offset.y, 0)

    async def test_affected_assets_scene_opens_at_bottom_of_log(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            app.detail_navigation_active = True
            app.detail_view_key = "story_assets"
            app._render_current_module()
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)

        self.assertTrue(log.is_vertical_scroll_end)

    async def test_initial_home_dashboard_keeps_only_overview_and_actions(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)
            text_output = "\n".join(line.text for line in log.lines)

        self.assertIn("Overview", text_output)
        self.assertIn("Actionable items", text_output)
        self.assertNotIn("Pathfinder Platform Overview", text_output)
        self.assertNotIn("Operational signals", text_output)
        self.assertNotIn("Access mix", text_output)
        self.assertNotIn("Activity heat map", text_output)
        self.assertNotIn("Analyst options", text_output)

    async def test_app_command_renders_only_the_app_list(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            app._handle_module_command("/app")
            app._render_current_module()
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)
            text_output = "\n".join(line.text for line in log.lines)

        self.assertIn("App picker", text_output)
        self.assertIn("1. Privileged Remote Access", text_output)
        self.assertIn("7. Remote Support", text_output)
        self.assertNotIn("Overview", text_output)
        self.assertNotIn("Actionable items", text_output)
        self.assertNotIn("Which app should I open?", text_output)
        self.assertNotIn("Highlighted app preview", text_output)
        self.assertNotIn("Analyst lens", text_output)

    async def test_pressing_enter_in_app_picker_switches_to_selected_app_dashboard(self) -> None:
        app = PathfinderPrototypeApp()

        async def _noop_animate_processing(*args, **kwargs) -> None:
            return None

        app._animate_processing = _noop_animate_processing  # type: ignore[method-assign]

        async with app.run_test() as pilot:
            app._handle_module_command("/app")
            app.module_picker_index = 1
            app._render_current_module()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)
            text_output = "\n".join(line.text for line in log.lines)

        self.assertEqual(app._active_module().key, "password_safe")
        self.assertIn("Password Safe Overview", text_output)
        self.assertNotIn("App picker", text_output)


class NavigationAndRenderingTests(unittest.TestCase):
    def test_idle_startup_spinner_uses_dots14_frames(self) -> None:
        app = PathfinderPrototypeApp()
        widgets = {
            "#top-title": _DummyStatic(),
            "#top-meta": _DummyStatic(),
            "#typing-indicator": _DummyStatic(),
            "#command-hint": _DummyStatic(),
            "#session-status": _DummyStatic(),
        }
        app.query_one = lambda selector, *args, **kwargs: widgets[selector]  # type: ignore[method-assign]

        app.processing = False
        app.chrome_tick = 0
        app._refresh_chrome()

        typing_indicator = widgets["#typing-indicator"].value
        self.assertIn(typing_indicator.plain, PROCESSING_SPINNER_FRAMES)
        self.assertNotIn(typing_indicator.plain, {">", "|", "/", "\\"})
        self.assertIn("/help", widgets["#command-hint"].value.plain)
        self.assertIn("Use /help when you have questions", widgets["#command-hint"].value.plain)

    def test_enter_activates_selection_when_navigation_is_active_and_input_is_empty(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_navigation_active = True
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]

        activated = {"called": False}

        def _activate() -> None:
            activated["called"] = True

        app.action_activate_selection = _activate  # type: ignore[method-assign]
        event = _DummyKeyEvent("enter")

        app.on_key(event)

        self.assertTrue(activated["called"])
        self.assertTrue(event.prevented)
        self.assertTrue(event.stopped)

    def test_enter_does_not_activate_selection_when_input_has_text(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_navigation_active = True
        app.query_one = lambda *args, **kwargs: _DummyInput("show me more")  # type: ignore[method-assign]

        activated = {"called": False}

        def _activate() -> None:
            activated["called"] = True

        app.action_activate_selection = _activate  # type: ignore[method-assign]
        event = _DummyKeyEvent("enter")

        app.on_key(event)

        self.assertFalse(activated["called"])
        self.assertFalse(event.prevented)
        self.assertFalse(event.stopped)

    def test_home_actions_no_longer_include_scene_shortcuts(self) -> None:
        self.assertEqual([action.key for action in HOME_ACTIONS], [
            "true_privilege_graph",
            "live_session_queue",
            "pending_approvals",
        ])

    def test_home_selection_only_covers_visible_actionable_items(self) -> None:
        app = PathfinderPrototypeApp()
        app.home_navigation_active = True
        app.home_selection_index = len(ATTENTION_ITEMS)

        self.assertEqual(app._home_selection_count(), len(ATTENTION_ITEMS))
        self.assertIsNone(app._selected_action_index())

    def test_true_privilege_graph_render_shows_catalog_before_graph(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "true_privilege_graph"
        app.detail_action_index = 0

        renderables = app._build_home_action_renderables("true_privilege_graph")
        text_output = _renderables_to_text(renderables)

        self.assertIn("Worth-noted graphs", text_output)
        self.assertIn("Samantha Lee production spine", text_output)
        self.assertIn("Selection", text_output)
        self.assertIn("Use Up/Down and Enter", text_output)
        self.assertNotIn("Focused path", text_output)
        self.assertNotIn("Cloud-Prod-Admins", text_output)

    def test_selecting_true_privilege_graph_option_opens_focused_graph(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "true_privilege_graph"
        app.detail_action_index = 1
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "graph_focus:contractor-support-overlap")
        self.assertEqual(app.detail_action_index, 0)
        self.assertEqual(app.histories["pathfinder"][-1].kind, "home_action")
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "graph_focus:contractor-support-overlap")

        renderables = app._build_home_action_renderables("graph_focus:contractor-support-overlap")
        text_output = _renderables_to_text(renderables)
        self.assertIn("Focused path", text_output)
        self.assertIn("Contractor support overlap", text_output)
        self.assertIn("core-support-breakglass", text_output)
        self.assertIn("return to graph catalog", text_output)

    def test_live_session_queue_render_contains_session_table(self) -> None:
        app = PathfinderPrototypeApp()

        renderables = app._build_home_action_renderables("live_session_queue")
        text_output = _renderables_to_text(renderables)

        self.assertIn("Live session queue", text_output)
        self.assertIn("Active sessions", text_output)
        self.assertIn("pra-2214", text_output)
        self.assertIn("amy.miller", text_output)
        self.assertIn("review now", text_output)

    def test_password_safe_dashboard_render_highlights_password_safe_operating_lanes(self) -> None:
        app = PathfinderPrototypeApp()
        password_safe_module = next(module for module in MODULES if module.key == "password_safe")

        renderables = app._build_module_dashboard_renderables(password_safe_module)
        text_output = _renderables_to_text(renderables)

        self.assertIn("Operating model", text_output)
        self.assertIn("Product lanes", text_output)
        self.assertIn("Discovery & onboarding", text_output)
        self.assertIn("Managed account hygiene", text_output)
        self.assertIn("Change Password After Release", text_output)
        self.assertIn("Approval & checkout pressure", text_output)
        self.assertIn("Session oversight", text_output)
        self.assertIn("Secrets & non-human access", text_output)
        self.assertIn("SSH keys", text_output)

    def test_portfolio_cover_render_contains_wordmark_and_decorative_shapes(self) -> None:
        app = PathfinderPrototypeApp()

        renderables = app._build_home_action_renderables("portfolio_cover")
        text_output = _renderables_to_text(renderables)

        self.assertIn("Pathfinder CLI cover", text_output)
        self.assertIn("Pathfinder CLI concept scene", text_output)
        self.assertIn("terminal-native Pathfinder platform concept", text_output)
        self.assertIn("CLI playground for trying Pathfinder dashboard ideas", text_output)
        self.assertIn("Pathfinder signal path", text_output)
        self.assertIn("CLI interaction path", text_output)
        self.assertIn("____   _  _____", text_output)
        self.assertIn("+", text_output)
        self.assertIn("/\\", text_output)

    def test_selecting_story_portfolio_cover_opens_cover_scene(self) -> None:
        app = PathfinderPrototypeApp()
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_story_mode("pathfinder")
        actions = app._active_story_detail_actions("story_menu")
        app.detail_action_index = [action.key for action in actions].index("story_mode_portfolio_cover")
        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "story_mode_portfolio_cover")
        self.assertTrue(app.detail_navigation_active)

    def test_temp_sunset_scene_render_matches_loading_screen_structure(self) -> None:
        app = PathfinderPrototypeApp()

        renderables = app._build_home_action_renderables("temp_sunset_scene")
        text_output = _renderables_to_text(renderables)

        self.assertIn("Temp Pathfinder loading scene", text_output)
        self.assertIn("PATHFINDER CLI loading concept", text_output)
        self.assertIn("block wordmark with layered offsets, gradient bar, and geometric accents", text_output)
        self.assertIn("establishing trusted pathfinder cli session", text_output)
        self.assertIn("step 2/5", text_output)
        self.assertIn("31%", text_output)
        self.assertIn("\u2588", text_output)
        self.assertIn("\u2593", text_output)
        self.assertIn("[]", text_output)
        self.assertIn("<>", text_output)
        self.assertIn("/\\", text_output)

    def test_selecting_story_temp_sunset_scene_opens_scene(self) -> None:
        app = PathfinderPrototypeApp()
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_story_mode("pathfinder")
        actions = app._active_story_detail_actions("story_menu")
        app.detail_action_index = [action.key for action in actions].index("story_mode_temp_sunset_scene")
        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "story_mode_temp_sunset_scene")
        self.assertTrue(app.detail_navigation_active)

    def test_pending_approvals_render_contains_selectable_table(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "pending_approvals"
        app.detail_action_index = 0

        renderables = app._build_home_action_renderables("pending_approvals")
        text_output = _renderables_to_text(renderables)

        self.assertIn("Pending approvals", text_output)
        self.assertIn("Approval queue", text_output)
        self.assertIn("prod-admin checkout", text_output)
        self.assertIn("Selection", text_output)
        self.assertIn("Use Up/Down and Enter", text_output)

    def test_selecting_pending_approval_row_opens_detail_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "pending_approvals"
        app.detail_action_index = 0
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "approval_detail:ps-prod-admin")
        self.assertEqual(app.detail_action_index, 0)
        self.assertEqual(app.histories["pathfinder"][-1].kind, "home_action")
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "approval_detail:ps-prod-admin")

    def test_approving_pending_request_returns_to_queue_with_updated_state(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "approval_detail:ps-prod-admin"
        app.detail_action_index = 0
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.pending_approval_state_by_key["ps-prod-admin"], "approved")
        self.assertEqual(app.detail_view_key, "pending_approvals")
        self.assertIn("Approved prod-admin checkout", app.histories["pathfinder"][-1].text)

    def test_selection_activation_uses_contextual_processing_message(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_navigation_active = True
        app.investigation_case_key = "amy.miller"
        app.investigation_action_index = 0

        selection = app._selection_activation()

        self.assertIsNotNone(selection)
        processing_message, _ = selection  # type: ignore[misc]
        self.assertEqual(processing_message, "Compiling live session context...")

    def test_actions_command_refreshes_actionable_items(self) -> None:
        app = PathfinderPrototypeApp()

        app._handle_utility_command("/actions")

        self.assertTrue(app.home_navigation_active)
        self.assertEqual(app.home_selection_index, 0)
        self.assertEqual(app.histories["pathfinder"][-1].kind, "actionable_items")
        self.assertEqual(app.histories["pathfinder"][-1].source_prompt, "/actions")

    def test_reset_command_restores_fresh_dashboard_state(self) -> None:
        app = PathfinderPrototypeApp()
        app.module_index = 2
        app.module_picker_active = True
        app.home_navigation_active = True
        app.detail_navigation_active = True
        app.detail_view_key = "story_findings"
        app.histories["pathfinder"].append(ConversationEntry(role="assistant", text="old"))
        app.pending_approvals.append(app.pending_approvals[0])
        app.pending_approval_state_by_key["ps-prod-admin"] = "approved"
        app.agent_status_rows.pop()
        app.story_context = app._default_story_context()
        app.story_context_by_module["pathfinder"] = app.story_context

        app._handle_utility_command("/reset")

        self.assertEqual(app._active_module().key, "pathfinder")
        self.assertFalse(app.module_picker_active)
        self.assertFalse(app.home_navigation_active)
        self.assertFalse(app.detail_navigation_active)
        self.assertIsNone(app.detail_view_key)
        self.assertTrue(all(not history for history in app.histories.values()))
        self.assertEqual(len(app.pending_approvals), 4)
        self.assertTrue(all(state == "waiting" for state in app.pending_approval_state_by_key.values()))
        self.assertEqual(len(app.agent_status_rows), 10)
        self.assertIsNone(app.story_context)
        self.assertTrue(all(context is None for context in app.story_context_by_module.values()))

    def test_help_lists_collapsed_commands_and_new_entries(self) -> None:
        app = PathfinderPrototypeApp()

        help_text = app._build_help_text().plain

        self.assertEqual(help_text.count("/app"), 1)
        self.assertEqual(help_text.count("/agent"), 1)
        self.assertIn("/story", help_text)
        self.assertIn("/actions", help_text)
        self.assertIn("/permission", help_text)
        self.assertIn(("/actions", "Display the actionable items again."), COMMAND_HELP)

    def test_permission_command_renders_soc_role_boundaries(self) -> None:
        app = PathfinderPrototypeApp()

        app._handle_utility_command("/permission")
        renderables = app._build_conversation_body(app.histories["pathfinder"][-1], app._active_module())
        text_output = _renderables_to_text(renderables)

        self.assertIn("SOC Analyst II permissions", text_output)
        self.assertIn("Area / action", text_output)
        self.assertIn("Permission", text_output)
        self.assertIn("allow", text_output)
        self.assertIn("not allow", text_output)
        self.assertIn("review detections", text_output)
        self.assertIn("restricted secrets", text_output)

    def test_actionable_item_visual_markers_are_applied(self) -> None:
        app = PathfinderPrototypeApp()
        _, critical_detail = app._build_attention_lines(ATTENTION_ITEMS[0])
        _, warning_detail = app._build_attention_lines(ATTENTION_ITEMS[1])

        risk_index = critical_detail.plain.index("91")
        risk_span_found = any(
            span.start <= risk_index
            and span.end >= risk_index + 2
            and PALETTE["risk"] in str(span.style)
            for span in critical_detail.spans
        )

        self.assertTrue(risk_span_found)
        self.assertIn("[x_x] unusual privileged activity", critical_detail.plain)
        self.assertIn("][ active session overlap", critical_detail.plain)
        self.assertIn("/!\\ approval evidence missing", warning_detail.plain)

    def test_critical_attention_detail_reuses_action_visual_and_highlights_recommendation(self) -> None:
        app = PathfinderPrototypeApp()

        detail = app._build_attention_response(ATTENTION_ITEMS[0])
        text_output = detail.plain

        self.assertNotIn("AI-native", text_output)
        self.assertIn("risk 91", text_output)
        self.assertIn("[x_x] unusual privileged activity", text_output)
        self.assertIn("][ active session overlap", text_output)
        self.assertIn("Start the investigation flow", text_output)

        risk_index = text_output.index("91")
        recommendation_index = text_output.index("Start the investigation")
        self.assertTrue(any(span.start <= risk_index and span.end >= risk_index + 2 for span in detail.spans))
        self.assertTrue(any(span.start <= recommendation_index and span.end >= recommendation_index + len("Start the investigation") for span in detail.spans))

    def test_response_visualization_templates_follow_prompt_keywords(self) -> None:
        app = PathfinderPrototypeApp()
        module = app._active_module()

        chart_cases = (
            ("show a horizontal bar chart for operational signal health", "bar", "Operational signals"),
            ("show the access mix as a pie chart", "pie", "Access mix"),
            ("show an activity heat map for hotspots", "heatmap", "Activity heat map"),
        )

        for prompt, expected_kind, expected_title in chart_cases:
            with self.subTest(prompt=prompt):
                summary, show_table, show_metrics, visualization_kind = app._build_response(prompt, module)
                entry = ConversationEntry(
                    role="assistant",
                    text=summary,
                    source_prompt=prompt,
                    show_table=show_table,
                    show_metrics=show_metrics,
                    visualization_kind=visualization_kind,
                )
                text_output = _renderables_to_text(app._build_conversation_body(entry, module))

                self.assertEqual(visualization_kind, expected_kind)
                self.assertIn(expected_title, text_output)

    def test_demo_activity_heatmap_screen_is_visual_and_selectable(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_demo_activity_heatmap"
        app.detail_action_index = 0

        text_output = _renderables_to_text(app._build_story_renderables("story_demo_activity_heatmap"))
        actions = app._active_story_detail_actions("story_demo_activity_heatmap")

        self.assertIn("Activity heat map", text_output)
        self.assertIn("Weekly signal heat map", text_output)
        self.assertIn("identity", text_output)
        self.assertIn("policy", text_output)
        self.assertIn("connector", text_output)
        self.assertIn("response", text_output)
        self.assertIn("91", text_output)
        self.assertIn("93", text_output)
        self.assertIn("review Thursday policy spike", text_output)
        self.assertEqual([action.label for action in actions], [
            "review Thursday policy spike",
            "compare connector drift",
            "open approval backlog",
            "return",
        ])

    def test_demo_queue_breakdown_screen_uses_composition_visual(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_demo_queue_breakdown"
        app.detail_action_index = 0

        text_output = _renderables_to_text(app._build_story_renderables("story_demo_queue_breakdown"))
        actions = app._active_story_detail_actions("story_demo_queue_breakdown")

        self.assertIn("Privileged access review queue", text_output)
        self.assertIn("Queue composition", text_output)
        self.assertIn("correlated 46%", text_output)
        self.assertIn("watch 31%", text_output)
        self.assertIn("stale 23%", text_output)
        self.assertIn("open correlated queue", text_output)
        self.assertGreaterEqual(len(app._build_demo_queue_pie_text().plain.splitlines()), 6)
        self.assertEqual([action.label for action in actions], [
            "open correlated queue",
            "review stale approvals",
            "inspect watch items",
            "return",
        ])

    def test_demo_privilege_graph_screen_maps_reachable_path(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_demo_privilege_graph"
        app.detail_action_index = 0

        text_output = _renderables_to_text(app._build_story_renderables("story_demo_privilege_graph"))
        actions = app._active_story_detail_actions("story_demo_privilege_graph")

        self.assertIn("Reachable privilege path: svc-backup-ops", text_output)
        self.assertIn("Reachable privilege graph", text_output)
        self.assertIn("SVC", text_output)
        self.assertIn("svc-backup-ops", text_output)
        self.assertIn("grp-cloud-admins", text_output)
        self.assertIn("grp-prod-breakglass", text_output)
        self.assertIn("aws-prod-admin", text_output)
        self.assertIn("pra-2214 -> prod-bastion-07", text_output)
        self.assertIn("prod-sql-07", text_output)
        self.assertIn("Password Safe checkout trail", text_output)
        self.assertIn("MISMATCH", text_output)
        self.assertIn("production backup and database tier", text_output)
        self.assertIn("Risk summary", text_output)
        self.assertEqual([action.label for action in actions], [
            "assess session relatedness",
            "compare approval evidence",
            "prepare containment options",
            "return",
        ])

    def test_demo_story_screens_support_enter_and_escape_return(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_demo_queue_breakdown"
        app.detail_action_index = 0
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]
        app._mark_updated = lambda: None  # type: ignore[method-assign]

        handled = app._handle_story_detail_action("pathfinder", app._active_story_detail_actions("story_demo_queue_breakdown")[0])

        self.assertTrue(handled)
        self.assertIn("Correlated-risk queue queued", app.histories["pathfinder"][-1].text)

        app.detail_navigation_active = True
        app.detail_view_key = "story_demo_queue_breakdown"
        app.on_key(_DummyKeyEvent("escape"))

        self.assertFalse(app.detail_navigation_active)
        self.assertIsNone(app.detail_view_key)

    def test_amy_case_summary_actions_follow_contextual_order(self) -> None:
        self.assertEqual(
            [action.key for action in INVESTIGATION_CASES["amy.miller"].next_actions],
            [
                "view_live_session",
                "review_signin_timeline",
                "compare_role_changes",
                "show_privilege_path",
                "simulate_containment",
                "return_to_queue",
            ],
        )

    def test_live_session_render_contains_expected_sections(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "live_session"
        app.detail_action_index = 0

        renderables = app._build_live_session_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Live session: pra-2214", text_output)
        self.assertIn("approval: not confirmed", text_output)
        self.assertIn("Session details", text_output)
        self.assertIn("approval record", text_output)
        self.assertIn("critical", text_output)
        self.assertIn("Investigate next", text_output)
        self.assertIn("inspect target activity", text_output)

    def test_live_session_detail_state_restores_after_module_switch(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "live_session"
        app.detail_action_index = 3

        app._remember_detail_state("pathfinder")
        app._set_active_module_index(1)
        app._set_active_module_index(0)

        self.assertTrue(app.detail_navigation_active)
        self.assertEqual(app.detail_view_key, "live_session")
        self.assertEqual(app.detail_action_index, 3)

    def test_target_activity_render_contains_timeline_and_next_actions(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "target_activity"
        app.detail_action_index = 0

        renderables = app._build_target_activity_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Target activity: pra-2214", text_output)
        self.assertIn("Sensitivity", text_output)
        self.assertIn("Recent activity", text_output)
        self.assertIn("| 19:32", text_output)
        self.assertIn("  |", text_output)
        self.assertIn("OPEN   session opened", text_output)
        self.assertIn("SCOPE   admin scope confirmed", text_output)
        self.assertIn("REVIEW   backup policy viewed", text_output)
        self.assertIn("FLAG   credential-related action attempted", text_output)
        self.assertIn("READ   production config read", text_output)
        self.assertIn("Why this matters", text_output)
        self.assertIn("Recommended action", text_output)
        self.assertIn("Decide next", text_output)
        self.assertIn("show privilege path", text_output)
        self.assertIn("simulate containment", text_output)
        self.assertNotIn("Confidence meter", text_output)
        self.assertNotIn("Best current read", text_output)
        self.assertNotIn("Session relatedness analysis opened with explicit confidence and evidence gaps.", text_output)

    def test_story_findings_keyboard_shortcuts_select_expected_actions(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_findings"
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]

        calls = {"activate": 0}

        def _activate() -> None:
            calls["activate"] += 1

        app.action_activate_selection = _activate  # type: ignore[method-assign]

        app.on_key(_DummyKeyEvent("e"))
        self.assertEqual(app.detail_action_index, 1)
        app.on_key(_DummyKeyEvent("a"))
        self.assertEqual(app.detail_action_index, 2)
        app.on_key(_DummyKeyEvent("p"))
        self.assertEqual(app.detail_action_index, 3)
        self.assertEqual(calls["activate"], 3)

    def test_story_findings_screen_omits_persistent_context_chips(self) -> None:
        app = PathfinderPrototypeApp()

        text_output = _renderables_to_text(app._build_story_findings_renderables())

        self.assertIn("Investigation: svc-backup-ops", text_output)
        self.assertIn("Assessment", text_output)
        self.assertNotIn("AI assessment", text_output)
        self.assertNotIn("[active investigation]", text_output)
        self.assertNotIn("[role-aware]", text_output)
        self.assertNotIn("[session memory active]", text_output)

    def test_story_session_relatedness_uses_single_decision_chip_and_simple_timeline(self) -> None:
        app = PathfinderPrototypeApp()

        text_output = _renderables_to_text(app._build_story_session_relatedness_renderables())

        self.assertIn("[confidence: medium]", text_output)
        self.assertNotIn("[active investigation]", text_output)
        self.assertNotIn("[role-aware]", text_output)
        self.assertIn("temporal overlap", text_output)
        self.assertIn("identity overlap", text_output)
        self.assertIn("intent certainty", text_output)
        self.assertIn("attribution confidence", text_output)
        self.assertNotIn("attribution\nconfidence", text_output)
        self.assertIn("session risk", text_output)
        self.assertIn("target sensitivity", text_output)
        self.assertIn("approval confidence", text_output)
        self.assertGreaterEqual(text_output.count("high"), 3)
        self.assertLess(text_output.index("Confidence"), text_output.index("Sensitivity"))
        self.assertIn("o [OPEN]", text_output)
        self.assertIn("o [SCOPE]", text_output)
        self.assertIn("o [READ]", text_output)
        self.assertNotIn("^ [", text_output)

    def test_story_navigation_supports_j_k_tab_and_escape_back(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_findings"
        app.detail_action_index = 0
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]
        app._mark_updated = lambda: None  # type: ignore[method-assign]

        app.on_key(_DummyKeyEvent("j"))
        self.assertEqual(app.detail_action_index, 1)
        app.on_key(_DummyKeyEvent("k"))
        self.assertEqual(app.detail_action_index, 0)
        app.on_key(_DummyKeyEvent("tab"))
        self.assertEqual(app.detail_action_index, 1)

        app.detail_view_key = "story_supporting_evidence"
        app.detail_return_view_key = "story_findings"
        app.detail_action_index = 0
        app.on_key(_DummyKeyEvent("escape"))
        self.assertEqual(app.detail_view_key, "story_findings")

    def test_story_followups_reuse_session_memory_for_assets_view(self) -> None:
        app = PathfinderPrototypeApp()

        app._start_story_from_prompt("pathfinder", "investigate suspicious lateral movement tied to a service account")
        applied = app._handle_story_followup_prompt(
            "pathfinder",
            "production, last 24 hours, include containment recommendations",
        )
        reused = app._handle_story_followup_prompt(
            "pathfinder",
            "Show me just the affected assets and group them by severity",
        )

        self.assertTrue(applied)
        self.assertTrue(reused)
        self.assertEqual(app.detail_view_key, "story_assets")
        self.assertIsNotNone(app.story_context)
        self.assertEqual(app.story_context.environment, "production")
        self.assertEqual(app.story_context.time_range, "last 24 hours")

    def test_story_combined_packet_stages_new_approval_requests(self) -> None:
        app = PathfinderPrototypeApp()

        app._start_story_from_prompt("pathfinder", "investigate suspicious lateral movement tied to a service account")
        app._apply_story_scope(
            "pathfinder",
            environment="production",
            time_range="last 24 hours",
            goal="triage + containment recommendation",
            source_prompt="production, last 24 hours, include containment recommendations",
        )
        app._open_story_scene("pathfinder", "story_containment", "Containment options loaded.", source_prompt="containment")
        selected_action = next(
            action for action in app._active_story_detail_actions("story_containment")
            if action.key == "story_prepare_combined_response_packet"
        )

        handled = app._handle_story_detail_action("pathfinder", selected_action)

        self.assertTrue(handled)
        self.assertEqual(app.detail_view_key, "story_handoff")
        self.assertIn("story-pra-2214-terminate", [approval.key for approval in app.pending_approvals])
        self.assertIn("story-aws-prod-admin-suspend", [approval.key for approval in app.pending_approvals])
        self.assertEqual(app.story_context.prepared_approval_keys, ("story-pra-2214-terminate", "story-aws-prod-admin-suspend"))

    def test_story_containment_screen_renders_break_options(self) -> None:
        app = PathfinderPrototypeApp()

        app._start_story_from_prompt("pathfinder", "investigate suspicious lateral movement tied to a service account")
        app._open_story_scene("pathfinder", "story_containment", "Containment options loaded.", source_prompt="show path break options")

        renderables = app._build_story_containment_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Containment options", text_output)
        self.assertIn("show path break options", app.histories["pathfinder"][-1].source_prompt)
        self.assertIn("[approval required]", text_output)
        self.assertNotIn("[active investigation]", text_output)
        self.assertNotIn("[role-aware]", text_output)
        self.assertIn("do both after approval", text_output)
        self.assertIn("Risk reduction", text_output)
        self.assertIn("cues:", text_output)
        self.assertNotIn("Decision cues", text_output)
        self.assertIn("Recommended", text_output)
        self.assertIn("Prepare the combined response packet", text_output)
        self.assertIn("Boundary", text_output)
        self.assertIn("view last step results", text_output)

    def test_hidden_story_mode_restores_previous_view_on_close(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "story_findings"
        app.detail_action_index = 2
        app._remember_detail_state("pathfinder")

        app._open_story_mode("pathfinder")
        app._close_story_mode("pathfinder")

        self.assertTrue(app.detail_navigation_active)
        self.assertEqual(app.detail_view_key, "story_findings")
        self.assertEqual(app.detail_action_index, 2)

    def test_story_menu_includes_reserved_scene_options(self) -> None:
        app = PathfinderPrototypeApp()
        app._open_story_mode("pathfinder")

        renderables = app._build_story_menu_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Portfolio cover", text_output)
        self.assertIn("Temp sunset scene", text_output)

    def test_story_scene_options_reuse_existing_scene_renderers(self) -> None:
        app = PathfinderPrototypeApp()

        cover_output = _renderables_to_text(app._build_story_mode_renderables("story_mode_portfolio_cover"))
        sunset_output = _renderables_to_text(app._build_story_mode_renderables("story_mode_temp_sunset_scene"))

        self.assertIn("Pathfinder CLI cover", cover_output)
        self.assertIn("Temp Pathfinder loading scene", sunset_output)
        self.assertIn("return to story menu", cover_output)
        self.assertIn("return to story menu", sunset_output)


if __name__ == "__main__":
    unittest.main()
