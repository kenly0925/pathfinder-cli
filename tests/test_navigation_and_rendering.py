import io
import unittest

from rich.console import Console
from textual.widgets import RichLog

from pathfinder_cli.app import HOME_ACTIONS, INVESTIGATION_CASES, MODULES, PathfinderPrototypeApp


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


class MountBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_initial_dashboard_opens_at_top_of_main_log(self) -> None:
        app = PathfinderPrototypeApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            log = app.query_one("#main-log", RichLog)

        self.assertEqual(log.scroll_offset.y, 0)

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

    def test_home_actions_include_scene_shortcuts(self) -> None:
        self.assertEqual([action.key for action in HOME_ACTIONS], [
            "true_privilege_graph",
            "live_session_queue",
            "pending_approvals",
            "portfolio_cover",
            "temp_sunset_scene",
        ])

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

    def test_selecting_portfolio_cover_action_opens_cover_scene(self) -> None:
        app = PathfinderPrototypeApp()
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_action(3)

        self.assertEqual(app.detail_view_key, "portfolio_cover")
        self.assertFalse(app.detail_navigation_active)
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "portfolio_cover")

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

    def test_selecting_temp_sunset_scene_action_opens_scene(self) -> None:
        app = PathfinderPrototypeApp()
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_action(4)

        self.assertEqual(app.detail_view_key, "temp_sunset_scene")
        self.assertFalse(app.detail_navigation_active)
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "temp_sunset_scene")

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
        self.assertIn("session risk", text_output)
        self.assertIn("target sensitivity", text_output)
        self.assertIn("approval confidence", text_output)
        self.assertIn("Recent activity", text_output)
        self.assertIn("REVIEW", text_output)
        self.assertIn("backup policy viewed", text_output)
        self.assertIn("⚑", text_output)
        self.assertLess(text_output.index("Sensitivity"), text_output.index("Recent activity"))
        self.assertIn("Decide next", text_output)
        self.assertIn("open incident review", text_output)

    def test_selecting_inspect_target_activity_enters_target_activity_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "live_session"
        app.detail_action_index = 0
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "target_activity")
        self.assertEqual(app.detail_action_index, 0)
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "inspect_target_activity")

    def test_privilege_path_render_contains_graph_and_next_actions(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "privilege_path"
        app.detail_action_index = 0

        renderables = app._build_privilege_path_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Privilege path", text_output)
        self.assertIn("Focused path", text_output)
        self.assertIn("ID", text_output)
        self.assertIn("grp-cloud-admins", text_output)
        self.assertIn("BREAK", text_output)
        self.assertIn("cut inherited admin edge here", text_output)
        self.assertIn("aws-prod-admin", text_output)
        self.assertIn("LIVE", text_output)
        self.assertIn("pra-2214", text_output)
        self.assertIn("Decide next", text_output)
        self.assertIn("simulate containment", text_output)

    def test_selecting_show_privilege_path_enters_privilege_path_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "live_session"
        app.detail_action_index = 3
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "privilege_path")
        self.assertEqual(app.detail_action_index, 0)
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "show_privilege_path")

    def test_return_to_activity_review_reloads_target_activity_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "privilege_path"
        app.detail_action_index = 4
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "target_activity")
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "inspect_target_activity")

    def test_containment_render_contains_comparison_matrix_and_response_actions(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "containment"
        app.detail_action_index = 0
        app.detail_return_view_key = "privilege_path"

        renderables = app._build_containment_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Containment simulation", text_output)
        self.assertIn("Containment options", text_output)
        self.assertIn("revoke session only", text_output)
        self.assertIn("92 -> 18", text_output)
        self.assertIn("Fastest total reduction", text_output)
        self.assertIn("Least disruption", text_output)
        self.assertIn("Highest residual risk", text_output)
        self.assertIn("Decide next", text_output)
        self.assertIn("revoke session now", text_output)
        self.assertIn("return to privilege path", text_output)

    def test_selecting_simulate_containment_enters_containment_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "target_activity"
        app.detail_action_index = 1
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "containment")
        self.assertEqual(app.detail_return_view_key, "target_activity")
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "simulate_containment")

    def test_cancel_return_from_containment_reloads_prior_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "containment"
        app.detail_action_index = 4
        app.detail_return_view_key = "privilege_path"
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "privilege_path")
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "show_privilege_path")

    def test_selecting_do_both_from_containment_enters_verification_view(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "containment"
        app.detail_action_index = 0
        app.detail_return_view_key = "privilege_path"
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertEqual(app.detail_view_key, "verification")
        self.assertEqual(app.verification_profile_key, "do_both_actions")
        self.assertEqual(app.histories["pathfinder"][-1].action_key, "post_action_verification")

    def test_verification_render_contains_checklist_and_next_actions(self) -> None:
        app = PathfinderPrototypeApp()
        app.detail_navigation_active = True
        app.detail_view_key = "verification"
        app.detail_action_index = 0
        app.verification_profile_key = "do_both_actions"

        renderables = app._build_verification_renderables()
        text_output = _renderables_to_text(renderables)

        self.assertIn("Post-action verification", text_output)
        self.assertIn("[ok] live PRA session pra-2214 closed", text_output)
        self.assertIn("risk after", text_output)
        self.assertIn("18", text_output)
        self.assertIn("low", text_output)
        self.assertIn("open incident review", text_output)
        self.assertIn("close case as contained", text_output)

    def test_return_to_queue_from_verification_clears_investigation_state(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_case_key = "amy.miller"
        app.detail_navigation_active = True
        app.detail_view_key = "verification"
        app.detail_action_index = 2
        app.verification_profile_key = "do_both_actions"
        app.query_one = lambda *args, **kwargs: _DummyInput("")  # type: ignore[method-assign]
        app._render_current_module = lambda: None  # type: ignore[method-assign]

        app._open_selected_detail_action()

        self.assertFalse(app.detail_navigation_active)
        self.assertIsNone(app.investigation_case_key)
        self.assertTrue(app.home_navigation_active)

    def test_conversation_separator_is_dashed(self) -> None:
        app = PathfinderPrototypeApp()
        app.query_one = lambda *args, **kwargs: type("Log", (), {"size": type("Size", (), {"width": 48})()})()  # type: ignore[method-assign]

        separator = app._conversation_separator()

        self.assertTrue(separator.startswith("- "))
        self.assertIn(" ", separator)

    def test_processing_status_line_uses_spinner_and_message(self) -> None:
        app = PathfinderPrototypeApp()
        app.chrome_tick = 1
        app.processing_message = "Compiling live session context..."

        status_line = app._build_processing_status_line()

        self.assertEqual(status_line.plain, "/ Compiling live session context...")

    def test_tick_ui_rerenders_log_while_processing(self) -> None:
        app = PathfinderPrototypeApp()
        app.processing = True

        calls = {"render": 0, "chrome": 0}

        def _render() -> None:
            calls["render"] += 1

        def _refresh() -> None:
            calls["chrome"] += 1

        app._render_current_module = _render  # type: ignore[method-assign]
        app._refresh_chrome = _refresh  # type: ignore[method-assign]

        app._tick_ui()

        self.assertEqual(calls["render"], 1)
        self.assertEqual(calls["chrome"], 0)

    def test_footer_hint_shows_help_and_rotating_assistant_message(self) -> None:
        app = PathfinderPrototypeApp()
        app.chrome_tick = 0
        app.module_picker_active = True
        app.detail_navigation_active = True
        app.detail_view_key = "true_privilege_graph"

        footer_hint = app._build_footer_hint()

        self.assertIn("/help", footer_hint.plain)
        self.assertIn("/", footer_hint.plain)
        self.assertIn("I can show you some features.", footer_hint.plain)

    def test_footer_hint_spinner_animates_independently_of_message_rotation(self) -> None:
        app = PathfinderPrototypeApp()

        app.chrome_tick = 0
        first = app._build_footer_hint().plain
        app.chrome_tick = 1
        second = app._build_footer_hint().plain

        self.assertIn("I can show you some features.", first)
        self.assertIn("I can show you some features.", second)
        self.assertNotEqual(first, second)

    def test_top_meta_shows_model_and_token_usage(self) -> None:
        app = PathfinderPrototypeApp()

        meta = app._build_top_meta()

        self.assertIn("Pathfinder AI", meta.plain)
        self.assertIn("GPT-5.4", meta.plain)
        self.assertIn("Tokens", meta.plain)
        self.assertIn("200k", meta.plain)

    def test_default_user_role_is_soc_analyst_two(self) -> None:
        app = PathfinderPrototypeApp()

        self.assertEqual(app.user_role, "SOC Analyst II")


if __name__ == "__main__":
    unittest.main()
