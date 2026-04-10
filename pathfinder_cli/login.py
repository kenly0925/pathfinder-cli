from __future__ import annotations

import ctypes
import getpass
import os
import time
from typing import Final

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

from .theme import BEYONDTRUST_ASCII, PALETTE, gradient_bar


LOGIN_STEPS: Final[int] = 32
PASSWORD_ICON: Final[str] = "\N{KEY}"
SPINNER_FRAMES: Final[str] = "/-\\|"
AUTH_PHASES: Final[tuple[str, ...]] = (
    "validating local operator profile",
    "establishing trusted directory session",
    "verifying MFA proof and device posture",
    "syncing policy and entitlement context",
    "loading Pathfinder workspace",
)


def run_login_flow() -> str:
    console = _build_console()
    username = _prompt_username(console)
    _prompt_password(console)
    _animate_login(console, username)
    return username


def _prompt_username(console: Console) -> str:
    while True:
        console.print(_prompt_text("username"), end="")
        username = input().strip()
        if username:
            return username
        console.print(
            f"[bold {PALETTE['warn']}]A username is required to continue.[/]"
        )


def _prompt_password(console: Console) -> str:
    while True:
        console.print(_prompt_text("password", icon=PASSWORD_ICON), end="")
        password = _read_hidden_password()
        if password:
            return password
        console.print(
            f"[bold {PALETTE['warn']}]A password is required to continue.[/]"
        )


def _animate_login(console: Console, username: str) -> None:
    console.clear()
    with Live(console=console, refresh_per_second=30, transient=True) as live:
        for step in range(LOGIN_STEPS + 1):
            progress = step / LOGIN_STEPS
            live.update(_login_renderable(username, progress))
            time.sleep(0.05)


def _login_renderable(username: str, progress: float) -> Align:
    title = Text(BEYONDTRUST_ASCII, style=f"bold {PALETTE['orange_primary']}")
    spinner = _spinner_frame(progress)
    phase_index = _auth_phase_index(progress)

    subtitle = Text()
    subtitle.append(f"{spinner} ", style=f"bold {PALETTE['orange_primary']}")
    subtitle.append(_auth_phase_label(progress), style=f"bold {PALETTE['orange_primary']}")
    subtitle.append("  ", style=PALETTE["text_main"])
    subtitle.append(username, style=PALETTE["text_muted"])

    footer = Text()
    footer.append(f"{spinner} ", style=f"bold {PALETTE['orange_primary']}")
    footer.append(f"step {phase_index + 1}/{len(AUTH_PHASES)}", style=f"bold {PALETTE['orange_primary']}")
    footer.append(" | ", style=PALETTE["line"])
    footer.append("secure broker handoff in progress", style=PALETTE["orange_primary"])

    group = Group(
        Align.center(title),
        Text(""),
        Align.center(subtitle),
        Text(""),
        Align.center(gradient_bar(progress, width=34)),
        Text(""),
        Align.center(footer),
    )
    return Align.center(group, vertical="middle")


def _spinner_frame(progress: float) -> str:
    index = min(LOGIN_STEPS, max(0, round(progress * LOGIN_STEPS)))
    return SPINNER_FRAMES[index % len(SPINNER_FRAMES)]


def _auth_phase_index(progress: float) -> int:
    if progress >= 1:
        return len(AUTH_PHASES) - 1
    return min(len(AUTH_PHASES) - 1, int(progress * len(AUTH_PHASES)))


def _auth_phase_label(progress: float) -> str:
    return AUTH_PHASES[_auth_phase_index(progress)]


def _prompt_text(label: str, icon: str | None = None) -> Text:
    text = Text()
    text.append(f"{label}:", style=f"bold {PALETTE['orange_primary']}")
    text.append(" ", style=PALETTE["text_main"])
    if icon:
        text.append(icon, style=f"bold {PALETTE['orange_soft']}")
        text.append(" ", style=PALETTE["text_main"])
    return text


def _read_hidden_password() -> str:
    if os.name == "nt":
        return _read_hidden_password_windows()
    return getpass.getpass("")


def _read_hidden_password_windows() -> str:
    import msvcrt

    password_chars: list[str] = []

    while True:
        character = msvcrt.getwch()
        if character in ("\r", "\n"):
            msvcrt.putwch("\r")
            msvcrt.putwch("\n")
            return "".join(password_chars)
        if character == "\003":
            raise KeyboardInterrupt
        if character == "\b":
            if password_chars:
                password_chars.pop()
            continue
        if character in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue
        password_chars.append(character)


def _build_console() -> Console:
    if os.name != "nt":
        return Console(force_terminal=True, color_system="truecolor")

    if _enable_windows_vt_mode():
        return Console(force_terminal=True, color_system="truecolor", legacy_windows=False)

    return Console(color_system="windows", legacy_windows=True)


def _enable_windows_vt_mode() -> bool:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    if handle == 0 or handle == -1:
        return False

    mode = ctypes.c_uint()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
        return False

    enable_vt = 0x0004
    if mode.value & enable_vt:
        return True

    return kernel32.SetConsoleMode(handle, mode.value | enable_vt) != 0
