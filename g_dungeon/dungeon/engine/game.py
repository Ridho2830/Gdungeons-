"""
Module: engine/game.py
Description: Pengontrol Utama Game PyGame (Main Game Engine).
Mengimplementasikan Main Game Loop resmi (Input -> Update -> Render)
dan orkestrasi Finite State Machine.
"""

import sys
from typing import Optional, Union
import pygame

from engine.constants import (
    FPS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATE_COMBAT,
    STATE_DIALOG,
    STATE_END,
    STATE_EXPLORATION,
    STATE_MENU,
    STATE_PAUSE,
    STATE_PUZZLE,
    STATE_ROLE_SELECT,
    TITLE,
)
from engine.assets import AssetManager
from engine.audio import AudioManager
from engine.state_machine import StateMachine
from engine.states.menu_state import MenuState
from engine.states.role_select_state import RoleSelectState
from engine.states.exploration_state import ExplorationState
from engine.states.combat_state import CombatState
from engine.states.puzzle_state import PuzzleState
from engine.states.dialog_state import DialogState
from engine.states.pause_state import PauseState
from engine.states.end_state import EndState
from core.game_state import GameStateManager
from core.player import PlayerRole


class Game:
    """
    Engine utama permainan G-Dungeons berbasis PyGame.
    Menjalankan siklus Main Game Loop terpusat sesuai standar rubrik penilaian game.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()

        # Inisialisasi Jendela Layar
        self.screen: pygame.Surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)

        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.running: bool = True

        # Pengelola Inti
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.state_machine = StateMachine()

        # Model Game State (Domain Logika)
        self.state_mgr: Optional[GameStateManager] = None

        # Daftarkan Seluruh State Resmi ke State Machine
        self._register_states()

        # State Awal: MENU_STATE
        self.state_machine.change_state(STATE_MENU)

    def _register_states(self) -> None:
        """Mendaftarkan seluruh 8 state game ke dalam FSM terpusat."""
        self.state_machine.register_state(STATE_MENU, MenuState(self.state_machine, self))
        self.state_machine.register_state(STATE_ROLE_SELECT, RoleSelectState(self.state_machine, self))
        self.state_machine.register_state(STATE_EXPLORATION, ExplorationState(self.state_machine, self))
        self.state_machine.register_state(STATE_COMBAT, CombatState(self.state_machine, self))
        self.state_machine.register_state(STATE_PUZZLE, PuzzleState(self.state_machine, self))
        self.state_machine.register_state(STATE_DIALOG, DialogState(self.state_machine, self))
        self.state_machine.register_state(STATE_PAUSE, PauseState(self.state_machine, self))
        self.state_machine.register_state(STATE_END, EndState(self.state_machine, self))

    def start_new_game(self, player_name: str, role: Union[PlayerRole, str]) -> None:
        """Memulai sesi permainan baru dengan instansiasi GameStateManager."""
        if isinstance(role, str):
            role_enum = PlayerRole.MAGE if role.lower() == "mage" else PlayerRole.KNIGHT
        else:
            role_enum = role
        self.state_mgr = GameStateManager(player_name=player_name, role=role_enum)

    def change_state(self, state_name: str, **kwargs) -> None:
        """Helper praktis untuk mengganti state pada StateMachine."""
        self.state_machine.change_state(state_name, **kwargs)



    def stop(self) -> None:
        """Menghentikan game loop dan menutup aplikasi secara aman."""
        self.running = False

    def handle_events(self) -> None:
        """
        Tahap 1 Main Game Loop: Pemrosesan Masukan Pengguna (Input Handling).
        Memantau event OS, tombol keyboard, dan interaksi mouse.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.stop()
                return

            # Teruskan event ke State yang sedang aktif
            curr = self.state_machine.current_state
            if curr:
                curr.handle_event(event)

    def update(self, dt: float) -> None:
        """
        Tahap 2 Main Game Loop: Pembaruan Logika Game (Logic Update).
        Menghitung perpindahan posisi, timer animasi, dan aturan game per delta time frame.
        """
        curr = self.state_machine.current_state
        if curr:
            curr.update(dt)

    def render(self) -> None:
        """
        Tahap 3 Main Game Loop: Penggambaran Visual ke Layar (Rendering).
        Menggambar latar belakang, sprite entitas, teks, dan antarmuka HUD.
        """
        # Bersihkan layar dengan warna dasar
        self.screen.fill((15, 12, 22))

        # Jika sedang dalam tumpukan Pause, render dulu state di bawahnya agar terlihat sebagai latar
        if self.state_machine.state_stack:
            for _, bg_state in self.state_machine.state_stack:
                bg_state.render(self.screen)

        # Render state aktif teratas
        curr = self.state_machine.current_state
        if curr:
            curr.render(self.screen)

    def run(self) -> None:
        """
        MAIN GAME LOOP UTAMA
        Siklus ini berjalan terus-menerus memantau input, memperbarui logika (update),
        dan menggambar ulang layar (render) setiap frame (60 FPS) hingga pengguna keluar.
        """
        while self.running:
            # 1. Delta Time & Pembatasan Frame Rate (60 FPS)
            dt = self.clock.tick(FPS) / 1000.0

            # 2. Tangani Input Pengguna
            self.handle_events()

            # 3. Perbarui Logika Permainan
            self.update(dt)

            # 4. Gambar Tampilan Visual
            self.render()

            # 5. Flip Frame Buffer ke Monitor
            pygame.display.flip()

        # Bersihkan resource saat keluar
        pygame.quit()
        sys.exit(0)
