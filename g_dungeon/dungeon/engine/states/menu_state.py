"""
Module: engine/states/menu_state.py
Description: Layar Menu Utama (MENU_STATE). Menampilkan latar pixel art, logo, dan menu navigasi.
"""

from typing import Any, List, Optional
import pygame
from engine.assets import AssetManager
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
    STATE_ROLE_SELECT,
)
from engine.state_machine import GameState
from engine.ui import RolesGuideModal, UIButton


class MenuState(GameState):
    """Implementasi MENU_STATE sesuai rubrik penilaian."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.buttons: List[UIButton] = []
        self.show_about_modal: bool = False
        self.show_roles_modal: bool = False
        self.roles_modal: Optional[RolesGuideModal] = None
        self._init_ui()

    def _init_ui(self) -> None:
        center_x = SCREEN_WIDTH // 2
        start_y = 380
        btn_w, btn_h = 240, 52
        spacing = 65

        # Tombol Mulai Petualangan
        self.buttons.append(
            UIButton(
                rect=pygame.Rect(center_x - btn_w // 2, start_y, btn_w, btn_h),
                text="Mulai Petualangan",
                icon_name="atk",
                font_size=18,
                on_click=self._on_play_clicked,
            )
        )

        # Tombol Tentang Role
        self.buttons.append(
            UIButton(
                rect=pygame.Rect(center_x - btn_w // 2, start_y + spacing, btn_w, btn_h),
                text="Tentang Role",
                icon_name="book_gold",
                font_size=18,
                on_click=self._on_roles_clicked,
            )
        )

        # Tombol Tentang Game
        self.buttons.append(
            UIButton(
                rect=pygame.Rect(center_x - btn_w // 2, start_y + spacing * 2, btn_w, btn_h),
                text="Tentang Game",
                icon_name="book_arcane",
                font_size=18,
                on_click=self._on_about_clicked,
            )
        )

        # Tombol Keluar
        self.buttons.append(
            UIButton(
                rect=pygame.Rect(center_x - btn_w // 2, start_y + spacing * 3, btn_w, btn_h),
                text="Keluar Aplikasi",
                icon_name="dagger",
                font_size=18,
                hover_color=(160, 50, 50),
                on_click=self._on_exit_clicked,
            )
        )

        # Tombol Tutup Modal About
        self.btn_close_about = UIButton(
            rect=pygame.Rect(center_x - 70, 480, 140, 40),
            text="Tutup",
            font_size=16,
            on_click=self._close_about,
        )

    def _on_play_clicked(self) -> None:
        self.machine.change_state(STATE_ROLE_SELECT)

    def _on_roles_clicked(self) -> None:
        self.show_roles_modal = True
        self.roles_modal = RolesGuideModal(on_close=self._close_roles_modal)

    def _close_roles_modal(self) -> None:
        self.show_roles_modal = False
        self.roles_modal = None

    def _on_about_clicked(self) -> None:
        self.show_about_modal = True

    def _close_about(self) -> None:
        self.show_about_modal = False

    def _on_exit_clicked(self) -> None:
        self.game.stop()

    def ShowMenu(self, surface: pygame.Surface) -> None:
        """Alias ShowMenu() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.render(surface)

    def HandleMenuInput(self, event: pygame.event.Event) -> None:
        """Alias HandleMenuInput() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.handle_event(event)


    def handle_event(self, event: pygame.event.Event) -> None:
        if self.show_roles_modal and self.roles_modal:
            self.roles_modal.handle_event(event)
            return

        if self.show_about_modal:
            self.btn_close_about.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.show_about_modal = False
            return

        for btn in self.buttons:
            if btn.handle_event(event):
                break

    def update(self, dt: float) -> None:
        if self.show_roles_modal and self.roles_modal:
            self.roles_modal.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        # Background utama menu
        bg = self.assets.get_image("main_menu_bg.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (0, 0))

        # Overlay tipis agar teks & tombol kontras dan mudah dibaca (UX Readability)
        dark_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dark_overlay.fill((10, 8, 15, 110))
        surface.blit(dark_overlay, (0, 0))

        # Logo Game
        logo = self.assets.get_image("menu_title_logo.png")
        if logo:
            logo_rect = logo.get_rect(center=(SCREEN_WIDTH // 2, 210))
            surface.blit(logo, logo_rect)
        else:
            font_title = self.assets.get_font(46, bold=True)
            title_surf = font_title.render("G - D U N G E O N S", True, COLOR_GOLD)
            surface.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, 200)))

        # Subtitle
        font_sub = self.assets.get_font(18)
        sub_surf = font_sub.render("Edisi Grafis PyGame - Petualangan RPG & Struktur Data", True, COLOR_TEXT_MUTED)
        surface.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH // 2, 315)))

        # Tombol-tombol navigasi
        for btn in self.buttons:
            btn.render(surface)

        # Modal 'Tentang Role'
        if self.show_roles_modal and self.roles_modal:
            self.roles_modal.render(surface)

        # Modal 'Tentang Game'
        if self.show_about_modal:
            self._render_about_modal(surface)

    def _render_about_modal(self, surface: pygame.Surface) -> None:
        # Gelapkan latar
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 180))
        surface.blit(dim_surf, (0, 0))

        box_w, box_h = 600, 340
        box_rect = pygame.Rect((SCREEN_WIDTH - box_w) // 2, (SCREEN_HEIGHT - box_h) // 2, box_w, box_h)

        pygame.draw.rect(surface, COLOR_PANEL_BG, box_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_GOLD, box_rect, width=2, border_radius=10)

        font_h = self.assets.get_font(22, bold=True)
        h_surf = font_h.render("Tentang G-Dungeons", True, COLOR_GOLD)
        surface.blit(h_surf, (box_rect.x + 30, box_rect.y + 25))

        lines = [
            "Game RPG 2D berbasis PyGame dengan integrasi konsep Algoritma & Struktur Data:",
            "• Graph & Dijkstra Algorithm (Navigasi dungeon & skill Map Vision)",
            "• Stack LIFO (Puzzle bejana warna The Eternal Relic)",
            "• Queue FIFO (Quest pesanan ban berjalan Village)",
            "• 8-Puzzle Matriks & Inversion Parity (Labyrinth Tower)",
            "• Turn-Based Battle dengan sistem Rage Monster Kaiju & Indikator Armor",
        ]

        font_body = self.assets.get_font(14)
        y = box_rect.y + 70
        for line in lines:
            line_surf = font_body.render(line, True, COLOR_TEXT_WHITE)
            surface.blit(line_surf, (box_rect.x + 30, y))
            y += 28

        self.btn_close_about.render(surface)
