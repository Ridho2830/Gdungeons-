# G-Dungeons: PyGame Edition (Rubrik Penilaian Standar Industri)

Game RPG 2D grafis interaktif **G-Dungeons** berbasis **PyGame (pygame-ce)** dan **Python 3**, dirancang khusus untuk memenuhi 100% kriteria teknis dan pengalaman pengguna (*User Experience / UX*) pada **Template Perencanaan Proyek Game & Rubrik Penilaian**.

---

## 🎮 Fitur Utama & Keselarasan Rubrik

### 1. Main Game Loop Kanonikal (`engine/game.py`)
Menerapkan siklus standar industri berjalan stabil pada 60 FPS:
```python
while self.running:
    dt = self.clock.tick(60) / 1000.0  # Delta Time
    self.handle_events()               # 1. Pemrosesan Input
    self.update(dt)                    # 2. Pembaruan Logika
    self.render()                      # 3. Penggambaran Visual
    pygame.display.flip()              # 4. Double Buffer Flip
```

### 2. State Machine Terpusat (`engine/state_machine.py`)
Semua state didaftarkan dan dikontrol secara eksplisit:
* `MENU_STATE`: Layar menu utama dengan background animasi, logo, dan tombol pixel art.
* `ROLE_SELECT_STATE`: Pemilihan peran (Fighter / Knight vs Mage / Wizard) dengan live animated sprite preview.
* `EXPLORATION_STATE`: Navigasi graf 10 ruangan dengan bobot jalur dan visualisasi Algoritma Dijkstra (Mage Map Vision).
* `COMBAT_STATE`: Pertarungan turn-based dengan sprite sheet animasi, sistem armor, monster rage mode, floating damage, dan screen shake.
* `PUZZLE_STATE`: Tiga teka-teki interaktif (8-Puzzle Matriks, Bejana Warna Stack LIFO, Ban Berjalan Queue FIFO).
* `DIALOG_STATE`: Percakapan NPC bercabang dengan Elder Tree Gyoot di Whispering Forest.
* `PAUSE_STATE`: Overlay menu jeda semi-transparan saat tombol `[ESC]` ditekan (Resume, Restart, Audio, Menu Utama).
* `END_STATE`: Layar hasil menang/kalah dengan perhitungan skor `CalculateFinalScore` dan ringkasan rute perjalanan `TravelHistory`.

### 3. Pemrograman Berorientasi Objek (OOP) & Komponen Visual (`engine/entities.py`)
* `GameObject`: Membungkus komponen dasar Transform (x, y, rect), Collider, update, dan render.
* `AnimatedSprite`: Mengelola pemutaran animasi sprite sheet dari frame pixel art.
* `PlayerEntity`: Menghubungkan logika `Player` dengan animasi Knight / Wizard (Idle, Attack, Hurt, Defend, Death).
* `MonsterEntity`: Menghubungkan logika `Monster` dengan sprite Kaiju Boss, animasi getar saat terluka, dan aura menyala saat Rage.

### 4. Struktur Data & Algoritma (DSA)
* **Weighted Undirected Graph & Algoritma Dijkstra** (`core/dungeon_graph.py`): Peta 10 ruangan dan pencarian rute terpendek tercepat.
* **Stack (LIFO)** (`puzzles/color_stack_puzzle.py`): Puzzle sortir cairan tabung reaksi di The Eternal Relic.
* **Queue (FIFO)** (`puzzles/conveyor_quest.py`): Quest ban berjalan pesanan di Village Workshop.
* **Matriks & Inversion Parity** (`puzzles/sliding_puzzle.py`): 8-Puzzle ubin geser di Labyrinth Tower.
* **Hash Map / Dict Lookup** (`core/item.py`): Sistem tas inventaris pemain $O(1)$.

