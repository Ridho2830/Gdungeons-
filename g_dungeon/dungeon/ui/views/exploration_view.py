"""
Module: ui/views/exploration_view.py
Description: Layar utama penjelajahan dungeon bertema Pixel RPG Fantasy
(Atlas Peta Graph Visual Bertekstur, Sprite Animasi Hero Live, Node Badges 16-Bit,
Navigasi Jalur Berpendar, & Panel Kontrol Interaktif).
"""

import math
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional, Set, Tuple
import customtkinter as ctk

from core.dungeon_graph import DijkstraResult, DungeonLocation, RoomEvent
from ui.asset_loader import (
    get_map_background_tk,
    get_map_node_icon_ctk,
    get_map_node_icon_tk,
    get_player_map_idle_tk_frames,
    get_rpg_icon_by_name,
    load_image,
    load_pil_image,
)
from ui.components.log_panel import LogPanel
from ui.components.stat_bar import StatBar
from ui.components.inventory_dialog import InventoryDialog
from ui.theme import (
    BG_CARD, BG_DARK, BG_HOVER, BG_PANEL, BORDER_COLOR, COLOR_ACCENT,
    COLOR_CURRENT, COLOR_DANGER, COLOR_DEFENSE, COLOR_GOLD, COLOR_HEAL,
    COLOR_PRIMARY, FONT_BODY, FONT_BOLD, FONT_HEADING, FONT_MONO,
    FONT_MONO_SMALL, FONT_SMALL, FONT_SUBTITLE, FONT_TITLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
)


