from __future__ import annotations

from typing import Final

from rich.text import Text


PALETTE: Final[dict[str, str]] = {
    "bg_deep": "#26211F",
    "bg_panel": "#26211F",
    "bg_soft": "#403632",
    "bg_input": "#473C38",
    "bg_emphasis": "#12100F",
    "text_main": "#F0E5DB",
    "text_muted": "#C9B8AA",
    "line": "#7D6C65",
    "orange_primary": "#FF6A00",
    "orange_soft": "#F09A3E",
    "orange_pale": "#C084FC",
    "yellow": "#F59E0B",
    "blue": "#60A5FA",
    "violet": "#A78BFA",
    "purple": "#C084FC",
    "teal": "#2DD4BF",
    "rose": "#FB7185",
    "slate": "#A1A1AA",
    "blue_bg": "#1E3A8A",
    "green_bg": "#14532D",
    "amber_bg": "#78350F",
    "red_bg": "#7F1D1D",
    "violet_bg": "#4C1D95",
    "purple_bg": "#581C87",
    "teal_bg": "#134E4A",
    "slate_bg": "#27272A",
    "blue_text": "#60A5FA",
    "green_text": "#4ADE80",
    "amber_text": "#F59E0B",
    "red_text": "#F87171",
    "violet_text": "#A78BFA",
    "purple_text": "#C084FC",
    "teal_text": "#2DD4BF",
    "slate_text": "#A1A1AA",
    "info": "#D6C7BC",
    "ok": "#4ADE80",
    "warn": "#F59E0B",
    "risk": "#F87171",
}


SIDEBAR_BRAND: Final[str] = "BeyondTrust"


BEYONDTRUST_ASCII: Final[str] = r"""
██████╗ ███████╗██╗   ██╗ ██████╗ ███╗   ██╗██████╗
██╔══██╗██╔════╝╚██╗ ██╔╝██╔═══██╗████╗  ██║██╔══██╗
██████╔╝█████╗   ╚████╔╝ ██║   ██║██╔██╗ ██║██║  ██║
██╔══██╗██╔══╝    ╚██╔╝  ██║   ██║██║╚██╗██║██║  ██║
██████╔╝███████╗   ██║   ╚██████╔╝██║ ╚████║██████╔╝
╚═════╝ ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚═════╝
████████╗██████╗ ██╗   ██╗███████╗████████╗
╚══██╔══╝██╔══██╗██║   ██║██╔════╝╚══██╔══╝
   ██║   ██████╔╝██║   ██║███████╗   ██║
   ██║   ██╔══██╗██║   ██║╚════██║   ██║
   ██║   ██║  ██║╚██████╔╝███████║   ██║
   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝
""".strip("\n")


GRADIENT_STOPS: Final[tuple[tuple[int, int, int], ...]] = (
    (154, 52, 18),
    (194, 65, 12),
    (249, 115, 22),
    (251, 146, 60),
    (253, 186, 116),
)


def gradient_color(ratio: float) -> str:
    clamped = max(0.0, min(1.0, ratio))
    segments = len(GRADIENT_STOPS) - 1
    scaled = clamped * segments
    index = min(int(scaled), segments - 1)
    local_ratio = scaled - index
    start = GRADIENT_STOPS[index]
    end = GRADIENT_STOPS[index + 1]
    channel = tuple(
        int(start[position] + (end[position] - start[position]) * local_ratio)
        for position in range(3)
    )
    return f"#{channel[0]:02x}{channel[1]:02x}{channel[2]:02x}"


def gradient_bar(progress: float, width: int = 26, idle: bool = False) -> Text:
    clamped = max(0.0, min(1.0, progress))
    filled = 0 if idle else max(1, round(clamped * width))
    text = Text()

    for index in range(width):
        if index < filled and not idle:
            color = gradient_color(index / max(1, width - 1))
            text.append("  ", style=f"on {color}")
        else:
            text.append("  ", style=f"on {PALETTE['bg_input']}")

    percent = 0 if idle else int(clamped * 100)
    text.append(f" {percent:3d}%", style=f"bold {PALETTE['orange_soft']}")
    return text


def pipe_bar(value: int, width: int = 10) -> Text:
    clamped = max(0, min(100, value))
    filled = max(1, round((clamped / 100) * width))
    text = Text()

    for index in range(width):
        if index < filled:
            color = gradient_color(index / max(1, filled - 1))
            text.append("▮", style=f"bold {color}")
        else:
            text.append("▯", style=PALETTE["line"])

    return text
