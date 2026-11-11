"""Global visual tokens and shared CustomTkinter styles."""
import sys
import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_FAMILY = "Microsoft YaHei UI" if sys.platform.startswith("win") else None

# Midnight studio palette: deep blue charcoal surfaces, teal action color,
# warm coral for destructive actions. Keep all UI colors defined here.
COLOR = {
    "app": "#0B1117",
    "sidebar": "#101923",
    "panel": "#131F2A",
    "panel_alt": "#172632",
    "card": "#192833",
    "card_hover": "#203443",
    "input": "#0E1821",
    "border": "#293B49",
    "border_focus": "#35C6B0",
    "accent": "#35C6B0",
    "accent_hover": "#2AA995",
    "accent_soft": "#193C3A",
    "danger": "#C85F6A",
    "danger_hover": "#A94954",
    "text": "#E5EEF4",
    "text_soft": "#B5C5D0",
    "muted": "#8498A7",
    "link": "#78B9E8",
    "white": "#FFFFFF",
}

SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 24, "xxl": 32}
RADIUS = 12
RADIUS_SM = 8
THUMB = 62
PAD = SPACE["md"]
SEPARATOR = ", "

APP_BG = COLOR["app"]
SIDEBAR_BG = COLOR["sidebar"]
PANEL_BG = COLOR["panel"]
CARD_BG = COLOR["card"]
SUBTLE = COLOR["muted"]
LINK_COLOR = COLOR["link"]

PRIMARY_BTN = dict(fg_color=COLOR["accent"], hover_color=COLOR["accent_hover"],
                   text_color=COLOR["app"], corner_radius=RADIUS_SM,
                   border_width=0)
SECONDARY = dict(fg_color=COLOR["panel_alt"], hover_color=COLOR["card_hover"],
                 text_color=COLOR["text"], corner_radius=RADIUS_SM,
                 border_width=1, border_color=COLOR["border"])
DANGER_BTN = dict(fg_color=COLOR["danger"], hover_color=COLOR["danger_hover"],
                  text_color=COLOR["white"], corner_radius=RADIUS_SM,
                  border_width=0)
ENTRY_STYLE = dict(fg_color=COLOR["input"], border_color=COLOR["border"],
                   text_color=COLOR["text"], placeholder_text_color=COLOR["muted"],
                   border_width=1, corner_radius=RADIUS_SM)
SURFACE_STYLE = dict(fg_color=COLOR["panel"], corner_radius=RADIUS)


def font(size: int = 13, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size,
                       weight="bold" if bold else "normal")


class HiddenScrollbarFrame(ctk.CTkScrollableFrame):
    """Scrollable surface styled with the app palette and a visible scrollbar."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("scrollbar_fg_color", COLOR["panel"])
        kwargs.setdefault("scrollbar_button_color", COLOR["muted"])
        kwargs.setdefault("scrollbar_button_hover_color", COLOR["accent"])
        super().__init__(*args, **kwargs)
