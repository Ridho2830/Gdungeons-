"""
Module: engine/states/end_state.py
Description: Layar Hasil Akhir Menang / Kalah (END_STATE).
Memenuhi kriteria Rubrik: 'CalculateFinalScore() & ShowEndingScreen()'.
"""

from typing import Any, List
import pygame
from engine.assets import AssetManager
from engine.audio import AudioManager
from engine.constants import (
    COLOR_BTN_HOVER,
    COLOR_BTN_NORMAL,
    COLOR_GOLD,
    COLOR_HP_GREEN,
    COLOR_HP_RED,
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


class EndState(GameState):
    """Implementasi END_STATE untuk hasil menang atau kalah."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.won: bool = False
        self.reason: str = ""
        self.final_score: int = 0
        self.travel_summary: List[str] = []

        self.buttons: List[UIButton] = []
        self._init_buttons()

    def _init_buttons(self) -> None:
        btn_w, btn_h = 240, 48
        center_x = SCREEN_WIDTH // 2
        y = 610

        self.btn_play_again = UIButton(
            rect=pygame.Rect(center_x - btn_w - 20, y, btn_w, btn_h),
            text="Main Lagi",
            icon_name="heal",
            font_size=16,
            on_click=self._on_play_again,
        )

        self.btn_main_menu = UIButton(
            rect=pygame.Rect(center_x + 20, y, btn_w, btn_h),
            text="Menu Utama",
            icon_name="chest_gold",
            font_size=16,
            on_click=self._on_main_menu,
        )

        self.buttons = [self.btn_play_again, self.btn_main_menu]

    def enter(self, won: bool = False, reason: str = "", **kwargs: Any) -> None:
        self.won = won
        self.reason = reason
        self._calculate_final_score()

        if self.won:
            self.audio.play("victory")
        else:
            self.audio.play("defeat")

    def _calculate_final_score(self) -> None:
        """
        Menghitung skor akhir permainan (CalculateFinalScore) resmi sesuai template:
        Skor = (HP tersisa * 2) + (Gold * 10) + (Teka-teki selesai * 250) - (Total langkah * 5)
        Langkah = jumlah bobot edge yang dilalui di peta graf.
        """
        if not self.game.state_mgr:
            self.final_score = 0
            return

        state = self.game.state_mgr
        self.final_score = state.calculate_final_score()

        # Catat ringkasan rute
        self.travel_summary = [
            f"• Dari {rec.from_location} ➡ {rec.location_name} (Bobot: {rec.distance} langkah)"
            for rec in state.player.travel_history[-6:]
        ]

    def _on_play_again(self) -> None:
        self.audio.play("click")
        self.machine.change_state(STATE_ROLE_SELECT)

    def _on_main_menu(self) -> None:
        self.audio.play("click")
        self.machine.change_state(STATE_MENU)

    def CalculateFinalScore(self) -> int:
        """Alias CalculateFinalScore() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self._calculate_final_score()
        return self.final_score

    def ShowEndingScreen(self, surface: pygame.Surface) -> None:
        """Alias ShowEndingScreen() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.render(surface)


    def handle_event(self, event: pygame.event.Event) -> None:
        for btn in self.buttons:
            if btn.handle_event(event):
                break

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        # Background arena / dark
        bg = self.assets.get_image("main_menu_bg.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (0, 0))

        # Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 12, 22, 225))
        surface.blit(overlay, (0, 0))

        # Kotak Ringkasan
        box_w, box_h = 760, 480
        box_rect = pygame.Rect((SCREEN_WIDTH - box_w) // 2, 90, box_w, box_h)

        pygame.draw.rect(surface, COLOR_PANEL_BG, box_rect, border_radius=12)
        border_col = COLOR_GOLD if self.won else COLOR_HP_RED
        pygame.draw.rect(surface, border_col, box_rect, width=3, border_radius=12)

        # Header Status
        font_h = self.assets.get_font(34, bold=True)
        title_txt = "🎉 KEMENANGAN GEMILANG! 🎉" if self.won else "💀 GAME OVER 💀"
        title_col = COLOR_GOLD if self.won else COLOR_HP_RED
        t_surf = font_h.render(title_txt, True, title_col)
        surface.blit(t_surf, t_surf.get_rect(center=(box_rect.centerx, box_rect.y + 45)))

        # Alasan
        font_sub = self.assets.get_font(16)
        r_surf = font_sub.render(self.reason, True, COLOR_TEXT_WHITE)
        surface.blit(r_surf, r_surf.get_rect(center=(box_rect.centerx, box_rect.y + 90)))

        # Skor Akhir
        font_sc = self.assets.get_font(26, bold=True)
        sc_surf = font_sc.render(f"SKOR AKHIR: {self.final_score} POIN", True, COLOR_GOLD)
        surface.blit(sc_surf, sc_surf.get_rect(center=(box_rect.centerx, box_rect.y + 135)))

        # Garis Pembatas
        pygame.draw.line(
            surface,
            COLOR_PANEL_BORDER,
            (box_rect.x + 40, box_rect.y + 165),
            (box_rect.right - 40, box_rect.y + 165),
            width=2,
        )

        # Statistik Pemain & Riwayat Perjalanan
        font_sec = self.assets.get_font(17, bold=True)
        sec_surf = font_sec.render("📜 Ringkasan Riwayat Petualangan:", True, COLOR_TEXT_MUTED)
        surface.blit(sec_surf, (box_rect.x + 40, box_rect.y + 185))

        font_item = self.assets.get_font(14)
        y = box_rect.y + 220
        for entry in self.travel_summary:
            e_surf = font_item.render(entry, True, COLOR_TEXT_WHITE)
            surface.blit(e_surf, (box_rect.x + 40, y))
            y += 24

        # Detail Tambahan
        if self.game.state_mgr:
            p = self.game.state_mgr.player
            p_stat = f"Karakter: {p.name} ({p.role.value}) | Total Perjalanan: {len(p.travel_history)} langkah"
            p_surf = font_sec.render(p_stat, True, COLOR_GOLD)
            surface.blit(p_surf, (box_rect.x + 40, box_rect.bottom - 50))

        # Render Tombol
        for btn in self.buttons:
            btn.render(surface)
