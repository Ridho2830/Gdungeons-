"""
Module: core/monster.py
Description: Definisi kelas Monster dan 5 data musuh resmi sesuai Dokumen Perencanaan & Rubrik:
Crystal Slime, Skeleton Guard, Shadow Wraith, Magma Golem, dan Corrupted Crystal Kaiju (Boss).
"""

from typing import Dict, Optional, Tuple
import random


class Monster:
    """Representasi musuh monster dengan sistem pertahanan, AI unik, dan rage mode."""

    def __init__(
        self,
        name: str,
        hp: int,
        attack: int,
        defense: int,
        gold: int = 0,
        is_boss: bool = False,
        title: str = "",
        room_name: str = "",
    ) -> None:
        self.name: str = name
        self.max_hp: int = hp
        self.hp: int = hp
        self.base_attack: int = attack
        self.attack: int = attack
        self.max_defense: int = defense
        self.defense: int = defense
        self.temp_defense_buff: int = 0  # Buff bertahan sementara (Skeleton Guard)
        self.gold_reward: int = gold
        self.is_boss: bool = is_boss
        self.title: str = title
        self.room_name: str = room_name
        self.is_alive: bool = True
        self.enraged: bool = False
        self.turn_counter: int = 0

    @property
    def atk(self) -> int:
        return self.attack

    @property
    def def_(self) -> int:
        return self.defense + self.temp_defense_buff

    def take_damage(self, raw_damage: int) -> Tuple[int, int]:
        """
        Damage mengurangi defense terlebih dahulu. Sisanya memotong HP.
        Mengembalikan (damage_absorbed, damage_to_hp).
        """
        total_def = self.defense + self.temp_defense_buff
        absorbed = 0
        damage_to_hp = 0

        if total_def > 0:
            if raw_damage <= total_def:
                absorbed = raw_damage
                if self.temp_defense_buff >= raw_damage:
                    self.temp_defense_buff -= raw_damage
                else:
                    rem = raw_damage - self.temp_defense_buff
                    self.temp_defense_buff = 0
                    self.defense = max(0, self.defense - rem)
                damage_to_hp = 0
            else:
                absorbed = total_def
                damage_to_hp = raw_damage - total_def
                self.temp_defense_buff = 0
                self.defense = 0
        else:
            damage_to_hp = raw_damage

        self.hp = max(0, self.hp - damage_to_hp)
        if self.hp == 0:
            self.is_alive = False

        # Reset temp buff setelah terkena pukulan
        self.temp_defense_buff = 0
        return absorbed, damage_to_hp

    @property
    def current_rage(self) -> int:
        """
        Kalkulasi dinamis progres meter kemarahan (0 - 100%):
        - Jika sudah Enraged: 100% (Maksimal).
        - Boss Kaiju: Akumulasi progres damage dari 0% s.d 100% saat HP menuju batas 50% HP.
        - Monster biasa: Akumulasi progres damage dari 0% s.d 100% saat HP menuju batas 40% HP.
        """
        if not self.is_alive or self.hp <= 0:
            return 0
        if self.enraged:
            return 100

        dmg_taken = max(0, self.max_hp - self.hp)
        if self.is_boss:
            threshold = self.max_hp * 0.5
            return min(100, max(0, int((dmg_taken / threshold) * 100)))
        else:
            threshold = self.max_hp * 0.6
            return min(100, max(0, int((dmg_taken / threshold) * 100)))

    def check_enrage(self) -> bool:
        """
        Memeriksa apakah monster terpicu masuk ke mode Enraged:
        - Boss Corrupted Crystal Kaiju: HP < 50% (+20 ATK & 20% Peluang Kritis).
        - Monster Biasa: HP < 40% (+10 ATK fase mengamuk).
        """
        if not self.is_alive or self.enraged:
            return False

        if self.is_boss and self.hp < (self.max_hp * 0.5):
            self.enraged = True
            self.attack += 20
            return True
        elif not self.is_boss and self.hp < (self.max_hp * 0.4):
            self.enraged = True
            self.attack += 10
            return True

        return False

    def decide_action(self, battle_turn: int) -> Tuple[str, int, str]:
        """
        AI Perilaku Musuh sesuai Tabel 2.3:
        - Crystal Slime: Selalu menyerang.
        - Skeleton Guard: 70% menyerang, 30% bertahan (DEF +10 satu giliran).
        - Shadow Wraith: Menyerang; saat HP < 50%, lifesteal 30% damage menjadi HP.
        - Magma Golem: Setiap giliran ke-3 memakai Hantaman Berat x1.5.
        - Corrupted Crystal Kaiju: Setiap ronde kelipatan 5 Atomic Breath x2.2.
        
        Mengembalikan tuple: (action_type, raw_damage, description)
        action_type: 'attack', 'defend', 'lifesteal', 'heavy_slam', 'ultimate'
        """
        self.turn_counter += 1

        # 1. Boss: Corrupted Crystal Kaiju
        if self.is_boss:
            if battle_turn % 5 == 0:
                dmg = int(self.attack * 2.2)
                return "ultimate", dmg, "Atomic Breath"
            else:
                is_crit = self.enraged and (random.random() < 0.20)
                dmg = int(self.attack * 1.5) if is_crit else self.attack
                return "attack", dmg, "Cakaran Kristal Terkorupsi" + (" (CRITICAL RAGE!)" if is_crit else "")

        # 2. Magma Golem
        if "Magma Golem" in self.name:
            if self.turn_counter % 3 == 0:
                dmg = int(self.attack * 1.5)
                return "heavy_slam", dmg, "Hantaman Berat Magma (x1.5 DMG)"
            return "attack", self.attack, "Pukulan Batu Lahar"

        # 3. Skeleton Guard
        if "Skeleton Guard" in self.name:
            if random.random() < 0.30:
                self.temp_defense_buff = 10
                return "defend", 0, "Menaikkan Perisai Tulang (+10 DEF)"
            return "attack", self.attack, "Tebasan Pedang Karat"

        # 4. Shadow Wraith
        if "Shadow Wraith" in self.name:
            if self.hp < (self.max_hp * 0.5):
                return "lifesteal", self.attack, "Hisapan Jiwa Bayangan (30% Lifesteal)"
            return "attack", self.attack, "Cakaran Bayangan Dingin"

        # 5. Crystal Slime (Default)
        return "attack", self.attack, "Semprotan Asam Kristal"

    def reset(self) -> None:
        """Mengembalikan kondisi monster ke keadaan semula saat pemain melarikan diri (Mundur)."""
        self.hp = self.max_hp
        self.attack = self.base_attack
        self.defense = self.max_defense
        self.temp_defense_buff = 0
        self.is_alive = True
        self.enraged = False
        self.turn_counter = 0


