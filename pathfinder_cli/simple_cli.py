from __future__ import annotations

import os
import re
import sys
import time
from typing import Final

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table


ASCII_BANNER: Final[str] = r"""
   ____      _               ____ _     ___
  / ___|   _| |__   ___ _ __/ ___| |   |_ _|
 | |  | | | | '_ \ / _ \ '__| |   | |    | |
 | |__| |_| | |_) |  __/ |  | |___| |___ | |
  \____\__, |_.__/ \___|_|   \____|_____|___|
       |___/
"""
BT_AGENT_LABEL: Final[str] = "\N{ROBOT FACE} BT Pathfinder"


THEME: Final[dict[str, str]] = {
    "banner": "bold cyan",
    "hint": "dim",
    "selected_dot": "green",
    "unselected_dot": "grey50",
    "selected_text": "bold white",
    "unselected_text": "white",
    "user_label": "bold cyan",
    "assistant_label": "bold green",
    "spinner": "cyan",
    "bar_fill": "green",
    "bar_empty": "grey37",
}


MENU_OPTIONS: Final[list[tuple[str, str]]] = [
    ("chat", "Start Conversation"),
    ("table_demo", "Show Sample Table"),
    ("metrics_demo", "Show Sample Metrics"),
    ("quit", "Quit"),
]
AGENT_STATUS_CORE_TOKENS: Final[frozenset[str]] = frozenset({"agent", "agents"})
AGENT_STATUS_HINT_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "status",
        "state",
        "health",
        "healthy",
        "connector",
        "connected",
        "disconnected",
        "connection",
        "connections",
        "token",
        "expiring",
        "auth",
        "authentication",
        "access",
        "role",
        "mode",
        "modes",
        "verified",
    }
)
AGENT_STATUS_ROWS: Final[tuple[tuple[str, str, str, str, str], ...]] = (
    ("identity security insights", "connected", "detections, true privilege graph", "analyze"),
    ("okta", "connected", "sign-ins, mfa, groups", "observe"),
    ("microsoft entra id", "token expiring", "risk, app roles, directory changes", "observe"),
    ("ad bridge", "connected", "ad auth, unix/linux policy", "observe"),
    ("endpoint privilege management", "connected", "host policy, elevation events", "observe"),
    ("password safe", "connected", "secrets, rotation, managed accounts", "observe + act"),
    ("privileged remote access", "connected", "live sessions, approvals, recordings", "observe + act"),
    ("entitle", "connected", "jit grants, cloud roles, saas access", "observe + act"),
    ("servicenow", "connected", "tickets, change approvals, case actions", "act"),
    ("audit evidence", "connected", "summary, proof log, exports", "analyze"),
)


