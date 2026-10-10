"""
Module: ui/components/roles_dialog.py
Description: Dialog popup kustom bertema Dark RPG untuk menampilkan informasi
dan animasi IDLE sprite 2D Pixel Art dari role Mage dan Fighter.
"""

from typing import List, Optional
import customtkinter as ctk

from ui.asset_loader import (
    get_knight_idle_frames, get_wizard_idle_frames,
    get_rpg_icon_by_name
)
from ui.theme import (
    BG_CARD, BG_DARK, BORDER_COLOR, COLOR_ACCENT, COLOR_DANGER,
    COLOR_DEFENSE, COLOR_GOLD, COLOR_PRIMARY, FONT_BODY, FONT_BOLD,
    FONT_HEADING, FONT_SMALL, FONT_SUBTITLE, TEXT_MUTED, TEXT_PRIMARY,
    TEXT_SECONDARY
)


class RolesInfoDialog(ctk.CTkToplevel):
    """Jendela pop-up modal bertema Dark RPG untuk menampilkan detail role & animasi idle."""

    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.title("Panduan Role Karakter - G-Dungeons")
        self.geometry("820x620")
        self.minsize(780, 580)
        self.configure(fg_color=BG_DARK)

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center di atas jendela induk
        self._center_window(parent)

        # Frame sprite
        self.wizard_frames: List[ctk.CTkImage] = get_wizard_idle_frames((140, 128))
        self.knight_frames: List[ctk.CTkImage] = get_knight_idle_frames((130, 138))

        self.w_frame_idx: int = 0
        self.k_frame_idx: int = 0
        self._anim_job: Optional[str] = None

        # Build UI Layout
        self.setup_ui()

        # Start animation loop
        self.start_animation()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _center_window(self, parent) -> None:
        """Memposisikan jendela pop-up tepat di tengah jendela utama."""
        self.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()

            w = 820
            h = 620
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry("820x620")

    def setup_ui(self) -> None:
        """Menyusun layout antarmuka modal."""
        # Container utama dengan border
        container = ctk.CTkFrame(
            self,
            fg_color="#0F111A",
            border_color="#333A56",
            border_width=2,
            corner_radius=14
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. Header Bar
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 10))

        icon_title = get_rpg_icon_by_name("sword_gold", (24, 24))
        lbl_title = ctk.CTkLabel(
            header,
            text=" PANDUAN ROLE & KELAS HERO",
            image=icon_title,
            compound="left",
            font=FONT_SUBTITLE,
            text_color=COLOR_GOLD
        )
        lbl_title.pack(anchor="center")

        lbl_desc = ctk.CTkLabel(
            header,
            text="Setiap kelas memiliki gaya bertarung, atribut, dan keunggulan taktis yang berbeda di G-Dungeons.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        lbl_desc.pack(anchor="center", pady=(2, 0))

        # 2. Dua Kartu Role Side-by-Side
        cards_container = ctk.CTkFrame(container, fg_color="transparent")
        cards_container.pack(fill="both", expand=True, padx=16, pady=6)

        # Kartu Kiri: MAGE
        self.card_mage = self.create_role_card(
            parent=cards_container,
            role_title="MAGE (Penyihir)",
            role_subtitle="Arcane Caster & Path Navigator",
            border_accent="#8B5CF6",
            frames=self.wizard_frames,
            stats={"HP": 1500, "ATK": 100, "DEF": 75},
            skill_name="Map Vision (Algoritma Dijkstra)",
            skill_desc="Mampu menghitung rute terpendek dan tercepat ke seluruh ruangan dungeon menggunakan Min-Heap Dijkstra.",
            playstyle="Taktis, navigasi cerdas, hemat energi tempur."
        )
        self.card_mage["frame"].pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Kartu Kanan: FIGHTER
        self.card_fighter = self.create_role_card(
            parent=cards_container,
            role_title="FIGHTER (Pendekar)",
            role_subtitle="Titan Armor & Frontline Brawler",
            border_accent="#EF4444",
            frames=self.knight_frames,
            stats={"HP": 3000, "ATK": 200, "DEF": 200},
            skill_name="Titan Defense & Berserker Power",
            skill_desc="Pertahanan lapis baja kokoh dan serangan fisik dahsyat untuk menghadapi pertarungan garis depan melawan Kaiju raksasa.",
            playstyle="Agresif, tahan benturan keras, pertempuran langsung."
        )
        self.card_fighter["frame"].pack(side="right", fill="both", expand=True, padx=(8, 0))

        # 3. Bottom Button
        btn_close = ctk.CTkButton(
            container,
            text="✔  Tutup Panduan",
            font=FONT_BOLD,
            height=38,
            width=220,
            fg_color="#374151",
            hover_color="#4B5563",
            corner_radius=8,
            command=self.on_close
        )
        btn_close.pack(pady=(12, 16))

    def create_role_card(
        self,
        parent: ctk.CTkFrame,
        role_title: str,
        role_subtitle: str,
        border_accent: str,
        frames: List[ctk.CTkImage],
        stats: dict,
        skill_name: str,
        skill_desc: str,
        playstyle: str
    ) -> dict:
        """Membuat panel kartu terstruktur untuk satu role."""
        card = ctk.CTkFrame(
            parent,
            fg_color="#141724",
            border_color=border_accent,
            border_width=2,
            corner_radius=12
        )

        # Header Role dengan icon pixel sesuai role
        if "Mage" in role_title:
            card_icon = get_rpg_icon_by_name("book_arcane", (22, 22))
            skill_icon = get_rpg_icon_by_name("book_gold", (18, 18))
        else:
            card_icon = get_rpg_icon_by_name("sword_heavy", (22, 22))
            skill_icon = get_rpg_icon_by_name("armor_emerald", (18, 18))

        ctk.CTkLabel(
            card,
            text=f" {role_title}",
            image=card_icon,
            compound="left",
            font=FONT_HEADING,
            text_color=border_accent
        ).pack(pady=(12, 1))

        ctk.CTkLabel(
            card,
            text=role_subtitle,
            font=("Segoe UI", 10),
            text_color=TEXT_MUTED
        ).pack(pady=(0, 8))

        # Kotak Visual Sprite IDLE (Pixel Art)
        sprite_box = ctk.CTkFrame(card, fg_color="#090B12", corner_radius=8, height=140)
        sprite_box.pack(fill="x", padx=16, pady=4)
        sprite_box.pack_propagate(False)

        initial_img = frames[0] if frames else None
        lbl_sprite = ctk.CTkLabel(sprite_box, text="" if initial_img else "(No Sprite)", image=initial_img)
        lbl_sprite.pack(expand=True)

        # Label State Idle
        ctk.CTkLabel(
            card,
            text="• 2D Pixel Idle Animation •",
            font=("Segoe UI", 9),
            text_color="#6B7280"
        ).pack(pady=(2, 6))

        # Atribut & Stats dengan Icon RPG
        stats_box = ctk.CTkFrame(card, fg_color="#1A1E2F", corner_radius=8)
        stats_box.pack(fill="x", padx=16, pady=4)

        stat_row = ctk.CTkFrame(stats_box, fg_color="transparent")
        stat_row.pack(fill="x", padx=8, pady=6)

        icon_hp = get_rpg_icon_by_name("hp", (18, 18))
        ctk.CTkLabel(
            stat_row,
            text=f" {stats['HP']}",
            image=icon_hp,
            compound="left",
            font=FONT_BOLD,
            text_color=COLOR_DANGER
        ).pack(side="left", expand=True)

        icon_atk = get_rpg_icon_by_name("atk", (18, 18))
        ctk.CTkLabel(
            stat_row,
            text=f" {stats['ATK']}",
            image=icon_atk,
            compound="left",
            font=FONT_BOLD,
            text_color=COLOR_GOLD
        ).pack(side="left", expand=True)

        icon_def = get_rpg_icon_by_name("def", (18, 18))
        ctk.CTkLabel(
            stat_row,
            text=f" {stats['DEF']}",
            image=icon_def,
            compound="left",
            font=FONT_BOLD,
            text_color=COLOR_DEFENSE
        ).pack(side="left", expand=True)

        # Kotak Fitur / Keahlian Khusus
        feature_box = ctk.CTkFrame(card, fg_color="#10131F", border_color="#262C42", border_width=1, corner_radius=8)
        feature_box.pack(fill="both", expand=True, padx=16, pady=(6, 12))

        ctk.CTkLabel(
            feature_box,
            text=f" {skill_name}",
            image=skill_icon,
            compound="left",
            font=FONT_BOLD,
            text_color=border_accent,
            wraplength=320,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            feature_box,
            text=skill_desc,
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY,
            wraplength=320,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 4))

        ctk.CTkLabel(
            feature_box,
            text=f"🎯 Gaya Main: {playstyle}",
            font=("Segoe UI", 9, "italic"),
            text_color="#9CA3AF",
            wraplength=320,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 6))

        return {
            "frame": card,
            "lbl_sprite": lbl_sprite,
            "frames": frames
        }

    def start_animation(self) -> None:
        """Memulai loop animasi pergantian frame sprite."""
        self._animate_step()

    def _animate_step(self) -> None:
        """Memperbarui frame berikutnya untuk kedua sprite."""
        if self.wizard_frames:
            self.w_frame_idx = (self.w_frame_idx + 1) % len(self.wizard_frames)
            self.card_mage["lbl_sprite"].configure(image=self.wizard_frames[self.w_frame_idx])

        if self.knight_frames:
            self.k_frame_idx = (self.k_frame_idx + 1) % len(self.knight_frames)
            self.card_fighter["lbl_sprite"].configure(image=self.knight_frames[self.k_frame_idx])

        # Frame rate ~8 FPS (125ms per frame)
        self._anim_job = self.after(125, self._animate_step)

    def on_close(self) -> None:
        """Menghentikan timer animasi sebelum menutup jendela."""
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None
        self.destroy()
