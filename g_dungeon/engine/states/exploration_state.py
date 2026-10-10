"""
Module: engine/states/exploration_state.py
Description: Layar Eksplorasi Peta Dungeon (PLAY_STATE - MAP).
Menampilkan graf 10 ruangan bertema 2D Pixel RPG Fantasy, visualisasi Algoritma
Dijkstra (Mage Map Vision), interaksi event ruangan, dan pelacak objektif di HUD.
"""

from typing import Any, Dict, List, Optional, Tuple
import math
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
    COLOR_PANEL_HEADER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATE_COMBAT,
    STATE_DIALOG,
    STATE_PAUSE,
    STATE_PUZZLE,
)
from engine.entities import AnimatedSprite
from engine.state_machine import GameState
from engine.ui import FloatingTextManager, LogBox, ObjectiveHUD, UIButton, UIProgressBar
from core.dungeon_graph import DungeonLocation, RoomEvent
from core.player import PlayerRole


class ExplorationState(GameState):
    """Layar navigasi graf dungeon dan aksi ruangan bertema Pixel RPG Fantasy."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.objective_hud = ObjectiveHUD(pygame.Rect(0, 0, SCREEN_WIDTH, 56))
        self.log_box = LogBox(pygame.Rect(820, 520, 440, 180), max_lines=7)
        self.floating_texts = FloatingTextManager()


        # Bar status pemain di HUD bawah
        self.hp_bar = UIProgressBar(
            rect=pygame.Rect(20, 675, 260, 26),
            max_value=3000,
            current_value=3000,
            fill_color=COLOR_HP_GREEN,
            label="HP",
        )
        self.def_bar = UIProgressBar(
            rect=pygame.Rect(295, 675, 180, 26),
            max_value=200,
            current_value=200,
            fill_color=COLOR_DEFENSE_BLUE,
            label="DEF",
        )

        # Area peta graf (kiri-tengah)
        self.map_rect = pygame.Rect(20, 68, 780, 580)
        # Area panel info ruangan & aksi (kanan)
        self.panel_rect = pygame.Rect(820, 68, 440, 440)

        self.travel_buttons: List[UIButton] = []
        self.action_button: Optional[UIButton] = None
        self.btn_map_vision: Optional[UIButton] = None
        self.btn_inventory: Optional[UIButton] = None
        self.btn_pause: Optional[UIButton] = None

        # Mode Dijkstra Vision (Mage)
        self.dijkstra_active: bool = False
        self.dijkstra_paths: Dict[int, List[int]] = {}

        # Interaksi Peta & Animasi
        self.hovered_node_id: Optional[int] = None
        self.anim_time: float = 0.0
        self.player_map_sprite: Optional[AnimatedSprite] = None

        # Modal Inventory
        self.show_inventory_modal: bool = False
        self.btn_close_inv: Optional[UIButton] = None

    def enter(self, **kwargs: Any) -> None:
        """Dipanggil saat memasuki layar eksplorasi."""
        self.dijkstra_active = False
        self.anim_time = 0.0
        self.hovered_node_id = None
        self._setup_player_sprite()
        self._refresh_ui()
        if self.game.state_mgr:
            loc = self.game.state_mgr.current_location
            self.log_box.add_message(f"[*] Tiba di #{loc.id} {loc.name}.")
            # Pasif Mage: Arcane Intellect + Map Vision otomatis aktif
            if self.game.state_mgr.player.role == PlayerRole.MAGE:
                self.dijkstra_active = True
                res = self.game.state_mgr.dungeon.dijkstra_shortest_paths(loc.id)
                self.dijkstra_paths = {r.target_id: r.path_ids for r in res}
                self.log_box.add_message("[*] Pasif Mage aktif: Map Vision otomatis menyorot rute terpendek.")

    def _setup_player_sprite(self) -> None:
        """Menginisialisasi sprite hidup animasi pahlawan di atas node peta."""
        if not self.game.state_mgr:
            return
        role = self.game.state_mgr.player.role
        if role == PlayerRole.KNIGHT:
            frames = self.assets.get_cropped_knight_idle_frames(scale_size=(44, 48))
            self.player_map_sprite = AnimatedSprite(0, 0, {"idle": frames}, default_anim="idle", fps=8.0)
        else:
            frames = self.assets.get_cropped_wizard_idle_frames(scale_size=(48, 44))
            self.player_map_sprite = AnimatedSprite(0, 0, {"idle": frames}, default_anim="idle", fps=7.0)

    def _refresh_ui(self) -> None:
        """Memperbarui tombol aksi dan tetangga berdasarkan lokasi saat ini."""
        if not self.game.state_mgr:
            return

        state = self.game.state_mgr
        curr_loc = state.current_location

        # Perbarui HP & DEF Bar
        self.hp_bar.set_value(state.player.hp, state.player.max_hp)
        self.def_bar.set_value(state.player.defense, state.player.max_defense)

        # Tombol Aksi Ruangan Khusus
        self.action_button = None
        action_rect = pygame.Rect(self.panel_rect.x + 16, self.panel_rect.y + 192, 408, 36)

        if curr_loc.event_type == RoomEvent.BATTLE and curr_loc.monster_name:
            monster = state.monsters.get(curr_loc.monster_name)
            if monster and monster.is_alive:
                self.action_button = UIButton(
                    rect=action_rect,
                    text=f">> Bertarung: {monster.name}!",
                    icon_name="atk",
                    hover_color=(180, 50, 40),
                    on_click=lambda: self._trigger_battle(curr_loc.monster_name),
                )
        elif curr_loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK, RoomEvent.QUEST_CONVEYOR):
            is_done = False
            if curr_loc.event_type == RoomEvent.PUZZLE_SLIDING:
                is_done = state.completed_sliding_puzzle
            elif curr_loc.event_type == RoomEvent.PUZZLE_STACK:
                is_done = state.completed_stack_puzzle
            elif curr_loc.event_type == RoomEvent.QUEST_CONVEYOR:
                is_done = state.completed_village_quest

            btn_txt = ">> Buka Teka-teki" if not is_done else ">> Teka-teki Selesai (Buka Ulang)"
            self.action_button = UIButton(
                rect=action_rect,
                text=btn_txt,
                icon_name="book_arcane",
                hover_color=(110, 80, 160),
                on_click=lambda: self._trigger_puzzle(curr_loc.event_type),
            )
        elif curr_loc.event_type == RoomEvent.DIALOG_FOREST:
            self.action_button = UIButton(
                rect=action_rect,
                text=">> Bicara dengan Roh Pohon Gyoot",
                icon_name="book_gold",
                hover_color=(40, 130, 80),
                on_click=self._trigger_dialog,
            )
        elif curr_loc.event_type == RoomEvent.SAFETY_HEAL:
            self.action_button = UIButton(
                rect=action_rect,
                text=">> Istirahat di Api Unggun (+100 HP)",
                icon_name="heal",
                hover_color=(40, 130, 80),
                on_click=self._trigger_safety_heal,
            )

        # Tombol Tetangga / Jalur Berpindah dengan Ikon Node Pixel Art
        self.travel_buttons.clear()
        neighbors = state.dungeon.get_neighbors(curr_loc.id)

        # Posisi awal tombol jalur bertetangga (adaptif terhadap keberadaan tombol aksi)
        start_y = (self.panel_rect.y + 258) if self.action_button else (self.panel_rect.y + 204)

        if len(neighbors) > 3:
            # Layout 2 kolom jika tetangga lebih dari 3 (mencegah tumpang tindih ke LogBox)
            col_w = 198
            btn_h = 34
            gap_x = 10
            gap_y = 6
            for idx, (n_loc, dist) in enumerate(neighbors):
                col = idx % 2
                row = idx // 2
                bx = self.panel_rect.x + 16 + col * (col_w + gap_x)
                by = start_y + row * (btn_h + gap_y)
                node_icon = self.assets.get_map_node_icon(n_loc.id, size=(22, 22))
                btn = UIButton(
                    rect=pygame.Rect(bx, by, col_w, btn_h),
                    text=f"> #{n_loc.id} {n_loc.name} ({dist})",
                    font_size=12,
                    custom_icon=node_icon,
                    on_click=lambda tid=n_loc.id: self._travel_to(tid),
                )
                self.travel_buttons.append(btn)
        else:
            # Layout 1 kolom penuh jika tetangga 1 s.d 3
            btn_w = 408
            btn_h = 34
            gap_y = 6
            by = start_y
            for n_loc, dist in neighbors:
                node_icon = self.assets.get_map_node_icon(n_loc.id, size=(22, 22))
                btn = UIButton(
                    rect=pygame.Rect(self.panel_rect.x + 16, by, btn_w, btn_h),
                    text=f">> Ke #{n_loc.id} {n_loc.name} (Jarak: {dist})",
                    font_size=13,
                    custom_icon=node_icon,
                    on_click=lambda tid=n_loc.id: self._travel_to(tid),
                )
                self.travel_buttons.append(btn)
                by += btn_h + gap_y

        # Tombol Map Vision (Mage)
        if state.player.role == PlayerRole.MAGE:
            self.btn_map_vision = UIButton(
                rect=pygame.Rect(490, 670, 160, 32),
                text="Map Vision",
                icon_name="magic",
                font_size=13,
                hover_color=(120, 60, 180),
                on_click=self._toggle_map_vision,
            )
        else:
            self.btn_map_vision = None

        # Tombol Tas / Inventory
        self.btn_inventory = UIButton(
            rect=pygame.Rect(660, 670, 140, 32),
            text="Buka Tas",
            icon_name="inventory",
            font_size=13,
            on_click=self._open_inventory,
        )

        # Tombol Pause
        self.btn_pause = UIButton(
            rect=pygame.Rect(SCREEN_WIDTH - 110, 12, 90, 32),
            text="[ Pause ]",
            font_size=13,
            on_click=lambda: self.machine.push_state(STATE_PAUSE),
        )

        # Tombol Tutup Inventory
        self.btn_close_inv = UIButton(
            rect=pygame.Rect(SCREEN_WIDTH // 2 - 60, 520, 120, 36),
            text="Tutup",
            font_size=14,
            on_click=self._close_inventory,
        )

    def _travel_to(self, target_id: int) -> None:
        """Memindahkan pemain ke ruangan lain via graph."""
        if not self.game.state_mgr:
            return
        success, msg = self.game.state_mgr.move_player(target_id)
        if success:
            self.audio.play("click")
            self.log_box.add_message(f"[+] {msg}")
            # Update Dijkstra jika Map Vision aktif
            if self.dijkstra_active:
                res = self.game.state_mgr.dungeon.dijkstra_shortest_paths(target_id)
                self.dijkstra_paths = {r.target_id: r.path_ids for r in res}
            self._refresh_ui()
        else:
            self.audio.play("hit")
            self.log_box.add_message(f"[!] {msg}")
            self.floating_texts.add("TERKUNCI!", SCREEN_WIDTH // 2, 280, COLOR_HP_RED)

    def _trigger_battle(self, monster_name: str) -> None:
        self.machine.change_state(STATE_COMBAT, monster_name=monster_name)

    def _trigger_puzzle(self, puzzle_type: RoomEvent) -> None:
        self.machine.change_state(STATE_PUZZLE, puzzle_type=puzzle_type)

    def _trigger_dialog(self) -> None:
        self.machine.change_state(STATE_DIALOG)

    def _trigger_safety_heal(self) -> None:
        if not self.game.state_mgr:
            return
        healed = self.game.state_mgr.player.heal(100)
        self.audio.play("heal")
        self.log_box.add_message(f"[+] Beristirahat di api unggun. Memulihkan +{healed} HP!")
        self._refresh_ui()

    def _toggle_map_vision(self) -> None:
        """Menghitung rute tercepat Dijkstra ke semua ruangan menggunakan skill Mage."""
        if not self.game.state_mgr:
            return
        self.dijkstra_active = not self.dijkstra_active
        if self.dijkstra_active:
            self.audio.play("magic")
            start_id = self.game.state_mgr.current_location.id
            res = self.game.state_mgr.dungeon.dijkstra_shortest_paths(start_id)
            self.dijkstra_paths = {r.target_id: r.path_ids for r in res}
            self.log_box.add_message("[*] Map Vision aktif! Algoritma Dijkstra memindai rute tercepat.")
        else:
            self.dijkstra_paths.clear()
            self.log_box.add_message("[*] Map Vision dinonaktifkan.")

    def MoveToRoom(self, target_id: int) -> None:
        """Alias MoveToRoom() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self._travel_to(target_id)

    def ComputeShortestPath(self, start_id: Optional[int] = None) -> Any:
        """Alias ComputeShortestPath() sesuai Bagian 1.3 dan Rubrik Teknis."""
        if not self.game.state_mgr:
            return []
        sid = start_id if start_id is not None else self.game.state_mgr.current_location.id
        return self.game.state_mgr.dungeon.dijkstra_shortest_paths(sid)

    def TriggerEncounter(self) -> None:
        """Alias TriggerEncounter() sesuai Bagian 1.3 dan Rubrik Teknis."""
        if not self.game.state_mgr:
            return
        curr = self.game.state_mgr.current_location
        if curr.event_type == RoomEvent.BATTLE and curr.monster_name:
            self._trigger_battle(curr.monster_name)
        elif curr.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK, RoomEvent.QUEST_CONVEYOR):
            self._trigger_puzzle(curr.event_type)
        elif curr.event_type == RoomEvent.DIALOG_FOREST:
            self._trigger_dialog()

    def _open_inventory(self) -> None:
        self.show_inventory_modal = True


    def _close_inventory(self) -> None:
        self.show_inventory_modal = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.show_inventory_modal:
                self.show_inventory_modal = False
            else:
                self.machine.push_state(STATE_PAUSE)
            return

        if self.show_inventory_modal:
            if self.btn_close_inv:
                self.btn_close_inv.handle_event(event)
            return

        if self.btn_pause and self.btn_pause.handle_event(event):
            return
        if self.btn_inventory and self.btn_inventory.handle_event(event):
            return
        if self.btn_map_vision and self.btn_map_vision.handle_event(event):
            return
        if self.action_button and self.action_button.handle_event(event):
            return

        for btn in self.travel_buttons:
            if btn.handle_event(event):
                return

        # Deteksi hover mouse pada node peta
        if event.type == pygame.MOUSEMOTION:
            self._handle_map_hover(event.pos)

        # Klik langsung pada node peta
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_map_click(event.pos)

    def _handle_map_hover(self, pos: Tuple[int, int]) -> None:
        """Memeriksa apakah mouse melayang di atas node ruangan peta."""
        if not self.game.state_mgr:
            return
        state = self.game.state_mgr
        curr_id = state.current_location.id
        neighbors = {n_loc.id for n_loc, _ in state.dungeon.get_neighbors(curr_id)}

        self.hovered_node_id = None
        for loc_id, loc in state.dungeon.locations.items():
            nx = int(self.map_rect.x + loc.ui_x * self.map_rect.width)
            ny = int(self.map_rect.y + loc.ui_y * self.map_rect.height)
            if math.hypot(pos[0] - nx, pos[1] - ny) <= 28:
                self.hovered_node_id = loc_id
                break

        if self.hovered_node_id is not None and self.hovered_node_id in neighbors:
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            except Exception:
                pass
        else:
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            except Exception:
                pass

    def _handle_map_click(self, pos: Tuple[int, int]) -> None:
        if not self.game.state_mgr:
            return
        state = self.game.state_mgr
        curr_id = state.current_location.id
        neighbors = {n_loc.id for n_loc, _ in state.dungeon.get_neighbors(curr_id)}

        for loc_id, loc in state.dungeon.locations.items():
            node_x = int(self.map_rect.x + loc.ui_x * self.map_rect.width)
            node_y = int(self.map_rect.y + loc.ui_y * self.map_rect.height)
            dist = math.hypot(pos[0] - node_x, pos[1] - node_y)
            if dist <= 28:
                if loc_id in neighbors:
                    self._travel_to(loc_id)
                elif loc_id == curr_id:
                    self.log_box.add_message(f"[*] Anda sudah berada di #{loc.id} {loc.name}.")
                else:
                    self.log_box.add_message(f"[!] #{loc.id} {loc.name} tidak terhubung langsung dari sini. Pilih ruangan berlingkar hijau.")
                break

    def update(self, dt: float) -> None:
        self.anim_time += dt
        self.hp_bar.update(dt)
        self.def_bar.update(dt)
        if self.player_map_sprite:
            self.player_map_sprite.update(dt)
        self.floating_texts.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        # Background peta
        bg = self.assets.get_image("dungeon_map_bg_dark.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (0, 0))

        # 1. Gambar Area Peta Graf (Graph Network) Tematik RPG
        self._render_graph_map(surface)

        # 2. Gambar Panel Info Ruangan & Aksi
        self._render_room_panel(surface)

        # 3. Gambar Status Pemain & Log Box di Bawah
        self._render_bottom_hud(surface)

        # 4. Gambar Top Objective HUD
        if self.game.state_mgr:
            mgr = self.game.state_mgr
            subs = [
                ("Fragmen I (Tower)", mgr.completed_sliding_puzzle),
                ("Fragmen II (Relic)", mgr.completed_stack_puzzle),
                ("Fragmen III (Village)", mgr.completed_village_quest),
                ("Elder Tree", mgr.completed_forest_dialogue),
            ]
            self.objective_hud.render(
                surface,
                main_objective=f"Kumpulkan 2 Fragmen Kristal ({mgr.player.crystal_fragments}/2) & Kalahkan Boss!",
                sub_objectives=subs,
                location_name=mgr.player.location,
            )

        if self.btn_pause:
            self.btn_pause.render(surface)

        # Modal Inventory jika terbuka
        if self.show_inventory_modal:
            self._render_inventory_modal(surface)

        # Floating damage / alerts ("TERKUNCI!", dsb.)
        self.floating_texts.render(surface)


    def _render_graph_map(self, surface: pygame.Surface) -> None:
        """Menggambar atlas dungeon 10 ruangan dengan tekstur lantai batu, jalur cobblestone, dan ikon pixel art."""
        # Canvas lantai dungeon tematik
        map_bg_img = self.assets.get_image("dungeon_map_bg.png", scale=(self.map_rect.width, self.map_rect.height))
        surface.blit(map_bg_img, self.map_rect.topleft)

        # Overlay peredup halus agar node dan jalur terlihat kontras
        dim_surf = pygame.Surface((self.map_rect.width, self.map_rect.height), pygame.SRCALPHA)
        dim_surf.fill((14, 10, 22, 160))
        surface.blit(dim_surf, self.map_rect.topleft)

        # Bingkai luar batu & aksen emas
        pygame.draw.rect(surface, (45, 36, 60), self.map_rect, width=3, border_radius=6)
        inner_frame = self.map_rect.inflate(-4, -4)
        pygame.draw.rect(surface, (130, 105, 55), inner_frame, width=1, border_radius=5)

        # Ornamen siku sudut (Medieval L-Brackets)
        bx, by, bw, bh = self.map_rect.x, self.map_rect.y, self.map_rect.width, self.map_rect.height
        c_col = COLOR_GOLD
        # Sudut kiri atas
        pygame.draw.line(surface, c_col, (bx + 2, by + 2), (bx + 18, by + 2), 2)
        pygame.draw.line(surface, c_col, (bx + 2, by + 2), (bx + 2, by + 18), 2)
        # Sudut kanan atas
        pygame.draw.line(surface, c_col, (bx + bw - 18, by + 2), (bx + bw - 2, by + 2), 2)
        pygame.draw.line(surface, c_col, (bx + bw - 2, by + 2), (bx + bw - 2, by + 18), 2)
        # Sudut kiri bawah
        pygame.draw.line(surface, c_col, (bx + 2, by + bh - 2), (bx + 18, by + bh - 2), 2)
        pygame.draw.line(surface, c_col, (bx + 2, by + bh - 18), (bx + 2, by + bh - 2), 2)
        # Sudut kanan bawah
        pygame.draw.line(surface, c_col, (bx + bw - 18, by + bh - 2), (bx + bw - 2, by + bh - 2), 2)
        pygame.draw.line(surface, c_col, (bx + bw - 2, by + bh - 18), (bx + bw - 2, by + bh - 2), 2)

        # Banner pita judul peta di atas
        header_badge = pygame.Rect(self.map_rect.centerx - 170, self.map_rect.y + 10, 340, 24)
        pygame.draw.rect(surface, (22, 17, 30, 220), header_badge, border_radius=4)
        pygame.draw.rect(surface, (140, 115, 60), header_badge, width=1, border_radius=4)
        h_font = self.assets.get_font(13, bold=True)
        h_txt = h_font.render("[ PETA DUNGEON: 10 RUANGAN ]", True, COLOR_GOLD)
        surface.blit(h_txt, h_txt.get_rect(center=header_badge.center))

        # Pita legenda di bawah peta
        legend_badge = pygame.Rect(self.map_rect.centerx - 225, self.map_rect.bottom - 26, 450, 20)
        pygame.draw.rect(surface, (20, 16, 28, 210), legend_badge, border_radius=4)
        leg_font = self.assets.get_font(11)
        leg_txt = leg_font.render("[Emas] Posisi Kamu  |  [Hijau] Dapat Ditempuh  |  [Cyan] Rute Terpendek (Mage)", True, (200, 195, 215))
        surface.blit(leg_txt, leg_txt.get_rect(center=legend_badge.center))

        if not self.game.state_mgr:
            return

        dungeon = self.game.state_mgr.dungeon
        curr_id = self.game.state_mgr.current_location.id
        neighbors_set = {n_loc.id for n_loc, _ in dungeon.get_neighbors(curr_id)}

        # -------------------------------------------------------------
        # 1. Gambar Jalur Cobblestone (Edges) dengan Bobot Jarak Tempuh
        # -------------------------------------------------------------
        drawn_edges = set()
        for from_id, neighbors in dungeon.adjacency.items():
            loc_from = dungeon.get_location_by_id(from_id)
            if not loc_from:
                continue
            x1 = int(self.map_rect.x + loc_from.ui_x * self.map_rect.width)
            y1 = int(self.map_rect.y + loc_from.ui_y * self.map_rect.height)

            for to_id, weight in neighbors:
                edge_pair = tuple(sorted((from_id, to_id)))
                if edge_pair in drawn_edges:
                    continue
                drawn_edges.add(edge_pair)

                loc_to = dungeon.get_location_by_id(to_id)
                if not loc_to:
                    continue
                x2 = int(self.map_rect.x + loc_to.ui_x * self.map_rect.width)
                y2 = int(self.map_rect.y + loc_to.ui_y * self.map_rect.height)

                # Jalur Dijkstra (Glow Emas jika Map Vision aktif)
                is_dijkstra_path = False
                if self.dijkstra_active:
                    for path in self.dijkstra_paths.values():
                        for k in range(len(path) - 1):
                            if (path[k] == from_id and path[k + 1] == to_id) or (
                                path[k] == to_id and path[k + 1] == from_id
                            ):
                                is_dijkstra_path = True
                                break

                # Lapisan 1: Bayangan parit batu gelap (Drop Shadow)
                pygame.draw.line(surface, (14, 10, 20), (x1, y1), (x2, y2), 7)

                if is_dijkstra_path:
                    # Rute bercahaya sihir emas (Mage Dijkstra Vision)
                    pygame.draw.line(surface, (255, 215, 60), (x1, y1), (x2, y2), 4)
                else:
                    # Jalur batu cobblestone standar
                    pygame.draw.line(surface, (75, 68, 92), (x1, y1), (x2, y2), 3)

                # Tablet batu penanda bobot jarak di tengah jalur (Stone Milestone)
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                badge_rect = pygame.Rect(mid_x - 13, mid_y - 9, 26, 18)

                badge_bg = (160, 125, 25) if is_dijkstra_path else (30, 24, 40)
                badge_border = COLOR_GOLD if is_dijkstra_path else (95, 80, 120)
                pygame.draw.rect(surface, badge_bg, badge_rect, border_radius=4)
                pygame.draw.rect(surface, badge_border, badge_rect, width=1, border_radius=4)

                font_w = self.assets.get_font(12, bold=True)
                w_col = (255, 245, 200) if is_dijkstra_path else COLOR_TEXT_MUTED
                w_surf = font_w.render(str(weight), True, w_col)
                surface.blit(w_surf, w_surf.get_rect(center=badge_rect.center))

        # -------------------------------------------------------------
        # 2. Gambar Node Ruangan (10 Chambers Pixel Art)
        # -------------------------------------------------------------
        current_node_pos: Optional[Tuple[int, int]] = None

        for loc_id, loc in dungeon.locations.items():
            nx = int(self.map_rect.x + loc.ui_x * self.map_rect.width)
            ny = int(self.map_rect.y + loc.ui_y * self.map_rect.height)

            is_current = (loc_id == curr_id)
            is_neighbor = (loc_id in neighbors_set)
            is_hovered = (loc_id == self.hovered_node_id)

            if is_current:
                current_node_pos = (nx, ny)

            # Plinth / Bantalan Batu Bulat di Bawah Ikon
            pygame.draw.circle(surface, (22, 18, 30), (nx, ny), 28)
            pygame.draw.circle(surface, (55, 45, 70), (nx, ny), 28, 2)

            # Gambar Ikon Pixel Art 16-Bit Ruangan (52x52 px)
            node_icon = self.assets.get_map_node_icon(loc_id, size=(52, 52))
            surface.blit(node_icon, (nx - 26, ny - 26))

            # Bingkai Cincin Status Node
            if is_current:
                # Efek berdenyut emas untuk lokasi pemain saat ini
                pulse_r = 30 + int((math.sin(self.anim_time * 5.0) + 1.0) * 3)
                pygame.draw.circle(surface, (255, 215, 50), (nx, ny), pulse_r, 1)
                pygame.draw.circle(surface, COLOR_GOLD, (nx, ny), 28, 3)
                pygame.draw.circle(surface, (255, 240, 160), (nx, ny), 24, 1)
            elif is_neighbor:
                # Cincin hijau zamrud menandakan jalur terbuka & dapat diklik langsung
                green_pulse = 28 + int((math.sin(self.anim_time * 6.0) + 1.0) * 2)
                pygame.draw.circle(surface, (46, 204, 113), (nx, ny), green_pulse, 1)
                border_c = (100, 240, 255) if is_hovered else (46, 204, 113)
                pygame.draw.circle(surface, border_c, (nx, ny), 28, 3)
            elif is_hovered:
                # Highlight cyan terang saat mouse melayang
                pygame.draw.circle(surface, (120, 220, 255), (nx, ny), 28, 2)
            else:
                # Cincin besi antik standar
                pygame.draw.circle(surface, (85, 75, 100), (nx, ny), 27, 2)

            # Pin Badge Tipe Event Ruangan di Sudut Kanan Atas (nx + 18, ny - 18)
            pin_x, pin_y = nx + 18, ny - 18
            pin_bg = (60, 50, 75)
            pin_border = (120, 100, 140)
            pin_icon_name: Optional[str] = None

            if loc.event_type == RoomEvent.BATTLE:
                pin_bg = (180, 40, 40)
                pin_border = COLOR_GOLD
                pin_icon_name = "atk"
            elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK, RoomEvent.QUEST_CONVEYOR):
                pin_bg = (100, 50, 160)
                pin_border = (180, 130, 255)
                pin_icon_name = "book_arcane"
            elif loc.event_type == RoomEvent.SAFETY_HEAL:
                pin_bg = (35, 130, 60)
                pin_border = (100, 225, 140)
                pin_icon_name = "heal"
            elif loc.event_type == RoomEvent.DIALOG_FOREST:
                pin_bg = (160, 120, 30)
                pin_border = COLOR_GOLD
                pin_icon_name = "book_gold"

            pygame.draw.circle(surface, pin_bg, (pin_x, pin_y), 9)
            pygame.draw.circle(surface, pin_border, (pin_x, pin_y), 9, 1)

            if pin_icon_name:
                mini_icon = self.assets.get_rpg_icon(pin_icon_name, size=(12, 12))
                if mini_icon:
                    surface.blit(mini_icon, mini_icon.get_rect(center=(pin_x, pin_y)))

            # Papan Nama Ruangan (Pill Banner) di Bawah Node
            name_str = f"#{loc_id} {loc.name}"
            font_name = self.assets.get_font(12, bold=(is_current or is_neighbor))
            name_surf = font_name.render(
                name_str,
                True,
                COLOR_GOLD if is_current else ((130, 255, 180) if is_neighbor else COLOR_TEXT_WHITE),
            )

            pill_w = name_surf.get_width() + 14
            pill_rect = pygame.Rect(nx - pill_w // 2, ny + 31, pill_w, 18)
            pygame.draw.rect(surface, (20, 16, 28, 230), pill_rect, border_radius=4)

            p_border = COLOR_GOLD if is_current else ((46, 204, 113) if is_neighbor else (70, 60, 85))
            pygame.draw.rect(surface, p_border, pill_rect, width=1, border_radius=4)
            surface.blit(name_surf, name_surf.get_rect(center=pill_rect.center))

        # -------------------------------------------------------------
        # 3. Render Sprite Hidup Karakter Pemain di Ruangan Aktif
        # -------------------------------------------------------------
        if current_node_pos:
            cx, cy = current_node_pos
            if self.player_map_sprite:
                self.player_map_sprite.rect.center = (cx, cy - 20)
                self.player_map_sprite.render(surface)
            else:
                p_role = self.game.state_mgr.player.role.value
                token = self.assets.get_player_map_token(p_role, size=(40, 44))
                bob_y = int(math.sin(self.anim_time * 4) * 3)
                surface.blit(token, (cx - 20, cy - 36 + bob_y))

            # Banner Mengambang [ KAU ] di Atas Pahlawan
            tag_rect = pygame.Rect(cx - 22, cy - 48, 44, 16)
            pygame.draw.rect(surface, (25, 20, 36), tag_rect, border_radius=3)
            pygame.draw.rect(surface, COLOR_GOLD, tag_rect, width=1, border_radius=3)
            tag_txt = self.assets.get_font(10, bold=True).render("KAU", True, COLOR_GOLD)
            surface.blit(tag_txt, tag_txt.get_rect(center=tag_rect.center))

            # Jarum Penunjuk Segitiga Emas ke Kepala Karakter
            pygame.draw.polygon(surface, COLOR_GOLD, [(cx - 4, cy - 32), (cx + 4, cy - 32), (cx, cy - 28)])

        # -------------------------------------------------------------
        # 4. Tooltip Mengambang Saat Mouse Melayang di Atas Ruangan Lain
        # -------------------------------------------------------------
        if self.hovered_node_id is not None and self.hovered_node_id != curr_id:
            h_loc = dungeon.get_location_by_id(self.hovered_node_id)
            if h_loc:
                mx, my = pygame.mouse.get_pos()
                tt_lines = [f"#{h_loc.id} {h_loc.name}"]
                if self.hovered_node_id in neighbors_set:
                    dist = dungeon.get_distance(curr_id, self.hovered_node_id)
                    tt_lines.append(f">> Terjangkau (Jarak: {dist})")
                else:
                    tt_lines.append(">> Belum terhubung langsung")

                tt_font = self.assets.get_font(12)
                rendered_lines = [tt_font.render(tl, True, COLOR_GOLD if idx == 0 else COLOR_TEXT_WHITE) for idx, tl in enumerate(tt_lines)]
                max_w = max(r.get_width() for r in rendered_lines) + 16
                tt_h = len(rendered_lines) * 18 + 10
                tt_rect = pygame.Rect(mx + 12, my - 24, max_w, tt_h)

                # Pastikan tooltip tidak keluar dari batas layar
                if tt_rect.right > SCREEN_WIDTH:
                    tt_rect.x = mx - max_w - 8
                if tt_rect.bottom > SCREEN_HEIGHT:
                    tt_rect.y = my - tt_h - 8

                pygame.draw.rect(surface, (22, 17, 30), tt_rect, border_radius=5)
                pygame.draw.rect(surface, (120, 100, 150), tt_rect, width=1, border_radius=5)
                line_y = tt_rect.y + 5
                for r in rendered_lines:
                    surface.blit(r, (tt_rect.x + 8, line_y))
                    line_y += 18

    def _render_room_panel(self, surface: pygame.Surface) -> None:
        """Panel informasi ruangan dan navigasi jalur bertetangga."""
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.panel_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.panel_rect, width=2, border_radius=8)

        if not self.game.state_mgr:
            return

        loc = self.game.state_mgr.current_location

        # Header Ruangan dengan Ikon Pixel Art 60x60
        header_rect = pygame.Rect(self.panel_rect.x, self.panel_rect.y, self.panel_rect.width, 74)
        pygame.draw.rect(surface, COLOR_PANEL_HEADER, header_rect, border_top_left_radius=8, border_top_right_radius=8)

        # Kotak Ikon Ruangan
        icon_box = pygame.Rect(header_rect.x + 12, header_rect.y + 7, 60, 60)
        pygame.draw.rect(surface, (20, 16, 28), icon_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_GOLD, icon_box, width=1, border_radius=6)
        big_icon = self.assets.get_map_node_icon(loc.id, size=(56, 56))
        surface.blit(big_icon, big_icon.get_rect(center=icon_box.center))

        # Judul & Tag Ruangan
        font_h = self.assets.get_font(17, bold=True)
        h_surf = font_h.render(f"#{loc.id} {loc.name}", True, COLOR_GOLD)
        surface.blit(h_surf, (header_rect.x + 80, header_rect.y + 12))

        # Tag Kategori Ruangan
        cat_tag = "[ JALUR EKSPLORASI ]"
        cat_col = (140, 130, 160)
        if loc.event_type == RoomEvent.BATTLE:
            cat_tag = "[ ARENA KAIJU / MONSTER ]"
            cat_col = (231, 76, 60)
        elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK, RoomEvent.QUEST_CONVEYOR):
            cat_tag = "[ RUANG TEKA-TEKI KUNO ]"
            cat_col = (175, 120, 255)
        elif loc.event_type == RoomEvent.SAFETY_HEAL:
            cat_tag = "[ TEMPAT ISTIRAHAT AMAN ]"
            cat_col = (46, 204, 113)
        elif loc.event_type == RoomEvent.DIALOG_FOREST:
            cat_tag = "[ DIALOG ROH POHON ]"
            cat_col = (240, 195, 80)

        cat_surf = self.assets.get_font(12, bold=True).render(cat_tag, True, cat_col)
        surface.blit(cat_surf, (header_rect.x + 80, header_rect.y + 38))

        # Deskripsi Ruangan di dalam Kotak Inset Bergaya Parchment
        desc_box = pygame.Rect(self.panel_rect.x + 16, self.panel_rect.y + 78, 408, 66)
        pygame.draw.rect(surface, (20, 16, 28), desc_box, border_radius=6)
        pygame.draw.rect(surface, (60, 50, 75), desc_box, width=1, border_radius=6)

        font_desc = self.assets.get_font(13)
        words = loc.description.split()
        lines = []
        curr_line = ""
        for w in words:
            if len(curr_line + " " + w) > 46:
                lines.append(curr_line)
                curr_line = w
            else:
                curr_line = (curr_line + " " + w).strip()
        if curr_line:
            lines.append(curr_line)

        dy = desc_box.y + 7
        for l in lines:
            l_surf = font_desc.render(l, True, COLOR_TEXT_WHITE)
            surface.blit(l_surf, (desc_box.x + 10, dy))
            dy += 19

        # Sub-header Aksi Ruangan
        font_sub = self.assets.get_font(13, bold=True)
        if self.action_button:
            a_lbl = font_sub.render("Aksi di Ruangan Ini:", True, COLOR_GOLD)
            surface.blit(a_lbl, (self.panel_rect.x + 18, self.panel_rect.y + 152))

            # Status Khusus Ruangan jika ada
            status_txt = ""
            if loc.event_type == RoomEvent.BATTLE and loc.monster_name:
                monster = self.game.state_mgr.monsters.get(loc.monster_name)
                if monster:
                    if monster.is_alive:
                        status_txt = f"Monster: {monster.name} | HP: {monster.hp}/{monster.max_hp} | ATK: {monster.attack}"
                    else:
                        status_txt = f"Monster: {monster.name} telah dikalahkan! Ruangan aman."
            elif loc.event_type == RoomEvent.SAFETY_HEAL:
                status_txt = "Api Unggun menyala hangat. Duduk untuk memulihkan +100 HP."
            elif loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK, RoomEvent.QUEST_CONVEYOR):
                status_txt = "Misteri kuno menanti kecerdasanmu untuk membuka jalan."

            if status_txt:
                st_surf = self.assets.get_font(11).render(status_txt, True, (200, 195, 215))
                surface.blit(st_surf, (self.panel_rect.x + 18, self.panel_rect.y + 172))

            self.action_button.render(surface)

        # Sub-header Navigasi Jalur Bertetangga
        j_lbl_y = (self.panel_rect.y + 236) if self.action_button else (self.panel_rect.y + 178)
        j_lbl = font_sub.render("Jalur Bertetangga (Klik untuk Berpindah):", True, COLOR_GOLD)
        surface.blit(j_lbl, (self.panel_rect.x + 18, j_lbl_y))

        for btn in self.travel_buttons:
            btn.render(surface)

    def _render_bottom_hud(self, surface: pygame.Surface) -> None:
        if not self.game.state_mgr:
            return

        p = self.game.state_mgr.player

        # Status teks pahlawan di kiri bawah
        font_stat = self.assets.get_font(13, bold=True)
        stat_txt = font_stat.render(
            f"{p.name} ({p.role.value}) | ATK: {p.attack} | DEF: {p.defense} | Gold: {p.gold} | Fragmen: {p.crystal_fragments}/2 | Potion: {p.potions} | Langkah: {p.total_steps}",
            True,
            COLOR_GOLD,
        )
        surface.blit(stat_txt, (20, 652))

        self.hp_bar.render(surface)
        self.def_bar.render(surface)

        if self.btn_map_vision:
            self.btn_map_vision.render(surface)
        if self.btn_inventory:
            self.btn_inventory.render(surface)

        self.log_box.render(surface)

    def _render_inventory_modal(self, surface: pygame.Surface) -> None:
        """Jendela modal inventaris pemain."""
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 180))
        surface.blit(dim_surf, (0, 0))

        box_w, box_h = 560, 400
        box_rect = pygame.Rect((SCREEN_WIDTH - box_w) // 2, (SCREEN_HEIGHT - box_h) // 2, box_w, box_h)

        pygame.draw.rect(surface, COLOR_PANEL_BG, box_rect, border_radius=10)
        pygame.draw.rect(surface, COLOR_GOLD, box_rect, width=2, border_radius=10)

        font_h = self.assets.get_font(20, bold=True)
        h_surf = font_h.render("[ TAS / INVENTARIS PEMAIN ]", True, COLOR_GOLD)
        surface.blit(h_surf, (box_rect.x + 25, box_rect.y + 20))

        if self.game.state_mgr:
            inv = self.game.state_mgr.player.inventory
            font_item = self.assets.get_font(14)
            items = inv.get_all_items()
            y = box_rect.y + 65
            if not items:
                none_surf = font_item.render("Tas masih kosong.", True, COLOR_TEXT_MUTED)
                surface.blit(none_surf, (box_rect.x + 25, y))
            else:
                for itm in items:
                    icon_surf = self.assets.get_item_icon(itm.name, size=(22, 22))
                    text_x = box_rect.x + 25
                    if icon_surf:
                        surface.blit(icon_surf, (text_x, y))
                        text_x += icon_surf.get_width() + 10

                    t_str = f"{itm.name} (x{itm.quantity}) - {itm.description}"
                    it_surf = font_item.render(t_str, True, COLOR_TEXT_WHITE)
                    surface.blit(it_surf, (text_x, y + 2))
                    y += 32

        if self.btn_close_inv:
            self.btn_close_inv.render(surface)
