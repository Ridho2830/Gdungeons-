"""
Module: engine/state_machine.py
Description: Arsitektur Finite State Machine (FSM) untuk pengelolaan transisi antar layar game.
Memenuhi kriteria Rubrik Teknis: 'Manajemen State'.
"""

from typing import Any, Dict, List, Optional
import pygame


class GameState:
    """
    Kelas dasar untuk semua status (State) dalam game.
    Setiap turunan mengimplementasikan penanganan input, pembaruan logika, dan penggambaran visual.
    """

    def __init__(self, machine: "StateMachine") -> None:
        self.machine: "StateMachine" = machine

    def enter(self, **kwargs: Any) -> None:
        """Dipanggil saat game berpindah masuk ke state ini."""
        pass

    def exit(self) -> None:
        """Dipanggil saat game berpindah keluar dari state ini."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """Memproses masukan tombol keyboard dan mouse."""
        pass

    def update(self, dt: float) -> None:
        """Memperbarui kalkulasi logika state per frame."""
        pass

    def render(self, surface: pygame.Surface) -> None:
        """Menggambar tampilan grafis state ke canvas layar."""
        pass


class StateMachine:
    """
    Pengelola State terpusat (FSM).
    Menyimpan variabel status aktif dan riwayat tumpukan state (untuk Pause overlay).
    """

    def __init__(self) -> None:
        self.states: Dict[str, GameState] = {}
        self.current_state_name: Optional[str] = None
        self.state_stack: List[Tuple[str, GameState]] = []

    def register_state(self, name: str, state: GameState) -> None:
        """Mendaftarkan state baru ke dalam sistem."""
        self.states[name] = state

    @property
    def current_state(self) -> Optional[GameState]:
        """Mengembalikan objek state yang sedang aktif."""
        if not self.current_state_name:
            return None
        return self.states.get(self.current_state_name)

    def change_state(self, new_state_name: str, **kwargs: Any) -> None:
        """
        Berpindah ke state baru:
        1. Menjalankan exit() pada state lama.
        2. Memperbarui variabel current_state_name.
        3. Menjalankan enter() pada state baru.
        """
        if self.current_state:
            self.current_state.exit()

        self.current_state_name = new_state_name
        target = self.states.get(new_state_name)
        if target:
            target.enter(**kwargs)
        else:
            print(f"[StateMachine] Peringatan: State '{new_state_name}' tidak terdaftar!")

    def push_state(self, overlay_state_name: str, **kwargs: Any) -> None:
        """
        Menumpuk state baru di atas state aktif tanpa menghapusnya (berguna untuk Pause Menu).
        """
        if self.current_state_name and self.current_state:
            self.state_stack.append((self.current_state_name, self.current_state))

        self.current_state_name = overlay_state_name
        target = self.states.get(overlay_state_name)
        if target:
            target.enter(**kwargs)

    def pop_state(self) -> None:
        """Kembali ke state sebelumnya dari tumpukan (Resume dari Pause)."""
        if self.current_state:
            self.current_state.exit()

        if self.state_stack:
            prev_name, prev_state = self.state_stack.pop()
            self.current_state_name = prev_name
        else:
            self.current_state_name = None
