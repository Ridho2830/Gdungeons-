"""
Module: engine/states/dialog_state.py
Description: Layar Percakapan NPC Interaktif (DIALOG_STATE) dengan Elder Tree Gyoot di Hutan Whispering Forest.
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
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATE_EXPLORATION,
)
from engine.state_machine import GameState
from engine.ui import UIButton


class DialogState(GameState):
    """Implementasi interaksi dialog NPC cerita di dalam dungeon."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.speaker_name: str = "Elder Tree Gyoot"
        self.current_text: str = ""
        self.buttons: List[UIButton] = []
        self._init_dialog_choices()

    def _init_dialog_choices(self) -> None:
        btn_w, btn_h = 420, 44
        start_x = (SCREEN_WIDTH - btn_w) // 2
        start_y = 510

        self.btn_lore = UIButton(
            rect=pygame.Rect(start_x, start_y, btn_w, btn_h),
            text="Tanyakan kelemahan Monster Zero",
            icon_name="book_gold",
            on_click=self._on_ask_weakness,
        )

        self.btn_blessing = UIButton(
            rect=pygame.Rect(start_x, start_y + 52, btn_w, btn_h),
            text="Minta Berkah Pohon Purba (+200 HP)",
            icon_name="heal",
            on_click=self._on_ask_blessing,
        )

        self.btn_leave = UIButton(
            rect=pygame.Rect(start_x, start_y + 104, btn_w, btn_h),
            text="Pamit dan Kembali ke Peta",
            icon_name="boots",
            on_click=self._on_leave,
        )

        self.buttons = [self.btn_lore, self.btn_blessing, self.btn_leave]

    def enter(self, **kwargs: Any) -> None:
        self.current_text = (
            "Salam sejahtera, wahai penjelajah. Aku adalah Gyoot, roh penjaga Whispering Forest. "
            "Kekuatan jahat Corrupted Crystal Kaiju di Throne of Extinction telah meracuni labirin ini. "
            "Pintu sarangnya terkunci rapat! Kau wajib mengumpulkan minimal 2 dari 3 Fragmen Kristal dari teka-teki kuno!"
        )
        if self.game.state_mgr:
            self.game.state_mgr.completed_forest_dialogue = True

    def _on_ask_weakness(self) -> None:
        self.audio.play("magic")
        self.current_text = (
            "Dengarkan baik-baik: Corrupted Crystal Kaiju akan memasuki Rage Mode saat HP di bawah 50%! "
            "Dan setiap 5 ronde, ia melepaskan Atomic Breath dahsyat! Gunakan perisai zirah Knight "
            "atau manfaatkan Map Vision dari Mage untuk merencanakan rute terpendek mengumpulkan Fragmen Kristal!"
        )

    def _on_ask_blessing(self) -> None:
        if not self.game.state_mgr:
            return
        p = self.game.state_mgr.player
        p.potions += 1
        p.inventory.add_item("Health Potion", 1, 300)
        healed = p.heal(200)
        self.audio.play("heal")
        self.current_text = (
            f"Kekuatan akar kehidupan meresap ke jiwamu (+{healed} HP) dan aku memberimu 1 Health Potion ekstra! "
            f"(Total Potion: {p.potions}). Semoga keberanian menyertaimu di Throne of Extinction."
        )

    def _on_leave(self) -> None:
        self.audio.play("click")
        self.machine.change_state(STATE_EXPLORATION)

    def ShowDialog(self, surface: pygame.Surface) -> None:
        """Alias ShowDialog() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.render(surface)

    def SelectChoice(self, choice_idx: int) -> None:
        """Alias SelectChoice() sesuai Bagian 1.3 dan Rubrik Teknis."""
        if choice_idx == 0:
            self._on_ask_advice()
        elif choice_idx == 1:
            self._on_ask_blessing()
        elif choice_idx == 2:
            self._on_leave()


    def handle_event(self, event: pygame.event.Event) -> None:
        for btn in self.buttons:
            if btn.handle_event(event):
                break

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        # Background Hutan
        bg = self.assets.get_image("forest_dialog_bg.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (0, 0))

        # Panel Dialog di Bawah
        box_w, box_h = 920, 220
        box_rect = pygame.Rect((SCREEN_WIDTH - box_w) // 2, 260, box_w, box_h)

        pygame.draw.rect(surface, (20, 18, 28, 235), box_rect, border_radius=10)
        pygame.draw.rect(surface, (40, 150, 90), box_rect, width=2, border_radius=10)

        # Nama Pembicara
        font_h = self.assets.get_font(20, bold=True)
        h_surf = font_h.render(f"🌳 {self.speaker_name}", True, COLOR_GOLD)
        surface.blit(h_surf, (box_rect.x + 25, box_rect.y + 18))

        # Teks Dialog
        font_body = self.assets.get_font(15)
        words = self.current_text.split()
        lines = []
        curr_l = ""
        for w in words:
            if len(curr_l + " " + w) > 95:
                lines.append(curr_l)
                curr_l = w
            else:
                curr_l = (curr_l + " " + w).strip()
        if curr_l:
            lines.append(curr_l)

        dy = box_rect.y + 60
        for line in lines:
            l_surf = font_body.render(line, True, COLOR_TEXT_WHITE)
            surface.blit(l_surf, (box_rect.x + 25, dy))
            dy += 24

        # Render Pilihan Tombol Respon
        for btn in self.buttons:
            btn.render(surface)
