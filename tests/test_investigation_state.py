import unittest

from pathfinder_cli.app import INVESTIGATION_CASES, PathfinderPrototypeApp


class InvestigationStateTests(unittest.TestCase):
    def test_saved_investigation_restores_when_module_becomes_active(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_navigation_active = True
        app.investigation_case_key = "amy.miller"
        app.investigation_action_index = 2

        app._remember_investigation_state("pathfinder")
        app._set_active_module_index(1)
        app._set_active_module_index(0)

        self.assertTrue(app.investigation_navigation_active)
        self.assertEqual(app.investigation_case_key, "amy.miller")
        self.assertEqual(app.investigation_action_index, 2)

    def test_clearing_module_state_prevents_restoring_stale_investigation(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_navigation_active = True
        app.investigation_case_key = "amy.miller"
        app.investigation_action_index = 1

        app._remember_investigation_state("pathfinder")
        app._clear_investigation_state("pathfinder")
        app._set_active_module_index(1)
        app._set_active_module_index(0)

        self.assertFalse(app.investigation_navigation_active)
        self.assertIsNone(app.investigation_case_key)
        self.assertEqual(app.investigation_action_index, 0)

    def test_restoring_clamps_out_of_range_action_index(self) -> None:
        app = PathfinderPrototypeApp()
        app.investigation_navigation_active = True
        app.investigation_case_key = "amy.miller"
        app.investigation_action_index = 99

        app._remember_investigation_state("pathfinder")
        app._set_active_module_index(1)
        app._set_active_module_index(0)

        self.assertEqual(
            app.investigation_action_index,
            len(INVESTIGATION_CASES["amy.miller"].next_actions) - 1,
        )


if __name__ == "__main__":
    unittest.main()
