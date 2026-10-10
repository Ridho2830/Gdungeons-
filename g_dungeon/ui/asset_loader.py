"""
Module: ui/asset_loader.py
Description: Pengelola aset terpusat (Asset Loader & Cache) untuk memuat
gambar, sprite monster, background, logo, dan tombol secara terstruktur.
"""

import os
from typing import Dict, Optional, Tuple
from PIL import Image, ImageTk
import customtkinter as ctk

# Root direktori assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Subdirektori standar
DIR_BACKGROUNDS = os.path.join(ASSETS_DIR, "backgrounds")
DIR_UI_BUTTONS = os.path.join(ASSETS_DIR, "ui", "buttons")
DIR_UI_LOGOS = os.path.join(ASSETS_DIR, "ui", "logos")
DIR_UI_MAP_NODES = os.path.join(ASSETS_DIR, "ui", "map_nodes")
DIR_MONSTERS = os.path.join(ASSETS_DIR, "monsters")
DIR_PLAYERS = os.path.join(ASSETS_DIR, "players")
DIR_RPG_ICONS = os.path.join(ASSETS_DIR, "16x16 Assorted RPG Icons")

# Cache global agar gambar tidak terhapus oleh Garbage Collector
_IMAGE_CACHE: Dict[str, ctk.CTkImage] = {}
_ROLE_IDLE_CACHE: Dict[str, list] = {}
_TK_CACHE: Dict[str, ImageTk.PhotoImage] = {}
_MAP_IDLE_CACHE: Dict[str, list] = {}
_RPG_ICON_CACHE: Dict[str, ctk.CTkImage] = {}
_RPG_TK_CACHE: Dict[str, ImageTk.PhotoImage] = {}


def get_asset_path(rel_path: str) -> Optional[str]:
    """
    Mencari lokasi absolut dari sebuah file aset.
    Mendukung path relatif spesifik (misal: 'ui/buttons/btn_play.png')
    maupun pencarian fleksibel berbasis nama file (misal: 'btn_play.png').
    """
    # 1. Cek langsung dari root assets
    direct_path = os.path.join(ASSETS_DIR, rel_path)
    if os.path.exists(direct_path) and os.path.isfile(direct_path):
        return direct_path

    filename = os.path.basename(rel_path)

    # 2. Cari di subdirektori terorganisir
    search_dirs = [
        DIR_UI_BUTTONS,
        DIR_UI_LOGOS,
        DIR_UI_MAP_NODES,
        DIR_BACKGROUNDS,
        DIR_MONSTERS,
        DIR_PLAYERS,
        DIR_RPG_ICONS,
    ]

    for sdir in search_dirs:
        candidate = os.path.join(sdir, filename)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate

    # 3. Pencarian rekursif jika belum ditemukan
    for root, _, files in os.walk(ASSETS_DIR):
        if filename in files:
            return os.path.join(root, filename)

    return None


def load_pil_image(rel_path: str) -> Optional[Image.Image]:
    """Memuat gambar mentah menggunakan PIL Image."""
    path = get_asset_path(rel_path)
    if path:
        try:
            return Image.open(path)
        except Exception as e:
            print(f"[AssetLoader] Gagal membuka gambar PIL '{rel_path}': {e}")
    return None


def load_image(
    rel_path: str,
    size: Optional[Tuple[int, int]] = None,
    resample: Image.Resampling = Image.Resampling.LANCZOS,
    use_cache: bool = True
) -> Optional[ctk.CTkImage]:
    """
    Memuat gambar sebagai ctk.CTkImage siap pakai untuk widget CustomTkinter.
    Menyimpan hasil ke dalam cache agar aman dari garbage collection.
    """
    cache_key = f"{rel_path}_{size}_{resample}"
    if use_cache and cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    path = get_asset_path(rel_path)
    if not path:
        return None

    try:
        pil_img = Image.open(path)
        if size is not None and resample != Image.Resampling.LANCZOS:
            resized_pil = pil_img.resize(size, resample)
            ctk_img = ctk.CTkImage(light_image=resized_pil, dark_image=resized_pil, size=size)
        elif size is not None:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        else:
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)

        if use_cache:
            _IMAGE_CACHE[cache_key] = ctk_img

        return ctk_img
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat ctk.CTkImage '{rel_path}': {e}")
        return None


