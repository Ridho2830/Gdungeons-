"""
Module: engine/states/puzzle_state.py
Description: Layar Teka-Teki Grafis Interaktif (PUZZLE_STATE):
1. 8-Puzzle 3x3 Sliding Tile (Labyrinth Tower)
2. Bejana Reaksi Sortir Warna / Stack LIFO (The Eternal Relic)
3. Quest Ban Berjalan / Queue FIFO (Village Workshop)
"""

from typing import Any, List, Optional, Tuple
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
from core.dungeon_graph import RoomEvent
from puzzles.sliding_puzzle import SlidingPuzzle
from puzzles.color_stack_puzzle import ColorStackPuzzle
from puzzles.conveyor_quest import ConveyorQuest


class PuzzleState(GameState):
    """Pengelola visual interaktif untuk ketiga minigame algoritma."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.puzzle_type: RoomEvent = RoomEvent.PUZZLE_SLIDING
        self.sliding_puzzle: SlidingPuzzle = SlidingPuzzle()
        self.stack_puzzle: ColorStackPuzzle = ColorStackPuzzle()
        self.conveyor_quest: ConveyorQuest = ConveyorQuest()

        self.selected_tube_idx: Optional[int] = None
        self.feedback_msg: str = ""
        self.is_solved: bool = False

        self.buttons: List[UIButton] = []
        self._init_buttons()

    def _init_buttons(self) -> None:
        # Tombol Kembali ke Peta
        self.btn_back = UIButton(
            rect=pygame.Rect(40, 30, 160, 40),
            text="Kembali ke Peta",
            icon_name="boots",
            font_size=14,
            on_click=lambda: self.machine.change_state(STATE_EXPLORATION),
        )

        # Tombol Reset Puzzle
        self.btn_reset = UIButton(
            rect=pygame.Rect(SCREEN_WIDTH - 200, 30, 160, 40),
            text="Reset Puzzle",
            icon_name="heal",
            font_size=14,
            hover_color=(160, 60, 60),
            on_click=self._reset_current_puzzle,
        )

        self.buttons = [self.btn_back, self.btn_reset]

    def enter(self, puzzle_type: RoomEvent = RoomEvent.PUZZLE_SLIDING, **kwargs: Any) -> None:
        self.puzzle_type = puzzle_type
        self.feedback_msg = ""
        self.selected_tube_idx = None
        self.is_solved = False

        if puzzle_type == RoomEvent.PUZZLE_SLIDING:
            self.sliding_puzzle.shuffle()
        elif puzzle_type == RoomEvent.PUZZLE_STACK:
            self.stack_puzzle.reset()
        elif puzzle_type == RoomEvent.QUEST_CONVEYOR:
            self.conveyor_quest.reset()

    def _reset_current_puzzle(self) -> None:
        self.audio.play("click")
        self.feedback_msg = "Puzzle direset ke posisi awal."
        if self.puzzle_type == RoomEvent.PUZZLE_SLIDING:
            self.sliding_puzzle.shuffle()
        elif self.puzzle_type == RoomEvent.PUZZLE_STACK:
            self.stack_puzzle.reset()
            self.selected_tube_idx = None
        elif self.puzzle_type == RoomEvent.QUEST_CONVEYOR:
            self.conveyor_quest.reset()

    def handle_event(self, event: pygame.event.Event) -> None:
        for btn in self.buttons:
            if btn.handle_event(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.puzzle_type == RoomEvent.PUZZLE_SLIDING:
                self._handle_sliding_click(event.pos)
            elif self.puzzle_type == RoomEvent.PUZZLE_STACK:
                self._handle_stack_click(event.pos)
            elif self.puzzle_type == RoomEvent.QUEST_CONVEYOR:
                self._handle_conveyor_click(event.pos)

    def _handle_sliding_click(self, pos: Tuple[int, int]) -> None:
        if self.is_solved:
            return

        grid_start_x = (SCREEN_WIDTH - 360) // 2
        grid_start_y = 200
        tile_size = 110
        gap = 10

        for row in range(3):
            for col in range(3):
                tile_idx = row * 3 + col
                tx = grid_start_x + col * (tile_size + gap)
                ty = grid_start_y + row * (tile_size + gap)
                rect = pygame.Rect(tx, ty, tile_size, tile_size)

                if rect.collidepoint(pos):
                    val = self.sliding_puzzle.board[tile_idx]
                    if val != 0 and self.sliding_puzzle.move_by_index(tile_idx):
                        self.audio.play("puzzle")
                        if self.sliding_puzzle.is_solved():
                            if self.game.state_mgr:
                                msg = self.game.state_mgr.on_puzzle_completed("sliding")
                                self._on_puzzle_solved(msg)
                            else:
                                self._on_puzzle_solved("8-Puzzle Terpecahkan! Mendapatkan Fragmen Kristal I!")
                    break

    def _handle_stack_click(self, pos: Tuple[int, int]) -> None:
        if self.is_solved:
            return

        tube_w, tube_h = 90, 240
        start_x = (SCREEN_WIDTH - (4 * tube_w + 3 * 50)) // 2
        start_y = 220

        for i in range(4):
            tx = start_x + i * (tube_w + 50)
            rect = pygame.Rect(tx, start_y, tube_w, tube_h)

            if rect.collidepoint(pos):
                if self.selected_tube_idx is None:
                    # Pilih tabung sumber
                    if self.stack_puzzle.tubes[i]:
                        self.selected_tube_idx = i
                        self.audio.play("click")
                        self.feedback_msg = f"Tabung {i+1} dipilih. Klik tabung tujuan untuk menuangkan."
                else:
                    # Tuang ke tabung target (LIFO Pop -> Push)
                    src = self.selected_tube_idx
                    dst = i
                    if src == dst:
                        self.selected_tube_idx = None
                        self.feedback_msg = "Pilihan tabung dibatalkan."
                    elif self.stack_puzzle.can_pour(src, dst):
                        self.stack_puzzle.pour(src, dst)
                        self.audio.play("puzzle")
                        self.selected_tube_idx = None
                        self.feedback_msg = f"Berhasil menuang warna dari Tabung {src+1} ke Tabung {dst+1}."

                        if self.stack_puzzle.is_solved():
                            if self.game.state_mgr:
                                msg = self.game.state_mgr.on_puzzle_completed("stack")
                                self._on_puzzle_solved(msg)
                            else:
                                self._on_puzzle_solved("Bejana Warna Selesai! Mendapatkan Fragmen Kristal II!")
                    else:
                        self.audio.play("click")
                        self.feedback_msg = "❌ Tidak bisa menuang! Warna harus sama atau tabung tujuan kosong."
                        self.selected_tube_idx = None
                break

    def _handle_conveyor_click(self, pos: Tuple[int, int]) -> None:
        if self.is_solved or self.conveyor_quest.is_finished:
            return

        # Tombol Ambil Item Terdepan
        pick_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, 480, 260, 48)
        if pick_rect.collidepoint(pos):
            front = self.conveyor_quest.front_item
            if front:
                ok, msg = self.conveyor_quest.process_pick(front)
                if ok:
                    self.audio.play("puzzle")
                    self.feedback_msg = f"✅ {msg}"
                else:
                    self.audio.play("click")
                    self.feedback_msg = f"❌ {msg}"

                if self.conveyor_quest.is_finished:
                    if self.game.state_mgr:
                        rew_msg = self.game.state_mgr.on_puzzle_completed("conveyor")
                        self._on_puzzle_solved(rew_msg)
                    else:
                        self._on_puzzle_solved("Quest Ban Berjalan Selesai! Mendapatkan Fragmen Kristal III!")

    def _on_puzzle_solved(self, message: str) -> None:
        self.is_solved = True
        self.audio.play("victory")
        self.feedback_msg = f"🎉 SELAMAT! {message}"

    def HandlePuzzleInput(self, event: pygame.event.Event) -> None:
        """Alias HandlePuzzleInput() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self.handle_event(event)

    def CheckPuzzleSolved(self) -> bool:
        """Alias CheckPuzzleSolved() sesuai Bagian 1.3 dan Rubrik Teknis."""
        if self.puzzle_type == RoomEvent.PUZZLE_SLIDING:
            return self.sliding_puzzle.is_solved()
        elif self.puzzle_type == RoomEvent.PUZZLE_STACK:
            return self.stack_puzzle.is_solved()
        elif self.puzzle_type == RoomEvent.QUEST_CONVEYOR:
            return self.conveyor_quest.is_finished
        return self.is_solved

    def update(self, dt: float) -> None:
        pass


    def render(self, surface: pygame.Surface) -> None:
        # Background teka-teki
        bg_name = "tower_puzzle_bg.png"
        if self.puzzle_type == RoomEvent.PUZZLE_STACK:
            bg_name = "relic_altar_bg.png"
        elif self.puzzle_type == RoomEvent.QUEST_CONVEYOR:
            bg_name = "village_workshop_bg.png"

        bg = self.assets.get_image(bg_name, scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (0, 0))

        # Overlay panel
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 12, 22, 190))
        surface.blit(overlay, (0, 0))

        # Tombol Navigasi
        for btn in self.buttons:
            btn.render(surface)

        # Render Konten Puzzle Spesifik
        if self.puzzle_type == RoomEvent.PUZZLE_SLIDING:
            self._render_sliding_puzzle(surface)
        elif self.puzzle_type == RoomEvent.PUZZLE_STACK:
            self._render_stack_puzzle(surface)
        elif self.puzzle_type == RoomEvent.QUEST_CONVEYOR:
            self._render_conveyor_quest(surface)

        # Pesan Feedback di Bawah
        if self.feedback_msg:
            font_fb = self.assets.get_font(15, bold=True)
            col = COLOR_HP_GREEN if "SELAMAT" in self.feedback_msg or "✅" in self.feedback_msg else COLOR_GOLD
            fb_surf = font_fb.render(self.feedback_msg, True, col)
            surface.blit(fb_surf, fb_surf.get_rect(center=(SCREEN_WIDTH // 2, 650)))

    def _render_sliding_puzzle(self, surface: pygame.Surface) -> None:
        font_h = self.assets.get_font(24, bold=True)
        h_surf = font_h.render("TEKA-TEKI 8-PUZZLE: LABYRINTH TOWER", True, COLOR_GOLD)
        surface.blit(h_surf, h_surf.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        font_desc = self.assets.get_font(14)
        d_surf = font_desc.render(
            f"Geser ubin angka 1 s.d 8 ke petak kosong hingga berurutan. Langkah: {self.sliding_puzzle.move_count}",
            True,
            COLOR_TEXT_WHITE,
        )
        surface.blit(d_surf, d_surf.get_rect(center=(SCREEN_WIDTH // 2, 130)))

        # Frame Grid 3x3
        grid_start_x = (SCREEN_WIDTH - 360) // 2
        grid_start_y = 180
        tile_size = 110
        gap = 10

        frame_rect = pygame.Rect(grid_start_x - 12, grid_start_y - 12, 360 + 24, 360 + 24)
        pygame.draw.rect(surface, (30, 22, 40), frame_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_GOLD, frame_rect, width=3, border_radius=10)

        for row in range(3):
            for col in range(3):
                tile_idx = row * 3 + col
                val = self.sliding_puzzle.board[tile_idx]
                tx = grid_start_x + col * (tile_size + gap)
                ty = grid_start_y + row * (tile_size + gap)
                tile_rect = pygame.Rect(tx, ty, tile_size, tile_size)

                if val == 0:
                    # Petak kosong
                    pygame.draw.rect(surface, (18, 14, 25), tile_rect, border_radius=6)
                else:
                    # Ubin berisi angka
                    pygame.draw.rect(surface, (60, 48, 80), tile_rect, border_radius=6)
                    pygame.draw.rect(surface, COLOR_GOLD, tile_rect, width=2, border_radius=6)
                    font_num = self.assets.get_font(36, bold=True)
                    num_surf = font_num.render(str(val), True, COLOR_TEXT_WHITE)
                    surface.blit(num_surf, num_surf.get_rect(center=tile_rect.center))

    def _render_stack_puzzle(self, surface: pygame.Surface) -> None:
        font_h = self.assets.get_font(24, bold=True)
        h_surf = font_h.render("TEKA-TEKI TABUNG SORTIR WARNA (STACK LIFO)", True, COLOR_GOLD)
        surface.blit(h_surf, h_surf.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        font_desc = self.assets.get_font(14)
        d_surf = font_desc.render(
            f"Susun warna yang sama di tiap tabung dengan prinsip Last-In-First-Out. Langkah: {self.stack_puzzle.move_count}",
            True,
            COLOR_TEXT_WHITE,
        )
        surface.blit(d_surf, d_surf.get_rect(center=(SCREEN_WIDTH // 2, 130)))

        tube_w, tube_h = 90, 240
        start_x = (SCREEN_WIDTH - (4 * tube_w + 3 * 50)) // 2
        start_y = 200

        color_map = {
            "Red": (231, 76, 60),
            "Blue": (52, 152, 219),
            "Green": (46, 204, 113),
            "Yellow": (241, 196, 15),
        }

        for i, tube in enumerate(self.stack_puzzle.tubes):
            tx = start_x + i * (tube_w + 50)
            tube_rect = pygame.Rect(tx, start_y, tube_w, tube_h)

            # Latar tabung
            is_sel = (self.selected_tube_idx == i)
            bg_col = (45, 35, 60) if is_sel else (25, 20, 35)
            border_col = COLOR_GOLD if is_sel else (100, 90, 120)

            pygame.draw.rect(surface, bg_col, tube_rect, border_bottom_left_radius=15, border_bottom_right_radius=15)
            pygame.draw.rect(surface, border_col, tube_rect, width=3 if is_sel else 2, border_bottom_left_radius=15, border_bottom_right_radius=15)

            # Render cairan bertumpuk dari bawah ke atas
            block_h = 65
            for block_idx, color_name in enumerate(tube):
                bx = tx + 6
                by = start_y + tube_h - (block_idx + 1) * block_h - 6
                b_rect = pygame.Rect(bx, by, tube_w - 12, block_h - 4)
                col = color_map.get(color_name, (180, 180, 180))
                pygame.draw.rect(surface, col, b_rect, border_radius=4)

                # Label teks warna
                font_c = self.assets.get_font(12, bold=True)
                c_txt = font_c.render(color_name, True, (255, 255, 255))
                surface.blit(c_txt, c_txt.get_rect(center=b_rect.center))

            # Nomor Tabung di bawah
            font_t = self.assets.get_font(14, bold=True)
            t_txt = font_t.render(f"Tabung {i+1}", True, COLOR_GOLD if is_sel else COLOR_TEXT_MUTED)
            surface.blit(t_txt, t_txt.get_rect(center=(tx + tube_w // 2, start_y + tube_h + 25)))

    def _render_conveyor_quest(self, surface: pygame.Surface) -> None:
        font_h = self.assets.get_font(24, bold=True)
        h_surf = font_h.render("QUEST BAN BERJALAN: ANTREAN FIFO (QUEUE)", True, COLOR_GOLD)
        surface.blit(h_surf, h_surf.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        font_desc = self.assets.get_font(14)
        target = self.conveyor_quest.target_item
        score = self.conveyor_quest.score
        d_surf = font_desc.render(
            f"Barang Permintaan Saat Ini: '{target}' | Skor: {score}/5",
            True,
            COLOR_GOLD if target else COLOR_HP_GREEN,
        )
        surface.blit(d_surf, d_surf.get_rect(center=(SCREEN_WIDTH // 2, 130)))

        # Visual Ban Berjalan
        conveyor_rect = pygame.Rect(180, 260, 920, 140)
        pygame.draw.rect(surface, (45, 38, 55), conveyor_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, conveyor_rect, width=3, border_radius=10)

        # Gambar barang-barang di antrean (Kiri = Paling depan / FIFO)
        items = self.conveyor_quest.get_conveyor_items()
        box_w, box_h = 120, 90
        start_x = conveyor_rect.x + 30
        for idx, item_name in enumerate(items):
            bx = start_x + idx * (box_w + 50)
            by = conveyor_rect.y + 25
            b_rect = pygame.Rect(bx, by, box_w, box_h)

            is_front = (idx == 0)
            box_col = (70, 55, 95) if is_front else (40, 32, 50)
            border_col = COLOR_GOLD if is_front else COLOR_PANEL_BORDER

            pygame.draw.rect(surface, box_col, b_rect, border_radius=6)
            pygame.draw.rect(surface, border_col, b_rect, width=2 if is_front else 1, border_radius=6)

            font_i = self.assets.get_font(14, bold=is_front)
            i_surf = font_i.render(item_name, True, COLOR_GOLD if is_front else COLOR_TEXT_WHITE)
            surface.blit(i_surf, i_surf.get_rect(center=b_rect.center))

            if is_front:
                font_tag = self.assets.get_font(11, bold=True)
                tag_surf = font_tag.render("FRONT (FIFO)", True, COLOR_GOLD)
                surface.blit(tag_surf, tag_surf.get_rect(center=(b_rect.centerx, b_rect.y - 12)))

        # Tombol Aksi Ambil Barang Terdepan
        pick_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, 480, 260, 48)
        is_hover = pick_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, COLOR_BTN_HOVER if is_hover else COLOR_BTN_NORMAL, pick_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_GOLD if is_hover else COLOR_PANEL_BORDER, pick_rect, width=2, border_radius=6)

        font_btn = self.assets.get_font(16, bold=True)
        btn_txt = font_btn.render("📦 Ambil Barang Terdepan", True, COLOR_TEXT_WHITE)
        surface.blit(btn_txt, btn_txt.get_rect(center=pick_rect.center))
