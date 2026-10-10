"""
Module: ui/app.py
Description: Controller utama aplikasi CustomTkinter (App Window & View Switcher).
"""

from typing import Optional
import customtkinter as ctk

from core.game_state import GameStateManager
from core.monster import Monster
from core.player import PlayerRole
from ui.theme import BG_DARK
from ui.views import (
    CombatView, DialogForestView, ExplorationView, MainMenuView,
    RoleSelectView, SlidingPuzzleView, ColorStackPuzzleView, ConveyorQuestView
)


class GDungeonApp(ctk.CTk):
    """Jendela utama aplikasi dan pengontrol perpindahan layar (View Controller)."""

    def __init__(self) -> None:
        super().__init__()

        # Konfigurasi Window
        self.title("G-Dungeons RPG (Python GUI Edition)")
        self.geometry("980x680")
        self.minsize(880, 600)
        self.configure(fg_color=BG_DARK)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Maksimalkan ukuran window saat startup
        self.after(0, self._maximize_window)

        # Game State
        self.game_state: Optional[GameStateManager] = None

        # Container Frame untuk View aktif
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.current_view: Optional[ctk.CTkFrame] = None

        # Mulai dari Main Menu
        self.show_main_menu()

    def _maximize_window(self) -> None:
        """Memaksimalkan window aplikasi ke ukuran layar penuh (maximized)."""
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                pass

    def set_view(self, new_view: ctk.CTkFrame) -> None:
        """Mengganti view lama dengan view yang baru."""
        if self.current_view is not None:
            self.current_view.destroy()
        self.current_view = new_view
        self.current_view.pack(fill="both", expand=True)

    # ==================== VIEW SWITCHERS ====================

    def show_main_menu(self) -> None:
        """Menampilkan menu awal."""
        self.set_view(MainMenuView(self.container, self))

    def show_role_select(self) -> None:
        """Menampilkan form pembuatan karakter."""
        self.set_view(RoleSelectView(self.container, self))

    def start_game(self, player_name: str, role: PlayerRole) -> None:
        """Menginisialisasi GameStateManager baru dan memulai eksplorasi."""
        self.game_state = GameStateManager(player_name=player_name, role=role)
        self.show_exploration()

    def show_exploration(self) -> None:
        """Menampilkan layar peta & navigasi dungeon."""
        if not self.game_state:
            self.show_main_menu()
            return
        self.set_view(ExplorationView(self.container, self))

    def show_combat(self, monster: Monster) -> None:
        """Menampilkan arena pertarungan melawan monster."""
        self.set_view(CombatView(self.container, self, monster))

    def show_sliding_puzzle(self) -> None:
        """Menampilkan 8-Puzzle di Labyrinth Tower."""
        self.set_view(SlidingPuzzleView(self.container, self))

    def show_stack_puzzle(self) -> None:
        """Menampilkan Puzzle Bejana Warna di The Eternal Relic."""
        self.set_view(ColorStackPuzzleView(self.container, self))

    def show_conveyor_quest(self) -> None:
        """Menampilkan Quest Ban Berjalan di Village."""
        self.set_view(ConveyorQuestView(self.container, self))

    def show_forest_dialogue(self) -> None:
        """Menampilkan dialog dengan Gyoot di Forest."""
        self.set_view(DialogForestView(self.container, self))