class SimplePathfinderCLI:
    def __init__(self) -> None:
        self.console = Console()
        self.running = True
        self.menu_index = 0

    def run(self) -> None:
        while self.running:
            action = self._menu_loop()
            if action == "chat":
                self._chat_loop()
            elif action == "table_demo":
                self._show_table_demo()
            elif action == "metrics_demo":
                self._show_metrics_demo()
            else:
                self.running = False

        self.console.print("\n[dim]Session ended.[/dim]")

    def _menu_loop(self) -> str:
        if not sys.stdin.isatty():
            return self._menu_loop_fallback()

        while True:
            self._render_menu()
            key = _read_key()

            if key == "up":
                self.menu_index = (self.menu_index - 1) % len(MENU_OPTIONS)
            elif key == "down":
                self.menu_index = (self.menu_index + 1) % len(MENU_OPTIONS)
            elif key == "enter":
                return MENU_OPTIONS[self.menu_index][0]
            elif key in {"q", "esc"}:
                return "quit"

    def _menu_loop_fallback(self) -> str:
        self._render_menu()
        choices = [str(i + 1) for i in range(len(MENU_OPTIONS))]
        choice = Prompt.ask("Select option", choices=choices, default="1")
        return MENU_OPTIONS[int(choice) - 1][0]

    def _render_menu(self) -> None:
        self.console.clear()
        self.console.print(f"[{THEME['banner']}]{ASCII_BANNER}[/{THEME['banner']}]")
        self.console.print(
            f"[{THEME['hint']}]Use Up/Down arrows and Enter. Press q to quit.[/{THEME['hint']}]\n"
        )

        for index, (_, label) in enumerate(MENU_OPTIONS):
            selected = index == self.menu_index
            dot_style = THEME["selected_dot"] if selected else THEME["unselected_dot"]
            text_style = THEME["selected_text"] if selected else THEME["unselected_text"]
            dot = "o" if selected else "."
            self.console.print(f"  [{dot_style}]{dot}[/{dot_style}] [{text_style}]{label}[/{text_style}]")

    def _chat_loop(self) -> None:
        self.console.clear()
        self.console.print(f"[{THEME['banner']}]{ASCII_BANNER}[/{THEME['banner']}]")
        self.console.print(
            f"[{THEME['hint']}]Natural language chat. Use /menu to return, /quit to exit.[/{THEME['hint']}]"
        )

        while self.running:
            try:
                query = self.console.input(f"\n[{THEME['user_label']}]you >[/{THEME['user_label']}] ").strip()
            except (EOFError, KeyboardInterrupt):
                self.running = False
                return

            if not query:
                continue

            command = query.lower()
            if command in {"/menu", "/back"}:
                return
            if command in {"/quit", "/exit"}:
                self.running = False
                return

            with self.console.status(f"[{THEME['spinner']}]thinking...[/{THEME['spinner']}]", spinner="line"):
                time.sleep(0.8)

            self._render_assistant_response(query)

    def _render_assistant_response(self, query: str) -> None:
        lower_query = query.lower()
        wants_agent_status = self._matches_agent_status_request(query)
        wants_table = any(token in lower_query for token in ("table", "compare", "list", "breakdown"))
        wants_metrics = any(
            token in lower_query for token in ("metric", "metrics", "trend", "graph", "chart", "latency", "error")
        )

        if wants_agent_status:
            summary = (
                "Agent status loaded across BeyondTrust capabilities and connected tools. "
                "Microsoft Entra ID is the only connector with a token nearing expiry."
            )
            self.console.print(f"[{THEME['assistant_label']}]{BT_AGENT_LABEL} >[/{THEME['assistant_label']}] {summary}")
            self.console.print()
            self.console.print(self._build_agent_status_table())
            return

        summary = (
            "I parsed your request and generated a structured response. "
            "Ask for a table, metrics, or both to shape the output."
        )
        self.console.print(f"[{THEME['assistant_label']}]{BT_AGENT_LABEL} >[/{THEME['assistant_label']}] {summary}")

        if wants_table:
            self.console.print()
            self.console.print(self._build_table(query))

        if wants_metrics:
            self.console.print()
            self.console.print(self._build_metrics(query))

        if not wants_table and not wants_metrics:
            self.console.print(f"[{THEME['hint']}]Tip: try 'show a table of top risks and metrics'.[/{THEME['hint']}]")

    def _show_table_demo(self) -> None:
        self.console.clear()
        with self.console.status(f"[{THEME['spinner']}]building table...[/{THEME['spinner']}]", spinner="line"):
            time.sleep(0.6)
        self.console.print(self._build_table("table demo risk latency signal"))
        self._wait_for_enter()

    def _show_metrics_demo(self) -> None:
        self.console.clear()
        with self.console.status(f"[{THEME['spinner']}]building metrics...[/{THEME['spinner']}]", spinner="line"):
            time.sleep(0.6)
        self.console.print(self._build_metrics("metrics demo"))
        self._wait_for_enter()

    def _wait_for_enter(self) -> None:
        self.console.print(f"\n[{THEME['hint']}]Press Enter to return to menu.[/{THEME['hint']}]")
        try:
            input()
        except EOFError:
            pass

    def _build_table(self, query: str) -> Table:
        table = Table(title="Response Table", header_style="bold cyan")
        table.add_column("Item")
        table.add_column("Score")
        table.add_column("Status")

        keywords = self._extract_keywords(query)
        for index, keyword in enumerate(keywords, start=1):
            score = 50 + (sum(ord(ch) for ch in keyword) + index * 13) % 50
            status = "stable" if score >= 75 else "watch"
            table.add_row(keyword.title(), f"{score}%", status)

        return table

    def _build_metrics(self, query: str) -> Table:
        seed = sum(ord(ch) for ch in query)
        metrics = [
            ("Confidence", 55 + (seed % 40)),
            ("Signal Quality", 50 + ((seed // 3) % 45)),
            ("Latency Health", 45 + ((seed // 7) % 50)),
        ]

        table = Table(title="Simple Metrics", header_style="bold cyan")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_column("Bar")

        for name, value in metrics:
            bar = self._bar(value)
            table.add_row(name, f"{value}%", bar)

        return table

    def _build_agent_status_table(self) -> Table:
        table = Table(title="Agent Status", header_style="bold cyan")
        table.add_column("Agent")
        table.add_column("Connector")
        table.add_column("Access")
        table.add_column("Role")

        for agent, connector, access, role in AGENT_STATUS_ROWS:
            table.add_row(agent, connector, access, role)

        return table

    def _bar(self, value: int, width: int = 24) -> str:
        clamped = max(0, min(100, value))
        filled = max(1, round((clamped / 100) * width))
        empty = width - filled
        return (
            f"[{THEME['bar_fill']}]{'#' * filled}[/{THEME['bar_fill']}]"
            f"[{THEME['bar_empty']}]{'.' * empty}[/{THEME['bar_empty']}]"
        )

    def _extract_keywords(self, query: str) -> list[str]:
        cleaned = [token.strip(".,!?;:()[]{}\"'").lower() for token in query.split()]
        keywords = [token for token in cleaned if token and len(token) > 3]
        if not keywords:
            return ["signal", "risk", "latency"]
        return keywords[:4]

    def _matches_agent_status_request(self, query: str) -> bool:
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not tokens:
            return False

        if tokens & AGENT_STATUS_CORE_TOKENS and tokens & AGENT_STATUS_HINT_TOKENS:
            return True

        hint_matches = len(tokens & AGENT_STATUS_HINT_TOKENS)
        return hint_matches >= 3 and any(token in tokens for token in ("status", "health", "connection"))


def _read_key() -> str:
    if os.name == "nt":
        return _read_key_windows()
    return _read_key_posix()


def _read_key_windows() -> str:
    import msvcrt

    while True:
        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            special = msvcrt.getwch()
            return {
                "H": "up",
                "P": "down",
                "K": "left",
                "M": "right",
            }.get(special, "")
        if key in ("\r", "\n"):
            return "enter"
        if key == "\x1b":
            return "esc"
        if key.lower() == "q":
            return "q"
        return key


def _read_key_posix() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
        if key == "\x1b":
            key2 = sys.stdin.read(1)
            if key2 == "[":
                key3 = sys.stdin.read(1)
                return {
                    "A": "up",
                    "B": "down",
                    "C": "right",
                    "D": "left",
                }.get(key3, "esc")
            return "esc"
        if key in ("\r", "\n"):
            return "enter"
        if key.lower() == "q":
            return "q"
        return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def run() -> None:
    SimplePathfinderCLI().run()
