"""
Module: puzzles/sliding_puzzle.py
Description: Logika 8-Puzzle (3x3 Sliding Tile Puzzle) untuk Labyrinth Tower.
"""

import random
from typing import List, Optional, Tuple


class SlidingPuzzle:
    """
    Logika permainan 8-Puzzle (3x3 grid).
    Pemain menggeser ubin bernomor 1-8 hingga tersusun rapi:
    [1, 2, 3]
    [4, 5, 6]
    [7, 8, 0] (0 adalah petak kosong)
    """

    GOAL_STATE = [1, 2, 3, 4, 5, 6, 7, 8, 0]

    def __init__(self, size: int = 3) -> None:
        self.size = size
        self.board: List[int] = list(self.GOAL_STATE)
        self.move_count: int = 0
        self.shuffle()

    @property
    def empty_index(self) -> int:
        """Mengembalikan indeks petak kosong (0)."""
        return self.board.index(0)

    def is_solved(self) -> bool:
        """Memeriksa apakah susunan ubin saat ini cocok dengan posisi menang."""
        return self.board == self.GOAL_STATE

    def get_grid(self) -> List[List[int]]:
        """Mengembalikan matriks 2D 3x3 dari susunan papan."""
        return [
            self.board[i * self.size : (i + 1) * self.size]
            for i in range(self.size)
        ]

    def can_move_tile(self, tile_index: int) -> bool:
        """Memeriksa apakah ubin pada indeks tertentu bersebelahan dengan petak kosong."""
        empty_idx = self.empty_index
        row_tile, col_tile = divmod(tile_index, self.size)
        row_empty, col_empty = divmod(empty_idx, self.size)
        return (abs(row_tile - row_empty) + abs(col_tile - col_empty)) == 1

    def move_by_index(self, tile_index: int) -> bool:
        """Menggeser ubin yang diklik menuju petak kosong jika valid."""
        if not self.can_move_tile(tile_index):
            return False

        empty_idx = self.empty_index
        self.board[empty_idx], self.board[tile_index] = (
            self.board[tile_index],
            self.board[empty_idx],
        )
        self.move_count += 1
        return True

    def move_direction(self, direction: str) -> bool:
        """
        Menggeser petak kosong berdasarkan arah:
        'W' / 'UP'    : petak kosong bergerak ke atas (ubin di atas bergeser turun)
        'S' / 'DOWN'  : petak kosong bergerak ke bawah
        'A' / 'LEFT'  : petak kosong bergerak ke kiri
        'D' / 'RIGHT' : petak kosong bergerak ke kanan
        """
        row, col = divmod(self.empty_index, self.size)
        new_row, new_col = row, col

        dir_upper = direction.upper()
        if dir_upper in ("W", "UP"):
            new_row -= 1
        elif dir_upper in ("S", "DOWN"):
            new_row += 1
        elif dir_upper in ("A", "LEFT"):
            new_col -= 1
        elif dir_upper in ("D", "RIGHT"):
            new_col += 1
        else:
            return False

        if 0 <= new_row < self.size and 0 <= new_col < self.size:
            target_idx = new_row * self.size + new_col
            return self.move_by_index(target_idx)
        return False

    def is_solvable(self, state: List[int]) -> bool:
        """Memeriksa solvabilitas 8-puzzle berdasarkan jumlah inversi."""
        inversions = 0
        tiles = [x for x in state if x != 0]
        for i in range(len(tiles)):
            for j in range(i + 1, len(tiles)):
                if tiles[i] > tiles[j]:
                    inversions += 1
        return inversions % 2 == 0

    def shuffle(self, steps: int = 40) -> None:
        """Mengacak puzzle dengan simulasi langkah acak agar selalu dapat diselesaikan."""
        self.board = list(self.GOAL_STATE)
        self.move_count = 0
        last_empty = -1

        for _ in range(steps):
            empty_idx = self.empty_index
            r, c = divmod(empty_idx, self.size)
            neighbors = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    n_idx = nr * self.size + nc
                    if n_idx != last_empty:
                        neighbors.append(n_idx)

            if neighbors:
                chosen = random.choice(neighbors)
                last_empty = empty_idx
                self.board[empty_idx], self.board[chosen] = (
                    self.board[chosen],
                    self.board[empty_idx],
                )

        # Jika kebetulan sudah terpecahkan setelah shuffle, geser 1 langkah
        if self.is_solved():
            self.move_by_index(self.empty_index - 1)
        self.move_count = 0
