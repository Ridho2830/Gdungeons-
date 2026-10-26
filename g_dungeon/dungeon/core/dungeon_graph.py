"""
Module: core/dungeon_graph.py
Description: Struktur Graph 10 Ruangan dan 13 Edge berbobot resmi sesuai Bagian 2.4 Dokumen Perencanaan.
Mengimplementasikan Algoritma Dijkstra menggunakan Min-Heap (heapq).
"""

import heapq
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RoomEvent(Enum):
    """Tipe event atau interaksi khusus pada sebuah ruangan."""
    NONE = "None"
    BATTLE = "Battle"
    PUZZLE_SLIDING = "Puzzle Sliding"
    PUZZLE_STACK = "Puzzle Stack"
    QUEST_CONVEYOR = "Quest Conveyor"
    DIALOG_FOREST = "Dialog Forest"
    SAFETY_HEAL = "Safety Heal"



@dataclass
class DungeonLocation:
    """Informasi sebuah ruangan / vertex di dalam dungeon."""
    id: int
    name: str
    description: str
    event_type: RoomEvent = RoomEvent.NONE
    monster_name: Optional[str] = None
    is_boss_lair: bool = False
    reward_desc: str = ""
    # Koordinat visual normalisasi (0.0 s.d 1.0) untuk rendering peta pada Canvas GUI
    ui_x: float = 0.5
    ui_y: float = 0.5


@dataclass
class DijkstraResult:
    """Hasil kalkulasi algoritma Dijkstra dari titik awal ke tujuan."""
    target_id: int
    target_name: str
    distance: int
    path_ids: List[int]
    path_names: List[str]


