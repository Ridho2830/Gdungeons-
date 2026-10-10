"""
Module: ui/views/role_select_view.py
Description: Layar pembuatan karakter (Input nama dan pemilihan Role: Mage vs Fighter)
dengan tema 2D Pixel Art RPG yang konsisten dan animasi idle sprite hidup.
"""

from typing import List, Optional
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

from core.player import PlayerRole, ROLE_CONFIGS
from ui.asset_loader import (
    get_knight_idle_frames, get_wizard_idle_frames, load_pil_image,
    get_rpg_icon_by_name
)
from ui.theme import (
    BG_CARD, BG_DARK, BG_PANEL, BORDER_COLOR, COLOR_ACCENT, COLOR_DANGER,
    COLOR_DEFENSE, COLOR_GOLD, COLOR_PRIMARY, FONT_BODY, FONT_BOLD,
    FONT_HEADING, FONT_SMALL, FONT_SUBTITLE, FONT_TITLE, TEXT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY
)


class RoleSelectView(ctk.CTkFrame):
    """Layar pemilihan hero bertema Pixel Art 2D Retro RPG lengkap dengan live idle animation."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller
        self.selected_role: PlayerRole = PlayerRole.MAGE

        self._current_w = 980
        self._current_h = 680
        self._bg_pil: Optional[Image.Image] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # Sprite frames untuk animasi
        self.wizard_frames: List[ctk.CTkImage] = get_wizard_idle_frames((135, 122))
        self.knight_frames: List[ctk.CTkImage] = get_knight_idle_frames((125, 132))
        self._w_idx: int = 0
        self._k_idx: int = 0
        self._anim_job: Optional[str] = None

        # 1. Background Dungeon Pixel Art
        self.setup_background()

        # 2. Main Card Container
        self.setup_selection_panel()

        # 3. Start live idle animation
        self.start_idle_animation()

        # Resize listener
        self.bind("<Configure>", self._on_resize)

    def setup_background(self) -> None:
        """Memuat background 2D Pixel Art dengan overlay tematik."""
        self._bg_pil = load_pil_image("backgrounds/main_menu_bg.png")
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
                print(f"[RoleSelectView] Peringatan background: {e}")

    def setup_selection_panel(self) -> None:
        """Menyusun panel tengah pemilihan role hero."""
        container = ctk.CTkFrame(
            self,
            fg_color="#0F111A",
            border_color="#333A56",
            border_width=2,
            corner_radius=16,
            width=840,
            height=630
        )
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)

        # Header Title dengan Icon Pedang Emas Pixel
        self._icon_title = get_rpg_icon_by_name("sword_gold", (26, 26))
        title_label = ctk.CTkLabel(
            container,
            text=" PEMILIHAN HERO & PERAN",
            image=self._icon_title,
            compound="left",
            font=FONT_TITLE,
            text_color=COLOR_GOLD
        )
        title_label.pack(pady=(22, 2))

        subtitle = ctk.CTkLabel(
            container,
            text="Tentukan identitas dan spesialisasi tempurmu sebelum melangkah ke dungeon",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        subtitle.pack(pady=(0, 14))

        # Input Nama Pahlawan
        name_frame = ctk.CTkFrame(container, fg_color="#141724", border_color="#272D42", border_width=1, corner_radius=10)
        name_frame.pack(fill="x", padx=50, pady=(0, 14))

        ctk.CTkLabel(
            name_frame,
            text="👤 Nama Petualang:",
            font=FONT_BOLD,
            text_color=COLOR_PRIMARY
        ).pack(side="left", padx=(16, 12), pady=8)

        self.entry_name = ctk.CTkEntry(
            name_frame,
            placeholder_text="Masukkan nama pahlawanmu...",
            font=FONT_BODY,
            height=36,
            width=360,
            fg_color="#0B0D14",
            border_color="#333A56",
            text_color=TEXT_PRIMARY
        )
        self.entry_name.pack(side="left", padx=(0, 16), pady=8)
        self.entry_name.insert(0, "Hero")

        # Kartu Pilihan Role (Side by Side: Mage & Fighter)
        cards_frame = ctk.CTkFrame(container, fg_color="transparent")
        cards_frame.pack(fill="both", expand=True, padx=40, pady=(0, 14))

        # Card Mage (Kiri)
        self.card_mage = self.build_hero_card(
            parent=cards_frame,
            role=PlayerRole.MAGE,
            title="MAGE (Penyihir)",
            subtitle="Arcane Caster & Path Navigator",
            accent_color=COLOR_ACCENT,
            frames=self.wizard_frames,
            stats={"HP": 1500, "ATK": 100, "DEF": 75},
            skill_title="Skill: Map Vision (Dijkstra)",
            skill_desc="Memindai seluruh dungeon & menghitung rute tercepat secara otomatis.",
            side="left"
        )

        # Card Fighter (Kanan)
        self.card_fighter = self.build_hero_card(
            parent=cards_frame,
            role=PlayerRole.FIGHTER,
            title="FIGHTER (Pendekar)",
            subtitle="Titan Armor & Frontline Brawler",
            accent_color="#EF4444",
            frames=self.knight_frames,
            stats={"HP": 3000, "ATK": 200, "DEF": 200},
            skill_title="Pasif: Titan Defense & Power",
            skill_desc="Pertahanan lapis baja kokoh & serangan dahsyat penahan amukan Kaiju.",
            side="right"
        )

        # Update visual highlight aktif
        self.update_card_selection()

        # Tombol Aksi di Bagian Bawah
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=50, pady=(0, 20))

        btn_back = ctk.CTkButton(
            btn_frame,
            text="⬅ Kembali",
            font=FONT_BODY,
            width=150,
            height=42,
            fg_color="#374151",
            hover_color="#4B5563",
            corner_radius=8,
            command=self.app.show_main_menu
        )
        btn_back.pack(side="left")

        self._icon_enter = get_rpg_icon_by_name("sword_crystal", (22, 22))
        btn_start = ctk.CTkButton(
            btn_frame,
            text=" Masuk Dungeon ➔",
            image=self._icon_enter,
            compound="left",
            font=FONT_HEADING,
            height=42,
            fg_color=COLOR_PRIMARY,
            hover_color="#2563EB",
            corner_radius=8,
            command=self.confirm_and_start
        )
        btn_start.pack(side="right", fill="x", expand=True, padx=(20, 0))

    def build_hero_card(
        self,
        parent: ctk.CTkFrame,
        role: PlayerRole,
        title: str,
        subtitle: str,
        accent_color: str,
        frames: List[ctk.CTkImage],
        stats: dict,
        skill_title: str,
        skill_desc: str,
        side: str
    ) -> dict:
        """Membuat komponen kartu hero pixel art interaktif."""
        card = ctk.CTkFrame(
            parent,
            fg_color="#141724",
            border_color=BORDER_COLOR,
            border_width=2,
            corner_radius=12
        )
        card.pack(side=side, fill="both", expand=True, padx=10, pady=2)

        # Klik pada kartu langsung memilih role
        card.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        # Title dengan icon pixel yang sesuai dengan class
        if role == PlayerRole.MAGE:
            card_icon = get_rpg_icon_by_name("book_arcane", (22, 22))
        else:
            card_icon = get_rpg_icon_by_name("sword_heavy", (22, 22))

        lbl_t = ctk.CTkLabel(
            card, text=f" {title}", image=card_icon, compound="left",
            font=FONT_HEADING, text_color=accent_color
        )
        lbl_t.pack(pady=(12, 1))
        lbl_t.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        lbl_sub = ctk.CTkLabel(card, text=subtitle, font=("Segoe UI", 9), text_color=TEXT_MUTED)
        lbl_sub.pack(pady=(0, 6))
        lbl_sub.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        # Kotak Visual Sprite Live IDLE
        sprite_box = ctk.CTkFrame(card, fg_color="#090B12", corner_radius=8, height=125)
        sprite_box.pack(fill="x", padx=14, pady=2)
        sprite_box.pack_propagate(False)
        sprite_box.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        initial_img = frames[0] if frames else None
        lbl_sprite = ctk.CTkLabel(sprite_box, text="" if initial_img else "(Sprite)", image=initial_img)
        lbl_sprite.pack(expand=True)
        lbl_sprite.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        # Status Baris Atribut dengan Icon Pixel RPG (HP Potion, Sword, Shield Plate)
        stat_bar = ctk.CTkFrame(card, fg_color="#1A1E2F", corner_radius=6)
        stat_bar.pack(fill="x", padx=14, pady=6)
        stat_bar.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        row = ctk.CTkFrame(stat_bar, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=5)
        row.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        icon_hp = get_rpg_icon_by_name("hp", (18, 18))
        lbl_hp = ctk.CTkLabel(
            row, text=f" {stats['HP']}", image=icon_hp, compound="left",
            font=FONT_BOLD, text_color=COLOR_DANGER
        )
        lbl_hp.pack(side="left", expand=True)
        lbl_hp.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        icon_atk = get_rpg_icon_by_name("atk", (18, 18))
        lbl_atk = ctk.CTkLabel(
            row, text=f" {stats['ATK']}", image=icon_atk, compound="left",
            font=FONT_BOLD, text_color=COLOR_GOLD
        )
        lbl_atk.pack(side="left", expand=True)
        lbl_atk.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        icon_def = get_rpg_icon_by_name("def", (18, 18))
        lbl_def = ctk.CTkLabel(
            row, text=f" {stats['DEF']}", image=icon_def, compound="left",
            font=FONT_BOLD, text_color=COLOR_DEFENSE
        )
        lbl_def.pack(side="left", expand=True)
        lbl_def.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        # Kotak Keunggulan / Skill dengan Icon Tematik
        skill_box = ctk.CTkFrame(card, fg_color="#0E111C", border_color="#242A3D", border_width=1, corner_radius=6)
        skill_box.pack(fill="both", expand=True, padx=14, pady=(2, 8))
        skill_box.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        if role == PlayerRole.MAGE:
            skill_icon = get_rpg_icon_by_name("book_gold", (18, 18))
        else:
            skill_icon = get_rpg_icon_by_name("armor_emerald", (18, 18))

        lbl_sk_t = ctk.CTkLabel(
            skill_box, text=f" {skill_title}", image=skill_icon, compound="left",
            font=FONT_BOLD, text_color=accent_color, wraplength=270, justify="left"
        )
        lbl_sk_t.pack(anchor="w", padx=8, pady=(4, 1))
        lbl_sk_t.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        lbl_sk_d = ctk.CTkLabel(skill_box, text=skill_desc, font=("Segoe UI", 9), text_color=TEXT_SECONDARY, wraplength=280, justify="left")
        lbl_sk_d.pack(anchor="w", padx=8, pady=(0, 6))
        lbl_sk_d.bind("<Button-1>", lambda e, r=role: self.select_role(r))

        # Tombol Pilih Role Ini
        btn_select = ctk.CTkButton(
            card,
            text="Pilih Role Ini",
            font=FONT_BOLD,
            height=32,
            corner_radius=6,
            command=lambda r=role: self.select_role(r)
        )
        btn_select.pack(fill="x", padx=16, pady=(0, 10))

        return {
            "frame": card,
            "lbl_sprite": lbl_sprite,
            "btn_select": btn_select,
            "accent_color": accent_color,
            "role": role,
            "frames": frames
        }

    def start_idle_animation(self) -> None:
        """Menjalankan loop animasi sprite idle kedua hero secara bersamaan."""
        self._idle_step()

    def _idle_step(self) -> None:
        """Memajukan frame animasi sprite idle."""
        if self.wizard_frames and hasattr(self, "card_mage"):
            self._w_idx = (self._w_idx + 1) % len(self.wizard_frames)
            self.card_mage["lbl_sprite"].configure(image=self.wizard_frames[self._w_idx])

        if self.knight_frames and hasattr(self, "card_fighter"):
            self._k_idx = (self._k_idx + 1) % len(self.knight_frames)
            self.card_fighter["lbl_sprite"].configure(image=self.knight_frames[self._k_idx])

        self._anim_job = self.after(125, self._idle_step)

    def select_role(self, role: PlayerRole) -> None:
        """Memilih role karakter aktif."""
        self.selected_role = role
        self.update_card_selection()

    def update_card_selection(self) -> None:
        """Memperbarui visual highlight kartu yang dipilih."""
        # Update Mage Card
        if self.selected_role == PlayerRole.MAGE:
            self.card_mage["frame"].configure(border_color=COLOR_ACCENT, border_width=3)
            self.card_mage["btn_select"].configure(
                text="✔ TERPILIH",
                fg_color=COLOR_ACCENT,
                hover_color="#7C3AED",
                text_color="#FFFFFF"
            )
        else:
            self.card_mage["frame"].configure(border_color="#272D42", border_width=1)
            self.card_mage["btn_select"].configure(
                text="Pilih Role Ini",
                fg_color="transparent",
                border_color=COLOR_ACCENT,
                border_width=1,
                hover_color="#1E2338",
                text_color=COLOR_ACCENT
            )

        # Update Fighter Card
        if self.selected_role == PlayerRole.FIGHTER:
            self.card_fighter["frame"].configure(border_color="#EF4444", border_width=3)
            self.card_fighter["btn_select"].configure(
                text="✔ TERPILIH",
                fg_color="#EF4444",
                hover_color="#DC2626",
                text_color="#FFFFFF"
            )
        else:
            self.card_fighter["frame"].configure(border_color="#272D42", border_width=1)
            self.card_fighter["btn_select"].configure(
                text="Pilih Role Ini",
                fg_color="transparent",
                border_color="#EF4444",
                border_width=1,
                hover_color="#1E2338",
                text_color="#EF4444"
            )

    def _on_resize(self, event) -> None:
        """Menyesuaikan skala gambar background ketika ukuran window berubah."""
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

    def stop_animation(self) -> None:
        """Menghentikan timer animasi."""
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

    def destroy(self) -> None:
        """Pembersihan saat view dihancurkan."""
        self.stop_animation()
        super().destroy()

    def confirm_and_start(self) -> None:
        """Validasi nama dan mulai permainan."""
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("Peringatan", "Silakan masukkan nama petualang terlebih dahulu!")
            return

        self.stop_animation()
        self.app.start_game(name, self.selected_role)