class ExplorationView(ctk.CTkFrame):
    """Layar utama eksplorasi dungeon dengan peta graph visual 2D Pixel RPG interaktif."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller
        self.game_state = self.app.game_state
        self.player = self.game_state.player
        self.dungeon = self.game_state.dungeon

        self._current_w = 1200
        self._current_h = 750
        self._bg_pil: Optional[object] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # 0. Background Dungeon Penuh untuk Frame Utama
        self.setup_background()

        # Koordinat pixel node di canvas
        self.node_positions: Dict[int, Tuple[int, int]] = {}

        # Cache objek gambar Tkinter agar tidak dihapus oleh Garbage Collector
        self._canvas_img_refs: List[tk.PhotoImage] = []

        # State animasi & interaksi
        self.hovered_node_id: Optional[int] = None
        self.dijkstra_active: bool = False
        self.dijkstra_highlight_edges: Set[Tuple[int, int]] = set()
        self.idle_frame_idx: int = 0
        self.anim_after_id: Optional[str] = None

        # Muat frame idle sprite hero untuk peta
        role_str = self.player.role.value
        self.player_map_idle_frames = get_player_map_idle_tk_frames(role_str, (38, 42))

        # 1. Header Bar Status Pemain
        self.header = self.create_header()
        self.header.pack(fill="x", side="top", padx=15, pady=(10, 5))

        # Bind resize listener untuk background utama
        self.bind("<Configure>", self._on_window_resize)

        # 2. Main Content (Split Kiri: Canvas Peta, Kanan: Kontrol & Navigasi)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # Panel Kiri: Canvas Peta Dungeon Graph
        left_panel = ctk.CTkFrame(
            content_frame, fg_color=BG_PANEL, border_color=BORDER_COLOR,
            border_width=1, corner_radius=12
        )
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Header Peta
        map_title_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        map_title_frame.pack(fill="x", padx=14, pady=(8, 2))

        lbl_map_title = ctk.CTkLabel(
            map_title_frame, text="🗺️ ATLAS DUNGEON RERUNTUHAN PURBA",
            font=FONT_HEADING, text_color=COLOR_GOLD
        )
        lbl_map_title.pack(side="left")

        self.lbl_map_status_hint = ctk.CTkLabel(
            map_title_frame,
            text="🟢 Hijau: Dapat Dikunjungi  |  ⭐ Emas: Posisi Hero",
            font=FONT_MONO_SMALL, text_color=TEXT_MUTED
        )
        self.lbl_map_status_hint.pack(side="right")

        # Canvas Tkinter untuk visualisasi Peta Graph
        self.canvas = tk.Canvas(
            left_panel, bg="#0A0C14", highlightthickness=1,
            highlightbackground="#242B40", cursor="arrow"
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self.canvas.bind("<Configure>", lambda e: self.draw_graph_map())
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_canvas_mouse_move)
        self.canvas.bind("<Leave>", self.on_canvas_mouse_leave)

        # Baris Petunjuk / Legenda Bawah Canvas
        legend_frame = ctk.CTkFrame(left_panel, fg_color="#121522", corner_radius=6, height=28)
        legend_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.lbl_legend_info = ctk.CTkLabel(
            legend_frame,
            text="💡 Petunjuk: Arahkan kursor ke ruangan untuk melihat info. Klik ruangan hijau untuk melangkah.",
            font=FONT_SMALL, text_color=TEXT_SECONDARY
        )
        self.lbl_legend_info.pack(side="left", padx=10, pady=2)

        # Panel Kanan: Info Ruangan & Kontrol Aksi
        right_panel = ctk.CTkFrame(
            content_frame, fg_color=BG_PANEL, border_color=BORDER_COLOR,
            border_width=1, corner_radius=12, width=390
        )
        right_panel.pack(side="right", fill="both", padx=(8, 0))
        right_panel.pack_propagate(False)

        self.setup_right_panel(right_panel)

        # 3. Footer: Log Penjelajahan
        self.log_panel = LogPanel(self, title="Riwayat Penjelajahan & Log Sistem", height=90)
        self.log_panel.pack(fill="x", side="bottom", padx=15, pady=(5, 10))
        self.log_panel.add_log(f"Petualangan dimulai! Karaktermu berada di {self.player.location}.")

        self.refresh_view()

        # Mulai animasi idle & efek peta berkala
        self.start_map_animation()

    # ==================== SIKLUS HIDUP & ANIMASI ====================

    def start_map_animation(self) -> None:
        """Memulai loop animasi periodik untuk sprite hero di peta."""
        self.animate_map_tick()

    def animate_map_tick(self) -> None:
        """Satu tick animasi idle sprite di peta."""
        if not self.winfo_exists():
            return

        self.idle_frame_idx += 1
        # Update sprite pemain di canvas jika ada
        if self.player_map_idle_frames:
            curr_id = self.game_state.current_location.id
            if curr_id in self.node_positions:
                px, py = self.node_positions[curr_id]
                frame = self.player_map_idle_frames[self.idle_frame_idx % len(self.player_map_idle_frames)]
                # Update item sprite jika sudah ada tag
                if self.canvas.find_withtag("hero_sprite"):
                    self.canvas.itemconfigure("hero_sprite", image=frame)

        self.anim_after_id = self.after(160, self.animate_map_tick)

    def destroy(self) -> None:
        """Membersihkan timer animasi saat view ditutup."""
        if self.anim_after_id:
            try:
                self.after_cancel(self.anim_after_id)
            except Exception:
                pass
        super().destroy()

    def setup_background(self) -> None:
        """Memuat gambar latar belakang lantai batu dungeon skala penuh untuk frame utama."""
        self._bg_pil = load_pil_image("backgrounds/dungeon_map_bg_dark.png")
        if self._bg_pil:
            try:
                self._bg_ctk = ctk.CTkImage(
                    light_image=self._bg_pil,
                    dark_image=self._bg_pil,
                    size=(self._current_w, self._current_h)
                )
                self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                if hasattr(self, "_canvas"):
                    self.bg_label.lift(self._canvas)
            except Exception as e:
                print(f"[ExplorationView] Gagal memuat background: {e}")

    def _on_window_resize(self, event) -> None:
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
                    if hasattr(self, "_canvas"):
                        self.bg_label.lift(self._canvas)

    # ==================== HEADER BAR ====================

    def create_header(self) -> ctk.CTkFrame:
        """Membuat bilah status pemain bertema pixel fantasy di bagian atas."""
        header = ctk.CTkFrame(
            self, fg_color=BG_PANEL, border_color=BORDER_COLOR,
            border_width=1, corner_radius=10, height=54
        )

        role_icon = get_rpg_icon_by_name("sword_gold", (20, 20)) if "Fighter" in self.player.role.value else get_rpg_icon_by_name("book_arcane", (20, 20))
        role_color = COLOR_PRIMARY if "Fighter" in self.player.role.value else COLOR_ACCENT

        # Profil Pemain
        prof_frame = ctk.CTkFrame(header, fg_color="transparent")
        prof_frame.pack(side="left", padx=16, pady=8)

        lbl_profile = ctk.CTkLabel(
            prof_frame,
            text=f" {self.player.name}",
            image=role_icon,
            compound="left",
            font=FONT_BOLD,
            text_color=TEXT_PRIMARY
        )
        lbl_profile.pack(side="left")

        role_badge = ctk.CTkLabel(
            prof_frame,
            text=f"[{self.player.role.value.upper()}]",
            font=FONT_MONO_SMALL,
            text_color=role_color
        )
        role_badge.pack(side="left", padx=(8, 0))

        # Bilah Stat HP & DEF
        bar_frame = ctk.CTkFrame(header, fg_color="transparent")
        bar_frame.pack(side="left", padx=20)

        self.bar_hp = StatBar(
            bar_frame, label="HP", current=self.player.hp, maximum=self.player.max_hp,
            bar_color=COLOR_DANGER, width=140, height=10
        )
        self.bar_hp.pack(side="left", padx=10)

        self.bar_def = StatBar(
            bar_frame, label="DEF", current=self.player.defense, maximum=self.player.max_defense,
            bar_color=COLOR_DEFENSE, width=140, height=10
        )
        self.bar_def.pack(side="left", padx=10)

        # Lencana Lokasi Aktif
        self.badge_loc = ctk.CTkLabel(
            header,
            text=f"🧭 Lokasi: {self.player.location}",
            font=FONT_BOLD,
            text_color=COLOR_GOLD
        )
        self.badge_loc.pack(side="right", padx=16)

        return header

    # ==================== PANEL KANAN (KONTROL & INFO) ====================

    def setup_right_panel(self, parent: ctk.CTkFrame) -> None:
        """Mengatur isi panel kontrol sisi kanan bertema Pixel RPG."""
        # 1. KARTU RUANGAN AKTIF
        room_card = ctk.CTkFrame(parent, fg_color=BG_CARD, border_color=BORDER_COLOR, border_width=1, corner_radius=10)
        room_card.pack(fill="x", padx=12, pady=(12, 6))

        # Header Kartu Ruangan
        top_row = ctk.CTkFrame(room_card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 4))

        self.lbl_room_badge = ctk.CTkLabel(
            top_row, text="[RUANGAN AKTIF]", font=FONT_MONO_SMALL, text_color=COLOR_GOLD
        )
        self.lbl_room_badge.pack(side="left")

        # Konten Utama Ruangan (Preview Icon + Teks)
        info_row = ctk.CTkFrame(room_card, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_room_icon_preview = ctk.CTkLabel(info_row, text="", width=68, height=68)
        self.lbl_room_icon_preview.pack(side="left", padx=(0, 10))

        text_col = ctk.CTkFrame(info_row, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)

        self.lbl_room_title = ctk.CTkLabel(
            text_col, text="", font=FONT_HEADING, text_color=COLOR_GOLD, anchor="w"
        )
        self.lbl_room_title.pack(fill="x")

        self.lbl_room_desc = ctk.CTkLabel(
            text_col, text="", font=FONT_SMALL, text_color=TEXT_SECONDARY,
            wraplength=260, justify="left", anchor="w"
        )
        self.lbl_room_desc.pack(fill="x", pady=(2, 0))

        # 2. EVENT KHUSUS RUANGAN (DINAMIS)
        self.event_frame = ctk.CTkFrame(parent, fg_color="#1E1420", border_color="#581C87", border_width=1, corner_radius=10)
        self.event_frame.pack(fill="x", padx=12, pady=6)

        self.lbl_event_status = ctk.CTkLabel(
            self.event_frame, text="", font=FONT_BOLD, text_color=TEXT_PRIMARY, wraplength=340
        )
        self.lbl_event_status.pack(pady=(10, 6), padx=10)

        self.btn_room_event = ctk.CTkButton(
            self.event_frame, text="Mulai Event", font=FONT_BOLD, height=36,
            fg_color=COLOR_PRIMARY, hover_color="#2563EB", command=self.trigger_room_event
        )
        self.btn_room_event.pack(fill="x", padx=12, pady=(0, 10))

        # 3. NAVIGASI JALUR RUANGAN YANG TERHUBUNG
        nav_header = ctk.CTkFrame(parent, fg_color="transparent")
        nav_header.pack(fill="x", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            nav_header, text="🧭 PILIH JALUR MELANGKAH:", font=FONT_BOLD, text_color=TEXT_PRIMARY
        ).pack(side="left")

        self.lbl_neighbor_count = ctk.CTkLabel(
            nav_header, text="(0 Jalur)", font=FONT_MONO_SMALL, text_color=TEXT_MUTED
        )
        self.lbl_neighbor_count.pack(side="right")

        self.paths_scroll = ctk.CTkScrollableFrame(parent, fg_color="#121522", corner_radius=8, height=130)
        self.paths_scroll.pack(fill="both", expand=True, padx=12, pady=4)

        # 4. ACTION BAR (Mage Map Vision & Tas Inventory)
        actions_frame = ctk.CTkFrame(parent, fg_color="transparent")
        actions_frame.pack(fill="x", padx=12, pady=(6, 12))

        if self.player.can_use_map_vision:
            icon_vision = get_rpg_icon_by_name("book_gold", (18, 18))
            self.btn_dijkstra = ctk.CTkButton(
                actions_frame, text=" Map Vision (Dijkstra)", image=icon_vision, compound="left",
                font=FONT_BOLD, height=34, fg_color=COLOR_ACCENT, hover_color="#7C3AED", command=self.toggle_dijkstra_vision
            )
            self.btn_dijkstra.pack(fill="x", pady=(0, 6))

        icon_inv = get_rpg_icon_by_name("inventory", (20, 20))
        btn_inv = ctk.CTkButton(
            actions_frame, text=" Buka Tas / Inventory", image=icon_inv, compound="left",
            font=FONT_BODY, height=34, fg_color=BG_CARD, border_color=BORDER_COLOR,
            border_width=1, hover_color=BG_HOVER, command=self.show_inventory_dialog
        )
        btn_inv.pack(fill="x")

    # ==================== RENDERING PETA GRAPH 2D PIXEL RPG ====================

    def draw_graph_map(self) -> None:
        """Menggambar visual peta graph 2D Pixel RPG lengkap di Canvas Tkinter."""
        self.canvas.delete("all")
        self._canvas_img_refs.clear()

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 50 or height < 50:
            req_w = self.canvas.winfo_reqwidth()
            req_h = self.canvas.winfo_reqheight()
            width = req_w if req_w >= 50 else 540
            height = req_h if req_h >= 50 else 440

        # 1. Gambar Background Tekstur Batu Lantai Dungeon Pixel
        bg_tk = get_map_background_tk((width, height))
        if bg_tk:
            self._canvas_img_refs.append(bg_tk)
            self.canvas.create_image(0, 0, image=bg_tk, anchor="nw", tags="map_bg")
        else:
            # Fallback warna gelap bertema
            self.canvas.create_rectangle(0, 0, width, height, fill="#0F121C", outline="")

        # 2. Hitung posisi pixel tiap node (dengan padding aman)
        self.node_positions.clear()
        pad_x = 55
        pad_y = 55
        usable_w = max(50, width - (pad_x * 2))
        usable_h = max(50, height - (pad_y * 2))

        for loc in self.dungeon.locations.values():
            px = int(loc.ui_x * usable_w) + pad_x
            py = int(loc.ui_y * usable_h) + pad_y
            self.node_positions[loc.id] = (px, py)

        curr_loc_id = self.game_state.current_location.id
        current_neighbor_pairs = self.dungeon.get_neighbors(curr_loc_id)
        current_neighbor_ids = {n_loc.id for n_loc, _ in current_neighbor_pairs}

        # 3. GAMBAR JALUR KONEKSI (EDGES)
        drawn_edges = set()
        for from_id, neighbors in self.dungeon.adjacency.items():
            if from_id not in self.node_positions:
                continue
            x1, y1 = self.node_positions[from_id]

            for to_id, weight in neighbors:
                if to_id not in self.node_positions:
                    continue
                edge_key = tuple(sorted((from_id, to_id)))
                if edge_key in drawn_edges:
                    continue
                drawn_edges.add(edge_key)

                x2, y2 = self.node_positions[to_id]
                is_connected_to_current = (from_id == curr_loc_id or to_id == curr_loc_id)
                is_hovered_edge = (
                    self.hovered_node_id in (from_id, to_id) and is_connected_to_current
                )
                is_dijkstra_path = self.dijkstra_active and (edge_key in self.dijkstra_highlight_edges)

                # Bayangan luar jalur batu (Gutter / trench)
                self.canvas.create_line(x1, y1, x2, y2, fill="#07090F", width=8, capstyle="round")

                # Jalur Batu Aktif / Pasif
                if is_hovered_edge:
                    # Jalur yang sedang disorot kursor (Pendar Emas Menyala)
                    self.canvas.create_line(x1, y1, x2, y2, fill="#D97706", width=5, capstyle="round")
                    self.canvas.create_line(x1, y1, x2, y2, fill="#FDE047", width=2.5, capstyle="round")
                elif is_dijkstra_path:
                    # Jalur Rekomendasi Dijkstra (Ungu Mistis Berpendar)
                    self.canvas.create_line(x1, y1, x2, y2, fill="#7C3AED", width=5, capstyle="round")
                    self.canvas.create_line(x1, y1, x2, y2, fill="#C084FC", width=2.5, capstyle="round", dash=(6, 3))
                elif is_connected_to_current:
                    # Jalur yang dapat diakses langsung dari posisi pemain (Hijau Zamrud Terbuka)
                    self.canvas.create_line(x1, y1, x2, y2, fill="#047857", width=4.5, capstyle="round")
                    self.canvas.create_line(x1, y1, x2, y2, fill="#34D399", width=2, capstyle="round", dash=(5, 3))
                else:
                    # Jalur batu biasa / belum terhubung langsung
                    self.canvas.create_line(x1, y1, x2, y2, fill="#1E2336", width=3.5, capstyle="round")
                    self.canvas.create_line(x1, y1, x2, y2, fill="#2F3650", width=1.5, capstyle="round", dash=(2, 4))

                # Lencana jarak tempuh / bobot jalan di tengah jalur
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2

                if is_hovered_edge:
                    pill_bg = "#B45309"
                    pill_border = "#FDE047"
                    pill_text = "#FFFFFF"
                elif is_dijkstra_path:
                    pill_bg = "#5B21B6"
                    pill_border = "#C084FC"
                    pill_text = "#FFFFFF"
                elif is_connected_to_current:
                    pill_bg = "#064E3B"
                    pill_border = "#10B981"
                    pill_text = "#D1FAE5"
                else:
                    pill_bg = "#111422"
                    pill_border = "#333A56"
                    pill_text = "#9CA3AF"

                # Gambar kotak lencana jarak
                bw, bh = 14, 9
                self.canvas.create_rectangle(
                    mid_x - bw, mid_y - bh, mid_x + bw, mid_y + bh,
                    fill=pill_bg, outline=pill_border, width=1
                )
                self.canvas.create_text(
                    mid_x, mid_y, text=str(weight), fill=pill_text,
                    font=("Consolas", 8, "bold")
                )

        # 4. GAMBAR RUANGAN / VERTEX (NODE PIXEL BADGES)
        for loc_id, (nx, ny) in self.node_positions.items():
            loc = self.dungeon.get_location_by_id(loc_id)
            if not loc:
                continue

            is_current = (loc_id == curr_loc_id)
            is_neighbor = loc_id in current_neighbor_ids
            is_hovered = (loc_id == self.hovered_node_id)

            # Bayangan dasar batu
            self.canvas.create_oval(
                nx - 24, ny + 16, nx + 24, ny + 28,
                fill="#07090F", outline="", tags="shadow"
            )

            # Bingkai aura luar
            if is_current:
                # Emas berpendar tebal untuk Hero
                self.canvas.create_oval(
                    nx - 28, ny - 28, nx + 28, ny + 28,
                    outline="#F59E0B", width=3, fill="#1C180E"
                )
                self.canvas.create_oval(
                    nx - 25, ny - 25, nx + 25, ny + 25,
                    outline="#FBBF24", width=1
                )
            elif is_hovered and is_neighbor:
                # Hover pada jalur terbuka
                self.canvas.create_oval(
                    nx - 28, ny - 28, nx + 28, ny + 28,
                    outline="#FDE047", width=3, fill="#064E3B"
                )
            elif is_neighbor:
                # Hijau zamrud untuk ruangan yang bisa langsung dikunjungi
                self.canvas.create_oval(
                    nx - 27, ny - 27, nx + 27, ny + 27,
                    outline="#10B981", width=2.5, fill="#0B2019"
                )
            elif is_hovered:
                # Hover pada ruangan jauh
                self.canvas.create_oval(
                    nx - 27, ny - 27, nx + 27, ny + 27,
                    outline="#38BDF8", width=2, fill="#141E2D"
                )
            else:
                # Ruangan belum terjangkau
                self.canvas.create_oval(
                    nx - 26, ny - 26, nx + 26, ny + 26,
                    outline="#2E344E", width=1.5, fill="#121524"
                )

            # Gambar Icon Pixel Art 16-Bit Ruangan
            node_icon_tk = get_map_node_icon_tk(loc_id, (46, 46))
            if node_icon_tk:
                self._canvas_img_refs.append(node_icon_tk)
                self.canvas.create_image(nx, ny, image=node_icon_tk, anchor="center")

            # Jika Ruangan Ini adalah Lokasi Pemain: GAMBAR SPRITE HERO LIVE
            if is_current:
                if self.player_map_idle_frames:
                    hero_frame = self.player_map_idle_frames[self.idle_frame_idx % len(self.player_map_idle_frames)]
                    self._canvas_img_refs.append(hero_frame)
                    self.canvas.create_image(
                        nx, ny - 4, image=hero_frame, anchor="center", tags="hero_sprite"
                    )

                # Tag Banner Mini "📍 HERO" di atas kepala
                self.canvas.create_rectangle(
                    nx - 22, ny - 34, nx + 22, ny - 22,
                    fill="#181B28", outline="#F59E0B", width=1
                )
                self.canvas.create_text(
                    nx, ny - 28, text="📍 HERO", fill="#FBBF24",
                    font=("Segoe UI", 7, "bold")
                )

            # Lencana status tipe ruangan di sudut atas kanan
            self.draw_node_event_badge(loc, nx, ny)

            # Plakat Nama Ruangan di Bawah Node
            self.draw_node_nameplate(loc, nx, ny, is_current, is_neighbor, is_hovered)

    def draw_node_event_badge(self, loc: DungeonLocation, nx: int, ny: int) -> None:
        """Menggambar pin penanda event khusus (Monster, Puzzle, Rest, Quest)."""
        bx, by = nx + 16, ny - 16

        if loc.event_type == RoomEvent.BATTLE:
            # Monster Room
            monster = self.game_state.get_current_room_monster() if loc.id == self.game_state.current_location.id else None
            # Jika monster masih hidup di lokasi ini
            is_defeated = False
            if loc.monster_name:
                m_obj = self.game_state.monsters.get(loc.monster_name.lower())
                if m_obj and not m_obj.is_alive:
                    is_defeated = True

            if is_defeated:
                # Tanda selesai / bersih
                self.canvas.create_oval(bx - 7, by - 7, bx + 7, by + 7, fill="#059669", outline="#10B981", width=1)
                self.canvas.create_text(bx, by, text="✓", fill="#FFFFFF", font=("Segoe UI", 7, "bold"))
            else:
                # Tanda pedang / bahaya
                self.canvas.create_oval(bx - 8, by - 8, bx + 8, by + 8, fill="#DC2626", outline="#F87171", width=1)
                self.canvas.create_text(bx, by, text="⚔", fill="#FFFFFF", font=("Segoe UI", 7, "bold"))

        elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK):
            solved = False
            if loc.name == "Labyrinth Tower" and self.game_state.completed_sliding_puzzle:
                solved = True
            elif loc.name == "The Eternal Relic" and self.game_state.completed_stack_puzzle:
                solved = True

            if solved:
                self.canvas.create_oval(bx - 7, by - 7, bx + 7, by + 7, fill="#059669", outline="#10B981", width=1)
                self.canvas.create_text(bx, by, text="✓", fill="#FFFFFF", font=("Segoe UI", 7, "bold"))
            else:
                self.canvas.create_oval(bx - 8, by - 8, bx + 8, by + 8, fill="#7C3AED", outline="#A78BFA", width=1)
                self.canvas.create_text(bx, by, text="🧩", fill="#FFFFFF", font=("Segoe UI", 7))

        elif loc.event_type == RoomEvent.SAFETY_HEAL:
            self.canvas.create_oval(bx - 8, by - 8, bx + 8, by + 8, fill="#059669", outline="#34D399", width=1)
            self.canvas.create_text(bx, by, text="🏕", fill="#FFFFFF", font=("Segoe UI", 7))

        elif loc.event_type == RoomEvent.QUEST_CONVEYOR:
            solved = self.game_state.completed_village_quest
            if solved:
                self.canvas.create_oval(bx - 7, by - 7, bx + 7, by + 7, fill="#059669", outline="#10B981", width=1)
                self.canvas.create_text(bx, by, text="✓", fill="#FFFFFF", font=("Segoe UI", 7, "bold"))
            else:
                self.canvas.create_oval(bx - 8, by - 8, bx + 8, by + 8, fill="#0284C7", outline="#38BDF8", width=1)
                self.canvas.create_text(bx, by, text="📦", fill="#FFFFFF", font=("Segoe UI", 7))

    def draw_node_nameplate(
        self, loc: DungeonLocation, nx: int, ny: int,
        is_current: bool, is_neighbor: bool, is_hovered: bool
    ) -> None:
        """Menggambar papan nama ruangan di bawah node."""
        py = ny + 36
        text_str = f"{loc.name}"

        if is_current:
            box_bg = "#1C180E"
            box_border = "#F59E0B"
            text_color = "#FDE047"
        elif is_hovered and is_neighbor:
            box_bg = "#0B261D"
            box_border = "#34D399"
            text_color = "#6EE7B7"
        elif is_neighbor:
            box_bg = "#0A1D16"
            box_border = "#10B981"
            text_color = "#A7F3D0"
        elif is_hovered:
            box_bg = "#131C2D"
            box_border = "#38BDF8"
            text_color = "#BAE6FD"
        else:
            box_bg = "#0E111C"
            box_border = "#262C42"
            text_color = "#9CA3AF"

        # Ukuran papan nama
        pw = max(38, len(text_str) * 3 + 10)
        ph = 8

        self.canvas.create_rectangle(
            nx - pw, py - ph, nx + pw, py + ph,
            fill=box_bg, outline=box_border, width=1
        )
        self.canvas.create_text(
            nx, py, text=text_str, fill=text_color,
            font=("Segoe UI", 8, "bold")
        )

    # ==================== INTERAKSI MOUSE PADA CANVAS ====================

    def on_canvas_mouse_move(self, event) -> None:
        """Memproses pergerakan kursor mouse di atas peta."""
        mx, my = event.x, event.y
        new_hover_id: Optional[int] = None

        for loc_id, (nx, ny) in self.node_positions.items():
            dist = math.hypot(mx - nx, my - ny)
            if dist <= 30:
                new_hover_id = loc_id
                break

        if new_hover_id != self.hovered_node_id:
            self.hovered_node_id = new_hover_id
            curr_id = self.game_state.current_location.id
            neighbor_ids = {n_loc.id for n_loc, _ in self.dungeon.get_neighbors(curr_id)}

            if self.hovered_node_id is not None:
                h_loc = self.dungeon.get_location_by_id(self.hovered_node_id)
                if self.hovered_node_id == curr_id:
                    self.canvas.config(cursor="arrow")
                    self.lbl_legend_info.configure(
                        text=f"📍 Kamu sedang berada di {h_loc.name} (#{h_loc.id}).",
                        text_color=COLOR_GOLD
                    )
                elif self.hovered_node_id in neighbor_ids:
                    self.canvas.config(cursor="hand2")
                    d_step = self.dungeon.get_distance(curr_id, self.hovered_node_id)
                    event_tag = self.get_event_short_description(h_loc)
                    self.lbl_legend_info.configure(
                        text=f"➔ Menuju {h_loc.name} (Jarak: {d_step}) {event_tag} — Klik untuk melangkah!",
                        text_color="#34D399"
                    )
                else:
                    self.canvas.config(cursor="arrow")
                    self.lbl_legend_info.configure(
                        text=f"🔒 {h_loc.name} (#{h_loc.id}) — Tidak terhubung langsung dari ruangan ini.",
                        text_color=TEXT_MUTED
                    )
            else:
                self.canvas.config(cursor="arrow")
                self.lbl_legend_info.configure(
                    text="💡 Petunjuk: Arahkan kursor ke ruangan untuk melihat info. Klik ruangan hijau untuk melangkah.",
                    text_color=TEXT_SECONDARY
                )

            self.draw_graph_map()

    def on_canvas_mouse_leave(self, event) -> None:
        """Mengembalikan status saat mouse keluar dari canvas."""
        if self.hovered_node_id is not None:
            self.hovered_node_id = None
            self.canvas.config(cursor="arrow")
            self.lbl_legend_info.configure(
                text="💡 Petunjuk: Arahkan kursor ke ruangan untuk melihat info. Klik ruangan hijau untuk melangkah.",
                text_color=TEXT_SECONDARY
            )
            self.draw_graph_map()

    def on_canvas_click(self, event) -> None:
        """Memproses klik pengguna pada node peta untuk berpindah ruangan."""
        click_x, click_y = event.x, event.y
        for loc_id, (nx, ny) in self.node_positions.items():
            distance = math.hypot(click_x - nx, click_y - ny)
            if distance <= 28:
                self.try_move_player(loc_id)
                break

    # ==================== LOGIKA PERPINDAHAN & EVENT ====================

    def refresh_view(self) -> None:
        """Memperbarui seluruh data tampilan eksplorasi."""
        curr_loc = self.game_state.current_location

        # 1. Update Header
        self.bar_hp.set_values(self.player.hp, self.player.max_hp)
        self.bar_def.set_values(self.player.defense, self.player.max_defense)
        self.badge_loc.configure(text=f"🧭 Lokasi: {curr_loc.name} (#{curr_loc.id})")

        # 2. Update Info Ruangan & Icon Preview di Panel Kanan
        self.lbl_room_title.configure(text=f"{curr_loc.name} (#{curr_loc.id})")
        self.lbl_room_desc.configure(text=curr_loc.description)
        self.lbl_room_badge.configure(text=self.get_event_category_badge(curr_loc))

        room_ctk_icon = get_map_node_icon_ctk(curr_loc.id, (68, 68))
        if room_ctk_icon:
            self.lbl_room_icon_preview.configure(image=room_ctk_icon)

        # 3. Update Daftar Jalur Navigasi
        for widget in self.paths_scroll.winfo_children():
            widget.destroy()

        neighbors = self.dungeon.get_neighbors(curr_loc.id)
        self.lbl_neighbor_count.configure(text=f"({len(neighbors)} Jalur Terhubung)")

        for target_loc, dist in neighbors:
            hint_icon = self.get_target_room_icon(target_loc)
            btn_text = f"  ➔  {hint_icon} {target_loc.name}   [👣 {dist}]"

            btn = ctk.CTkButton(
                self.paths_scroll,
                text=btn_text,
                font=FONT_BOLD,
                height=38,
                anchor="w",
                fg_color=BG_CARD,
                border_color=BORDER_COLOR,
                border_width=1,
                hover_color="#1E3A8A",
                command=lambda tid=target_loc.id: self.try_move_player(tid)
            )
            btn.pack(fill="x", pady=3)

            # Binding hover untuk menyalakan jalur di canvas
            btn.bind("<Enter>", lambda e, tid=target_loc.id: self._highlight_path_target(tid))
            btn.bind("<Leave>", lambda e: self._highlight_path_target(None))

        # 4. Update Event Box
        self.refresh_room_event(curr_loc)

        # 5. Gambar ulang peta canvas
        self.draw_graph_map()

    def _highlight_path_target(self, target_id: Optional[int]) -> None:
        """Menyorot node tujuan di peta saat kursor berada di atas tombol navigasi."""
        if self.hovered_node_id != target_id:
            self.hovered_node_id = target_id
            self.draw_graph_map()

    def get_event_category_badge(self, loc: DungeonLocation) -> str:
        """Mengembalikan label kategori ruangan untuk plakat info."""
        if loc.event_type == RoomEvent.BATTLE:
            return "[⚔️ SARANG MONSTER / BOSS]"
        elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK):
            return "[🧩 RUANGAN TEKA-TEKI KUNO]"
        elif loc.event_type == RoomEvent.SAFETY_HEAL:
            return "[🏕️ SANCTUARY / REST AREA]"
        elif loc.event_type == RoomEvent.QUEST_CONVEYOR:
            return "[📦 DESA PENGRAJIN / QUEST]"
        elif loc.event_type == RoomEvent.DIALOG_FOREST:
            return "[🌲 LEMBAH MISTIK ROH POHON]"
        elif loc.id == 0:
            return "[🏛️ GERBANG UTAMA DUNGEON]"
        return "[🗿 RERUNTUHAN PURBA]"

    def get_target_room_icon(self, loc: DungeonLocation) -> str:
        """Mengembalikan ikon representatif untuk daftar rute navigasi."""
        if loc.event_type == RoomEvent.BATTLE:
            return "⚔️"
        elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK):
            return "🧩"
        elif loc.event_type == RoomEvent.SAFETY_HEAL:
            return "🏕️"
        elif loc.event_type == RoomEvent.QUEST_CONVEYOR:
            return "📦"
        elif loc.event_type == RoomEvent.DIALOG_FOREST:
            return "🌲"
        return "🏛️"

    def get_event_short_description(self, loc: DungeonLocation) -> str:
        """Deskripsi singkat untuk tooltip di bawah peta."""
        if loc.event_type == RoomEvent.BATTLE:
            return f"| ⚔️ Ada {loc.monster_name or 'Monster'}!"
        elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK):
            return "| 🧩 Ruang Teka-Teki"
        elif loc.event_type == RoomEvent.SAFETY_HEAL:
            return "| 🏕️ Ruang Pemulihan HP"
        elif loc.event_type == RoomEvent.QUEST_CONVEYOR:
            return "| 📦 Quest Pemilahan Barang"
        elif loc.event_type == RoomEvent.DIALOG_FOREST:
            return "| 🌲 Bertemu Roh Gyoot"
        return ""

    def refresh_room_event(self, loc: DungeonLocation) -> None:
        """Memeriksa dan mengatur tampilan panel interaksi event aktif ruangan."""
        monster = self.game_state.get_current_room_monster()

        if monster and monster.is_alive:
            self.event_frame.pack(fill="x", padx=12, pady=6)
            self.event_frame.configure(fg_color="#2A1015", border_color="#991B1B")
            self.lbl_event_status.configure(
                text=f"⚠️ PERINGATAN KAIJU!\n{monster.name} sedang mengintai di sini!\n(HP: {monster.hp} | ATK: {monster.attack})",
                text_color=COLOR_DANGER
            )
            self.btn_room_event.configure(
                text=f"⚔️ Tantang {monster.name.upper()}",
                fg_color=COLOR_DANGER, hover_color="#B91C1C"
            )
        elif loc.name == "Labyrinth Tower" and not self.game_state.completed_sliding_puzzle:
            self.event_frame.pack(fill="x", padx=12, pady=6)
            self.event_frame.configure(fg_color="#171A2E", border_color="#2563EB")
            self.lbl_event_status.configure(
                text="🧩 Teka-teki 8-Puzzle Labirin Kuno\nSusun ubin angka kembali ke urutan semula.",
                text_color=COLOR_PRIMARY
            )
            self.btn_room_event.configure(
                text="Mainkan Labyrinth Puzzle", fg_color=COLOR_PRIMARY, hover_color="#1D4ED8"
            )
        elif loc.name == "The Eternal Relic" and not self.game_state.completed_stack_puzzle:
            self.event_frame.pack(fill="x", padx=12, pady=6)
            self.event_frame.configure(fg_color="#2A2010", border_color="#D97706")
            self.lbl_event_status.configure(
                text="⚗️ Relik Bejana Warna Abadi (Stack)\nUrutkan cairan mistis ke dalam tabung yang sesuai.",
                text_color=COLOR_GOLD
            )
            self.btn_room_event.configure(
                text="Selesaikan Relik Warna", fg_color=COLOR_GOLD, hover_color="#B45309"
            )
        elif loc.name == "Village" and not self.game_state.completed_village_quest:
            self.event_frame.pack(fill="x", padx=12, pady=6)
            self.event_frame.configure(fg_color="#0F241E", border_color="#059669")
            self.lbl_event_status.configure(
                text="📦 Quest Ban Berjalan Desa (Queue)\nBantu warga menyortir kiriman peralatan ke gerobak.",
                text_color="#34D399"
            )
            self.btn_room_event.configure(
                text="Mulai Quest Desa", fg_color="#10B981", hover_color="#047857"
            )
        elif loc.name == "Forest" and not self.game_state.completed_forest_dialogue:
            self.event_frame.pack(fill="x", padx=12, pady=6)
            self.event_frame.configure(fg_color="#0D251D", border_color="#10B981")
            self.lbl_event_status.configure(
                text="🌲 Suara Gemerisik Ranting Purba\nRoh Gyoot sedang menunggumu di rerimbunan pohon.",
                text_color="#6EE7B7"
            )
            self.btn_room_event.configure(
                text="Bicara dengan Gyoot", fg_color="#059669", hover_color="#047857"
            )
        elif loc.name == "Safety Room":
            self.event_frame.pack(fill="x", padx=12, pady=6)
            self.event_frame.configure(fg_color="#092019", border_color="#059669")
            self.lbl_event_status.configure(
                text="✨ Api Unggun Perkemahan yang Hangat\nTempat beristirahat untuk menyegarkan stamina pahlawan.",
                text_color="#34D399"
            )
            self.btn_room_event.configure(
                text="Beristirahat (+100 HP)", fg_color="#10B981", hover_color="#047857"
            )
        else:
            self.event_frame.pack_forget()

    def try_move_player(self, target_id: int) -> None:
        """Mengeksekusi perpindahan pemain ke lokasi target."""
        if target_id == self.game_state.current_location.id:
            self.log_panel.add_log(f"Kamu sudah berada di ruangan {self.game_state.current_location.name}.")
            return

        success, msg = self.game_state.move_player(target_id)
        if success:
            self.log_panel.add_log(f"➔ {msg}")
            # Reset Dijkstra overlay saat melangkah jika diinginkan
            self.refresh_view()
        else:
            self.log_panel.add_log(f"❌ {msg}")
            messagebox.showwarning("Jalur Tidak Terbuka", msg)

    def trigger_room_event(self) -> None:
        """Menjalankan event ruangan yang aktif."""
        curr_loc = self.game_state.current_location
        monster = self.game_state.get_current_room_monster()

        if monster and monster.is_alive:
            self.app.show_combat(monster)
        elif curr_loc.name == "Labyrinth Tower":
            self.app.show_sliding_puzzle()
        elif curr_loc.name == "The Eternal Relic":
            self.app.show_stack_puzzle()
        elif curr_loc.name == "Village":
            self.app.show_conveyor_quest()
        elif curr_loc.name == "Forest":
            self.app.show_forest_dialogue()
        elif curr_loc.name == "Safety Room":
            healed = self.player.heal(100)
            self.log_panel.add_log(f"Kamu beristirahat sejenak di dekat api unggun Safety Room (+{healed} HP).")
            self.refresh_view()

    def toggle_dijkstra_vision(self) -> None:
        """Mengaktifkan/menonaktifkan Map Vision Dijkstra & menampilkan laporan rute terpendek."""
        self.dijkstra_active = not self.dijkstra_active
        curr_id = self.game_state.current_location.id
        results = self.dungeon.dijkstra_shortest_paths(curr_id)

        self.dijkstra_highlight_edges.clear()
        if self.dijkstra_active:
            # Sorot rute terpendek ke Boss Lair (#10 Throne of Extinction)
            _, boss_path = self.dungeon.dijkstra(curr_id, 10)
            if boss_path:
                for i in range(len(boss_path) - 1):
                    u, v = int(boss_path[i]), int(boss_path[i + 1])
                    self.dijkstra_highlight_edges.add(tuple(sorted((u, v))))

            self.btn_dijkstra.configure(
                text="🔮 Map Vision [AKTIF]", fg_color="#6D28D9", hover_color="#5B21B6"
            )
            self.log_panel.add_log("🔮 Map Vision Dijkstra aktif! Rute terpendek berpendar ungu pada atlas peta.")
        else:
            self.btn_dijkstra.configure(
                text="🔮 Map Vision (Dijkstra)", fg_color=COLOR_ACCENT, hover_color="#7C3AED"
            )
            self.log_panel.add_log("🔮 Map Vision dinonaktifkan.")

        self.draw_graph_map()

        # Tampilkan pop-up informasi jalur
        if self.dijkstra_active:
            self.show_dijkstra_paths(results)

    def show_dijkstra_paths(self, results: Optional[List[DijkstraResult]] = None) -> None:
        """Menampilkan dialog rute terpendek Dijkstra."""
        curr_id = self.game_state.current_location.id
        if results is None:
            results = self.dungeon.dijkstra_shortest_paths(curr_id)

        lines = [
            f"🔮 MAP VISION (ALGORITMA DIJKSTRA) 🔮\n"
            f"Titik Awal: {self.player.location} (#{curr_id})\n" + "=" * 46
        ]
        for res in results:
            if res.target_id == curr_id:
                continue
            path_str = " ➔ ".join(res.path_names)
            lines.append(f"• Menuju {res.target_name} (Total Jarak: {res.distance})\n  Rute: {path_str}")

        popup_text = "\n\n".join(lines)
        messagebox.showinfo("Map Vision - Rute Terpendek Dijkstra", popup_text)

    def show_inventory_dialog(self) -> None:
        """Menampilkan dialog inventaris item kustom bertema Pixel RPG."""
        items = self.player.inventory.get_all_items()
        InventoryDialog(
            self,
            items=items,
            player_name=self.player.name,
            player=self.player,
            on_use_callback=self.refresh_view,
        )
