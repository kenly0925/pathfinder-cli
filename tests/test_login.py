import io
import unittest

from rich.console import Console

from pathfinder_cli.login import _login_renderable, _spinner_frame


def _render_to_text(renderable: object, width: int = 140) -> str:
    console = Console(record=True, file=io.StringIO(), width=width, color_system=None, force_terminal=False)
    console.print(renderable)
    return console.export_text(styles=False)


class LoginRenderTests(unittest.TestCase):
    def test_login_renderable_shows_auth_step_and_progress(self) -> None:
        text_output = _render_to_text(_login_renderable("analyst", 0.45))

        self.assertIn("verifying MFA proof and device posture", text_output)
        self.assertIn("analyst", text_output)
        self.assertIn("step 3/5", text_output)
        self.assertIn("secure broker handoff in progress", text_output)

    def test_spinner_frame_starts_with_forward_slash(self) -> None:
        self.assertEqual(_spinner_frame(0.0), "/")


if __name__ == "__main__":
    unittest.main()
