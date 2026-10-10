"""
Module: ui/components/inventory_dialog.py
Description: Dialog popup modal inventaris tas petualang (Inventory Dialog)
bertema 2D Pixel RPG lengkap dengan ikon aset 16x16 Assorted RPG Icons.
"""

from typing import List, Optional
import customtkinter as ctk

from core.item import Item
from ui.asset_loader import get_item_icon, get_rpg_icon_by_name
from ui.theme import (
    BG_CARD, BG_DARK, BORDER_COLOR, COLOR_GOLD, COLOR_PRIMARY,
    FONT_BODY, FONT_BOLD, FONT_HEADING, FONT_MONO_SMALL, FONT_SMALL,
    FONT_SUBTITLE, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY
)


class InventoryDialog(ctk.CTkToplevel):
    """Jendela pop-up modal inventaris petualang bertema Pixel Art RPG."""

    def __init__(self, parent, items: List[Item], player_name: str = "Hero") -> None:
        super().__init__(parent)
        self.items = items
        self.player_name = player_name

        self.title("Tas Petualang - G-Dungeons")
        self.geometry("560x520")
        self.resizable(False, False)
        self.configure(fg_color="#0B0D14")

        # Pastikan dialog selalu berada di depan jendela induk
        self.transient(parent)
        self.grab_set()

        # Pusatkan modal relatif terhadap jendela induk
        self.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 280
            py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 260
            self.geometry(f"+{max(20, px)}+{max(20, py)}")
        except Exception:
            pass

        self.setup_ui()

    def setup_ui(self) -> None:
        """Membangun layout antarmuka dialog inventaris."""
        container = ctk.CTkFrame(
            self,
            fg_color="#0F121C",
            border_color="#333A56",
            border_width=2,
            corner_radius=14
        )
        container.pack(fill="both", expand=True, padx=14, pady=14)

        # Header Bar
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))

        self.icon_chest = get_rpg_icon_by_name("chest_royal", (32, 32))
        lbl_title = ctk.CTkLabel(
            header,
            text=" TAS PETUALANG & RELIK KUNO",
            image=self.icon_chest,
            compound="left",
            font=FONT_SUBTITLE,
            text_color=COLOR_GOLD
        )
        lbl_title.pack(anchor="center")

        lbl_owner = ctk.CTkLabel(
            header,
            text=f"Milik: {self.player_name}  •  Total Item Tersimpan: {len(self.items)}",
            font=FONT_MONO_SMALL,
            text_color=TEXT_MUTED
        )
        lbl_owner.pack(anchor="center", pady=(2, 0))

        # Konten Daftar Item (Scrollable Frame)
        scroll_frame = ctk.CTkScrollableFrame(
            container,
            fg_color="#080A10",
            border_color="#1E2436",
            border_width=1,
            corner_radius=10,
            height=320
        )
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=6)

        if not self.items:
            # Tampilan jika tas masih kosong
            empty_box = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            empty_box.pack(expand=True, pady=40)

            empty_chest = get_rpg_icon_by_name("chest_wood", (48, 48))
            if empty_chest:
                ctk.CTkLabel(empty_box, text="", image=empty_chest).pack(pady=(0, 10))

            ctk.CTkLabel(
                empty_box,
                text="Tasmu Masih Kosong!",
                font=FONT_HEADING,
                text_color=TEXT_PRIMARY
            ).pack()

            ctk.CTkLabel(
                empty_box,
                text="Pecahkan teka-teki labirin menara, temui NPC misterius di hutan,\natau kalahkan monster untuk mengumpulkan senjata dan relik sakti.",
                font=FONT_SMALL,
                text_color=TEXT_MUTED,
                justify="center",
                wraplength=380
            ).pack(pady=(6, 0))
        else:
            # Tampilkan item satu per satu
            for idx, item in enumerate(self.items, 1):
                self.create_item_card(scroll_frame, item, idx)

        # Footer Bar & Tombol Tutup
        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(8, 12))

        btn_close = ctk.CTkButton(
            footer,
            text="Tutup Tas",
            font=FONT_BOLD,
            height=36,
            fg_color=COLOR_PRIMARY,
            hover_color="#2563EB",
            corner_radius=8,
            command=self.destroy
        )
        btn_close.pack(fill="x")

    def create_item_card(self, parent: ctk.CTkFrame, item: Item, idx: int) -> None:
        """Membuat satu kartu slot item dengan icon pixel 16x16 dan deskripsi lengkap."""
        card = ctk.CTkFrame(
            parent,
            fg_color="#131724",
            border_color="#272E44",
            border_width=1,
            corner_radius=8
        )
        card.pack(fill="x", pady=4, padx=2)

        # Slot Icon Item (Kotak Pixel Gelap)
        slot = ctk.CTkFrame(
            card,
            fg_color="#07090F",
            border_color="#1A1F30",
            border_width=1,
            corner_radius=6,
            width=50,
            height=50
        )
        slot.pack(side="left", padx=8, pady=8)
        slot.pack_propagate(False)

        icon_img = get_item_icon(item.name, size=(32, 32))
        lbl_icon = ctk.CTkLabel(slot, text="" if icon_img else f"#{idx}", image=icon_img)
        lbl_icon.pack(expand=True)

        # Info Item: Nama & Deskripsi
        info_col = ctk.CTkFrame(card, fg_color="transparent")
        info_col.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=6)

        title_row = ctk.CTkFrame(info_col, fg_color="transparent")
        title_row.pack(fill="x")

        lbl_name = ctk.CTkLabel(
            title_row,
            text=f"{item.name}",
            font=FONT_BOLD,
            text_color=COLOR_GOLD,
            anchor="w"
        )
        lbl_name.pack(side="left")

        # Pill Nilai/Kekuatan Item
        atk_icon = get_rpg_icon_by_name("atk", (14, 14))
        badge_val = ctk.CTkLabel(
            title_row,
            text=f" Nilai/DMG: {item.value}",
            image=atk_icon,
            compound="left",
            font=FONT_MONO_SMALL,
            text_color=COLOR_PRIMARY
        )
        badge_val.pack(side="right")

        lbl_desc = ctk.CTkLabel(
            info_col,
            text=item.description,
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
            anchor="w",
            wraplength=340,
            justify="left"
        )
        lbl_desc.pack(fill="x", pady=(2, 0))