class DungeonGraph:
    """Mengelola struktur graph dungeon dan navigasi antar lokasi."""

    def __init__(self, auto_populate: bool = True) -> None:
        self.locations: Dict[int, DungeonLocation] = {}
        self.location_name_to_id: Dict[str, int] = {}
        # Adjacency list: node_id -> list of (neighbor_id, weight)
        self.adjacency: Dict[int, List[Tuple[int, int]]] = {}
        if auto_populate:
            self._populate_defaults()

    def _populate_defaults(self) -> None:
        """Mendaftarkan 10 ruangan dan 13 edge resmi sesuai Bagian 2.4 dokumen perencanaan."""
        defaults = [
            DungeonLocation(id=1, name="Entrance Hall", description="Titik awal pahlawan, ruangan gerbang yang aman dan sunyi.", event_type=RoomEvent.NONE, reward_desc="Area awal", ui_x=0.18, ui_y=0.24),
            DungeonLocation(id=2, name="Whispering Forest", description="Hutan bisikan gaib tempat bertemunya Roh Pohon Kuno Gyoot.", event_type=RoomEvent.DIALOG_FOREST, reward_desc="Lore, Petunjuk, & 1 Potion", ui_x=0.48, ui_y=0.17),
            DungeonLocation(id=3, name="Labyrinth Tower", description="Menara labirin menjulang berisi teka-teki 8-Puzzle Matriks kuno.", event_type=RoomEvent.PUZZLE_SLIDING, reward_desc="Fragmen Kristal 1 (+200 Max HP)", ui_x=0.78, ui_y=0.17),
            DungeonLocation(id=4, name="The Eternal Relic", description="Ruangan altar suci bejana cairan kimia warna-warni (Stack LIFO).", event_type=RoomEvent.PUZZLE_STACK, reward_desc="Fragmen Kristal 2 (Kunci Boss)", ui_x=0.86, ui_y=0.44),
            DungeonLocation(id=5, name="Village Workshop", description="Bengkel desa bawah tanah dengan ban berjalan pemilah logistik (Queue FIFO).", event_type=RoomEvent.QUEST_CONVEYOR, reward_desc="Fragmen Kristal 3 (+2 Potion)", ui_x=0.24, ui_y=0.58),
            DungeonLocation(id=6, name="Ancient Armory", description="Gudang senjata berkarat dijaga prajurit kerangka kuno (Skeleton Guard).", event_type=RoomEvent.BATTLE, monster_name="Skeleton Guard", reward_desc="Harta 150 Gold + 1 Health Potion", ui_x=0.36, ui_y=0.40),
            DungeonLocation(id=7, name="Crystal Cavern", description="Gua kristal berkilauan sarang lendir asam beracun (Crystal Slime).", event_type=RoomEvent.BATTLE, monster_name="Crystal Slime", reward_desc="Kristal Mana (Reset Cooldown Skill)", ui_x=0.60, ui_y=0.38),
            DungeonLocation(id=8, name="Magma Forge", description="Tempaan magma membara markas raksasa batuan lahar (Magma Golem).", event_type=RoomEvent.BATTLE, monster_name="Magma Golem", reward_desc="DEF +15 Permanen", ui_x=0.54, ui_y=0.76),
            DungeonLocation(id=9, name="Shadow Crypt", description="Kuburan bayangan dingin tempat bersarangnya arwah penjerit (Shadow Wraith).", event_type=RoomEvent.BATTLE, monster_name="Shadow Wraith", reward_desc="Petunjuk Letak Boss Lair", ui_x=0.10, ui_y=0.72),
            DungeonLocation(id=10, name="Throne of Extinction", description="Singgasana kepunahan tempat bersemayamnya Corrupted Crystal Kaiju!", event_type=RoomEvent.BATTLE, monster_name="Corrupted Crystal Kaiju", is_boss_lair=True, reward_desc="Kemenangan Mutlak G-Dungeons!", ui_x=0.86, ui_y=0.76),
        ]
        for loc in defaults:
            self.add_location(loc)

        # 13 edge resmi
        paths = [
            (1, 2, 2), (1, 6, 3), (1, 9, 4),
            (2, 3, 3), (2, 7, 4),
            (3, 4, 3), (4, 7, 2), (4, 10, 5),
            (5, 6, 2), (5, 8, 3),
            (6, 8, 5), (8, 9, 2), (8, 10, 4),
        ]
        for u, v, w in paths:
            self.add_path(u, v, w)

    def add_location(self, location: DungeonLocation) -> None:
        """Mendaftarkan lokasi baru ke dalam graph."""
        self.locations[location.id] = location
        self.location_name_to_id[location.name.lower()] = location.id
        if location.id not in self.adjacency:
            self.adjacency[location.id] = []

    def AddEdge(self, from_id: int, to_id: int, distance: int) -> None:
        """Alias AddEdge sesuai Section 2.1 Dokumen Perencanaan."""
        self.add_path(from_id, to_id, distance)

    def add_edge(self, from_id: int, to_id: int, distance: int) -> None:
        self.add_path(from_id, to_id, distance)

    def add_path(self, from_id: int, to_id: int, distance: int) -> None:
        """Menghubungkan dua lokasi secara dua arah (undirected weighted edge)."""
        if from_id not in self.adjacency:
            self.adjacency[from_id] = []
        if to_id not in self.adjacency:
            self.adjacency[to_id] = []
        self.adjacency[from_id].append((to_id, distance))
        self.adjacency[to_id].append((from_id, distance))

    def get_rooms(self) -> List[DungeonLocation]:
        """Mengembalikan daftar seluruh ruangan di dalam dungeon."""
        return list(self.locations.values())

    def _resolve_node_id(self, node: Any) -> Optional[int]:
        if isinstance(node, int):
            return node if node in self.locations else None
        if isinstance(node, str):
            if node.isdigit() and int(node) in self.locations:
                return int(node)
            return self.location_name_to_id.get(node.lower())
        return None

    def Dijkstra(self, src: Any, dst: Any) -> Tuple[int, List[Any]]:
        """Alias Dijkstra(src, dst) sesuai Section 2.1 Dokumen Perencanaan."""
        return self.dijkstra(src, dst)

    def dijkstra(self, src: Any, dst: Any) -> Tuple[int, List[Any]]:
        """
        Kalkulasi rute terpendek dari src ke dst menggunakan Min-Heap (heapq).
        Mengembalikan (total_distance, list_path).
        """
        src_id = self._resolve_node_id(src)
        dst_id = self._resolve_node_id(dst)
        if src_id is None or dst_id is None:
            return -1, []

        distances: Dict[int, int] = {node: float("inf") for node in self.locations}
        previous_nodes: Dict[int, Optional[int]] = {node: None for node in self.locations}
        distances[src_id] = 0
        pq = [(0, src_id)]

        while pq:
            cur_dist, cur_node = heapq.heappop(pq)
            if cur_node == dst_id:
                break
            if cur_dist > distances[cur_node]:
                continue
            for neighbor_id, weight in self.adjacency.get(cur_node, []):
                new_dist = cur_dist + weight
                if new_dist < distances[neighbor_id]:
                    distances[neighbor_id] = new_dist
                    previous_nodes[neighbor_id] = cur_node
                    heapq.heappush(pq, (new_dist, neighbor_id))

        if distances[dst_id] == float("inf"):
            return -1, []

        path_ids = []
        curr: Optional[int] = dst_id
        while curr is not None:
            path_ids.append(curr)
            curr = previous_nodes[curr]
        path_ids.reverse()

        if isinstance(src, str) and src.isdigit():
            return distances[dst_id], [str(nid) for nid in path_ids]
        return distances[dst_id], path_ids

    def get_location_by_id(self, loc_id: int) -> Optional[DungeonLocation]:

        """Mendapatkan data lokasi berdasarkan ID integer."""
        return self.locations.get(loc_id)

    def get_location_by_name(self, name: str) -> Optional[DungeonLocation]:
        """Mendapatkan data lokasi berdasarkan nama ruangan."""
        loc_id = self.location_name_to_id.get(name.lower())
        if loc_id is not None:
            return self.locations.get(loc_id)
        return None

    def get_neighbors(self, loc_id: int) -> List[Tuple[DungeonLocation, int]]:
        """Mendapatkan daftar lokasi tetangga beserta bobot jarak tempuh."""
        neighbors = []
        for neighbor_id, weight in self.adjacency.get(loc_id, []):
            loc = self.locations.get(neighbor_id)
            if loc:
                neighbors.append((loc, weight))
        return neighbors

    def get_distance(self, from_id: int, to_id: int) -> int:
        """Mengembalikan jarak antara dua lokasi bertetangga, atau -1 jika tidak ada jalur langsung."""
        for neighbor_id, weight in self.adjacency.get(from_id, []):
            if neighbor_id == to_id:
                return weight
        return -1

    def dijkstra_shortest_paths(self, start_id: int) -> List[DijkstraResult]:
        """
        Implementasi Algoritma Dijkstra menggunakan Min-Heap (heapq).
        Mengembalikan daftar rute terpendek dari start_id ke semua node lain yang terjangkau.
        Kompleksitas waktu: O((V + E) log V).
        """
        distances: Dict[int, int] = {node: float("inf") for node in self.locations}
        previous_nodes: Dict[int, Optional[int]] = {node: None for node in self.locations}

        distances[start_id] = 0
        priority_queue = [(0, start_id)]

        while priority_queue:
            current_dist, current_node = heapq.heappop(priority_queue)

            if current_dist > distances[current_node]:
                continue

            for neighbor_id, weight in self.adjacency.get(current_node, []):
                new_distance = current_dist + weight
                if new_distance < distances[neighbor_id]:
                    distances[neighbor_id] = new_distance
                    previous_nodes[neighbor_id] = current_node
                    heapq.heappush(priority_queue, (new_distance, neighbor_id))

        results: List[DijkstraResult] = []
        for loc_id, loc in self.locations.items():
            if distances[loc_id] == float("inf"):
                continue

            # Rekonstruksi rute dari titik tujuan kembali ke start
            path_ids = []
            curr: Optional[int] = loc_id
            while curr is not None:
                path_ids.append(curr)
                curr = previous_nodes[curr]
            path_ids.reverse()

            path_names = [self.locations[node_id].name for node_id in path_ids]

            results.append(DijkstraResult(
                target_id=loc_id,
                target_name=loc.name,
                distance=int(distances[loc_id]),
                path_ids=path_ids,
                path_names=path_names
            ))

        # Urutkan berdasarkan jarak terpendek
        results.sort(key=lambda item: item.distance)
        return results


def build_default_dungeon() -> DungeonGraph:
    """Membangun peta dungeon standar 10 ruangan dan 13 edge resmi."""
    return DungeonGraph(auto_populate=True)

