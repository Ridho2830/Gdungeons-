"""
Module: core/game_state.py
Description: Pengelola status terpusat (GameStateManager) yang mengatur alur permainan,
perpindahan lokasi berbobot, validasi kunci Boss Lair (2 Fragmen), sistem reward ruangan,
serta kalkulasi skor akhir resmi sesuai template.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from core.dungeon_graph import DungeonGraph, DungeonLocation, RoomEvent, build_default_dungeon
from core.item import Item
from core.monster import Monster, create_default_monsters
from core.player import Player, PlayerRole


class GameStateManager:
    """Mengelola keseluruhan state permainan secara terstruktur (OOP)."""

    def __init__(self, player_name: str = "Player", role: PlayerRole = PlayerRole.KNIGHT) -> None:
        self.new_game(player_name, role)

    def new_game(self, player_name: str = "Player", role: PlayerRole = PlayerRole.KNIGHT) -> None:
        """Inisialisasi ulang permainan baru."""
        self.player: Player = Player(name=player_name, role=role, initial_location="Entrance Hall")
        self.dungeon: DungeonGraph = build_default_dungeon()
        self.monsters: Dict[str, Monster] = create_default_monsters()

        # Flag status penyelesaian teka-teki (Masing-masing berhadiah 1 Fragmen Kristal)
        self.completed_sliding_puzzle: bool = False
        self.completed_stack_puzzle: bool = False
        self.completed_village_quest: bool = False
        self.completed_forest_dialogue: bool = False

        # Catatan monster yang telah dikalahkan
        self.defeated_monsters: Set[str] = set()

        # Status game over atau kemenangan
        self.game_won: bool = False
        self.game_over: bool = False

    def Reset(self, player_name: str = "Player", role: Optional[PlayerRole] = None) -> None:
        """Alias Reset() sesuai template Section 2.1."""
        target_role = role if role is not None else self.player.role
        self.new_game(player_name, target_role)

    def AddTravel(self, location: str, distance: int, from_loc: str = "") -> None:
        """Alias AddTravel() sesuai template Section 2.1."""
        self.player.add_travel_record(location, distance, from_loc)

    @property
    def current_location(self) -> DungeonLocation:

        """Mengembalikan data lokasi ruangan pemain saat ini."""
        loc = self.dungeon.get_location_by_name(self.player.location)
        if loc is None:
            return self.dungeon.get_location_by_id(1)  # Default fallback ke Entrance Hall (1)
        return loc

    def move_player(self, target_location_id: int) -> Tuple[bool, str]:
        """
        Memindahkan pemain ke lokasi tujuan:
        - Memeriksa validitas jalur bertetangga.
        - Memeriksa syarat kunci Boss Lair: Pemain wajib membawa minimal 2 Fragmen Kristal.
        - Memperbarui lokasi pemain dan mencatat riwayat perjalanan serta total langkah (bobot).
        """
        curr_loc = self.current_location
        target_loc = self.dungeon.get_location_by_id(target_location_id)

        if not target_loc:
            return False, "Lokasi tujuan tidak ditemukan di dalam peta dungeon."

        distance = self.dungeon.get_distance(curr_loc.id, target_loc.id)
        if distance == -1:
            return False, f"Tidak ada jalur langsung dari {curr_loc.name} ke {target_loc.name}!"

        # KUNCI BOSS LAIR: Wajib membawa minimal 2 dari 3 Fragmen Kristal
        if target_loc.is_boss_lair or target_loc.id == 10:
            if self.player.crystal_fragments < 2:
                return (
                    False,
                    f"Pintu gerbang {target_loc.name} terkunci rapat oleh sihir kuno!\n"
                    f"Dibutuhkan minimal 2 Fragmen Kristal untuk mendobrak segel.\n"
                    f"(Fragmen saat ini: {self.player.crystal_fragments}/2). Selesaikan teka-teki labirin terlebih dahulu!"
                )

        # Perbarui lokasi pemain dan catat bobot jarak tempuh
        prev_name = self.player.location
        self.player.location = target_loc.name
        self.player.add_travel_record(target_loc.name, distance, prev_name)

        feedback = f"Berhasil berpindah ke {target_loc.name} (Jarak tempuh: {distance} langkah)."
        return True, feedback

    def get_current_room_monster(self) -> Optional[Monster]:
        """Mendapatkan data monster di ruangan saat ini jika belum dikalahkan."""
        loc = self.current_location
        if loc.event_type == RoomEvent.BATTLE and loc.monster_name:
            if loc.monster_name in self.defeated_monsters:
                return None
            monster = self.monsters.get(loc.monster_name)
            if monster and monster.is_alive:
                return monster
        return None

    def can_enter_room(self, target: Any) -> Tuple[bool, str]:
        """Memeriksa apakah pemain dapat memasuki ruangan tertentu (termasuk cek kunci Boss Lair)."""
        target_loc = None
        if isinstance(target, int):
            target_loc = self.dungeon.get_location_by_id(target)
        elif isinstance(target, str):
            if target.isdigit():
                target_loc = self.dungeon.get_location_by_id(int(target))
            else:
                target_loc = self.dungeon.get_location_by_name(target)
                if not target_loc and ("boss" in target.lower() or "throne" in target.lower()):
                    target_loc = self.dungeon.get_location_by_id(10)

        if not target_loc:
            return False, "Ruangan tidak ditemukan."

        if target_loc.is_boss_lair or target_loc.id == 10:
            if self.player.crystal_fragments < 2:
                return (
                    False,
                    f"Pintu gerbang {target_loc.name} terkunci rapat!\n"
                    f"Dibutuhkan minimal 2 Fragmen Kristal (saat ini: {self.player.crystal_fragments}/2)."
                )
        return True, ""

    def on_puzzle_completed(self, puzzle_id: str) -> str:
        """
        Menangani penyelesaian teka-teki dan pemberian Fragmen Kristal serta hadiah unik.
        Menerima ID teka-teki ('sliding', 'stack', 'conveyor') atau nama ruangan.
        """
        pid = puzzle_id.lower()
        msg = ""
        if ("sliding" in pid or "labyrinth" in pid or "8-puzzle" in pid) and not self.completed_sliding_puzzle:
            self.completed_sliding_puzzle = True
            self.player.crystal_fragments += 1
            self.player.max_hp += 200
            self.player.hp += 200
            msg = "Menyelesaikan 8-Puzzle! Memperoleh Fragmen Kristal I dan bonus permanen +200 Max HP!"
        elif ("stack" in pid or "eternal relic" in pid or "relic" in pid) and not self.completed_stack_puzzle:
            self.completed_stack_puzzle = True
            self.player.crystal_fragments += 1
            msg = "Menyelesaikan Bejana Warna! Memperoleh Fragmen Kristal II (Relik Abadi)!"
        elif ("conveyor" in pid or "village" in pid or "workshop" in pid) and not self.completed_village_quest:
            self.completed_village_quest = True
            self.player.crystal_fragments += 1
            self.player.potions += 2
            self.player.inventory.add_item("Health Potion", 2, 300, "Memulihkan 300 HP")
            msg = "Menyelesaikan Quest Ban Berjalan! Memperoleh Fragmen Kristal III dan 2 Health Potion!"
        return msg


    def claim_monster_rewards(self, monster: Monster) -> List[str]:
        """
        Memberikan hadiah khusus saat monster dikalahkan sesuai Tabel 2.3 dan Bagian 2.4:
        - Skeleton Guard: 150 Gold + 1 Health Potion
        - Crystal Slime: Kristal Mana (Reset Cooldown Skill) + 50 Gold
        - Magma Golem: DEF +15 Permanen + 100 Gold
        - Shadow Wraith: 100 Gold + Petunjuk Boss Lair
        - Boss: Menang game!
        """
        self.defeated_monsters.add(monster.name)
        rewards = []

        # Tambahkan gold dasar monster
        if monster.gold_reward > 0:
            self.player.gold += monster.gold_reward
            rewards.append(f"+{monster.gold_reward} Gold")

        if monster.name == "Skeleton Guard":
            extra_gold = 150
            self.player.gold += extra_gold
            self.player.potions += 1
            self.player.inventory.add_item("Health Potion", 1, 300)
            rewards.append(f"+{extra_gold} Gold rampasan peti perunggu & +1 Health Potion!")

        elif monster.name == "Crystal Slime":
            self.player.has_mana_crystal = True
            rewards.append("Memperoleh Kristal Mana! (Dapat digunakan untuk mereset cooldown skill)")

        elif monster.name == "Magma Golem":
            self.player.boost_defense_permanent(15)
            rewards.append("Menyerap inti lahar Magma Golem: Pertahanan meningkat +15 DEF permanen!")

        elif monster.name == "Shadow Wraith":
            rewards.append("Mendapatkan Peta Bayangan: Petunjuk letak Throne of Extinction terungkap!")

        elif monster.is_boss:
            self.game_won = True
            rewards.append("🏆 SELAMAT! Corrupted Crystal Kaiju telah ditaklukkan! Kamu menyelamatkan kerajaan!")

        return rewards

    def calculate_final_score(self) -> int:
        """
        Rumus Skor Akhir resmi sesuai Dokumen Perencanaan (Bagian 2.3):
        Skor = (HP tersisa * 2) + (Gold * 10) + (Teka-teki selesai * 250) - (Total langkah * 5)
        Langkah = jumlah bobot edge yang dilalui di peta.
        """
        puzzles_solved = (
            (1 if self.completed_sliding_puzzle else 0)
            + (1 if self.completed_stack_puzzle else 0)
            + (1 if self.completed_village_quest else 0)
        )
        score = (
            (max(0, self.player.hp) * 2)
            + (self.player.gold * 10)
            + (puzzles_solved * 250)
            - (self.player.total_steps * 5)
        )
        return max(0, score)


# Alias GameState sesuai template Bagian 2.1
GameState = GameStateManager