def get_knight_idle_frames(target_size: Tuple[int, int] = (120, 130)) -> list:
    """
    Memotong 7 frame sprite IDLE Knight (Fighter) dari sprite sheet dan mengembalikannya
    sebagai list ctk.CTkImage dengan skala pixel art tajam (NEAREST resampling).
    """
    cache_key = f"knight_idle_{target_size}"
    if cache_key in _ROLE_IDLE_CACHE:
        return _ROLE_IDLE_CACHE[cache_key]

    # Cari file IDLE.png Knight
    knight_idle_path = get_asset_path("players/Knight 2D Pixel Art/Knight 2D Pixel Art/IDLE.png")
    if not knight_idle_path:
        knight_idle_path = get_asset_path("IDLE.png")

    if not knight_idle_path or not os.path.exists(knight_idle_path):
        return []

    try:
        sheet = Image.open(knight_idle_path)
        frames = []
        # Sprite sheet terdiri dari 7 frame (lebar per frame 96px, tinggi 84px)
        # Karakter berada di area x=20..75, y=15..75
        for i in range(7):
            box = (i * 96 + 20, 15, i * 96 + 75, 75)
            cropped = sheet.crop(box)
            scaled = cropped.resize(target_size, Image.Resampling.NEAREST)
            frames.append(ctk.CTkImage(light_image=scaled, dark_image=scaled, size=target_size))

        _ROLE_IDLE_CACHE[cache_key] = frames
        return frames
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat frame idle Knight: {e}")
        return []


def get_wizard_idle_frames(target_size: Tuple[int, int] = (130, 120)) -> list:
    """
    Memotong 6 frame sprite Idle Wizard (Mage) dari sprite sheet dan mengembalikannya
    sebagai list ctk.CTkImage dengan skala pixel art tajam (NEAREST resampling).
    """
    cache_key = f"wizard_idle_{target_size}"
    if cache_key in _ROLE_IDLE_CACHE:
        return _ROLE_IDLE_CACHE[cache_key]

    wizard_idle_path = get_asset_path("players/Wizard Pack/Wizard Pack/Idle.png")
    if not wizard_idle_path:
        wizard_idle_path = get_asset_path("Idle.png")

    if not wizard_idle_path or not os.path.exists(wizard_idle_path):
        return []

    try:
        sheet = Image.open(wizard_idle_path)
        frames = []
        # Sprite sheet terdiri dari 6 frame (lebar per frame 231px, tinggi 190px)
        # Karakter berada di area x=55..175, y=45..155
        for i in range(6):
            box = (i * 231 + 55, 45, i * 231 + 175, 155)
            cropped = sheet.crop(box)
            scaled = cropped.resize(target_size, Image.Resampling.NEAREST)
            frames.append(ctk.CTkImage(light_image=scaled, dark_image=scaled, size=target_size))

        _ROLE_IDLE_CACHE[cache_key] = frames
        return frames
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat frame idle Wizard: {e}")
        return []


def get_role_idle_frames(role_name: str) -> list:
    """Mengembalikan daftar frame sprite IDLE berdasarkan nama role ('Mage' / 'Fighter')."""
    role_lower = str(role_name).strip().lower()
    if "mage" in role_lower or "wizard" in role_lower:
        return get_wizard_idle_frames()
    elif "fighter" in role_lower or "knight" in role_lower:
        return get_knight_idle_frames()
    return []


def get_knight_attack_frames(target_size: Tuple[int, int] = (170, 180)) -> list:
    """Memotong 6 frame sprite ATTACK Knight (Fighter) dari sprite sheet."""
    cache_key = f"knight_attack_{target_size}"
    if cache_key in _ROLE_IDLE_CACHE:
        return _ROLE_IDLE_CACHE[cache_key]

    atk_path = get_asset_path("players/Knight 2D Pixel Art/Knight 2D Pixel Art/ATTACK 1.png")
    if not atk_path:
        atk_path = get_asset_path("ATTACK 1.png")

    if not atk_path or not os.path.exists(atk_path):
        return []

    try:
        sheet = Image.open(atk_path)
        frames = []
        for i in range(6):
            box = (i * 96 + 10, 15, i * 96 + 85, 75)
            cropped = sheet.crop(box)
            scaled = cropped.resize(target_size, Image.Resampling.NEAREST)
            frames.append(ctk.CTkImage(light_image=scaled, dark_image=scaled, size=target_size))

        _ROLE_IDLE_CACHE[cache_key] = frames
        return frames
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat frame attack Knight: {e}")
        return []


