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
        self.btn_close_inv_top: Optional[UIButton] = None
        self.inventory_item_buttons: List[UIButton] = []

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
                self.log_box.add_message("[*] Pasif Mage aktif: Map Vision otomatis menyorot rute terpendek ke Boss.")

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

        # Rebuild modal inventaris jika sedang terbuka
        if self.show_inventory_modal:
            self._rebuild_inventory_ui()

    def _travel_to(self, target_id: int) -> None:
        """Memindahkan pemain ke ruangan lain via graph."""
        if not self.game.state_mgr:
            return
        success, msg = self.game.state_mgr.move_player(target_id)
        if success:
            self.audio.play("click")
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
        """Menyalakan/mematikan rute tercepat Dijkstra menggunakan skill Mage."""
        if not self.game.state_mgr:
            return
        self.dijkstra_active = not self.dijkstra_active
        if self.dijkstra_active:
            self.audio.play("magic")
            self.log_box.add_message("[*] Map Vision aktif! Algoritma Dijkstra menyorot rute tercepat.")
        else:
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
        self.audio.play("click")
        self._rebuild_inventory_ui()

    def _close_inventory(self) -> None:
        self.show_inventory_modal = False
        self.audio.play("click")
        self.inventory_item_buttons.clear()

    def _rebuild_inventory_ui(self) -> None:
        """Membangun tombol interaktif untuk setiap item di inventaris."""
        self.inventory_item_buttons.clear()
        if not self.game.state_mgr:
            return

        box_w, box_h = 680, 500
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2

        # Tombol [X] di pojok kanan atas modal
        self.btn_close_inv_top = UIButton(
            rect=pygame.Rect(box_x + box_w - 46, box_y + 14, 30, 30),
            text="X",
            font_size=14,
            hover_color=(190, 50, 40),
            on_click=self._close_inventory,
        )

        # Tombol Tutup [ESC] di bagian bawah modal
        self.btn_close_inv = UIButton(
            rect=pygame.Rect(box_x + (box_w - 180) // 2, box_y + box_h - 48, 180, 36),
            text="Tutup Tas [ESC]",
            font_size=13,
            on_click=self._close_inventory,
        )

        player = self.game.state_mgr.player
        items = player.inventory.get_all_items()

        items_start_y = box_y + 118
        card_h = 58
        gap_y = 6

        for i, itm in enumerate(items[:5]):
            card_y = items_start_y + i * (card_h + gap_y)
            # Tombol Gunakan untuk Potion
            if "potion" in itm.name.lower():
                btn_w = 145
                btn_h = 34
                btn_x = box_x + box_w - 28 - btn_w
                btn_y = card_y + (card_h - btn_h) // 2

                is_full = player.hp >= player.max_hp
                btn_text = "HP Penuh" if is_full else "Gunakan (+300 HP)"
                btn_hover = (60, 60, 70) if is_full else (40, 140, 80)

                btn = UIButton(
                    rect=pygame.Rect(btn_x, btn_y, btn_w, btn_h),
                    text=btn_text,
                    font_size=12,
                    icon_name="heal",
                    hover_color=btn_hover,
                    on_click=lambda name=itm.name: self._use_item_from_inventory(name),
                )
                self.inventory_item_buttons.append(btn)

    def _use_item_from_inventory(self, item_name: str) -> None:
        """Menggunakan item dari tas (misal: Health Potion memulihkan 300 HP)."""
        if not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        if "potion" in item_name.lower():
            if player.hp >= player.max_hp:
                self.audio.play("hit")
                self.floating_texts.add("HP SUDAH PENUH!", SCREEN_WIDTH // 2, 280, (255, 200, 50))
                self.log_box.add_message(f"[!] HP Anda sudah penuh ({player.hp}/{player.max_hp}). Potion disimpan.")
                return

            if player.potions <= 0:
                self.audio.play("hit")
                self.floating_texts.add("POTION HABIS!", SCREEN_WIDTH // 2, 280, COLOR_HP_RED)
                self.log_box.add_message("[!] Health Potion sudah habis di dalam tas!")
                return

            healed = player.use_potion()
            if healed > 0:
                self.audio.play("heal")
                self.floating_texts.add(f"+{healed} HP!", SCREEN_WIDTH // 2, 280, COLOR_HP_GREEN)
                self.log_box.add_message(
                    f"[+] Meminum Health Potion dari tas! Memulihkan +{healed} HP. Sisa stok: {player.potions} ({player.hp}/{player.max_hp} HP)."
                )
                self.hp_bar.set_value(player.hp, player.max_hp)
                self._rebuild_inventory_ui()
            else:
                self.log_box.add_message("[!] Tidak dapat memulihkan HP.")
        else:
            self.audio.play("click")
            self.log_box.add_message(f"[*] Item '{item_name}' adalah perlengkapan khusus yang aktif saat pertempuran/pencarian.")

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.show_inventory_modal:
                self._close_inventory()
            else:
                self.machine.push_state(STATE_PAUSE)
            return

        # Tangani interaksi Modal Inventory jika sedang terbuka
        if self.show_inventory_modal:
            if self.btn_close_inv_top and self.btn_close_inv_top.handle_event(event):
                return
            if self.btn_close_inv and self.btn_close_inv.handle_event(event):
                return
            for btn in self.inventory_item_buttons:
                if btn.handle_event(event):
                    return
            # Cegah klik tembus ke peta di bawah modal
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                return
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
            font_name = self.assets.get_font(12, bold=(loc_id == curr_id or loc_id in neighbors))
            name_str = f"#{loc_id} {loc.name}"
            pill_w = font_name.render(name_str, True, COLOR_TEXT_WHITE).get_width() + 14
            pill_rect = pygame.Rect(nx - pill_w // 2, ny + 31, pill_w, 18)
            dist = math.hypot(pos[0] - nx, pos[1] - ny)
            if dist <= 32 or pill_rect.collidepoint(pos):
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
            font_name = self.assets.get_font(12, bold=(loc_id == curr_id or loc_id in neighbors))
            name_str = f"#{loc_id} {loc.name}"
            pill_w = font_name.render(name_str, True, COLOR_TEXT_WHITE).get_width() + 14
            pill_rect = pygame.Rect(node_x - pill_w // 2, node_y + 31, pill_w, 18)
            dist = math.hypot(pos[0] - node_x, pos[1] - node_y)
            if dist <= 32 or pill_rect.collidepoint(pos):
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

    def get_active_dijkstra_info(self) -> Tuple[Set[Tuple[int, int]], int, List[int], int]:
        """
        Mengembalikan (edges_set, total_distance, path_node_ids, target_room_id).
        Jika mouse sedang melayang di atas ruangan lain, rute terpendek beradaptasi dinamis
        ke ruangan yang sedang ditunjuk; jika tidak, rute terpendek diarahkan ke Boss Lair (#10)!
        """
        if not self.dijkstra_active or not self.game.state_mgr:
            return set(), 0, [], 0

        curr_id = self.game.state_mgr.current_location.id
        target_id = 10  # Default ke Boss Lair (#10)

        if self.hovered_node_id is not None and self.hovered_node_id != curr_id:
            target_id = self.hovered_node_id

        dist, path = self.game.state_mgr.dungeon.dijkstra(curr_id, target_id)
        if dist == -1 or not path:
            return set(), 0, [], 0

        edges = set()
        for i in range(len(path) - 1):
            edges.add(tuple(sorted((int(path[i]), int(path[i + 1])))))
        return edges, dist, [int(x) for x in path], target_id

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
        legend_badge = pygame.Rect(self.map_rect.centerx - 260, self.map_rect.bottom - 32, 520, 24)
        pygame.draw.rect(surface, (18, 14, 26, 235), legend_badge, border_radius=5)
        pygame.draw.rect(surface, (110, 90, 50), legend_badge, width=1, border_radius=5)

        # 4 item legenda: Posisi Kamu (Emas), Jalur Terbuka (Hijau), Rute Dijkstra (Cyan), Selesai (Hijau ✓)
        leg_items = [
            ((255, 215, 50), "Posisi Kamu"),
            ((46, 204, 113), "Jalur Terbuka"),
            ((0, 230, 255), "Rute Dijkstra (Mage)"),
            ((80, 220, 120), "v Selesai/Aman"),
        ]
        cur_lx = legend_badge.x + 14
        leg_f = self.assets.get_font(11)
        for col, label in leg_items:
            pygame.draw.circle(surface, col, (cur_lx + 4, legend_badge.centery), 4)
            t_s = leg_f.render(label, True, (215, 210, 230))
            surface.blit(t_s, (cur_lx + 12, legend_badge.centery - t_s.get_height() // 2))
            cur_lx += t_s.get_width() + 22

        if not self.game.state_mgr:
            return

        dungeon = self.game.state_mgr.dungeon
        curr_id = self.game.state_mgr.current_location.id
        neighbors_set = {n_loc.id for n_loc, _ in dungeon.get_neighbors(curr_id)}

        # Kalkulasi rute terpendek Dijkstra yang sedang aktif
        dijkstra_edges, d_dist, d_path, d_target = self.get_active_dijkstra_info()

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

                is_dijkstra = edge_pair in dijkstra_edges
                is_neighbor_edge = (from_id == curr_id and to_id in neighbors_set) or (to_id == curr_id and from_id in neighbors_set)

                # Lapisan 1: Bayangan parit batu gelap (Drop Shadow)
                pygame.draw.line(surface, (10, 8, 16), (x1, y1), (x2, y2), 7)

                if is_dijkstra:
                    # Pendar sihir Arcane Cyan Dijkstra (Mage Map Vision)
                    pulse = (math.sin(self.anim_time * 6.0) + 1.0) * 0.5
                    glow_w = 5 + int(pulse * 2)
                    glow_col = (0, int(180 + 40 * pulse), 255)
                    pygame.draw.line(surface, (10, 90, 140), (x1, y1), (x2, y2), glow_w + 3)
                    pygame.draw.line(surface, glow_col, (x1, y1), (x2, y2), glow_w)
                    pygame.draw.line(surface, (200, 245, 255), (x1, y1), (x2, y2), 2)
                elif is_neighbor_edge:
                    # Jalur yang terhubung langsung ke ruangan aktif pahlawan (Emerald Cobblestone)
                    pygame.draw.line(surface, (25, 95, 55), (x1, y1), (x2, y2), 4)
                    pygame.draw.line(surface, (46, 204, 113), (x1, y1), (x2, y2), 2)
                else:
                    # Jalur batu cobblestone standar
                    pygame.draw.line(surface, (68, 60, 84), (x1, y1), (x2, y2), 3)

                # Tablet batu penanda bobot jarak di tengah jalur (Stone Milestone)
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                badge_rect = pygame.Rect(mid_x - 13, mid_y - 9, 26, 18)

                if is_dijkstra:
                    badge_bg = (10, 50, 75)
                    badge_border = (0, 230, 255)
                    w_col = (200, 250, 255)
                elif is_neighbor_edge:
                    badge_bg = (20, 50, 35)
                    badge_border = (46, 204, 113)
                    w_col = (180, 255, 210)
                else:
                    badge_bg = (28, 22, 38)
                    badge_border = (85, 72, 105)
                    w_col = COLOR_TEXT_MUTED

                pygame.draw.rect(surface, badge_bg, badge_rect, border_radius=4)
                pygame.draw.rect(surface, badge_border, badge_rect, width=1, border_radius=4)

                font_w = self.assets.get_font(12, bold=True)
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
            is_boss = (loc.is_boss_lair or loc_id == 10)
            boss_locked = is_boss and (self.game.state_mgr.player.crystal_fragments < 2)

            # Cek status ruangan selesai/cleared
            is_cleared = False
            if loc.event_type == RoomEvent.BATTLE and loc.monster_name:
                if loc.monster_name in self.game.state_mgr.defeated_monsters:
                    is_cleared = True
            elif loc.event_type == RoomEvent.PUZZLE_SLIDING and self.game.state_mgr.completed_sliding_puzzle:
                is_cleared = True
            elif loc.event_type == RoomEvent.PUZZLE_STACK and self.game.state_mgr.completed_stack_puzzle:
                is_cleared = True
            elif loc.event_type == RoomEvent.QUEST_CONVEYOR and self.game.state_mgr.completed_village_quest:
                is_cleared = True
            elif loc.event_type == RoomEvent.DIALOG_FOREST and self.game.state_mgr.completed_forest_dialogue:
                is_cleared = True

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
            elif boss_locked:
                # Cincin segel merah untuk Boss Lair yang terkunci
                pygame.draw.circle(surface, (200, 45, 45), (nx, ny), 28, 2)
            else:
                # Cincin besi antik standar
                pygame.draw.circle(surface, (85, 75, 100), (nx, ny), 27, 2)

            # Pin Badge Status & Tipe Event di Sudut Kanan Atas (nx + 18, ny - 18)
            pin_x, pin_y = nx + 18, ny - 18
            pin_r = 10

            if is_boss:
                if boss_locked:
                    pin_bg = (190, 35, 35)
                    pin_border = (255, 120, 120)
                    pygame.draw.circle(surface, pin_bg, (pin_x, pin_y), pin_r)
                    pygame.draw.circle(surface, pin_border, (pin_x, pin_y), pin_r, 1)
                    font_pin = self.assets.get_font(10, bold=True)
                    lock_txt = font_pin.render("X", True, (255, 255, 255))
                    surface.blit(lock_txt, lock_txt.get_rect(center=(pin_x, pin_y)))
                else:
                    pin_bg = (140, 30, 160)
                    pin_border = COLOR_GOLD
                    pygame.draw.circle(surface, pin_bg, (pin_x, pin_y), pin_r)
                    pygame.draw.circle(surface, pin_border, (pin_x, pin_y), pin_r, 1)
                    font_pin = self.assets.get_font(10, bold=True)
                    boss_txt = font_pin.render("!", True, COLOR_GOLD)
                    surface.blit(boss_txt, boss_txt.get_rect(center=(pin_x, pin_y)))
            elif is_cleared:
                # Badge Hijau Checkmark: Ruangan Selesai / Aman
                pin_bg = (30, 145, 65)
                pin_border = (120, 245, 155)
                pygame.draw.circle(surface, pin_bg, (pin_x, pin_y), pin_r)
                pygame.draw.circle(surface, pin_border, (pin_x, pin_y), pin_r, 1)
                font_pin = self.assets.get_font(11, bold=True)
                chk_txt = font_pin.render("v", True, (255, 255, 255))
                surface.blit(chk_txt, chk_txt.get_rect(center=(pin_x, pin_y - 1)))
            else:
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

            if is_current:
                name_col = COLOR_GOLD
                p_border = COLOR_GOLD
            elif is_neighbor:
                name_col = (130, 255, 180)
                p_border = (46, 204, 113)
            elif boss_locked:
                name_col = (240, 130, 130)
                p_border = (180, 45, 45)
            elif is_cleared:
                name_col = (170, 235, 190)
                p_border = (45, 120, 70)
            else:
                name_col = COLOR_TEXT_WHITE
                p_border = (70, 60, 85)

            name_surf = font_name.render(name_str, True, name_col)
            pill_w = name_surf.get_width() + 14
            pill_rect = pygame.Rect(nx - pill_w // 2, ny + 31, pill_w, 18)
            pygame.draw.rect(surface, (20, 16, 28, 230), pill_rect, border_radius=4)
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
                tt_lines: List[Tuple[str, Tuple[int, int, int], bool]] = [
                    (f"#{h_loc.id} {h_loc.name}", COLOR_GOLD, True)
                ]

                # Status Ruangan
                h_is_boss = (h_loc.is_boss_lair or h_loc.id == 10)
                h_boss_locked = h_is_boss and (self.game.state_mgr.player.crystal_fragments < 2)
                h_cleared = False
                if h_loc.event_type == RoomEvent.BATTLE and h_loc.monster_name:
                    if h_loc.monster_name in self.game.state_mgr.defeated_monsters:
                        h_cleared = True
                elif h_loc.event_type == RoomEvent.PUZZLE_SLIDING and self.game.state_mgr.completed_sliding_puzzle:
                    h_cleared = True
                elif h_loc.event_type == RoomEvent.PUZZLE_STACK and self.game.state_mgr.completed_stack_puzzle:
                    h_cleared = True
                elif h_loc.event_type == RoomEvent.QUEST_CONVEYOR and self.game.state_mgr.completed_village_quest:
                    h_cleared = True
                elif h_loc.event_type == RoomEvent.DIALOG_FOREST and self.game.state_mgr.completed_forest_dialogue:
                    h_cleared = True

                if h_is_boss:
                    if h_boss_locked:
                        tt_lines.append((f"[TERKUNCI: Butuh 2 Fragmen (saat ini: {self.game.state_mgr.player.crystal_fragments}/2)]", (255, 90, 90), False))
                    else:
                        tt_lines.append(("[SEGEL TERBUKA: Siap Menantang Boss Kaiju!]", (255, 215, 60), False))
                elif h_cleared:
                    tt_lines.append(("[STATUS: DIBERSIHKAN / AMAN]", (100, 240, 140), False))
                elif h_loc.event_type == RoomEvent.BATTLE and h_loc.monster_name:
                    tt_lines.append((f"[MONSTER: {h_loc.monster_name}]", (255, 120, 100), False))
                elif h_loc.event_type in (RoomEvent.PUZZLE_SLIDING, RoomEvent.PUZZLE_STACK, RoomEvent.QUEST_CONVEYOR):
                    tt_lines.append(("[TEKA-TEKI: Hadiah Fragmen Kristal]", (190, 140, 255), False))
                elif h_loc.event_type == RoomEvent.DIALOG_FOREST:
                    tt_lines.append(("[DIALOG NPC: Roh Pohon Kuno Gyoot]", (240, 200, 80), False))

                # Keterjangkauan Jalur
                if self.hovered_node_id in neighbors_set:
                    dist = dungeon.get_distance(curr_id, self.hovered_node_id)
                    tt_lines.append((f">> Dapat Ditempuh Langsung (Jarak: {dist} langkah)", (120, 255, 160), False))
                else:
                    tt_lines.append((">> Perlu transit melalui ruangan lain", COLOR_TEXT_MUTED, False))

                # Jalur Dijkstra (Mage Map Vision)
                if self.dijkstra_active and d_path and d_target == self.hovered_node_id:
                    path_str = " -> ".join(f"#{nid}" for nid in d_path)
                    tt_lines.append((f"Rute Terpendek: {path_str} ({d_dist} langkah)", (0, 230, 255), False))

                font_tt = self.assets.get_font(12)
                font_tt_bold = self.assets.get_font(12, bold=True)
                rendered_lines = []
                for txt, col, is_b in tt_lines:
                    f = font_tt_bold if is_b else font_tt
                    rendered_lines.append(f.render(txt, True, col))

                max_w = max(r.get_width() for r in rendered_lines) + 20
                tt_h = len(rendered_lines) * 19 + 12
                tt_rect = pygame.Rect(mx + 14, my - 24, max_w, tt_h)
                if tt_rect.right > SCREEN_WIDTH - 10:
                    tt_rect.x = mx - max_w - 10
                if tt_rect.bottom > SCREEN_HEIGHT - 10:
                    tt_rect.y = my - tt_h - 10
                if tt_rect.left < 10:
                    tt_rect.left = 10
                if tt_rect.top < 10:
                    tt_rect.top = 10

                pygame.draw.rect(surface, (20, 16, 28), tt_rect, border_radius=6)
                pygame.draw.rect(surface, (110, 95, 140), tt_rect, width=1, border_radius=6)
                ly = tt_rect.y + 6
                for r in rendered_lines:
                    surface.blit(r, (tt_rect.x + 10, ly))
                    ly += 19


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
        """Jendela modal inventaris pemain bernuansa RPG 16-bit pixel art interaktif."""
        # 1. Overlay redup hitam semi-transparan
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 195))
        surface.blit(dim_surf, (0, 0))

        box_w, box_h = 680, 500
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

        # Panel Latar Belakang Modal
        pygame.draw.rect(surface, (14, 17, 26), box_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_GOLD, box_rect, width=2, border_radius=12)
        pygame.draw.rect(surface, (38, 46, 68), box_rect.inflate(-4, -4), width=1, border_radius=10)

        # 2. Header Modal & Ikon Peti Emas
        chest_icon = self.assets.get_rpg_icon("chest_royal", (28, 28)) or self.assets.get_rpg_icon("inventory", (28, 28))
        if chest_icon:
            surface.blit(chest_icon, (box_x + 24, box_y + 16))

        font_title = self.assets.get_font(18, bold=True)
        t_surf = font_title.render("TAS & INVENTARIS PETUALANG", True, COLOR_GOLD)
        surface.blit(t_surf, (box_x + 60, box_y + 18))

        # Tombol [X] di pojok kanan atas
        if self.btn_close_inv_top:
            self.btn_close_inv_top.render(surface)

        if not self.game.state_mgr:
            return

        p = self.game.state_mgr.player

        # 3. Banner Ringkasan Status Pahlawan
        banner_rect = pygame.Rect(box_x + 20, box_y + 54, box_w - 40, 48)
        pygame.draw.rect(surface, (20, 24, 38), banner_rect, border_radius=6)
        pygame.draw.rect(surface, (40, 48, 70), banner_rect, width=1, border_radius=6)

        font_stat_b = self.assets.get_font(12, bold=True)
        font_stat_m = self.assets.get_font(12)

        # Nama & Role
        name_txt = font_stat_b.render(f"{p.name} ({p.role.value})", True, (240, 240, 255))
        surface.blit(name_txt, (banner_rect.x + 14, banner_rect.y + 8))

        # Mini HP Bar
        hp_bar_bg = pygame.Rect(banner_rect.x + 14, banner_rect.y + 28, 140, 12)
        pygame.draw.rect(surface, (40, 15, 15), hp_bar_bg, border_radius=3)
        hp_ratio = max(0.0, min(1.0, p.hp / max(1, p.max_hp)))
        if hp_ratio > 0:
            hp_bar_fill = pygame.Rect(banner_rect.x + 14, banner_rect.y + 28, int(140 * hp_ratio), 12)
            pygame.draw.rect(surface, (46, 204, 113), hp_bar_fill, border_radius=3)
        pygame.draw.rect(surface, (80, 90, 110), hp_bar_bg, width=1, border_radius=3)

        hp_txt = self.assets.get_font(10, bold=True).render(f"{p.hp}/{p.max_hp} HP", True, (255, 255, 255))
        surface.blit(hp_txt, (hp_bar_bg.x + 148, hp_bar_bg.y - 1))

        # Stats di sisi kanan banner
        st_txt = font_stat_m.render(
            f"DEF: {p.defense}   |   Gold: {p.gold}   |   Fragmen: {p.crystal_fragments}/2   |   Potion: {p.potions}",
            True,
            COLOR_GOLD,
        )
        surface.blit(st_txt, (banner_rect.right - st_txt.get_width() - 14, banner_rect.y + 16))

        # 4. Kotak Kontainer Slot Item
        items_rect = pygame.Rect(box_x + 20, box_y + 110, box_w - 40, 328)
        pygame.draw.rect(surface, (10, 12, 18), items_rect, border_radius=8)
        pygame.draw.rect(surface, (28, 34, 50), items_rect, width=1, border_radius=8)

        items = p.inventory.get_all_items()
        font_item_name = self.assets.get_font(13, bold=True)
        font_item_desc = self.assets.get_font(11)
        font_badge = self.assets.get_font(11, bold=True)

        if not items:
            empty_chest = self.assets.get_rpg_icon("chest_wood", (44, 44))
            cy = items_rect.y + 70
            if empty_chest:
                surface.blit(empty_chest, ((SCREEN_WIDTH - 44) // 2, cy))
                cy += 54
            em_title = font_title.render("Tas Petualang Masih Kosong!", True, (220, 220, 230))
            surface.blit(em_title, ((SCREEN_WIDTH - em_title.get_width()) // 2, cy))
            cy += 28
            em_sub = font_item_desc.render("Kalahkan monster atau selesaikan teka-teki untuk mengumpulkan item & relik.", True, COLOR_TEXT_MUTED)
            surface.blit(em_sub, ((SCREEN_WIDTH - em_sub.get_width()) // 2, cy))
        else:
            card_h = 58
            gap_y = 6
            start_y = items_rect.y + 8

            for i, itm in enumerate(items[:5]):
                cy = start_y + i * (card_h + gap_y)
                card_rect = pygame.Rect(items_rect.x + 8, cy, items_rect.width - 16, card_h)

                # Background kartu item
                pygame.draw.rect(surface, (18, 22, 34), card_rect, border_radius=6)
                pygame.draw.rect(surface, (36, 44, 64), card_rect, width=1, border_radius=6)

                # Slot Ikon Kotak Gelap
                slot_rect = pygame.Rect(card_rect.x + 8, card_rect.y + 7, 44, 44)
                pygame.draw.rect(surface, (8, 10, 16), slot_rect, border_radius=4)
                pygame.draw.rect(surface, (30, 36, 52), slot_rect, width=1, border_radius=4)

                icon_surf = self.assets.get_item_icon(itm.name, size=(28, 28))
                if icon_surf:
                    surface.blit(icon_surf, (slot_rect.x + 8, slot_rect.y + 8))

                # Nama Item & Jumlah
                name_surf = font_item_name.render(itm.name, True, COLOR_GOLD)
                surface.blit(name_surf, (slot_rect.right + 12, card_rect.y + 8))

                # Badge Jumlah (xN)
                qty_str = f"x{itm.quantity}"
                qty_txt = font_badge.render(qty_str, True, (255, 255, 255))
                qty_w = qty_txt.get_width() + 10
                qty_pill = pygame.Rect(slot_rect.right + 16 + name_surf.get_width(), card_rect.y + 8, qty_w, 18)
                pygame.draw.rect(surface, (50, 40, 90), qty_pill, border_radius=4)
                surface.blit(qty_txt, (qty_pill.x + 5, qty_pill.y + 2))

                # Deskripsi & Value
                desc_text = itm.description
                if itm.value:
                    desc_text += f" (Nilai/Kekuatan: {itm.value})"
                desc_surf = font_item_desc.render(desc_text, True, (180, 185, 205))
                surface.blit(desc_surf, (slot_rect.right + 12, card_rect.y + 30))

                # Badge kategori untuk item non-potion
                if "potion" not in itm.name.lower():
                    cat_txt = "[ Senjata Tempur ]" if itm.value > 0 else "[ Relik / Kunci ]"
                    cat_col = (130, 90, 220) if itm.value > 0 else (220, 160, 40)
                    cat_surf = font_badge.render(cat_txt, True, cat_col)
                    surface.blit(cat_surf, (card_rect.right - cat_surf.get_width() - 14, card_rect.y + 18))

            # Render tombol-tombol aksi item (misal: Gunakan Potion)
            for btn in self.inventory_item_buttons:
                btn.render(surface)

        # 5. Tombol Tutup di Bawah
        if self.btn_close_inv:
            self.btn_close_inv.render(surface)
