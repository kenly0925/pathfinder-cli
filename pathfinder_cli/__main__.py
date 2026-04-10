from __future__ import annotations

import argparse

from .app import PathfinderPrototypeApp
from .login import run_login_flow
from .simple_cli import run as run_simple


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pathfinder CLI launcher")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--login",
        action="store_true",
        help="Prompt for username and password, then launch the dashboard.",
    )
    mode_group.add_argument(
        "--start",
        action="store_true",
        help="Run the Textual dashboard directly without the login flow.",
    )
    mode_group.add_argument(
        "--simple",
        action="store_true",
        help="Run the fallback simple CLI instead of the Textual interface.",
    )
    args = parser.parse_args(argv)

    if args.simple:
        run_simple()
        return

    if args.login:
        username = run_login_flow()
        PathfinderPrototypeApp(authenticated_user=username).run()
        return

    PathfinderPrototypeApp().run()


if __name__ == "__main__":
    main()