def get_wizard_attack_frames(target_size: Tuple[int, int] = (180, 165)) -> list:
    """Memotong 8 frame sprite ATTACK Wizard (Mage) dari sprite sheet."""
    cache_key = f"wizard_attack_{target_size}"
    if cache_key in _ROLE_IDLE_CACHE:
        return _ROLE_IDLE_CACHE[cache_key]

    atk_path = get_asset_path("players/Wizard Pack/Wizard Pack/Attack1.png")
    if not atk_path:
        atk_path = get_asset_path("Attack1.png")

    if not atk_path or not os.path.exists(atk_path):
        return []

    try:
        sheet = Image.open(atk_path)
        frames = []
        for i in range(8):
            box = (i * 231 + 40, 45, i * 231 + 195, 155)
            cropped = sheet.crop(box)
            scaled = cropped.resize(target_size, Image.Resampling.NEAREST)
            frames.append(ctk.CTkImage(light_image=scaled, dark_image=scaled, size=target_size))

        _ROLE_IDLE_CACHE[cache_key] = frames
        return frames
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat frame attack Wizard: {e}")
        return []


def get_role_attack_frames(role_name: str, target_size: Optional[Tuple[int, int]] = None) -> list:
    """Mengembalikan daftar frame sprite ATTACK berdasarkan nama role ('Mage' / 'Fighter')."""
    role_lower = str(role_name).strip().lower()
    if "mage" in role_lower or "wizard" in role_lower:
        sz = target_size or (180, 165)
        return get_wizard_attack_frames(sz)
    elif "fighter" in role_lower or "knight" in role_lower:
        sz = target_size or (170, 180)
        return get_knight_attack_frames(sz)
    return []


