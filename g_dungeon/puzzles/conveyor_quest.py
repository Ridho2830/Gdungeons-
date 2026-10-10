"""
Module: puzzles/conveyor_quest.py
Description: Logika Quest Conveyor Belt berbasis antrean FIFO (collections.deque) untuk Village.
"""

from collections import deque
from typing import Deque, List, Optional, Tuple


class ConveyorQuest:
    """
    Minigame antrean barang (Queue / FIFO).
    Barang berjalan di atas conveyor belt. Pemain harus mengambil barang terdepan
    yang sesuai dengan instruksi permintaan.
    """

    ITEMS_POOL = ["Potion", "Sword", "Shield", "Bow", "Ring"]
    TOTAL_TURNS = 5

    def __init__(self) -> None:
        self.conveyor: Deque[str] = deque(self.ITEMS_POOL[:5])
        self.current_turn: int = 0
        self.score: int = 0
        self.is_finished: bool = False

    def reset(self) -> None:
        """Mengembalikan quest ke giliran awal."""
        self.conveyor = deque(self.ITEMS_POOL[:5])
        self.current_turn = 0
        self.score = 0
        self.is_finished = False

    @property
    def target_item(self) -> str:
        """Item yang diminta pada giliran saat ini."""
        if self.current_turn < self.TOTAL_TURNS:
            return self.ITEMS_POOL[self.current_turn]
        return ""

    @property
    def front_item(self) -> Optional[str]:
        """Melihat barang yang saat ini berada paling depan di ban berjalan."""
        return self.conveyor[0] if self.conveyor else None

    def get_conveyor_items(self) -> List[str]:
        """Mendapatkan daftar seluruh item yang ada di conveyor dari depan ke belakang."""
        return list(self.conveyor)

    def process_pick(self, picked_item: str) -> Tuple[bool, str]:
        """
        Memproses pengambilan item oleh pemain:
        - Harus sesuai target giliran saat ini.
        - Harus merupakan item paling depan di conveyor.
        Mengembalikan (is_correct, feedback_message).
        """
        if self.is_finished:
            return False, "Quest sudah selesai!"

        target = self.target_item
        front = self.front_item
        is_correct = False
        message = ""

        if picked_item.strip().lower() == target.lower() and front and front.lower() == target.lower():
            self.score += 10
            self.conveyor.popleft()  # Dequeue item dari depan
            is_correct = True
            message = f"Tepat! Kamu berhasil mengambil {target} (+10 Poin)."
        else:
            if self.conveyor:
                self.conveyor.popleft()
            message = f"Salah atau urutan keliru! Target yang diminta: {target}."

        # Tambahkan item baru di ujung belakang (enqueue)
        next_item_to_add = self.ITEMS_POOL[(self.current_turn + 1) % len(self.ITEMS_POOL)]
        self.conveyor.append(next_item_to_add)

        self.current_turn += 1
        if self.current_turn >= self.TOTAL_TURNS:
            self.is_finished = True

        return is_correct, message