### 5. Peningkatan Pengalaman Pengguna (UX Rubrik)
* **Objective Clarity**: Banner HUD di atas layar menampilkan Misi Utama dan checklist tugas.
* **Feedback**: Efek suara sintetis retro 8-bit tanpa dependensi file eksternal (`engine/audio.py`), angka damage melayang (+Heal, -DMG), dan guncangan layar (*Screen Shake*).
* **Readability**: Kontras tinggi, panel gelap RPG, dan garis tepi emas (*Gold Border*) pada elemen interaktif.
* **Intuitivitas Kontrol**: Klik mouse langsung di seluruh elemen UI dipadukan dengan tombol pintas keyboard (`ESC` untuk Pause).
* **Error Prevention**: Pause menu setiap saat, tombol reset puzzle, dan tombol mundur dari pertarungan.

---

## 📁 Struktur Direktori Proyek

```text
g_dungeon/
│
├── main.py                                  # Entry point utama game (PyGame Game Engine)
├── requirements.txt                         # Dependensi (pygame-ce, Pillow, python-docx)
├── README.md                                # Dokumentasi lengkap proyek
├── Perencanaan_dan_Rubrik_G_Dungeons.docx   # Dokumen perencanaan terisi lengkap siap dinilai
├── Template_Perencanaan_dan_Rubrik_Game.docx # Template asli perencanaan & rubrik
│
├── engine/                                  # [PYGAME ENGINE & VIEW-CONTROLLER]
│   ├── __init__.py
│   ├── constants.py                         # Dimensi layar (1280x720), palet warna, nama state
│   ├── audio.py                             # Generator suara prosedural 8-bit (Sound FX)
│   ├── assets.py                            # Caching gambar & sprite sheet loader (Pillow fallback)
│   ├── entities.py                          # Kelas OOP: GameObject, AnimatedSprite, PlayerEntity, MonsterEntity
│   ├── ui.py                                # Komponen UI: UIButton, UIProgressBar, FloatingText, ObjectiveHUD, LogBox
│   ├── state_machine.py                     # Finite State Machine terpusat (FSM)
│   ├── game.py                              # Pengontrol Utama Game & Main Game Loop resmi
│   └── states/                              # Kumpulan 8 Game States
│       ├── menu_state.py                    # Layar MENU_STATE
│       ├── role_select_state.py             # Layar ROLE_SELECT_STATE
│       ├── exploration_state.py             # Layar EXPLORATION_STATE (Peta Graf & Dijkstra)
│       ├── combat_state.py                  # Layar COMBAT_STATE (Turn-Based Battle)
│       ├── puzzle_state.py                  # Layar PUZZLE_STATE (3 Teka-Teki)
│       ├── dialog_state.py                  # Layar DIALOG_STATE (NPC Elder Tree)
│       ├── pause_state.py                   # Layar PAUSE_STATE (Overlay ESC)
│       └── end_state.py                     # Layar END_STATE (Menang / Kalah)
│
├── core/                                    # [MODEL LOGIKA DOMAIN]
│   ├── item.py                              # Model Item & Inventory
│   ├── player.py                            # Model Player, Role, & TravelRecord
│   ├── monster.py                           # Model Monster & Rage Mechanic
│   ├── dungeon_graph.py                     # Graf 10 Ruangan & Algoritma Dijkstra
│   └── game_state.py                        # GameStateManager terpusat
│
├── puzzles/                                 # [LOGIKA ALGORITMA TEKA-TEKI]
│   ├── sliding_puzzle.py                    # Logika 8-Puzzle Matriks
│   ├── color_stack_puzzle.py                # Logika Stack LIFO Sortir Warna
│   └── conveyor_quest.py                    # Logika Queue FIFO Ban Berjalan
│
└── assets/                                  # Folder aset visual gambar & sprite
    ├── backgrounds/                         # Background ruangan arena & labirin
    ├── monsters/                            # Sprite monster Kaiju
    ├── players/                             # Sprite sheet Knight & Wizard
    └── ui/                                  # Tombol pixel, logo, icon
```

---

## 🚀 Cara Menjalankan Game

1. Pastikan dependensi telah terinstal:
   ```bash
   pip install -r requirements.txt
   ```
2. Jalankan aplikasi:
   ```bash
   python main.py
   ```