def get_map_background_tk(target_size: Tuple[int, int]) -> Optional[ImageTk.PhotoImage]:
    """Memuat dan menskalakan background peta dungeon gelap untuk Canvas Tkinter."""
    cache_key = f"map_bg_{target_size}"
    if cache_key in _TK_CACHE:
        return _TK_CACHE[cache_key]

    path = get_asset_path("backgrounds/dungeon_map_bg_dark.png") or get_asset_path("backgrounds/dungeon_map_bg.png")
    if not path:
        return None

    try:
        pil_img = Image.open(path)
        scaled = pil_img.resize(target_size, Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(scaled)
        _TK_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat background peta: {e}")
        return None


def get_map_node_icon_tk(loc_id: int, target_size: Tuple[int, int] = (48, 48)) -> Optional[ImageTk.PhotoImage]:
    """Memuat icon pixel art untuk sebuah lokasi dungeon untuk Canvas Tkinter."""
    cache_key = f"node_icon_tk_{loc_id}_{target_size}"
    if cache_key in _TK_CACHE:
        return _TK_CACHE[cache_key]

    pattern = f"node_{loc_id}_"
    target_file = None
    if os.path.exists(DIR_UI_MAP_NODES):
        for f in os.listdir(DIR_UI_MAP_NODES):
            if f.startswith(pattern):
                target_file = os.path.join(DIR_UI_MAP_NODES, f)
                break

    if not target_file:
        target_file = get_asset_path(f"node_{loc_id}_entry.png")

    if not target_file or not os.path.exists(target_file):
        return None

    try:
        pil_img = Image.open(target_file)
        scaled = pil_img.resize(target_size, Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(scaled)
        _TK_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat icon tk node #{loc_id}: {e}")
        return None


def get_map_node_icon_ctk(loc_id: int, target_size: Tuple[int, int] = (68, 68)) -> Optional[ctk.CTkImage]:
    """Memuat icon pixel art untuk sebuah lokasi dungeon untuk widget CustomTkinter (preview info)."""
    cache_key = f"node_icon_ctk_{loc_id}_{target_size}"
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    pattern = f"node_{loc_id}_"
    target_file = None
    if os.path.exists(DIR_UI_MAP_NODES):
        for f in os.listdir(DIR_UI_MAP_NODES):
            if f.startswith(pattern):
                target_file = os.path.join(DIR_UI_MAP_NODES, f)
                break

    if not target_file:
        target_file = get_asset_path(f"node_{loc_id}_entry.png")

    if not target_file or not os.path.exists(target_file):
        return None

    try:
        pil_img = Image.open(target_file)
        scaled = pil_img.resize(target_size, Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=scaled, dark_image=scaled, size=target_size)
        _IMAGE_CACHE[cache_key] = ctk_img
        return ctk_img
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat icon ctk node #{loc_id}: {e}")
        return None


def get_player_map_idle_tk_frames(role_name: str, target_size: Tuple[int, int] = (38, 42)) -> list:
    """Memotong frame idle karakter dalam format ImageTk.PhotoImage untuk animasi di Canvas peta."""
    cache_key = f"player_map_idle_{role_name}_{target_size}"
    if cache_key in _MAP_IDLE_CACHE:
        return _MAP_IDLE_CACHE[cache_key]

    role_lower = str(role_name).strip().lower()
    frames = []

    try:
        if "mage" in role_lower or "wizard" in role_lower:
            w_path = get_asset_path("players/Wizard Pack/Wizard Pack/Idle.png") or get_asset_path("Idle.png")
            if w_path and os.path.exists(w_path):
                sheet = Image.open(w_path)
                for i in range(6):
                    box = (i * 231 + 55, 45, i * 231 + 175, 155)
                    crop = sheet.crop(box)
                    scaled = crop.resize(target_size, Image.Resampling.NEAREST)
                    frames.append(ImageTk.PhotoImage(scaled))
        else:
            k_path = get_asset_path("players/Knight 2D Pixel Art/Knight 2D Pixel Art/IDLE.png") or get_asset_path("IDLE.png")
            if k_path and os.path.exists(k_path):
                sheet = Image.open(k_path)
                for i in range(7):
                    box = (i * 96 + 20, 15, i * 96 + 75, 75)
                    crop = sheet.crop(box)
                    scaled = crop.resize(target_size, Image.Resampling.NEAREST)
                    frames.append(ImageTk.PhotoImage(scaled))

        _MAP_IDLE_CACHE[cache_key] = frames
        return frames
    except Exception as e:
        print(f"[AssetLoader] Gagal memuat player map idle tk frames: {e}")
        return []


# ==================== 16x16 ASSORTED RPG ICONS ====================

RPG_ICON_REGISTRY: Dict[str, Tuple[str, int, int]] = {
    # Weapons / Attack / Swords
    "atk": ("weapons.png", 5, 0),         # Golden Longsword (Default ATK)
    "sword_gold": ("weapons.png", 5, 0),  # Golden Longsword
    "sword_iron": ("weapons.png", 1, 0),  # Iron Longsword
    "sword_crystal": ("weapons.png", 3, 0), # Cyan Crystal Blade
    "sword_emerald": ("weapons.png", 6, 0), # Emerald Blade
    "sword_heavy": ("weapons.png", 5, 4), # Heavy Broadsword / Claymore
    "dagger": ("weapons.png", 0, 5),      # Swift Dagger

    # Armours / Defense / Shields / Robes
    "def": ("armours.png", 1, 6),         # Heavy Iron Plate Cuirass (Default DEF)
    "armor_iron": ("armours.png", 1, 6),  # Heavy Iron Plate Cuirass
    "armor_gold": ("armours.png", 1, 14), # Golden Paladin Cuirass
    "armor_emerald": ("armours.png", 1, 17), # Emerald Titan Armor
    "robe_arcane": ("armours.png", 7, 1), # Crimson Gem Arcane Robe
    "robe_mystic": ("armours.png", 7, 5), # Royal Mystic Robe

    # Potions / Vitality / Health / Healing
    "hp": ("potions.png", 3, 1),          # Red HP Potion Flask (Default HP)
    "potion_red": ("potions.png", 3, 1),  # Red HP Flask
    "potion_red_large": ("potions.png", 3, 4), # Grand Life Elixir
    "potion_elixir": ("potions.png", 4, 1), # Amber Vitality Elixir
    "potion_green": ("potions.png", 7, 1),  # Green Healing Antidote
    "heal": ("potions.png", 7, 1),         # Default Heal icon
    "potion_yellow": ("potions.png", 6, 1), # Stamina Tonic

    # Magic / Spell Books / Tomes
    "magic": ("books.png", 4, 0),         # Arcane Grimoire (Default Magic)
    "book_arcane": ("books.png", 4, 0),   # Arcane Grimoire
    "book_fire": ("books.png", 3, 0),     # Fire Spellbook
    "book_gold": ("books.png", 6, 0),     # Golden Holy Scripture
    "book_emerald": ("books.png", 7, 0),  # Nature / Wind Tome
    "book_silver": ("books.png", 3, 5),   # Ancient Silver Grimoire

    # Chests / Inventory / Rewards
    "inventory": ("chests.png", 4, 0),    # Golden Treasure Chest (Default Inventory)
    "chest_gold": ("chests.png", 4, 0),   # Golden Chest
    "chest_wood": ("chests.png", 1, 0),   # Classic Wooden Chest
    "chest_royal": ("chests.png", 4, 2),  # Royal Deluxe Vault
    "chest_open": ("chests.png", 1, 1),   # Open Treasure Chest

    # Consumables
    "mug": ("consumables.png", 0, 0),
    "pouch": ("consumables.png", 8, 4),
}


def get_rpg_icon(sheet_name: str, col: int, row: int, size: Tuple[int, int] = (20, 20)) -> Optional[ctk.CTkImage]:
    """Memotong satu icon 16x16 dari sheet, me-resize dengan NEAREST, dan mengembalikan CTkImage."""
    cache_key = f"{sheet_name}_{col}_{row}_{size[0]}x{size[1]}"
    if cache_key in _RPG_ICON_CACHE:
        return _RPG_ICON_CACHE[cache_key]

    path = get_asset_path(sheet_name)
    if not path or not os.path.exists(path):
        return None

    try:
        sheet = Image.open(path).convert("RGBA")
        x0, y0 = col * 16, row * 16
        x1, y1 = x0 + 16, y0 + 16
        tile = sheet.crop((x0, y0, x1, y1))
        scaled = tile.resize(size, Image.Resampling.NEAREST)
        ctk_img = ctk.CTkImage(light_image=scaled, dark_image=scaled, size=size)
        _RPG_ICON_CACHE[cache_key] = ctk_img
        return ctk_img
    except Exception as e:
        print(f"[AssetLoader] Gagal memotong RPG icon ({sheet_name}, {col}, {row}): {e}")
        return None


def get_rpg_icon_by_name(name: str, size: Tuple[int, int] = (20, 20)) -> Optional[ctk.CTkImage]:
    """Mengambil icon 16x16 berdasarkan nama registri (misal: 'atk', 'def', 'hp', 'magic', 'inventory')."""
    key = name.lower().strip()
    if key in RPG_ICON_REGISTRY:
        sheet, col, row = RPG_ICON_REGISTRY[key]
        return get_rpg_icon(sheet, col, row, size)
    return None


def get_rpg_tk_icon_by_name(name: str, size: Tuple[int, int] = (20, 20)) -> Optional[ImageTk.PhotoImage]:
    """Mengambil icon 16x16 sebagai ImageTk.PhotoImage untuk digunakan pada tk.Canvas."""
    key = name.lower().strip()
    cache_key = f"tk_{key}_{size[0]}x{size[1]}"
    if cache_key in _RPG_TK_CACHE:
        return _RPG_TK_CACHE[cache_key]

    if key not in RPG_ICON_REGISTRY:
        return None

    sheet_name, col, row = RPG_ICON_REGISTRY[key]
    path = get_asset_path(sheet_name)
    if not path or not os.path.exists(path):
        return None

    try:
        sheet = Image.open(path).convert("RGBA")
        tile = sheet.crop((col * 16, row * 16, (col + 1) * 16, (row + 1) * 16))
        scaled = tile.resize(size, Image.Resampling.NEAREST)
        tk_img = ImageTk.PhotoImage(scaled)
        _RPG_TK_CACHE[cache_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"[AssetLoader] Gagal membuat PhotoImage RPG icon '{name}': {e}")
        return None


def get_item_icon(item_name: str, size: Tuple[int, int] = (24, 24)) -> Optional[ctk.CTkImage]:
    """Mengembalikan icon RPG yang relevan untuk item inventaris berdasarkan namanya."""
    name_lower = str(item_name).lower().strip()
    if "fire" in name_lower:
        return get_rpg_icon_by_name("book_fire", size)
    elif "broom" in name_lower or "sapu" in name_lower:
        return get_rpg_icon_by_name("sword_crystal", size)
    elif "mokuton" in name_lower or "wood" in name_lower or "kayu" in name_lower:
        return get_rpg_icon_by_name("book_emerald", size)
    elif "potion" in name_lower or "elixir" in name_lower or "ramuan" in name_lower:
        return get_rpg_icon_by_name("potion_red_large", size)
    elif "pedang" in name_lower or "sword" in name_lower or "blade" in name_lower:
        return get_rpg_icon_by_name("sword_gold", size)
    elif "armor" in name_lower or "perisai" in name_lower or "shield" in name_lower:
        return get_rpg_icon_by_name("armor_iron", size)
    elif "relic" in name_lower or "altar" in name_lower or "gem" in name_lower:
        return get_rpg_icon_by_name("chest_royal", size)
    else:
        return get_rpg_icon_by_name("chest_wood", size)



