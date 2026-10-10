"""
Module: core/player.py
Description: Definisi kelas Player, Role (Knight & Mage), dan riwayat perjalanan TravelRecord.
Sesuai persis dengan Dokumen Perencanaan dan Rubrik Penilaian Game.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple
from core.item import Inventory, Item


class PlayerRole(Enum):
    """Pilihan peran/role pemain sesuai template resmi."""
    KNIGHT = "Knight"
    MAGE = "Mage"


@dataclass
class RoleStats:
    """Konfigurasi stat dasar untuk tiap peran."""
    role: PlayerRole
    hp: int
    max_hp: int
    attack: int
    defense: int
    description: str
    passive_name: str
    passive_desc: str


ROLE_CONFIGS = {
    PlayerRole.KNIGHT: RoleStats(
        role=PlayerRole.KNIGHT,
        hp=1500,
        max_hp=1500,
        attack=65,
        defense=45,
        description="Ksatria berzirah kokoh dengan pertahanan tinggi.",
        passive_name="Ironclad Fortitude",
        passive_desc="Damage fisik musuh berkurang 20% (tidak berlaku untuk Atomic Breath)."
    ),
    PlayerRole.MAGE: RoleStats(
        role=PlayerRole.MAGE,
        hp=1100,
        max_hp=1100,
        attack=95,
        defense=25,
        description="Penyihir berdaya serang dahsyat dengan penglihatan magis.",
        passive_name="Arcane Intellect & Map Vision",
        passive_desc="Rute terpendek Dijkstra otomatis ter-highlight di peta labirin."
    ),
}


@dataclass
class TravelRecord:
    """Catatan riwayat kunjungan satu lokasi."""
    location_name: str
    distance: int
    from_location: str


class Player:
    """Representasi karakter pemain di dalam game."""

    def __init__(self, name: str, role: PlayerRole, initial_location: str = "Entrance Hall") -> None:
        self.name: str = name
        self.role: PlayerRole = role

        # Inisialisasi stat berdasarkan role
        stats = ROLE_CONFIGS[role]
        self.max_hp: int = stats.max_hp
        self.hp: int = stats.hp
        self.attack: int = stats.attack
        self.defense: int = stats.defense
        self.base_defense: int = stats.defense
        self.max_defense: int = stats.defense

        # Resource & Progresi Game
        self.gold: int = 0
        self.crystal_fragments: int = 0  # Minimal butuh 2 untuk membuka Boss Lair
        self.potions: int = 3            # Stok awal 3 Health Potion (+300 HP)
        self.has_mana_crystal: bool = False  # Reset cooldown skill dari Crystal Cavern
        self.total_steps: int = 0        # Total bobot jarak tempuh yang dilalui (Langkah)
        self.skill_cooldown: int = 0     # Cooldown skill (3 ronde)
        self.shield: int = 0             # Kapasitas penahan damage (+80 dari Bertahan)

        self.location: str = initial_location
        self.inventory: Inventory = Inventory()
        self.travel_history: List[TravelRecord] = []

        # Masukkan 3 Health Potion awal ke inventory
        self.inventory.add_item("Health Potion", quantity=3, value=300, description="Memulihkan 300 HP")

        # Catat lokasi awal
        self.add_travel_record(initial_location, 0, "None")

    @property
    def is_alive(self) -> bool:
        """Memeriksa apakah pemain masih hidup."""
        return self.hp > 0

    @property
    def atk(self) -> int:
        """Alias untuk attack."""
        return self.attack

    @property
    def def_(self) -> int:
        """Alias untuk defense."""
        return self.defense

    @property
    def can_use_map_vision(self) -> bool:
        """Mage memiliki keunggulan pasif Map Vision otomatis."""
        return self.role == PlayerRole.MAGE

    def take_damage(self, raw_damage: int, is_atomic_breath: bool = False) -> Tuple[int, int]:
        """
        Menerima damage dengan kalkulasi:
        1. Pasif Knight (Ironclad Fortitude): Kurangi damage fisik 20% jika bukan Atomic Breath.
        2. Shield & Defense memotong damage terlebih dahulu.
        3. Sisa damage mengurangi HP.
        Mengembalikan (damage_absorbed, damage_to_hp).
        """
        effective_damage = raw_damage
        if self.role == PlayerRole.KNIGHT and not is_atomic_breath:
            effective_damage = max(1, int(raw_damage * 0.8))

        total_defense = self.defense + self.shield
        absorbed = 0
        damage_to_hp = 0

        if total_defense > 0:
            if effective_damage <= total_defense:
                absorbed = effective_damage
                # Kurangi shield dulu, sisa ke defense
                if self.shield >= effective_damage:
                    self.shield -= effective_damage
                else:
                    rem = effective_damage - self.shield
                    self.shield = 0
                    self.defense = max(0, self.defense - rem)
                damage_to_hp = 0
            else:
                absorbed = total_defense
                damage_to_hp = effective_damage - total_defense
                self.shield = 0
                self.defense = 0
        else:
            damage_to_hp = effective_damage

        self.hp = max(0, self.hp - damage_to_hp)
        return absorbed, damage_to_hp

    def use_potion(self) -> int:
        """Memakai 1 Health Potion (+300 HP). Mengembalikan jumlah HP yang dipulihkan."""
        if self.potions <= 0:
            return 0
        self.potions -= 1
        healed = min(300, self.max_hp - self.hp)
        self.hp += healed
        self.inventory.remove_item("Health Potion")
        return healed

    def heal(self, amount: int) -> int:
        """Memulihkan HP pemain hingga batas maksimal."""
        actual_heal = min(amount, self.max_hp - self.hp)
        self.hp += actual_heal
        return actual_heal

    def boost_defense_permanent(self, bonus: int) -> None:
        """Meningkatkan DEF permanen (Hadiah Magma Forge +15 DEF)."""
        self.defense += bonus
        self.base_defense += bonus
        self.max_defense += bonus

    def reset_shield(self) -> None:
        """Mereset shield sementara di akhir ronde dan memulihkan defense dasar."""
        self.shield = 0
        self.defense = self.base_defense

    def add_travel_record(self, location: str, distance: int, from_loc: str) -> None:
        """Menambahkan riwayat perpindahan lokasi dan mengakumulasi langkah."""
        self.travel_history.append(TravelRecord(location, distance, from_loc))
        self.total_steps += distance

    def __repr__(self) -> str:
        return f"Player(name='{self.name}', role={self.role.value}, HP={self.hp}/{self.max_hp}, Fragmen={self.crystal_fragments})"
