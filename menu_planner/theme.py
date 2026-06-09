"""
theme.py — Centralised colour tokens. Import current() anywhere to get the active theme dict.
Call set_theme("dark"|"light") then call refresh_theme() on all UI components.
"""
from __future__ import annotations
import platform

DARK: dict = {
    "name":           "dark",
    "bg":             "#121212",
    "surface":        "#1a1a1a",
    "surface2":       "#222222",
    "surface3":       "#2e2e2e",
    "border":         "rgba(255,255,255,0.07)",
    "border_med":     "rgba(255,255,255,0.12)",
    "border_hi":      "rgba(255,255,255,0.22)",
    "text":           "#e0e0e0",
    "text2":          "#aaaaaa",
    "text3":          "#555555",
    "accent":         "#4a9eff",
    "accent_h":       "#5aabff",
    "accent_p":       "#3a8eee",
    "card_bg":        "#252525",
    "card_h":         "#2e2e2e",
    "cell_bg":        "#1a1a1a",
    "cell_h":         "#222222",
    "cell_filled":    "#1e1e1e",
    "input_bg":       "rgba(255,255,255,0.05)",
    "input_bg_f":     "rgba(255,255,255,0.08)",
    "dlg_bg":         "#1a1a1a",
    "hdr_bg":         "#1a1a1a",
    "nav_bg":         "#161616",
    "scroll":         "rgba(255,255,255,0.2)",
    "scroll_h":       "rgba(255,255,255,0.35)",
    "sel_bg":         "#1e2f4a",
    "danger":         "#ef4444",
    "success":        "#22c55e",
    "warn":           "#f59e0b",
}

LIGHT: dict = {
    "name":           "light",
    "bg":             "#F8FAFC",
    "surface":        "#FFFFFF",
    "surface2":       "#F1F5F9",
    "surface3":       "#E2E8F0",
    "border":         "#E2E8F0",
    "border_med":     "#CBD5E1",
    "border_hi":      "#94A3B8",
    "text":           "#0F172A",
    "text2":          "#475569",
    "text3":          "#94A3B8",
    "accent":         "#3B82F6",
    "accent_h":       "#2563EB",
    "accent_p":       "#1D4ED8",
    "card_bg":        "#FFFFFF",
    "card_h":         "#F8FAFC",
    "cell_bg":        "#FFFFFF",
    "cell_h":         "#F8FAFC",
    "cell_filled":    "#FAFBFF",
    "input_bg":       "#FFFFFF",
    "input_bg_f":     "#F8FAFC",
    "dlg_bg":         "#FFFFFF",
    "hdr_bg":         "#FFFFFF",
    "nav_bg":         "#F8FAFC",
    "scroll":         "#CBD5E1",
    "scroll_h":       "#94A3B8",
    "sel_bg":         "#EFF6FF",
    "danger":         "#ef4444",
    "success":        "#22c55e",
    "warn":           "#f59e0b",
}

_current: dict = DARK


def current() -> dict:
    return _current


def name() -> str:
    return _current["name"]


def is_dark() -> bool:
    return _current["name"] == "dark"


def set_theme(theme_name: str) -> dict:
    global _current
    _current = DARK if theme_name == "dark" else LIGHT
    return _current


def detect_system() -> str:
    """Try to read Windows registry for system theme preference."""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if val == 1 else "dark"
    except Exception:
        pass
    return "dark"
