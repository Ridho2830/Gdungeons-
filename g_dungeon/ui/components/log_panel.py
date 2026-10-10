"""
Module: ui/components/log_panel.py
Description: Panel catatan log & teks narasi interaktif.
"""

import customtkinter as ctk
from ui.theme import BG_CARD, BORDER_COLOR, FONT_MONO_SMALL, TEXT_PRIMARY


class LogPanel(ctk.CTkFrame):
    """Panel konsol narasi dan pesan aksi."""

    def __init__(self, master, title: str = "Log Aktivitas", height: int = 140, **kwargs) -> None:
        super().__init__(master, fg_color=BG_CARD, border_color=BORDER_COLOR, border_width=1, corner_radius=8, **kwargs)
        
        self.textbox = ctk.CTkTextbox(
            self,
            font=FONT_MONO_SMALL,
            fg_color="transparent",
            text_color=TEXT_PRIMARY,
            wrap="word",
            height=height
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.textbox.configure(state="disabled")

    def add_log(self, message: str) -> None:
        """Menambahkan pesan baru dan melakukan auto-scroll ke bawah."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self) -> None:
        """Menghapus seluruh riwayat log."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
