"""
Module: core/item.py
Description: Definisi kelas Item dan Inventory pemain.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union


@dataclass
class Item:
    """Representasi sebuah item atau perlengkapan dalam permainan."""
    name: str
    value: int = 0
    description: str = ""
    quantity: int = 1

    def __str__(self) -> str:
        return f"{self.name} x{self.quantity} (Value/DMG: {self.value})"


class Inventory:
    """Mengelola koleksi item pemain menggunakan struktur data Pythonic (dict/list)."""

    def __init__(self) -> None:
        # Menggunakan dictionary untuk lookup cepat: item_name.lower() -> Item
        self._items: Dict[str, Item] = {}

    def add_item(self, item_or_name: Union[Item, str], quantity: int = 1, value: int = 0, description: str = "") -> None:
        """Menambahkan item ke dalam inventory. Menerima objek Item atau parameter (name, quantity, value, description)."""
        if isinstance(item_or_name, Item):
            key = item_or_name.name.lower()
            if key in self._items:
                self._items[key].quantity += item_or_name.quantity
            else:
                self._items[key] = item_or_name
        else:
            name_str = str(item_or_name)
            key = name_str.lower()
            if key in self._items:
                self._items[key].quantity += quantity
                if value:
                    self._items[key].value = value
                if description:
                    self._items[key].description = description
            else:
                self._items[key] = Item(name=name_str, value=value, description=description, quantity=quantity)

    def remove_item(self, item_name: str, quantity: int = 1) -> Optional[Item]:
        """Mengurangi jumlah item atau menghapus dari inventory jika habis."""
        key = item_name.lower()
        if key in self._items:
            item = self._items[key]
            item.quantity -= quantity
            if item.quantity <= 0:
                return self._items.pop(key, None)
            return item
        return None

    def get_item(self, item_name: str) -> Optional[Item]:
        """Mencari item di inventory tanpa menghapusnya."""
        return self._items.get(item_name.lower(), None)

    def has_item(self, item_name: str) -> bool:
        """Memeriksa apakah pemain memiliki item tertentu."""
        return item_name.lower() in self._items

    def get_all_items(self) -> List[Item]:
        """Mengembalikan daftar semua item di inventory."""
        return list(self._items.values())

    def is_empty(self) -> bool:
        """Memeriksa apakah inventory kosong."""
        return len(self._items) == 0

    def __len__(self) -> int:
        return len(self._items)

