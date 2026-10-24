"""UI modules: Desktop trading dashboard with dark mode"""
from .app_window import AppWindow
from .dashboard_view import DashboardView
from .signals_view import SignalsView
from .stats_view import StatsView
from .log_view import LogView
from .backtest_view import BacktestView
from .settings_view import SettingsView

__all__ = [
    "AppWindow",
    "DashboardView",
    "SignalsView",
    "StatsView",
    "LogView",
    "BacktestView",
    "SettingsView",
]
