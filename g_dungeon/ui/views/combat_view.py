"""
Module: ui/views/combat_view.py
Description: Layar pertarungan Turn-Based RPG (Pemain vs Monster/Kaiju) dengan
tampilan Arena Magma 2D Pixel RPG Skala Penuh (Maximized), Floating Status HUD,
Sprite Karakter Hero & Monster Live di medan laga, serta Action Log Panel.
"""

import os
from typing import Optional
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

from core.monster import Monster
from ui.asset_loader import (
    load_image, load_pil_image, get_role_idle_frames, get_role_attack_frames,
    get_rpg_icon_by_name
)
from ui.components.log_panel import LogPanel
from ui.components.stat_bar import StatBar
from ui.theme import (
    BG_CARD, BG_DARK, BG_PANEL, BORDER_COLOR, COLOR_DANGER, COLOR_DEFENSE,
    COLOR_GOLD, COLOR_HEAL, COLOR_PRIMARY, FONT_BODY, FONT_BOLD, FONT_HEADING,
    FONT_MONO_SMALL, FONT_SMALL, FONT_SUBTITLE, FONT_TITLE, TEXT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY
)


class CombatView(ctk.CTkFrame):
    """Layar arena pertempuran antara pemain dan monster berlatar belakang visual penuh."""

    def __init__(self, master, app_controller, monster: Monster) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller
        self.monster = monster
        self.game_state = self.app.game_state
        self.player = self.game_state.player

        self._current_w = max(1200, self.winfo_width())
        self._current_h = max(750, self.winfo_height())
        self._bg_pil: Optional[Image.Image] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # 1. Background Arena Pertempuran Skala Penuh (ditempatkan pertama)
        self.setup_background()

        # Animasi Sprite Pemain (2D Pixel Art)
        self.player_idle_frames = get_role_idle_frames(self.player.role.value)
        self.player_attack_frames = get_role_attack_frames(self.player.role.value)
        self._player_frame_idx: int = 0
        self._is_player_attacking: bool = False
        self._player_anim_job: Optional[str] = None

        # 2. Header Title Bar (Melayang di bagian atas)
        self.header = ctk.CTkFrame(
            self, fg_color="#0F121E", border_color="#DC2626", border_width=1,
            height=46, corner_radius=10
        )
        self.header.place(relx=0.5, rely=0.03, relwidth=0.96, anchor="n")
        self.header.pack_propagate(False)

        ctk.CTkLabel(
            self.header,
            text=f"⚔️ PERTARUNGAN: {self.player.name.upper()} VS {self.monster.name.upper()} ⚔️",
            font=FONT_HEADING,
            text_color=COLOR_DANGER
        ).pack(pady=8)

        # 3. Floating HUD: Status Pemain (Kiri Atas)
        self.player_hud = self.create_player_hud()
        self.player_hud.place(relx=0.02, rely=0.10, anchor="nw")

        # 4. Floating HUD: Status Monster (Kanan Atas)
        self.monster_hud = self.create_monster_hud()
        self.monster_hud.place(relx=0.98, rely=0.10, anchor="ne")

        # 5. Panggung Karakter di Arena Pertempuran (Tengah)
        # 5.A Stage Sprite Pemain (Kiri)
        self.player_stage = ctk.CTkFrame(self, fg_color="transparent")
        self.player_stage.place(relx=0.25, rely=0.54, anchor="center")

        initial_img = self.player_idle_frames[0] if self.player_idle_frames else None
        self.lbl_player_sprite = ctk.CTkLabel(self.player_stage, text="" if initial_img else "(Hero Sprite)", image=initial_img)
        self.lbl_player_sprite.pack()

        p_name_badge = ctk.CTkFrame(self.player_stage, fg_color="#101322", border_color=COLOR_PRIMARY, border_width=1, corner_radius=6)
        p_name_badge.pack(pady=(6, 0))
        icon_badge = get_rpg_icon_by_name("sword_gold", (18, 18))
        ctk.CTkLabel(p_name_badge, text=f" {self.player.name} ", image=icon_badge, compound="left", font=FONT_BOLD, text_color=COLOR_PRIMARY).pack(padx=8, pady=2)

        # 5.B Stage Monster (Kanan)
        self.monster_stage = ctk.CTkFrame(self, fg_color="transparent")
        self.monster_stage.place(relx=0.75, rely=0.52, anchor="center")

        image_loaded = self.try_load_monster_image(self.monster_stage)
        if not image_loaded:
            ascii_box = ctk.CTkTextbox(self.monster_stage, font=FONT_MONO_SMALL, fg_color="#0F121E", text_color="#F87171", width=280, height=220)
            ascii_box.pack(padx=4, pady=4)
            ascii_box.insert("1.0", self.monster.ascii_art)
            ascii_box.configure(state="disabled")

        m_name_badge = ctk.CTkFrame(self.monster_stage, fg_color="#101322", border_color=COLOR_DANGER, border_width=1, corner_radius=6)
        m_name_badge.pack(pady=(6, 0))
        ctk.CTkLabel(m_name_badge, text=f"  👹 {self.monster.name}  ", font=FONT_BOLD, text_color=COLOR_DANGER).pack(padx=8, pady=2)

        # 6. Bottom Area: Action Controls & Combat Log (Menempel Bawah)
        bottom_frame = ctk.CTkFrame(self, fg_color="#0E121E", border_color=BORDER_COLOR, border_width=1, corner_radius=14, height=155)
        bottom_frame.place(relx=0.5, rely=0.98, relwidth=0.96, anchor="s")
        bottom_frame.pack_propagate(False)

        # Action Buttons Panel (Kiri Bawah)
        actions_panel = ctk.CTkFrame(bottom_frame, fg_color="transparent", width=380)
        actions_panel.pack(side="left", fill="y", padx=15, pady=10)

        ctk.CTkLabel(actions_panel, text="PILIHAN AKSI GILIRAN:", font=FONT_BOLD, text_color=TEXT_PRIMARY).pack(anchor="w", pady=(0, 4))

        btn_row1 = ctk.CTkFrame(actions_panel, fg_color="transparent")
        btn_row1.pack(fill="x", pady=2)

        icon_atk = get_rpg_icon_by_name("sword_heavy", (20, 20))
        self.btn_attack = ctk.CTkButton(
            btn_row1, text=" Serang Normal", image=icon_atk, compound="left", font=FONT_BOLD, height=36,
            fg_color=COLOR_DANGER, hover_color="#DC2626", command=self.action_attack
        )
        self.btn_attack.pack(side="left", fill="x", expand=True, padx=(0, 4))

        icon_heal = get_rpg_icon_by_name("potion_green", (20, 20))
        self.btn_heal = ctk.CTkButton(
            btn_row1, text=" Pulihkan Diri (+100 HP)", image=icon_heal, compound="left", font=FONT_BOLD, height=36,
            fg_color=COLOR_HEAL, hover_color="#059669", command=self.action_heal
        )
        self.btn_heal.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Item Use Row
        item_row = ctk.CTkFrame(actions_panel, fg_color="transparent")
        item_row.pack(fill="x", pady=4)

        self.item_combo = ctk.CTkComboBox(
            item_row,
            values=self.get_inventory_item_names(),
            state="readonly",
            height=34,
            font=FONT_SMALL
        )
        self.item_combo.pack(side="left", fill="x", expand=True, padx=(0, 4))

        icon_item = get_rpg_icon_by_name("chest_gold", (18, 18))
        self.btn_use_item = ctk.CTkButton(
            item_row, text=" Gunakan Item", image=icon_item, compound="left", font=FONT_BOLD, height=34, width=128,
            fg_color=COLOR_GOLD, hover_color="#D97706", command=self.action_use_item
        )
        self.btn_use_item.pack(side="right")

        # Combat Log Panel (Kanan Bawah)
        self.combat_log = LogPanel(bottom_frame, title="Catatan Pertarungan", height=125)
        self.combat_log.pack(side="right", fill="both", expand=True, padx=15, pady=8)

        self.combat_log.add_log(f"🔥 Kamu berhadapan dengan {self.monster.name} di arena pertempuran!")
        self.combat_log.add_log(f"Tentukan langkah aksimu!")

        # Mulai animasi idle pemain
        self._start_player_animation()

        # Resize listener
        self.bind("<Configure>", self._on_resize)

    # ==================== HUD CREATION ====================

    def create_player_hud(self) -> ctk.CTkFrame:
        """Membuat panel status mengambang untuk pemain di pojok kiri atas."""
        hud = ctk.CTkFrame(
            self, fg_color="#101422", border_color=BORDER_COLOR,
            border_width=1, corner_radius=12, width=380, height=140
        )
        hud.pack_propagate(False)

        top_info = ctk.CTkFrame(hud, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(10, 2))

        ctk.CTkLabel(top_info, text=f"👤 {self.player.name}", font=FONT_BOLD, text_color=COLOR_PRIMARY).pack(side="left")
        ctk.CTkLabel(top_info, text=f"[{self.player.role.value}] ATK: {self.player.attack}", font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="right")

        self.player_hp_bar = StatBar(hud, label="HP Pemain", current=self.player.hp, maximum=self.player.max_hp, bar_color=COLOR_DANGER, height=11)
        self.player_hp_bar.pack(fill="x", padx=16, pady=3)

        self.player_def_bar = StatBar(hud, label="Defense (Armor)", current=self.player.defense, maximum=self.player.max_defense, bar_color=COLOR_DEFENSE, height=11)
        self.player_def_bar.pack(fill="x", padx=16, pady=3)

        return hud

    def create_monster_hud(self) -> ctk.CTkFrame:
        """Membuat panel status mengambang untuk monster di pojok kanan atas."""
        hud = ctk.CTkFrame(
            self, fg_color="#101422", border_color="#DC2626" if not self.monster.is_boss else "#C084FC",
            border_width=1, corner_radius=12, width=380, height=140
        )
        hud.pack_propagate(False)

        top_info = ctk.CTkFrame(hud, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(10, 2))

        boss_tag = " [FINAL BOSS]" if self.monster.is_boss else ""
        boss_color = "#C084FC" if self.monster.is_boss else COLOR_DANGER
        self.lbl_monster_name = ctk.CTkLabel(top_info, text=f"👹 {self.monster.name}{boss_tag}", font=FONT_BOLD, text_color=boss_color)
        self.lbl_monster_name.pack(side="left")

        self.lbl_monster_atk = ctk.CTkLabel(top_info, text=f"ATK: {self.monster.attack} | DEF: {self.monster.defense}", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.lbl_monster_atk.pack(side="right")

        self.monster_hp_bar = StatBar(hud, label="HP Monster", current=self.monster.hp, maximum=self.monster.max_hp, bar_color=COLOR_DANGER, height=11)
        self.monster_hp_bar.pack(fill="x", padx=16, pady=3)

        self.monster_def_bar = StatBar(hud, label="Monster DEF", current=self.monster.defense, maximum=self.monster.max_defense, bar_color=COLOR_DEFENSE, height=11)
        self.monster_def_bar.pack(fill="x", padx=16, pady=3)

        return hud

    def try_load_monster_image(self, parent_frame) -> bool:
        """Mencoba memuat sprite gambar pixel 2D monster dengan NEAREST resampling agar tetap tajam."""
        monster_map = {
            "Godzilla": ["monsters/godzilla_boss.png", "godzilla_boss.png", "master_kaiju_boss_256.png"],
            "Monster Zero": ["monsters/monster_zero.png", "monster_zero.png"],
            "Kong": ["monsters/kong.png", "kong.png"],
        }

        candidates = monster_map.get(self.monster.name, [f"monsters/{self.monster.name.lower().replace(' ', '_')}.png"])
        for rel_path in candidates:
            ctk_img = load_image(rel_path, size=(220, 220), resample=Image.Resampling.NEAREST)
            if ctk_img:
                lbl = ctk.CTkLabel(parent_frame, image=ctk_img, text="")
                lbl.pack(pady=4)
                return True
        return False

    def get_inventory_item_names(self):
        items = self.player.inventory.get_all_items()
        if not items:
            return ["(Tas Kosong)"]
        return [f"{it.name} (+{it.value} DMG)" for it in items]

    def refresh_stats(self) -> None:
        """Memperbarui nilai status bar dan data tempur."""
        self.player_hp_bar.set_values(self.player.hp, self.player.max_hp)
        self.player_def_bar.set_values(self.player.defense, self.player.max_defense)

        self.monster_hp_bar.set_values(self.monster.hp, self.monster.max_hp)
        self.monster_def_bar.set_values(self.monster.defense, self.monster.max_defense)
        self.lbl_monster_atk.configure(text=f"ATK: {self.monster.attack} | DEF: {self.monster.defense}")

        if self.monster.enraged:
            self.lbl_monster_name.configure(text=f"🔥 {self.monster.name} [ENRAGED] 🔥", text_color="#F59E0B")

        self.item_combo.configure(values=self.get_inventory_item_names())
        if self.player.inventory.is_empty():
            self.item_combo.set("(Tas Kosong)")

    # ==================== ANIMASI SPRITE PEMAIN ====================

    def _start_player_animation(self) -> None:
        """Memulai loop animasi idle pemain."""
        self._player_anim_step()

    def _player_anim_step(self) -> None:
        """Satu langkah animasi idle sprite pemain."""
        if not self._is_player_attacking and self.player_idle_frames and hasattr(self, "lbl_player_sprite"):
            self._player_frame_idx = (self._player_frame_idx + 1) % len(self.player_idle_frames)
            self.lbl_player_sprite.configure(image=self.player_idle_frames[self._player_frame_idx])

        self._player_anim_job = self.after(130, self._player_anim_step)

    def trigger_player_attack_anim(self) -> None:
        """Memicu sekuens animasi tebasan/mantra serangan pemain."""
        if not self.player_attack_frames or not hasattr(self, "lbl_player_sprite"):
            return
        self._is_player_attacking = True
        self._step_attack_anim(0)

    def _step_attack_anim(self, frame_idx: int) -> None:
        if not hasattr(self, "lbl_player_sprite") or not self.winfo_exists():
            return
        if frame_idx < len(self.player_attack_frames):
            self.lbl_player_sprite.configure(image=self.player_attack_frames[frame_idx])
            self.after(65, lambda: self._step_attack_anim(frame_idx + 1))
        else:
            self._is_player_attacking = False
            if self.player_idle_frames:
                self.lbl_player_sprite.configure(image=self.player_idle_frames[self._player_frame_idx])

    def stop_player_animation(self) -> None:
        """Menghentikan timer animasi pemain."""
        if self._player_anim_job is not None:
            try:
                self.after_cancel(self._player_anim_job)
            except Exception:
                pass
            self._player_anim_job = None

    def destroy(self) -> None:
        """Membersihkan timer animasi saat view dihancurkan."""
        self.stop_player_animation()
        super().destroy()

    # ==================== AKSI PERTEMPURAN ====================

    def action_attack(self) -> None:
        """Aksi serang normal."""
        self.trigger_player_attack_anim()
        logs = self.game_state.player_attack(self.monster)
        for log in logs:
            self.combat_log.add_log(log)
        self.refresh_stats()

        if not self.monster.is_alive:
            self.handle_victory()
        else:
            self.monster_turn()

    def action_heal(self) -> None:
        """Aksi memulihkan diri."""
        logs = self.game_state.player_heal()
        for log in logs:
            self.combat_log.add_log(log)
        self.refresh_stats()
        self.monster_turn()

    def action_use_item(self) -> None:
        """Menggunakan item dari tas."""
        selection = self.item_combo.get()
        if not selection or selection == "(Tas Kosong)":
            messagebox.showwarning("Tas Kosong", "Kamu tidak memiliki item serangan di dalam tas!")
            return

        item_name = selection.split(" (")[0]
        self.trigger_player_attack_anim()
        success, logs = self.game_state.player_use_item(item_name, self.monster)
        for log in logs:
            self.combat_log.add_log(log)
        self.refresh_stats()

        if not self.monster.is_alive:
            self.handle_victory()
        else:
            self.monster_turn()

    def monster_turn(self) -> None:
        """Giliran serangan balasan monster."""
        self.set_buttons_state("disabled")
        self.after(500, self._execute_monster_counter)

    def _execute_monster_counter(self) -> None:
        counter_logs = self.game_state.monster_counter_attack(self.monster)
        for log in counter_logs:
            self.combat_log.add_log(log)
        self.refresh_stats()

        if not self.player.is_alive:
            self.handle_defeat()
        else:
            self.set_buttons_state("normal")

    def set_buttons_state(self, state: str) -> None:
        self.btn_attack.configure(state=state)
        self.btn_heal.configure(state=state)
        self.btn_use_item.configure(state=state)

    def handle_victory(self) -> None:
        """Pemain menang melawan monster."""
        self.stop_player_animation()
        self.set_buttons_state("disabled")
        if self.monster.name == "Godzilla":
            messagebox.showinfo(
                "TAMAT / VICTORY!",
                "🎉 SELAMAT! KAMU TELAH MENAKLUKKAN GODZILLA!\n\n"
                "Kedamaian kembali tercipta di seluruh penjuru dungeon. Kamu adalah pahlawan sejati!"
            )
            self.app.show_main_menu()
        else:
            messagebox.showinfo(
                "Kemenangan!",
                f"Monster {self.monster.name} telah dikalahkan!\nJalan penjelajahan kembali aman."
            )
            self.app.show_exploration()

    def handle_defeat(self) -> None:
        """Pemain gugur dalam pertempuran."""
        self.stop_player_animation()
        self.set_buttons_state("disabled")
        messagebox.showerror(
            "GAME OVER",
            "☠️ Kamu telah gugur dalam pertempuran...\nPetualanganmu berakhir di sini."
        )
        self.app.show_main_menu()

    def setup_background(self) -> None:
        """Memuat gambar latar belakang arena pertempuran pixel art skala penuh."""
        self._bg_pil = load_pil_image("backgrounds/combat_arena_bg.png")
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
                print(f"[CombatView] Gagal menampilkan background arena: {e}")

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
