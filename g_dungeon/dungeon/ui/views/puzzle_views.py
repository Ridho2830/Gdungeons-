"""
Module: ui/views/puzzle_views.py
Description: Tampilan antarmuka GUI interaktif untuk 3 puzzle permainan
dengan latar belakang tematik Pixel 2D skala penuh (Maximized):
1. SlidingPuzzleView (8-Puzzle 3x3 di Labyrinth Tower - tower_puzzle_bg.png)
2. ColorStackPuzzleView (Bejana Sortir Warna di The Eternal Relic - relic_altar_bg.png)
3. ConveyorQuestView (Ban Berjalan FIFO di Village - village_workshop_bg.png)
"""

from typing import List, Optional
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from core.item import Item
from puzzles.color_stack_puzzle import ColorStackPuzzle
from puzzles.conveyor_quest import ConveyorQuest
from puzzles.sliding_puzzle import SlidingPuzzle
from ui.asset_loader import load_pil_image
from ui.theme import (
    BG_CARD, BG_DARK, BG_PANEL, BORDER_COLOR, COLOR_DANGER, COLOR_GOLD,
    COLOR_PRIMARY, FONT_BODY, FONT_BOLD, FONT_HEADING, FONT_SUBTITLE,
    FONT_TITLE, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY
)


