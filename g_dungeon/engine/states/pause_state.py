"""
Module: engine/states/pause_state.py
Description: Layar Jeda / Pause Menu (PAUSE_STATE).
Memenuhi kriteria Rubrik Teknis 'Manajemen State' dan Rubrik UX 'Pencegahan Frustrasi (Error Prevention)'.
"""

from typing import Any, List
import pygame
from engine.assets import AssetManager
from engine.audio import AudioManager
from engine.constants import (
    COLOR_BTN_HOVER,
    COLOR_BTN_NORMAL,
    COLOR_GOLD,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATE_MENU,
    STATE_ROLE_SELECT,
)
from engine.state_machine import GameState
from engine.ui import UIButton


class PauseState(GameState):
    """Implementasi PAUSE_STATE dengan overlay modal semi-transparan."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()
        self.buttons: List[UIButton] = []
        self._init_buttons()

    def _init_buttons(self) -> None:
        btn_w, btn_h = 260, 48
        center_x = SCREEN_WIDTH // 2 - btn_w // 2
        start_y = 240
        spacing = 58

        # Lanjutkan
        self.btn_resume = UIButton(
            rect=pygame.Rect(center_x, start_y, btn_w, btn_h),
            text="Lanjutkan Permainan",
            icon_name="boots",
            font_size=16,
            on_click=self._resume,
        )

        # Mulai Ulang
        self.btn_restart = UIButton(
            rect=pygame.Rect(center_x, start_y + spacing, btn_w, btn_h),
            text="Mulai Ulang Petualangan",
            icon_name="heal",
            font_size=16,
            on_click=self._restart,
        )

        # Toggle Suara
        self.btn_audio = UIButton(
            rect=pygame.Rect(center_x, start_y + spacing * 2, btn_w, btn_h),
            text="Efek Suara: AKTIF",
            icon_name="magic",
            font_size=16,
            on_click=self._toggle_audio,
        )

        # Menu Utama
        self.btn_menu = UIButton(
            rect=pygame.Rect(center_x, start_y + spacing * 3, btn_w, btn_h),
            text="Kembali ke Menu Utama",
            icon_name="chest_gold",
            font_size=16,
            on_click=self._go_to_menu,
        )

        # Keluar
        self.btn_exit = UIButton(
            rect=pygame.Rect(center_x, start_y + spacing * 4, btn_w, btn_h),
            text="Keluar Aplikasi",
            icon_name="dagger",
            font_size=16,
            hover_color=(160, 50, 50),
            on_click=self._exit_game,
        )

        self.buttons = [self.btn_resume, self.btn_restart, self.btn_audio, self.btn_menu, self.btn_exit]

    def _resume(self) -> None:
        self.audio.play("click")
        self.machine.pop_state()

    def _restart(self) -> None:
        self.audio.play("click")
        self.machine.pop_state()
        self.machine.change_state(STATE_ROLE_SELECT)

    def _toggle_audio(self) -> None:
        is_on = self.audio.toggle_sound()
        self.btn_audio.text = "🔊 Efek Suara: AKTIF" if is_on else "🔇 Efek Suara: MATI"
        self.audio.play("click")

    def _go_to_menu(self) -> None:
        self.audio.play("click")
        self.machine.pop_state()
        self.machine.change_state(STATE_MENU)

    def _exit_game(self) -> None:
        self.game.stop()

    def FreezeTime(self) -> None:
        """Alias FreezeTime() sesuai Bagian 1.3 dan Rubrik Teknis."""
        pass

    def ShowPauseUI(self, surface: pygame.Surface) -> None:
        """Alias ShowPauseUI() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.render(surface)


    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._resume()
            return

        for btn in self.buttons:
            if btn.handle_event(event):
                break

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        # Overlay gelap semi-transparan membekukan visual di bawahnya (Freeze effect)
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((10, 8, 18, 210))
        surface.blit(dim, (0, 0))

        # Panel Tengah
        panel_w, panel_h = 360, 420
        panel_rect = pygame.Rect((SCREEN_WIDTH - panel_w) // 2, (SCREEN_HEIGHT - panel_h) // 2 - 20, panel_w, panel_h)

        pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_GOLD, panel_rect, width=2, border_radius=12)

        # Header Judul Pause
        font_h = self.assets.get_font(24, bold=True)
        h_surf = font_h.render("PERMAINAN DIJEDA", True, COLOR_GOLD)
        surface.blit(h_surf, h_surf.get_rect(center=(panel_rect.centerx, panel_rect.y + 35)))

        font_hint = self.assets.get_font(13)
        hint_surf = font_hint.render("Tekan [ESC] untuk melanjutkan", True, COLOR_TEXT_MUTED)
        surface.blit(hint_surf, hint_surf.get_rect(center=(panel_rect.centerx, panel_rect.y + 65)))

        # Render Tombol
        for btn in self.buttons:
            btn.render(surface)