def create_default_monsters() -> Dict[str, Monster]:
    """Mendaftarkan 5 monster resmi sesuai tabel 2.3 dokumen perencanaan."""
    return {
        "Crystal Slime": Monster(
            name="Crystal Slime",
            hp=300,
            attack=40,
            defense=5,
            gold=50,
            is_boss=False,
            title="Lendir Kristal Beracun",
            room_name="Crystal Cavern"
        ),
        "Skeleton Guard": Monster(
            name="Skeleton Guard",
            hp=400,
            attack=50,
            defense=15,
            gold=75,
            is_boss=False,
            title="Penjaga Kuno Berzirah Karat",
            room_name="Ancient Armory"
        ),
        "Shadow Wraith": Monster(
            name="Shadow Wraith",
            hp=450,
            attack=55,
            defense=10,
            gold=100,
            is_boss=False,
            title="Arwah Gentayangan Penyerap Jiwa",
            room_name="Shadow Crypt"
        ),
        "Magma Golem": Monster(
            name="Magma Golem",
            hp=600,
            attack=60,
            defense=25,
            gold=100,
            is_boss=False,
            title="Raksasa Batuan Lahar Membara",
            room_name="Magma Forge"
        ),
        "Corrupted Crystal Kaiju": Monster(
            name="Corrupted Crystal Kaiju",
            hp=900,
            attack=85,
            defense=15,
            gold=0,
            is_boss=True,
            title="Penguasa Mutlak Throne of Extinction",
            room_name="Boss Lair: Throne of Extinction"
        ),
    }


# Roster referensi global & helper room
MONSTER_ROSTER = create_default_monsters()
RegularMonster = Monster
BossMonster = Monster


def create_monster_for_room(room_name: str) -> Optional[Monster]:
    """Mengembalikan instance monster berdasarkan nama ruangan."""
    for m in create_default_monsters().values():
        if m.room_name == room_name or (room_name and room_name in m.room_name):
            return m
    return None