class SlidingPuzzleView(ctk.CTkFrame):
    """GUI untuk 8-Puzzle di Labyrinth Tower berlatar Menara Kuno."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller
        self.puzzle = SlidingPuzzle()

        self._current_w = 1200
        self._current_h = 750
        self._bg_pil: Optional[Image.Image] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # 1. Background Menara Labirin Skala Penuh
        self.setup_background()

        # 2. Card Panel
        card = ctk.CTkFrame(
            self, fg_color="#0F121E", border_color="#3B82F6",
            border_width=2, corner_radius=16, width=560, height=600
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="🧩 LABYRINTH TOWER: 8-PUZZLE 🧩", font=FONT_SUBTITLE, text_color=COLOR_PRIMARY).pack(pady=(22, 4))
        ctk.CTkLabel(card, text="Susun angka 1 sampai 8 secara berurutan. Klik ubin di sebelah kotak kosong untuk menggeser.",
                     font=FONT_BODY, text_color=TEXT_SECONDARY, wraplength=480).pack(pady=(0, 12))

        self.lbl_moves = ctk.CTkLabel(card, text="Langkah: 0", font=FONT_BOLD, text_color=COLOR_GOLD)
        self.lbl_moves.pack(pady=(0, 8))

        # Grid 3x3
        self.grid_frame = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=12)
        self.grid_frame.pack(padx=60, pady=5)

        self.buttons: List[ctk.CTkButton] = []
        for i in range(9):
            btn = ctk.CTkButton(
                self.grid_frame,
                text="",
                font=("Segoe UI", 20, "bold"),
                width=86,
                height=86,
                corner_radius=8,
                command=lambda idx=i: self.on_tile_clicked(idx)
            )
            r, c = divmod(i, 3)
            btn.grid(row=r, column=c, padx=6, pady=6)
            self.buttons.append(btn)

        self.refresh_grid()

        # Action Buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=60, pady=(18, 8))

        ctk.CTkButton(
            btn_frame, text="Acak Ulang", font=FONT_BODY, width=120, height=36,
            fg_color="#374151", hover_color="#4B5563", command=self.reset_puzzle
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="⚡ Selesaikan Instan (Cheat)", font=FONT_BODY, height=36,
            fg_color="#9333EA", hover_color="#7E22CE", command=self.bypass_solve
        ).pack(side="right")

        # Tombol Kembali
        ctk.CTkButton(
            card, text="Kembali ke Eksplorasi", font=FONT_BODY, height=32,
            fg_color="#1E2336", hover_color="#2E344E", command=self.app.show_exploration
        ).pack(side="bottom", pady=12)

        # Bind resize listener
        self.bind("<Configure>", self._on_resize)

    def setup_background(self) -> None:
        """Memuat gambar latar belakang menara labirin skala penuh."""
        self._bg_pil = load_pil_image("backgrounds/tower_puzzle_bg.png")
        if self._bg_pil:
            try:
                self._bg_ctk = ctk.CTkImage(
                    light_image=self._bg_pil,
                    dark_image=self._bg_pil,
                    size=(self._current_w, self._current_h)
                )
                self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                self.bg_label.lift(self._canvas)
            except Exception as e:
                print(f"[SlidingPuzzleView] Gagal memuat background: {e}")

    def _on_resize(self, event) -> None:
        if event.widget in (self, getattr(self, "_canvas", None)):
            w, h = event.width, event.height
            if w < 100 or h < 100:
                return
            if abs(w - self._current_w) > 10 or abs(h - self._current_h) > 10:
                self._current_w = w
                self._current_h = h
                if self._bg_pil and hasattr(self, "bg_label"):
                    self._bg_ctk = ctk.CTkImage(
                        light_image=self._bg_pil,
                        dark_image=self._bg_pil,
                        size=(w, h)
                    )
                    self.bg_label.configure(image=self._bg_ctk)

    def refresh_grid(self) -> None:
        """Memperbarui visual angka pada tombol."""
        for i, val in enumerate(self.puzzle.board):
            btn = self.buttons[i]
            if val == 0:
                btn.configure(text="", fg_color="#181B28", state="disabled")
            else:
                is_movable = self.puzzle.can_move_tile(i)
                btn.configure(
                    text=str(val),
                    fg_color=COLOR_PRIMARY if is_movable else BG_CARD,
                    hover_color="#2563EB" if is_movable else BG_CARD,
                    state="normal" if is_movable else "disabled"
                )
        self.lbl_moves.configure(text=f"Langkah: {self.puzzle.move_count}")

    def on_tile_clicked(self, tile_index: int) -> None:
        """Menangani klik pada petak puzzle."""
        if self.puzzle.move_by_index(tile_index):
            self.refresh_grid()
            if self.puzzle.is_solved():
                self.on_win()

    def reset_puzzle(self) -> None:
        self.puzzle.shuffle()
        self.refresh_grid()

    def bypass_solve(self) -> None:
        """Bypass seperti tombol 'C' pada game aslinya."""
        self.puzzle.board = list(self.puzzle.GOAL_STATE)
        self.refresh_grid()
        self.on_win()

    def on_win(self) -> None:
        """Pemain berhasil menyelesaikan 8-puzzle."""
        self.app.game_state.player.inventory.add_item(
            Item(name="Fire Ball", value=1000, description="Bola api membara yang memberikan 1000 damage dahsyat.")
        )
        self.app.game_state.completed_sliding_puzzle = True
        messagebox.showinfo(
            "Teka-Teki Terpecahkan!",
            "Selamat! Kamu berhasil menyusun Labyrinth Puzzle!\n\n"
            "🎁 Hadiah Didapatkan: [Fire Ball] (+1000 Damage) telah masuk ke tasmu!"
        )
        self.app.show_exploration()


class ColorStackPuzzleView(ctk.CTkFrame):
    """GUI untuk Puzzle Sortir Warna (Stack) di The Eternal Relic berlatar Altar Relik Kuno."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller
        self.puzzle = ColorStackPuzzle()
        self.selected_source = None

        self._current_w = 1200
        self._current_h = 750
        self._bg_pil: Optional[Image.Image] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # 1. Background Altar Relik Skala Penuh
        self.setup_background()

        # 2. Card Panel
        card = ctk.CTkFrame(
            self, fg_color="#0F121E", border_color="#F59E0B",
            border_width=2, corner_radius=16, width=740, height=600
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="⚗️ THE ETERNAL RELIC: COLOR STACK ⚗️", font=FONT_SUBTITLE, text_color="#F59E0B").pack(pady=(22, 4))
        ctk.CTkLabel(card, text="Kelompokkan tiap warna ke dalam tabung yang sama (Maksimal 3 blok per tabung).\n"
                                "Klik tabung sumber untuk mengambil warna teratas, lalu klik tabung tujuan untuk menuang.",
                     font=FONT_BODY, text_color=TEXT_SECONDARY, wraplength=640).pack(pady=(0, 12))

        self.lbl_status = ctk.CTkLabel(card, text="Pilih tabung sumber untuk mulai menuang", font=FONT_BOLD, text_color=COLOR_GOLD)
        self.lbl_status.pack(pady=(0, 8))

        # 4 Tubes Frame
        self.tubes_container = ctk.CTkFrame(card, fg_color="transparent")
        self.tubes_container.pack(fill="both", expand=True, padx=40, pady=5)

        self.tube_widgets = []
        for i in range(4):
            t_frame = ctk.CTkFrame(self.tubes_container, fg_color="#141828", border_color=BORDER_COLOR, border_width=2, corner_radius=10, width=120, height=200)
            t_frame.pack(side="left", expand=True, padx=10, pady=5)
            t_frame.pack_propagate(False)

            lbl_tube_name = ctk.CTkLabel(t_frame, text=f"Tabung {i+1}", font=FONT_BOLD, text_color=TEXT_PRIMARY)
            lbl_tube_name.pack(pady=(8, 4))

            blocks_frame = ctk.CTkFrame(t_frame, fg_color="#0B0E18", corner_radius=6, width=90, height=120)
            blocks_frame.pack(pady=(4, 8), fill="both", expand=True, padx=8)

            btn_select = ctk.CTkButton(
                t_frame, text="Pilih", font=FONT_BODY, height=30,
                fg_color=COLOR_PRIMARY, hover_color="#2563EB",
                command=lambda idx=i: self.on_tube_clicked(idx)
            )
            btn_select.pack(pady=(0, 8), padx=8, fill="x")

            self.tube_widgets.append({"frame": t_frame, "blocks": blocks_frame, "btn": btn_select})

        self.refresh_tubes()

        # Bottom Buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=60, pady=(10, 18))

        ctk.CTkButton(
            btn_frame, text="Reset Posisi", font=FONT_BODY, width=130, height=36,
            fg_color="#374151", hover_color="#4B5563", command=self.reset_tubes
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Kembali ke Eksplorasi", font=FONT_BODY, width=160, height=36,
            fg_color="#4B5563", hover_color="#6B7280", command=self.app.show_exploration
        ).pack(side="right")

        # Bind resize listener
        self.bind("<Configure>", self._on_resize)

    def setup_background(self) -> None:
        """Memuat gambar latar belakang altar relik abadi skala penuh."""
        self._bg_pil = load_pil_image("backgrounds/relic_altar_bg.png")
        if self._bg_pil:
            try:
                self._bg_ctk = ctk.CTkImage(
                    light_image=self._bg_pil,
                    dark_image=self._bg_pil,
                    size=(self._current_w, self._current_h)
                )
                self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                self.bg_label.lift(self._canvas)
            except Exception as e:
                print(f"[ColorStackPuzzleView] Gagal memuat background: {e}")

    def _on_resize(self, event) -> None:
        if event.widget in (self, getattr(self, "_canvas", None)):
            w, h = event.width, event.height
            if w < 100 or h < 100:
                return
            if abs(w - self._current_w) > 10 or abs(h - self._current_h) > 10:
                self._current_w = w
                self._current_h = h
                if self._bg_pil and hasattr(self, "bg_label"):
                    self._bg_ctk = ctk.CTkImage(
                        light_image=self._bg_pil,
                        dark_image=self._bg_pil,
                        size=(w, h)
                    )
                    self.bg_label.configure(image=self._bg_ctk)

    def refresh_tubes(self) -> None:
        """Me-render isi blok warna dalam 4 tabung."""
        for i, tw in enumerate(self.tube_widgets):
            for widget in tw["blocks"].winfo_children():
                widget.destroy()

            tube_items = self.puzzle.get_tube(i)
            for color in reversed(tube_items):
                hex_col = self.puzzle.COLOR_HEX_MAP.get(color, "#6B7280")
                block = ctk.CTkFrame(tw["blocks"], fg_color=hex_col, height=28, corner_radius=4)
                block.pack(fill="x", padx=4, pady=2)
                ctk.CTkLabel(block, text=color, font=("Segoe UI", 10, "bold"), text_color="#FFFFFF").pack()

            if self.selected_source == i:
                tw["frame"].configure(border_color=COLOR_GOLD, border_width=3)
                tw["btn"].configure(text="Batal", fg_color=COLOR_DANGER)
            else:
                tw["frame"].configure(border_color=BORDER_COLOR, border_width=2)
                tw["btn"].configure(text="Pilih", fg_color=COLOR_PRIMARY)

    def on_tube_clicked(self, tube_idx: int) -> None:
        """Memproses aksi klik tabung (sumber -> tujuan)."""
        if self.selected_source is None:
            if not self.puzzle.get_tube(tube_idx):
                self.lbl_status.configure(text=f"Tabung {tube_idx+1} kosong! Pilih tabung lain.")
                return
            self.selected_source = tube_idx
            self.lbl_status.configure(text=f"Warna teratas terpilih dari Tabung {tube_idx+1}. Klik tabung tujuan!")
            self.refresh_tubes()
        else:
            if self.selected_source == tube_idx:
                self.selected_source = None
                self.lbl_status.configure(text="Pilihan dibatalkan.")
                self.refresh_tubes()
                return

            success = self.puzzle.pour(self.selected_source, tube_idx)
            src = self.selected_source
            self.selected_source = None
            self.refresh_tubes()

            if success:
                self.lbl_status.configure(text=f"Berhasil menuang dari Tabung {src+1} ke Tabung {tube_idx+1}!")
                if self.puzzle.is_solved():
                    self.on_win()
            else:
                self.lbl_status.configure(text="Tidak bisa menuang! Warna tidak cocok atau tabung tujuan penuh.")

    def reset_tubes(self) -> None:
        self.puzzle.reset()
        self.selected_source = None
        self.lbl_status.configure(text="Susunan tabung telah direset ke posisi awal.")
        self.refresh_tubes()

    def on_win(self) -> None:
        """Pemain menang puzzle warna."""
        self.app.game_state.player.boost_max_hp(1000)
        self.app.game_state.completed_stack_puzzle = True
        messagebox.showinfo(
            "Relik Abadi Menyala!",
            "Selamat! Seluruh bejana warna tersusun sempurna!\n\n"
            "🎁 Berkah Relik: Daya tahan fisikmu meningkat drastis! (+1000 Max HP)!"
        )
        self.app.show_exploration()


