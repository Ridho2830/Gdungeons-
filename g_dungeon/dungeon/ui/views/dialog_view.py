"""
Module: ui/views/dialog_view.py
Description: Layar percakapan interaktif dengan Roh Pohon Kuno (Gyoot / Elder Tree) di Forest.
"""

from typing import Optional
from PIL import Image
import customtkinter as ctk
from core.item import Item
from ui.asset_loader import load_image, load_pil_image
from ui.theme import (
    BG_CARD, BG_DARK, BG_PANEL, BORDER_COLOR, COLOR_GOLD, COLOR_PRIMARY,
    FONT_BODY, FONT_BOLD, FONT_HEADING, FONT_MONO_SMALL, FONT_SUBTITLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY
)

ASCII_GROOT = r"""
                            .=@*---=-*--=* :===++*%%*=:
                            +@---=-==---%**----+@*---*%+:+--
                        :.  %#-----=+---=+-----%*--+*=-*%++-.
                       :@@=.@+------+-----=----%-------=@@=
                      -%*%#%@-------+---------++-------=-+*
                     -@=-#-=*--------+--------=----------+@
                     #+--=------------------------------**%:
                     =+--------------------------------==+#
                     .#=--------------------------------==+
                      .#=--=#@@@@%*----:::--=#@@@@@#=---=*.
                       .%-=@@:.*@@@@-::::::=@@: +@@@@=-=*-
                        +++@@#*@@@@@+::::::*@@%#@@@@@+=**
                         #-@@@@@#%@@-::::::=@@@@@#@@#-=%.
                         +-=*%@@@@*-::::::::-*#%@%#+-=%=
                         +---------::::-------------=+@.
                         .+=---------++==++-----====+@:
                      .=.  =*+====----+++=---====+*%*:
                      *++=: .+%#*+==========++*#%@=  -
                      -=+++####+#@%##%%%%@%###%++##-*+
"""


