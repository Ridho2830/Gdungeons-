"""
Module: puzzles/color_stack_puzzle.py
Description: Logika Puzzle Sortir Warna / Bejana Tabung (Stack LIFO) untuk The Eternal Relic.
"""

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
        # Inisialisasi awal 4 tabung sesuai game aslinya (puzzle2.java)
        # Tabung 1: Blue, Red, Green
        # Tabung 2: Blue, Green, Red
        # Tabung 3: Green, Blue
        # Tabung 4: Red
        self.tubes: List[List[str]] = [
            ["Blue", "Red", "Green"],
            ["Blue", "Green", "Red"],
            ["Green", "Blue"],
            ["Red"],
        ]
        self.move_count: int = 0
        self.selected_tube: Optional[int] = None

    def reset(self) -> None:
        """Mengembalikan susunan tabung ke konfigurasi awal."""
        self.tubes = [
            ["Blue", "Red", "Green"],
            ["Blue", "Green", "Red"],
            ["Green", "Blue"],
            ["Red"],
        ]
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
        """
        Memeriksa apakah warna teratas tabung sumber dapat dituang ke tabung target.
        Syarat:
        1. Tabung sumber tidak kosong.
        2. Sumber dan target tidak sama.
        3. Tabung target belum penuh (kurang dari MAX_CAPACITY).
        4. Tabung target kosong ATAU warna teratas target sama dengan warna teratas sumber.
        """
        if source_idx == target_idx:
            return False
        if not self.tubes[source_idx]:
            return False
        if len(self.tubes[target_idx]) >= self.MAX_CAPACITY:
            return False

        color_to_move = self.peek(source_idx)
        target_top = self.peek(target_idx)

        return target_top is None or target_top == color_to_move

    def pour(self, source_idx: int, target_idx: int) -> bool:
        """
        Menuangkan satu blok warna dari tabung sumber ke target (Stack Pop -> Push).
        Mengembalikan True jika aksi berhasil.
        """
        if not self.can_pour(source_idx, target_idx):
            return False

        color = self.tubes[source_idx].pop()
        self.tubes[target_idx].append(color)
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