class ConveyorQuestView(ctk.CTkFrame):
    """GUI untuk Quest Ban Berjalan (Queue FIFO) di Village berlatar Bengkel Desa."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller
        self.quest = ConveyorQuest()

        self._current_w = 1200
        self._current_h = 750
        self._bg_pil: Optional[Image.Image] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # 1. Background Bengkel Desa Skala Penuh
        self.setup_background()

        # 2. Card Panel
        card = ctk.CTkFrame(
            self, fg_color="#0F121E", border_color="#10B981",
            border_width=2, corner_radius=16, width=760, height=540
        )
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="🏭 VILLAGE: CONVEYOR BELT QUEST 🏭", font=FONT_SUBTITLE, text_color="#10B981").pack(pady=(22, 4))
        ctk.CTkLabel(card, text="Ban berjalan mengantarkan barang secara antrean FIFO. Ambil item yang berada di depan sesuai permintaan!",
                     font=FONT_BODY, text_color=TEXT_SECONDARY, wraplength=640).pack(pady=(0, 12))

        self.lbl_score = ctk.CTkLabel(card, text="Skor: 0 | Giliran: 1 / 5", font=FONT_BOLD, text_color=COLOR_GOLD)
        self.lbl_score.pack(pady=(0, 8))

        # Target Item Box
        self.target_box = ctk.CTkFrame(card, fg_color="#141828", corner_radius=8)
        self.target_box.pack(fill="x", padx=60, pady=5)

        self.lbl_instruction = ctk.CTkLabel(self.target_box, text="", font=FONT_HEADING, text_color="#38BDF8")
        self.lbl_instruction.pack(pady=10)

        # Visual Conveyor
        ctk.CTkLabel(card, text="Ban Berjalan (Depan ➔ Belakang):", font=FONT_BOLD, text_color=TEXT_PRIMARY).pack(pady=(10, 4))
        self.belt_frame = ctk.CTkFrame(card, fg_color=BG_CARD, corner_radius=8, height=70)
        self.belt_frame.pack(fill="x", padx=60, pady=5)

        # Buttons Frame
        self.actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=60, pady=16)

        self.item_buttons = []
        for item in ["Potion", "Sword", "Shield", "Bow", "Ring"]:
            btn = ctk.CTkButton(
                self.actions_frame, text=item, font=FONT_BOLD, height=38,
                fg_color=COLOR_PRIMARY, hover_color="#2563EB",
                command=lambda it=item: self.pick_item(it)
            )
            btn.pack(side="left", expand=True, padx=4)
            self.item_buttons.append(btn)

        # Tombol Kembali
        ctk.CTkButton(
            card, text="Kembali ke Eksplorasi", font=FONT_BODY, height=32,
            fg_color="#1E2336", hover_color="#2E344E", command=self.app.show_exploration
        ).pack(side="bottom", pady=12)

        self.refresh_view()

        # Bind resize listener
        self.bind("<Configure>", self._on_resize)

    def setup_background(self) -> None:
        """Memuat gambar latar belakang bengkel desa skala penuh."""
        self._bg_pil = load_pil_image("backgrounds/village_workshop_bg.png")
        if self._bg_pil:
            try:
                self._bg_ctk = ctk.CTkImage(
                    light_image=self._bg_pil,
                    dark_image=self._bg_pil,
                    size=(self._current_w, self._current_h)
                )
                self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                self.bg_label.lift(self._canvas)
            except Exception as e:
                print(f"[ConveyorQuestView] Gagal memuat background: {e}")

    def _on_resize(self, event) -> None:
        if event.widget in (self, getattr(self, "_canvas", None)):
            w, h = event.width, event.height
            if w < 100 or h < 100:
                return
            if abs(w - self._current_w) > 10 or abs(h - self._current_h) > 10:
                self._current_w = w
                self._current_h = h
                if self._bg_pil and hasattr(self, "bg_label"):
                    self._bg_ctk = ctk.CTkImage(
                        light_image=self._bg_pil,
                        dark_image=self._bg_pil,
                        size=(w, h)
                    )
                    self.bg_label.configure(image=self._bg_ctk)

    def refresh_view(self) -> None:
        """Memperbarui visual item di ban berjalan."""
        self.lbl_score.configure(text=f"Skor: {self.quest.score} | Giliran: {min(5, self.quest.current_turn + 1)} / 5")
        self.lbl_instruction.configure(text=f"📋 Instruksi Saat Ini: Ambil [{self.quest.target_item}]")

        for widget in self.belt_frame.winfo_children():
            widget.destroy()

        items = self.quest.get_conveyor_items()
        for i, it in enumerate(items):
            color = "#10B981" if i == 0 else "#4B5563"
            tag = "(DEPAN)" if i == 0 else ""
            badge = ctk.CTkFrame(self.belt_frame, fg_color=color, corner_radius=6)
            badge.pack(side="left", expand=True, padx=4, pady=12)
            ctk.CTkLabel(badge, text=f"{it} {tag}".strip(), font=FONT_BODY, text_color="#FFFFFF").pack(padx=8, pady=4)

    def pick_item(self, item_name: str) -> None:
        """Menangani pengambilan item oleh pemain."""
        correct, msg = self.quest.process_pick(item_name)
        if self.quest.is_finished:
            self.on_finish()
        else:
            self.refresh_view()

    def on_finish(self) -> None:
        """Selesai quest."""
        self.app.game_state.player.inventory.add_item(
            Item(name="Used Broom", value=999999, description="Sapu ajaib legendaris dengan kekuatan mutlak penakluk Godzilla.")
        )
        self.app.game_state.completed_village_quest = True
        messagebox.showinfo(
            "Quest Selesai!",
            f"Kerja bagus! Skor Akhir: {self.quest.score}\n\n"
            "🎁 Warga desa menghadiahimu benda pusaka legendaris:\n"
            "[Used Broom] (+999.999 Damage) telah dimasukkan ke dalam tasmu!"
        )
        self.app.show_exploration()