class DialogForestView(ctk.CTkFrame):
    """Layar dialog dengan NPC Gyoot berlatar hutan mistis 2D Pixel RPG."""

    def __init__(self, master, app_controller) -> None:
        super().__init__(master, fg_color=BG_DARK)
        self.app = app_controller

        self._current_w = 1200
        self._current_h = 750
        self._bg_pil: Optional[Image.Image] = None
        self._bg_ctk: Optional[ctk.CTkImage] = None

        # 1. Background Hutan Mistis Skala Penuh
        self.setup_background()

        # 2. Card Container
        container = ctk.CTkFrame(
            self,
            fg_color="#0B131A",
            border_color="#10B981",
            border_width=2,
            corner_radius=16,
            width=840,
            height=630
        )
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.pack_propagate(False)

        # Bind resize listener
        self.bind("<Configure>", self._on_resize)

        # Title
        ctk.CTkLabel(
            container,
            text="🌲 PERTEMUAN DENGAN GYOOT (ELDER TREE) 🌲",
            font=FONT_SUBTITLE,
            text_color="#10B981"
        ).pack(pady=(20, 8))

        # Avatar Frame
        avatar_frame = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=10)
        avatar_frame.pack(fill="x", padx=40, pady=(0, 10))

        ctk.CTkLabel(
            avatar_frame,
            text=ASCII_GROOT.strip(),
            font=FONT_MONO_SMALL,
            text_color="#34D399",
            justify="center"
        ).pack(pady=8)

        # Dialog Box
        self.dialog_box = ctk.CTkFrame(container, fg_color="#131622", border_color=BORDER_COLOR, border_width=1, corner_radius=8)
        self.dialog_box.pack(fill="x", padx=40, pady=(0, 15))

        self.lbl_speaker = ctk.CTkLabel(
            self.dialog_box,
            text="Gyoot (Penjaga Hutan Purba):",
            font=FONT_BOLD,
            text_color=COLOR_GOLD
        )
        self.lbl_speaker.pack(anchor="w", padx=16, pady=(10, 4))

        self.lbl_text = ctk.CTkLabel(
            self.dialog_box,
            text="'Selamat datang, pengembara. Hawa sihir di tempat ini sangat pekat. Apa tujuanmu menginjakkan kaki di hutan terlarang ini?'",
            font=FONT_BODY,
            text_color=TEXT_PRIMARY,
            wraplength=680,
            justify="left"
        )
        self.lbl_text.pack(anchor="w", padx=16, pady=(0, 14))

        # Action Options
        self.choices_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.choices_frame.pack(fill="x", padx=40, pady=(0, 10))

        self.btn_opt1 = ctk.CTkButton(
            self.choices_frame,
            text="1. \"Aku ingin menyelamatkan dunia ini dari kegelapan.\"",
            font=FONT_BODY,
            height=38,
            anchor="w",
            fg_color=BG_CARD,
            hover_color="#2E344E",
            command=self.choose_option_1
        )
        self.btn_opt1.pack(fill="x", pady=4)

        self.btn_opt2 = ctk.CTkButton(
            self.choices_frame,
            text="2. \"Aku hanya ingin bertahan hidup dan mencari jalan keluar.\"",
            font=FONT_BODY,
            height=38,
            anchor="w",
            fg_color=BG_CARD,
            hover_color="#2E344E",
            command=self.choose_option_2
        )
        self.btn_opt2.pack(fill="x", pady=4)

        self.btn_opt3 = ctk.CTkButton(
            self.choices_frame,
            text="3. \"Aku tertarik dengan rahasia dan sihir purba hutan ini.\"",
            font=FONT_BODY,
            height=38,
            anchor="w",
            fg_color=BG_CARD,
            hover_color="#2E344E",
            command=self.choose_option_3
        )
        self.btn_opt3.pack(fill="x", pady=4)

        # Return Button (hidden initially)
        self.btn_continue = ctk.CTkButton(
            container,
            text="Lanjutkan Penjelajahan ➔",
            font=FONT_HEADING,
            height=42,
            fg_color=COLOR_PRIMARY,
            hover_color="#2563EB",
            command=self.finish_dialog
        )

    def choose_option_1(self) -> None:
        """Pilihan 1: Pemain menerima item Mokuton."""
        self.choices_frame.pack_forget()
        self.lbl_text.configure(
            text="'Niat yang mulia, wahai kesatria. Jalan di depan penuh mara bahaya, namun aku melihat keteguhan dalam dirimu.\n\n"
                 "Terimalah ini: Item [Mokuton] (+500 Damage). Gunakan dengan bijak untuk melumpuhkan musuh-musuhmu!'"
        )
        # Berikan item Mokuton ke inventory pemain
        self.app.game_state.player.inventory.add_item(
            Item(name="Mokuton", value=500, description="Kayu sihir kuno pemberian Gyoot penakluk musuh.")
        )
        self.app.game_state.completed_forest_dialogue = True
        self.btn_continue.pack(fill="x", padx=40, pady=(10, 0))

    def choose_option_2(self) -> None:
        """Pilihan 2."""
        self.choices_frame.pack_forget()
        self.lbl_text.configure(
            text="'Ah, seorang pencari kelangsungan hidup. Ketahuilah, hutan ini memiliki caranya sendiri untuk menguji tekadmu. "
                 "Berhati-hatilah melangkah di labirin bawah tanah ini.'"
        )
        self.app.game_state.completed_forest_dialogue = True
        self.btn_continue.pack(fill="x", padx=40, pady=(10, 0))

    def choose_option_3(self) -> None:
        """Pilihan 3."""
        self.choices_frame.pack_forget()
        self.lbl_text.configure(
            text="'Rahasia hutan ini teramat luas, pengembara. Namun waspadalah, sebagian misteri menuntut harga yang sangat mahal. "
                 "Semoga kebijaksanaan menyertaimu.'"
        )
        self.app.game_state.completed_forest_dialogue = True
        self.btn_continue.pack(fill="x", padx=40, pady=(10, 0))

    def finish_dialog(self) -> None:
        """Kembali ke layar eksplorasi."""
        self.app.show_exploration()

    def setup_background(self) -> None:
        """Memuat gambar latar belakang hutan mistis skala penuh."""
        self._bg_pil = load_pil_image("backgrounds/forest_dialog_bg.png")
        if self._bg_pil:
            try:
                self._bg_ctk = ctk.CTkImage(
                    light_image=self._bg_pil,
                    dark_image=self._bg_pil,
                    size=(self._current_w, self._current_h)
                )
                self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                self.bg_label.lift(self._canvas)
            except Exception as e:
                print(f"[DialogForestView] Gagal memuat background: {e}")

    def _on_resize(self, event) -> None:
        """Menyesuaikan skala gambar background ketika ukuran window berubah."""
        if event.widget in (self, getattr(self, "_canvas", None)):
            w, h = event.width, event.height
            if w < 100 or h < 100:
                return
            if abs(w - self._current_w) > 10 or abs(h - self._current_h) > 10:
                self._current_w = w
                self._current_h = h
                if self._bg_pil and hasattr(self, "bg_label"):
                    self._bg_ctk = ctk.CTkImage(
                        light_image=self._bg_pil,
                        dark_image=self._bg_pil,
                        size=(w, h)
                    )
                    self.bg_label.configure(image=self._bg_ctk)
