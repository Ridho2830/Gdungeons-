"""
Module: ui/components/stat_bar.py
Description: Komponen reusable CustomTkinter untuk status bar (HP, DEF, dsb).
"""

import customtkinter as ctk
from ui.theme import FONT_SMALL, FONT_BOLD, TEXT_PRIMARY, TEXT_MUTED


class StatBar(ctk.CTkFrame):
    """Bilah status dinamis dengan label, nilai numerik, dan progress bar warna."""

    def __init__(
        self,
        master,
        label: str,
        current: int,
        maximum: int,
        bar_color: str,
        width: int = 220,
        height: int = 14,
        **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.label_text = label
        self.maximum = max(1, maximum)
        self.current = current

        # Baris Header: Label & Angka
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 2))

        self.title_label = ctk.CTkLabel(
            header_frame,
            text=label,
            font=FONT_BOLD,
            text_color=TEXT_PRIMARY
        )
        self.title_label.pack(side="left")

        self.value_label = ctk.CTkLabel(
            header_frame,
            text=f"{current} / {maximum}",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        self.value_label.pack(side="right")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self,
            width=width,
            height=height,
            progress_color=bar_color,
            fg_color="#1E2235",
            corner_radius=6
        )
        self.progress_bar.pack(fill="x")
        self.update_progress()

    def update_progress(self) -> None:
        ratio = max(0.0, min(1.0, self.current / self.maximum))
        self.progress_bar.set(ratio)
        self.value_label.configure(text=f"{self.current} / {self.maximum}")

    def set_values(self, current: int, maximum: int) -> None:
        """Memperbarui nilai status bar secara langsung."""
        self.maximum = max(1, maximum)
        self.current = max(0, current)
        self.update_progress()
