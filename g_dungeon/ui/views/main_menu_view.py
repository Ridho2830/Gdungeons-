"""
Module: ui/views/main_menu_view.py
Description: Layar Menu Utama berformat Maximized / Layar Penuh dengan tema 2D Pixel RPG
(Latar Belakang Dungeon Luas, Logo Utama Pixel Megah dengan Alpha Composting Bersih,
Panggung Pedestal Hero Animasi Live, Tombol Menu Batu Ukir Pixel, & Footer Info).
"""

from typing import List, Optional
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

from ui.asset_loader import (
    get_knight_idle_frames,
    get_wizard_idle_frames,
    get_rpg_icon_by_name,
    load_image,
    load_pil_image,
)
from ui.components.roles_dialog import RolesInfoDialog
from ui.theme import (
    BG_CARD, BG_DARK, BORDER_COLOR, COLOR_ACCENT, COLOR_GOLD, COLOR_PRIMARY,
    FONT_BODY, FONT_BOLD, FONT_HEADING, FONT_MONO_SMALL, FONT_SMALL, FONT_TITLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
)


class MainMenuView(ctk.CTkFrame):
    """Tampilan menu awal bertema Pixel Art 2D Retro RPG dengan layout maximized adaptif."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller

        self._bg_pil: Optional[Image.Image] = load_pil_image("backgrounds/main_menu_bg.png")
        self._logo_pil: Optional[Image.Image] = load_pil_image("ui/logos/menu_title_logo.png")
        self._bg_ctk: Optional[ctk.CTkImage] = None

        self._current_w = max(1200, self.winfo_width())
        self._current_h = max(750, self.winfo_height())

        # Sprite frames untuk live animation kedua hero
        self.knight_frames: List[ctk.CTkImage] = get_knight_idle_frames((130, 140))
        self.wizard_frames: List[ctk.CTkImage] = get_wizard_idle_frames((140, 130))
        self._k_idx: int = 0
        self._w_idx: int = 0
        self._anim_job: Optional[str] = None

        # 1. Background Pixel Art Menyeluruh (ditempatkan pertama)
        self.setup_background()

        # 2. Main Maximized Stage Container
        self.setup_maximized_layout()

        # 3. Mulai loop animasi hero
        self.start_idle_animation()

        # Bind event resize untuk menyesuaikan background & layout
        self.bind("<Configure>", self._on_resize)

    # ==================== LATAR BELAKANG ====================

    def _render_composite_bg(self, w: int, h: int) -> ctk.CTkImage:
        """Menghasilkan CTkImage dengan logo terkomposisi secara alpha blending sempurna."""
        if not self._bg_pil:
            return None

        bg_composite = self._bg_pil.resize((w, h), Image.Resampling.BILINEAR).convert("RGBA")
        if self._logo_pil:
            logo_w = min(680, max(400, int(w * 0.36)))
            logo_h = int(logo_w * (185 / 490))
            logo_scaled = self._logo_pil.resize((logo_w, logo_h), Image.Resampling.BILINEAR).convert("RGBA")

            lx = (w - logo_w) // 2
            ly = max(25, int(h * 0.035))
            bg_composite.alpha_composite(logo_scaled, (lx, ly))

        return ctk.CTkImage(light_image=bg_composite, dark_image=bg_composite, size=(w, h))

    def setup_background(self) -> None:
        """Memuat gambar latar belakang dungeon 2D Pixel Art skala penuh."""
        if self._bg_pil:
            try:
                self._bg_ctk = self._render_composite_bg(self._current_w, self._current_h)
                self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                # Angkat tepat di atas canvas internal CTkFrame agar tidak terhalang
                self.bg_label.lift(self._canvas)
            except Exception as e:
                print(f"[MainMenuView] Peringatan: Gagal menampilkan background: {e}")

    # ==================== LAYOUT MAXIMIZED ====================

    def setup_maximized_layout(self) -> None:
        """Membangun layout penuh yang megah langsung di atas latar belakang tanpa overlay pemblokir."""
        # 1. FOOTER BAR (Menempel di Bagian Bawah Layar)
        self.footer_bar = ctk.CTkFrame(
            self, fg_color="#0A0D15", height=38,
            corner_radius=0, border_color="#242B40", border_width=1
        )
        self.footer_bar.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        lbl_f_left = ctk.CTkLabel(
            self.footer_bar,
            text="🎮 G-DUNGEONS • 16-Bit Pixel RPG Edition",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY
        )
        lbl_f_left.pack(side="left", padx=20)

        lbl_f_center = ctk.CTkLabel(
            self.footer_bar,
            text="Struktur Data & Algoritma Dungeon Adventure (Python & CustomTkinter)",
            font=FONT_MONO_SMALL,
            text_color=TEXT_MUTED
        )
        lbl_f_center.pack(side="left", expand=True)

        lbl_f_right = ctk.CTkLabel(
            self.footer_bar,
            text="Antigravity Studio RPG",
            font=FONT_SMALL,
            text_color=COLOR_GOLD
        )
        lbl_f_right.pack(side="right", padx=20)

        # 2. PITA SUBTITLE (Melayang Elegan di Bawah Logo Utama)
        self.sub_badge = ctk.CTkFrame(
            self, fg_color="#101322", border_color=COLOR_GOLD,
            border_width=1, corner_radius=8
        )
        self.sub_badge.place(relx=0.5, rely=0.25, anchor="center")

        ctk.CTkLabel(
            self.sub_badge,
            text="  ⚔️ STRUKTUR DATA & ALGORITMA • DUNGEON ADVENTURE ⚔️  ",
            font=FONT_BOLD,
            text_color=COLOR_GOLD
        ).pack(padx=16, pady=4)

        # 3. STAGE ROW: [PEDESTAL KNIGHT] + [MENU BUTTONS BOX] + [PEDESTAL WIZARD]
        self.stage_row = ctk.CTkFrame(self, fg_color="transparent")
        self.stage_row.place(relx=0.5, rely=0.62, anchor="center")

        # === KOLOM KIRI: PEDESTAL KNIGHT (FIGHTER) ===
        self.left_pedestal = self.create_hero_pedestal(
            parent=self.stage_row,
            role_title="KNIGHT / FIGHTER",
            role_color=COLOR_PRIMARY,
            hp_text="HP: 3000   DEF: 200",
            atk_text="ATK: 200 (Tebasan Fisik)",
            skill_text="Skill: Titan Defense",
            desc_text="Pertahanan baja tak tergoyahkan untuk duel jarak dekat.",
            role_key="knight"
        )

        # Wadah sprite Knight
        self.lbl_knight_sprite = ctk.CTkLabel(self.left_pedestal, text="", width=140, height=145)
        self.lbl_knight_sprite.pack(pady=(8, 10))

        # === KOLOM TENGAH: PORTAL MENU BUTTONS ===
        self.center_menu_card = ctk.CTkFrame(
            self.stage_row,
            fg_color="#0F121E",
            border_color="#F59E0B",
            border_width=2,
            corner_radius=16,
            width=430,
            height=380
        )
        self.center_menu_card.pack(side="left", padx=18, pady=4)
        self.center_menu_card.pack_propagate(False)

        # Title bar menu tengah
        menu_title_bar = ctk.CTkFrame(self.center_menu_card, fg_color="#171C2E", corner_radius=8)
        menu_title_bar.pack(fill="x", padx=16, pady=(12, 10))

        ctk.CTkLabel(
            menu_title_bar,
            text="👑 MENU UTAMA PETUALANGAN 👑",
            font=FONT_HEADING,
            text_color=TEXT_PRIMARY
        ).pack(pady=4)

        # Wadah tombol aksi
        buttons_frame = ctk.CTkFrame(self.center_menu_card, fg_color="transparent")
        buttons_frame.pack(fill="both", expand=True, padx=24, pady=2)

        # 1. Mulai Petualangan
        self.create_pixel_button(
            parent=buttons_frame,
            normal_file="btn_play.png",
            hover_file="btn_play_hover.png",
            fallback_text="▶  Mulai Petualangan",
            command=self.app.show_role_select,
            is_primary=True
        )

        # 2. Info Role Karakter
        self.create_pixel_button(
            parent=buttons_frame,
            normal_file="btn_roles.png",
            hover_file="btn_roles_hover.png",
            fallback_text="📜  Info Role Karakter",
            command=self.show_roles_info
        )

        # 3. Tentang Game
        self.create_pixel_button(
            parent=buttons_frame,
            normal_file="btn_about.png",
            hover_file="btn_about_hover.png",
            fallback_text="ℹ️  Tentang Game",
            command=self.show_about_info
        )

        # 4. Keluar Game
        self.create_pixel_button(
            parent=buttons_frame,
            normal_file="btn_exit.png",
            hover_file="btn_exit_hover.png",
            fallback_text="🚪  Keluar Game",
            command=self.app.quit,
            is_exit=True
        )

        ctk.CTkLabel(
            self.center_menu_card,
            text="Pilih tombol untuk memulai ekspedisi dungeon!",
            font=FONT_MONO_SMALL,
            text_color=TEXT_MUTED
        ).pack(side="bottom", pady=6)

        # === KOLOM KANAN: PEDESTAL WIZARD (MAGE) ===
        self.right_pedestal = self.create_hero_pedestal(
            parent=self.stage_row,
            role_title="WIZARD / MAGE",
            role_color=COLOR_ACCENT,
            hp_text="HP: 1500   DEF: 75",
            atk_text="ATK: 100 (Sihir Gaib)",
            skill_text="Skill: Map Vision (Dijkstra)",
            desc_text="Menguasai navigasi rute terpendek dan misteri kuno.",
            role_key="wizard"
        )

        # Wadah sprite Wizard
        self.lbl_wizard_sprite = ctk.CTkLabel(self.right_pedestal, text="", width=140, height=145)
        self.lbl_wizard_sprite.pack(pady=(8, 10))

        # Tampilkan frame pertama segera
        self.update_sprite_display()

    def create_hero_pedestal(
        self,
        parent: ctk.CTkFrame,
        role_title: str,
        role_color: str,
        hp_text: str,
        atk_text: str,
        skill_text: str,
        desc_text: str,
        role_key: str = "knight"
    ) -> ctk.CTkFrame:
        """Membuat kolom kartu pedestal hero pixel art di sisi kiri atau kanan menu."""
        pedestal = ctk.CTkFrame(
            parent,
            fg_color="#0F121E",
            border_color="#333A56",
            border_width=2,
            corner_radius=14,
            width=250,
            height=380
        )
        pedestal.pack(side="left", padx=10, pady=4)
        pedestal.pack_propagate(False)

        # Header Role Badge dengan Icon Pixel
        if role_key == "knight":
            badge_icon = get_rpg_icon_by_name("sword_heavy", (20, 20))
            skill_icon = get_rpg_icon_by_name("armor_emerald", (16, 16))
            atk_icon = get_rpg_icon_by_name("atk", (16, 16))
        else:
            badge_icon = get_rpg_icon_by_name("book_arcane", (20, 20))
            skill_icon = get_rpg_icon_by_name("book_gold", (16, 16))
            atk_icon = get_rpg_icon_by_name("magic", (16, 16))

        hp_icon = get_rpg_icon_by_name("hp", (16, 16))

        lbl_role = ctk.CTkLabel(
            pedestal, text=f" {role_title}", image=badge_icon, compound="left",
            font=FONT_BOLD, text_color=role_color
        )
        lbl_role.pack(pady=(12, 4))

        # Stat Box di bagian bawah pedestal
        stat_box = ctk.CTkFrame(
            pedestal, fg_color="#151A2A", border_color="#242B40",
            border_width=1, corner_radius=8
        )
        stat_box.pack(side="bottom", fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(stat_box, text=f" {hp_text}", image=hp_icon, compound="left", font=FONT_SMALL, text_color=TEXT_PRIMARY).pack(anchor="w", padx=8, pady=(6, 2))
        ctk.CTkLabel(stat_box, text=f" {atk_text}", image=atk_icon, compound="left", font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(anchor="w", padx=8, pady=1)
        ctk.CTkLabel(stat_box, text=f" {skill_text}", image=skill_icon, compound="left", font=FONT_BOLD, text_color=role_color).pack(anchor="w", padx=8, pady=2)
        ctk.CTkLabel(stat_box, text=desc_text, font=FONT_MONO_SMALL, text_color=TEXT_MUTED, wraplength=210, justify="left").pack(anchor="w", padx=8, pady=(2, 6))

        return pedestal

    # ==================== ANIMASI HERO IDLE ====================

    def start_idle_animation(self) -> None:
        """Memulai timer perputaran frame idle sprite Knight & Wizard."""
        self._tick_idle_animation()

    def _tick_idle_animation(self) -> None:
        """Tick periodik animasi idle kedua hero."""
        if not self.winfo_exists():
            return

        self._k_idx += 1
        self._w_idx += 1
        self.update_sprite_display()

        self._anim_job = self.after(160, self._tick_idle_animation)

    def update_sprite_display(self) -> None:
        """Memperbarui frame gambar pada label sprite hero."""
        if self.knight_frames and hasattr(self, "lbl_knight_sprite"):
            k_frame = self.knight_frames[self._k_idx % len(self.knight_frames)]
            self.lbl_knight_sprite.configure(image=k_frame)

        if self.wizard_frames and hasattr(self, "lbl_wizard_sprite"):
            w_frame = self.wizard_frames[self._w_idx % len(self.wizard_frames)]
            self.lbl_wizard_sprite.configure(image=w_frame)

    def destroy(self) -> None:
        """Membersihkan timer animasi saat view diganti."""
        if self._anim_job:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None
        super().destroy()

    # ==================== TOMBOL PIXEL ART ====================

    def create_pixel_button(
        self,
        parent: ctk.CTkFrame,
        normal_file: str,
        hover_file: str,
        fallback_text: str,
        command,
        is_primary: bool = False,
        is_exit: bool = False
    ) -> ctk.CTkButton:
        """Membuat tombol pixel art interaktif dengan efek transisi hover."""
        btn_w, btn_h = 360, 52

        ctk_norm = load_image(f"ui/buttons/{normal_file}", size=(btn_w, btn_h))
        ctk_hov = load_image(f"ui/buttons/{hover_file}", size=(btn_w, btn_h)) or ctk_norm

        if ctk_norm:
            btn = ctk.CTkButton(
                parent,
                text="",
                image=ctk_norm,
                fg_color="transparent",
                hover_color="#181C2B",
                width=btn_w,
                height=btn_h,
                corner_radius=6,
                cursor="hand2",
                command=command
            )
            btn.pack(pady=4)

            btn.bind("<Enter>", lambda e, b=btn, img=ctk_hov: b.configure(image=img))
            btn.bind("<Leave>", lambda e, b=btn, img=ctk_norm: b.configure(image=img))
            return btn

        # Fallback tombol teks biasa jika file gambar tidak ditemukan
        bg_col = COLOR_PRIMARY if is_primary else ("#374151" if is_exit else BG_CARD)
        hov_col = "#2563EB" if is_primary else ("#4B5563" if is_exit else "#2E344E")

        btn = ctk.CTkButton(
            parent,
            text=fallback_text,
            font=FONT_HEADING if is_primary else FONT_BODY,
            height=44,
            fg_color=bg_col,
            hover_color=hov_col,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=8,
            command=command
        )
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    # ==================== RESPONSIVE RESIZE ====================

    def _on_resize(self, event) -> None:
        """Menyesuaikan skala background dan tata letak saat ukuran window berubah."""
        if event.widget in (self, getattr(self, "_canvas", None)):
            w, h = event.width, event.height
            if w < 100 or h < 100:
                return

            if abs(w - self._current_w) > 10 or abs(h - self._current_h) > 10:
                self._current_w = w
                self._current_h = h
                if self._bg_pil and hasattr(self, "bg_label"):
                    self._bg_ctk = self._render_composite_bg(w, h)
                    if self._bg_ctk:
                        self.bg_label.configure(image=self._bg_ctk)

            # Responsif: jika lebar layar sangat sempit (< 980px), sembunyikan pedestal samping
            if hasattr(self, "left_pedestal") and hasattr(self, "right_pedestal"):
                if w < 980:
                    self.left_pedestal.pack_forget()
                    self.right_pedestal.pack_forget()
                else:
                    self.left_pedestal.pack(side="left", padx=10, pady=4, before=self.center_menu_card)
                    self.right_pedestal.pack(side="left", padx=10, pady=4, after=self.center_menu_card)

    def show_roles_info(self) -> None:
        """Menampilkan dialog informasi role pemain dengan visual sprite IDLE animasi."""
        RolesInfoDialog(self.winfo_toplevel())

    def show_about_info(self) -> None:
        """Menampilkan deskripsi game."""
        about = (
            "G-DUNGEONS (Python GUI Edition)\n\n"
            "Game RPG dungeon crawler yang menantang pemain menjelajahi 10 ruangan rahasia, "
            "memecahkan teka-teki logika (8-Puzzle, Stack Bejana Warna, Queue Conveyor), "
            "berinteraksi dengan penjaga hutan, serta menaklukkan raja monster Godzilla!\n\n"
            "Didesain dengan arsitektur OOP modular dan implementasi Struktur Data & Algoritma."
        )
        messagebox.showinfo("Tentang Game", about)
