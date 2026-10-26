"""
Module: puzzles/color_stack_puzzle.py
Description: Logika Puzzle Sortir Warna / Bejana Tabung (Stack LIFO) untuk The Eternal Relic.
"""

import random
from typing import List, Optional, Tuple

class ColorStackPuzzle:
    """
    Puzzle sortir warna berbasis Stack (LIFO).
    Terdapat 4 tabung dengan kapasitas maksimal 3 (atau 4) warna per tabung.
    Tujuan: Mengelompokkan semua warna yang sama ke dalam masing-masing tabung.
    """

    MAX_CAPACITY = 3

    COLOR_HEX_MAP = {
        "Red": "#ef4444",
        "Blue": "#3b82f6",
        "Green": "#10b981",
        "Yellow": "#f59e0b",
    }

    
    def __init__(self) -> None:
        self.tubes: List[List[str]] = []
        self.move_count: int = 0
        self.selected_tube: Optional[int] = None
        self.reset()

    
    def reset(self) -> None:
        """Acak puzzle tanpa warna sama yang berdampingan."""

        colors = (
            ["Red"] * 3
            + ["Blue"] * 3
            + ["Green"] * 3
        )

        while True:
            random.shuffle(colors)

            # Bagi 9 warna menjadi 3 tabung,
            # masing-masing berisi 3 warna.
            tubes = [
                colors[0:3].copy(),
                colors[3:6].copy(),
                colors[6:9].copy(),
                [],
            ]

            # Tolak susunan jika ada dua warna
            # sama yang berdampingan dalam tabung.
            valid = all(
                all(
                    tube[i] != tube[i + 1]
                    for i in range(len(tube) - 1)
                )
                for tube in tubes
            )

            if valid:
                self.tubes = tubes
                break

        self.move_count = 0
        self.selected_tube = None

    def get_tube(self, index: int) -> List[str]:
        """Mendapatkan daftar warna di tabung tertentu (elemen terakhir adalah paling atas/top)."""
        return self.tubes[index]

    def peek(self, tube_idx: int) -> Optional[str]:
        """Melihat warna teratas dari sebuah tabung tanpa mengeluarkannya."""
        if self.tubes[tube_idx]:
            return self.tubes[tube_idx][-1]
        return None

    
    def can_pour(self, source_idx: int, target_idx: int) -> bool:
        """Boleh menuang ke tabung mana pun yang masih memiliki ruang."""

        if source_idx == target_idx:
            return False

        if not self.tubes[source_idx]:
            return False

        if len(self.tubes[target_idx]) >= self.MAX_CAPACITY:
            return False

        # Warna berbeda tetap boleh dituang.
        return True

    def pour(self, source_idx: int, target_idx: int) -> bool:
        """
        Menuangkan kelompok warna teratas.
        Warna yang sama dan berdampingan bergerak bersama,
        sebanyak yang dapat ditampung tabung tujuan.
        """

        if not self.can_pour(source_idx, target_idx):
            return False

        source = self.tubes[source_idx]
        target = self.tubes[target_idx]

        # Ambil warna paling atas.
        color = source[-1]

        # Hitung berapa blok dengan warna sama
        # yang berdampingan di bagian paling atas.
        group_count = 0
        for block in reversed(source):
            if block == color:
                group_count += 1
            else:
                break

        # Hitung kapasitas tabung tujuan yang tersisa.
        free_space = self.MAX_CAPACITY - len(target)

        # Pindahkan sebanyak yang muat.
        amount = min(group_count, free_space)

        for _ in range(amount):
            target.append(source.pop())

        self.move_count += 1
        return True

    def is_solved(self) -> bool:
        """
        Memeriksa apakah permainan telah selesai:
        3 tabung terisi penuh (3 warna) dengan warna yang seragam di masing-masing tabung,
        dan 1 tabung kosong.
        """
        completed_tubes = 0
        for tube in self.tubes:
            if len(tube) == self.MAX_CAPACITY:
                # Periksa apakah semua warna dalam tabung ini identik
                if all(c == tube[0] for c in tube):
                    completed_tubes += 1

        return completed_tubes == 3
