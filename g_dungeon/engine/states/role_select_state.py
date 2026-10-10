"""
Module: engine/states/role_select_state.py
Description: Layar pemilihan peran/karakter pemain (Knight vs Mage), input nama hero,
dan integrasi panduan perbandingan role (Tentang Role) bertema Pixel RPG retro.
Sesuai persis dengan Dokumen Perencanaan & Rubrik Penilaian Game.
"""

from typing import Any, List, Optional, Tuple
import pygame
from engine.assets import AssetManager
from engine.audio import AudioManager
from engine.constants import (
    COLOR_BTN_HOVER,
    COLOR_BTN_NORMAL,
    COLOR_DEFENSE_BLUE,
    COLOR_GOLD,
    COLOR_HP_GREEN,
    COLOR_HP_RED,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATE_EXPLORATION,
    STATE_MENU,
)
from engine.entities import AnimatedSprite
from engine.state_machine import GameState
from engine.ui import RolesGuideModal, UIButton
from core.player import PlayerRole, ROLE_CONFIGS


class RoleSelectState(GameState):
    """Layar pemilihan peran pahlawan lengkap dengan live animated sprite, kartu interaktif, dan panduan role."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.selected_role: PlayerRole = PlayerRole.KNIGHT
        self.player_name: str = "Pahlawan"
        self.input_active: bool = False

        # Area kartu kedua kelas
        self.card_fighter_rect = pygame.Rect(150, 135, 450, 495)
        self.card_mage_rect = pygame.Rect(680, 135, 450, 495)
        self.name_box_rect = pygame.Rect(440, 82, 400, 38)

        # Modal 'Tentang Role'
        self.show_roles_modal: bool = False
        self.roles_modal: Optional[RolesGuideModal] = None

        # Preview animasi sprite
        self.knight_preview: Optional[AnimatedSprite] = None
        self.wizard_preview: Optional[AnimatedSprite] = None

        self.buttons: List[UIButton] = []
        self._init_previews()
        self._init_ui()

    def _init_previews(self) -> None:
        """Memuat sprite sheet IDLE Knight dan Wizard yang telah di-crop presisi."""
        knight_frames = self.assets.get_cropped_knight_idle_frames((110, 120))
        wizard_frames = self.assets.get_cropped_wizard_idle_frames((120, 110))

        # Posisi tepat di tengah sprite box masing-masing kartu
        k_cx = self.card_fighter_rect.x + (450 - 110) // 2
        k_cy = self.card_fighter_rect.y + 60
        self.knight_preview = AnimatedSprite(k_cx, k_cy, {"idle": knight_frames}, "idle", fps=8.0)

        w_cx = self.card_mage_rect.x + (450 - 120) // 2
        w_cy = self.card_mage_rect.y + 65
        self.wizard_preview = AnimatedSprite(w_cx, w_cy, {"idle": wizard_frames}, "idle", fps=7.0)

    def _init_ui(self) -> None:
        """Menyusun tombol seleksi dan navigasi."""
        # Tombol Pilih di dalam kartu
        self.btn_select_fighter = UIButton(
            rect=pygame.Rect(self.card_fighter_rect.x + 20, self.card_fighter_rect.y + 430, 410, 48),
            text="PILIH KNIGHT",
            icon_name="armor_iron",
            font_size=15,
            on_click=lambda: self._set_role(PlayerRole.KNIGHT),
        )

        self.btn_select_mage = UIButton(
            rect=pygame.Rect(self.card_mage_rect.x + 20, self.card_mage_rect.y + 430, 410, 48),
            text="PILIH MAGE",
            icon_name="robe_arcane",
            font_size=15,
            on_click=lambda: self._set_role(PlayerRole.MAGE),
        )

        # Tombol Navigasi Bawah
        self.btn_back = UIButton(
            rect=pygame.Rect(150, 650, 150, 46),
            text="Kembali",
            icon_name="boots",
            font_size=15,
            on_click=lambda: self.machine.change_state(STATE_MENU),
        )

        self.btn_roles_guide = UIButton(
            rect=pygame.Rect(320, 650, 240, 46),
            text="Tentang Role",
            icon_name="book_gold",
            font_size=15,
            hover_color=(120, 90, 40),
            on_click=self._open_roles_guide,
        )

        self.btn_start = UIButton(
            rect=pygame.Rect(680, 650, 450, 46),
            text="Masuk ke Dungeon >>",
            icon_name="sword_gold",
            font_size=17,
            bg_color=(30, 60, 140),
            hover_color=(45, 90, 210),
            on_click=self._on_start_game,
        )

        self.buttons = [
            self.btn_select_fighter,
            self.btn_select_mage,
            self.btn_back,
            self.btn_roles_guide,
            self.btn_start,
        ]
        self._update_selection_buttons()

    def _open_roles_guide(self) -> None:
        self.show_roles_modal = True
        self.roles_modal = RolesGuideModal(on_close=self._close_roles_guide)

    def _close_roles_guide(self) -> None:
        self.show_roles_modal = False
        self.roles_modal = None

    def _set_role(self, role: PlayerRole) -> None:
        if self.selected_role != role:
            self.selected_role = role
            self.audio.play("click")
            self._update_selection_buttons()

    def _update_selection_buttons(self) -> None:
        """Memperbarui teks dan warna tombol pemilihan sesuai status aktif."""
        if self.selected_role == PlayerRole.KNIGHT:
            self.btn_select_fighter.text = "HERO TERPILIH (KNIGHT)"
            self.btn_select_fighter.bg_color = (180, 130, 30)
            self.btn_select_fighter.hover_color = (210, 160, 40)
            self.btn_select_fighter.text_color = (255, 255, 255)

            self.btn_select_mage.text = "PILIH MAGE (PENYIHIR)"
            self.btn_select_mage.bg_color = COLOR_BTN_NORMAL
            self.btn_select_mage.hover_color = COLOR_BTN_HOVER
            self.btn_select_mage.text_color = COLOR_TEXT_WHITE
        else:
            self.btn_select_fighter.text = "PILIH KNIGHT (KSATRIA)"
            self.btn_select_fighter.bg_color = COLOR_BTN_NORMAL
            self.btn_select_fighter.hover_color = COLOR_BTN_HOVER
            self.btn_select_fighter.text_color = COLOR_TEXT_WHITE

            self.btn_select_mage.text = "HERO TERPILIH (MAGE)"
            self.btn_select_mage.bg_color = (180, 130, 30)
            self.btn_select_mage.hover_color = (210, 160, 40)
            self.btn_select_mage.text_color = (255, 255, 255)

    def _on_start_game(self) -> None:
        final_name = self.player_name.strip() if self.player_name.strip() else "Pahlawan"
        self.audio.play("victory")
        self.game.start_new_game(final_name, self.selected_role)
        self.machine.change_state(STATE_EXPLORATION)

    def ShowRoles(self, surface: pygame.Surface) -> None:
        """Alias ShowRoles() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.render(surface)

    def ConfirmRole(self) -> None:
        """Alias ConfirmRole() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self._on_start_game()


    def handle_event(self, event: pygame.event.Event) -> None:
        if self.show_roles_modal and self.roles_modal:
            self.roles_modal.handle_event(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.name_box_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False

            if self.card_fighter_rect.collidepoint(event.pos):
                self._set_role(PlayerRole.KNIGHT)
            elif self.card_mage_rect.collidepoint(event.pos):
                self._set_role(PlayerRole.MAGE)

        if event.type == pygame.KEYDOWN and self.input_active:
            if event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.input_active = False
            elif len(self.player_name) < 16 and event.unicode.isprintable():
                self.player_name += event.unicode

        for btn in self.buttons:
            if btn.handle_event(event):
                break

    def update(self, dt: float) -> None:
        if self.show_roles_modal and self.roles_modal:
            self.roles_modal.update(dt)
            return

        if self.knight_preview:
            self.knight_preview.update(dt)
        if self.wizard_preview:
            self.wizard_preview.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        bg = self.assets.get_image("main_menu_bg.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (0, 0))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((12, 10, 18, 195))
        surface.blit(overlay, (0, 0))

        font_h = self.assets.get_font(24, bold=True)
        title_s = font_h.render("PEMILIHAN HERO & PERAN", True, COLOR_GOLD)
        surface.blit(title_s, title_s.get_rect(center=(SCREEN_WIDTH // 2, 32)))

        font_sub = self.assets.get_font(13)
        sub_s = font_sub.render(
            "Tentukan identitas dan kelas petualanganmu sebelum melangkah masuk ke dalam dungeon",
            True,
            COLOR_TEXT_MUTED,
        )
        surface.blit(sub_s, sub_s.get_rect(center=(SCREEN_WIDTH // 2, 56)))

        # Input Nama Karakter
        font_label = self.assets.get_font(15, bold=True)
        lbl_surf = font_label.render("Nama Pahlawan:", True, COLOR_GOLD)
        surface.blit(lbl_surf, (285, 91))

        box_border = COLOR_GOLD if self.input_active else COLOR_PANEL_BORDER
        pygame.draw.rect(surface, (20, 17, 28), self.name_box_rect, border_radius=6)
        pygame.draw.rect(surface, box_border, self.name_box_rect, width=2, border_radius=6)

        font_in = self.assets.get_font(16)
        cursor = "|" if self.input_active and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        txt_display = (self.player_name if self.player_name else "Pahlawan") + cursor
        txt_col = COLOR_TEXT_WHITE if self.player_name else COLOR_TEXT_MUTED
        txt_surf = font_in.render(txt_display, True, txt_col)
        surface.blit(txt_surf, (self.name_box_rect.x + 12, self.name_box_rect.y + 8))

        # Kartu Kiri: KNIGHT
        self._render_hero_card(
            surface,
            rect=self.card_fighter_rect,
            role=PlayerRole.KNIGHT,
            title="KNIGHT (KSATRIA)",
            subtitle="Ironclad Fortitude & Frontline Shield",
            accent_color=(239, 68, 68),
            icon_key="armor_iron",
            preview=self.knight_preview,
            is_selected=(self.selected_role == PlayerRole.KNIGHT),
            stats={"HP": 1500, "ATK": 65, "DEF": 45},
            skill_title="Pasif: Ironclad Fortitude",
            skill_icon="armor_emerald",
            skill_lines=[
                "• Damage fisik musuh berkurang 20% otomatis.",
                "• Memiliki kapasitas HP 1500 dan Pertahanan 45 DEF.",
                "• Aksi Bertahan memberi Shield +80 meredam serangan.",
            ],
        )

        # Kartu Kanan: MAGE
        self._render_hero_card(
            surface,
            rect=self.card_mage_rect,
            role=PlayerRole.MAGE,
            title="MAGE (PENYIHIR)",
            subtitle="Arcane Intellect & Map Vision",
            accent_color=(167, 139, 250),
            icon_key="robe_arcane",
            preview=self.wizard_preview,
            is_selected=(self.selected_role == PlayerRole.MAGE),
            stats={"HP": 1100, "ATK": 95, "DEF": 25},
            skill_title="Pasif: Map Vision (Dijkstra)",
            skill_icon="book_gold",
            skill_lines=[
                "• Rute terpendek Dijkstra otomatis ter-highlight di peta.",
                "• Serangan sihir mematikan 95 ATK (Arcane Surge 1.8x).",
                "• Memindai rute tercepat ke Boss Lair dan teka-teki.",
            ],
        )

        for btn in self.buttons:
            btn.render(surface)

        if self.show_roles_modal and self.roles_modal:
            self.roles_modal.render(surface)

    def _render_hero_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        role: PlayerRole,
        title: str,
        subtitle: str,
        accent_color: Tuple[int, int, int],
        icon_key: str,
        preview: Optional[AnimatedSprite],
        is_selected: bool,
        stats: dict,
        skill_title: str,
        skill_icon: str,
        skill_lines: List[str],
    ) -> None:
        bg_col = (28, 24, 38) if is_selected else (18, 15, 24)
        border_col = COLOR_GOLD if is_selected else (60, 50, 75)
        border_w = 3 if is_selected else 1

        pygame.draw.rect(surface, bg_col, rect, border_radius=12)
        pygame.draw.rect(surface, border_col, rect, width=border_w, border_radius=12)

        if is_selected:
            badge_rect = pygame.Rect(rect.right - 130, rect.y + 10, 115, 24)
            pygame.draw.rect(surface, (180, 130, 30), badge_rect, border_radius=4)
            font_badge = self.assets.get_font(11, bold=True)
            b_txt = font_badge.render("[ TERPILIH ]", True, (255, 255, 255))
            surface.blit(b_txt, b_txt.get_rect(center=badge_rect.center))

        font_t = self.assets.get_font(18, bold=True)
        icon_s = self.assets.get_rpg_icon(icon_key, size=(22, 22))
        t_col = COLOR_GOLD if is_selected else accent_color
        txt_t = font_t.render(title, True, t_col)

        if icon_s:
            surface.blit(icon_s, (rect.x + 20, rect.y + 12))
        surface.blit(txt_t, (rect.x + 48, rect.y + 12))

        font_sub = self.assets.get_font(12)
        sub_s = font_sub.render(subtitle, True, COLOR_TEXT_MUTED)
        surface.blit(sub_s, (rect.x + 48, rect.y + 34))

        # Kotak Preview Sprite
        preview_box = pygame.Rect(rect.x + 20, rect.y + 55, 410, 135)
        pygame.draw.rect(surface, (14, 11, 20), preview_box, border_radius=8)
        pygame.draw.rect(surface, (45, 38, 55), preview_box, width=1, border_radius=8)

        if preview:
            preview.render(surface)

        # Baris Bar Status
        bar_y = rect.y + 200
        self._render_stat_row(surface, rect.x + 20, bar_y, "HP (Darah)", stats["HP"], 1500, COLOR_HP_GREEN, "hp")
        self._render_stat_row(surface, rect.x + 20, bar_y + 30, "ATK (Serangan)", stats["ATK"], 100, (235, 87, 87), "atk")
        self._render_stat_row(surface, rect.x + 20, bar_y + 60, "DEF (Pertahanan)", stats["DEF"], 50, COLOR_DEFENSE_BLUE, "def")

        # Deskripsi Pasif & Keunggulan
        skill_box = pygame.Rect(rect.x + 20, rect.y + 295, 410, 125)
        pygame.draw.rect(surface, (22, 18, 30), skill_box, border_radius=6)
        pygame.draw.rect(surface, (55, 45, 70), skill_box, width=1, border_radius=6)

        font_st = self.assets.get_font(13, bold=True)
        st_surf = font_st.render(skill_title, True, COLOR_GOLD)
        surface.blit(st_surf, (skill_box.x + 12, skill_box.y + 8))

        font_desc = self.assets.get_font(11)
        line_y = skill_box.y + 32
        for line in skill_lines:
            l_surf = font_desc.render(line, True, (215, 210, 225))
            surface.blit(l_surf, (skill_box.x + 12, line_y))
            line_y += 18

    def _render_stat_row(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        label: str,
        value: int,
        max_ref: int,
        color: Tuple[int, int, int],
        icon_name: str,
    ) -> None:
        font = self.assets.get_font(12, bold=True)
        lbl = font.render(f"{label}: {value}", True, COLOR_TEXT_WHITE)
        surface.blit(lbl, (x + 28, y))

        icon = self.assets.get_rpg_icon(icon_name, size=(18, 18))
        if icon:
            surface.blit(icon, (x + 4, y - 1))

        bar_rect = pygame.Rect(x + 230, y + 2, 170, 12)
        pygame.draw.rect(surface, (35, 28, 45), bar_rect, border_radius=3)
        pct = min(1.0, value / max_ref)
        if pct > 0:
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_rect.width * pct), bar_rect.height)
            pygame.draw.rect(surface, color, fill_rect, border_radius=3)
        pygame.draw.rect(surface, (60, 50, 75), bar_rect, width=1, border_radius=3)
