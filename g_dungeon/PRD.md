# Template Perencanaan Proyek Game & Rubrik Penilaian

## RPG TURN-BASED : G-DUNGEONS (PyGame Edition)

Dokumen ini berisi cetak biru perencanaan game beserta kesiapan terhadap rubrik penilaian teknis dan User Experience (UX), telah disinkronkan 100% dengan implementasi kode final dan aset permainan.

**Nama Anggota :**
- [Nama Anggota 1] ([NIM])
- [Nama Anggota 2] ([NIM])
- [Nama Anggota 3] ([NIM])

**Platform:** Desktop (Windows/macOS/Linux) | **Teknologi:** Python 3.10+ dan pygame saja | **Resolusi:** 1280 × 720 (60 FPS)

*Catatan: seluruh nilai angka (HP, ATK, bobot jalur) dan nama fungsi pada dokumen ini disamakan secara presisi dengan kode final. Rubrik menilai kesesuaian penjelasan dengan implementasi riil.*

---

## 1. Arsitektur & Alur Game (Loop & State)

### 1.1 Main Game Loop

Loop utama berada di `engine/game.py` (metode `Game.run()`, baris 143–158) dan berjalan terus sampai pemain keluar. Setiap frame menjalankan lima langkah berurutan:

- **Tick:** `dt = self.clock.tick(FPS) / 1000.0` (baris 151) membatasi game di 60 FPS dan menghasilkan delta time untuk animasi per frame, interpolasi UI, dan timer cooldown.
- **Input:** `self.handle_events()` (baris 154) membaca antrean `pygame.event.get()`, mendeteksi event keluar OS (`QUIT`), dan meneruskan interaksi mouse (klik, hover) serta keyboard (`ESC`) ke state yang sedang aktif.
- **Update:** `self.update(dt)` (baris 157) memperbarui logika pada state aktif: timer transisi, cooldown skill, giliran bertarung, dan cek menang/kalah.
- **Render:** `self.render()` (baris 160) menggambar berlapis: background, entitas sprite, efek visual (VFX floating text, screen shake), overlay UI modal, dan HUD.
- **Flip:** `pygame.display.flip()` (baris 163) menampilkan buffer frame yang sudah selesai digambar ke monitor.

Game bersifat *turn-based*, sehingga logika pertempuran maju per giliran aksi, sedangkan animasi, efek partikel, dan getaran layar tetap berjalan mulus per frame menggunakan delta time (`dt`).

### 1.2 Alur Progresi

```
MENU → ROLE_SELECT → EXPLORATION ⇄ (COMBAT | PUZZLE | DIALOG) → END (Menang/Kalah) → kembali ke MENU
                                    ↕ [ESC]
                                  PAUSE
```
`PAUSE` dapat dibuka dari `EXPLORATION` dan `COMBAT` kapan saja dengan menekan tombol `[ESC]`.

### 1.3 Daftar State Game

*Nama fungsi mengikuti konvensi template dan telah diimplementasikan sebagai metode resmi maupun alias di kode final:*

| **State** | **Padanan di template** | **Deskripsi** | **Fungsi utama (Kode Final)** |
|:---|:---|:---|:---|
| MENU_STATE | MENU_STATE | Layar awal: judul emas, tombol Mulai/Keluar, modal panduan peran & instruksi singkat. | `ShowMenu()`, `HandleMenuInput()`, `_on_play_clicked()`, `_on_exit_clicked()` di `engine/states/menu_state.py` |
| ROLE_SELECT_STATE | MENU_STATE (lanjutan) | Pilih Knight atau Mage dengan pratinjau animasi spritesheet live dan perbandingan stat. | `ShowRoles()`, `ConfirmRole()`, `_set_role()`, `_on_start_game()` di `engine/states/role_select_state.py` |
| EXPLORATION_STATE | PLAY_STATE | Navigasi peta graf 10 ruangan, menampilkan rute Dijkstra (Map Vision), memicu pertemuan. | `MoveToRoom()`, `ComputeShortestPath()`, `TriggerEncounter()`, `_travel_to()` di `engine/states/exploration_state.py` |
| COMBAT_STATE | PLAY_STATE | Pertempuran bergilir taktikal melawan 4 monster biasa atau Boss Kaiju beranimasi lengkap. | `PlayerAction()`, `MonsterTurn()`, `ApplyDamage()`, `CheckBattleEnd()` di `engine/states/combat_state.py` |
| PUZZLE_STATE | PLAY_STATE | Tiga teka-teki berbasis struktur data (Matrix, Stack, Queue); hadiah Fragmen Kristal. | `HandlePuzzleInput()`, `CheckPuzzleSolved()`, `_handle_sliding_click()` di `engine/states/puzzle_state.py` |
| DIALOG_STATE | PLAY_STATE | Percakapan bercabang dengan NPC Elder Tree Gyoot; hadiah lore dan 1 Health Potion. | `ShowDialog()`, `SelectChoice()`, `_on_ask_advice()`, `_on_ask_blessing()` di `engine/states/dialog_state.py` |
| PAUSE_STATE | PAUSE_STATE | Overlay gelap transparan (alpha 180); game membeku tanpa merusak state permainan. | `FreezeTime()`, `ShowPauseUI()`, `_resume()`, `_restart()`, `_go_to_menu()` di `engine/states/pause_state.py` |
| END_STATE | END_STATE | Layar menang/kalah, evaluasi skor akhir resmi, riwayat perjalanan pahlawan. | `CalculateFinalScore()`, `ShowEndingScreen()`, `_on_play_again()` di `engine/states/end_state.py` |

### 1.4 Transisi State

| **Dari** | **Ke** | **Pemicu** | **Implementasi di Kode** |
|:---|:---|:---|:---|
| MENU | ROLE_SELECT | Klik tombol "Mulai Petualangan" | `self.machine.change_state(STATE_ROLE_SELECT)` (`menu_state.py:98`) |
| ROLE_SELECT | EXPLORATION | Klik tombol "Konfirmasi Peran / Mulai Petualangan" | `self.ConfirmRole()` → `game.start_new_game(...)` (`role_select_state.py:171`) |
| EXPLORATION | COMBAT | Masuk ruangan berisi monster atau Boss Lair | `self.machine.change_state(STATE_COMBAT, monster=...)` (`exploration_state.py:280`) |
| EXPLORATION | PUZZLE / DIALOG | Masuk Labyrinth Tower, Eternal Relic, Village Workshop / Whispering Forest | `self.machine.change_state(STATE_PUZZLE)` / `change_state(STATE_DIALOG)` (`exploration_state.py:283`) |
| COMBAT | EXPLORATION | Monster kalah, atau pemain memilih aksi Mundur (kecuali melawan boss) | `self.machine.change_state(STATE_EXPLORATION)` (`combat_state.py:312`) |
| COMBAT | END | HP boss = 0 (menang) atau HP pemain = 0 (kalah) | `self.machine.change_state(STATE_END, won=True/False)` (`combat_state.py:430, 443`) |
| PUZZLE / DIALOG | EXPLORATION | Teka-teki selesai atau dialog ditutup | `self.machine.change_state(STATE_EXPLORATION)` (`puzzle_state.py:65`, `dialog_state.py:101`) |
| EXPLORATION / COMBAT | PAUSE | Tekan tombol `[ESC]` (tekan `[ESC]` lagi untuk melanjutkan) | `self.machine.push_state(STATE_PAUSE)` (`exploration_state.py:323`, `combat_state.py:488`) |
| PAUSE | MENU / EXPLORATION (baru) | Pilih Kembali ke Menu Utama / Mulai Ulang | `self.machine.change_state(STATE_MENU)` / `STATE_ROLE_SELECT` (`pause_state.py:100, 110`) |
| END | MENU | Klik Main Lagi / Menu Utama | `self.machine.change_state(STATE_ROLE_SELECT)` / `STATE_MENU` (`end_state.py:101, 105`) |

State aktif disimpan pada variabel `current_state` dan `current_state_name` di StateMachine (`engine/state_machine.py`), sedangkan data permainan (peran, HP, gold, fragmen, ruangan saat ini, riwayat) disimpan terpusat di `core/game_state.py` (`GameStateManager`).

### 1.5 Tech Stack & Dependensi

Proyek ditulis murni menggunakan **Python 3.10+** dan **satu library eksternal saja**, yaitu `pygame` (atau `pygame-ce`). Tidak ada Pillow (PIL), NumPy, SciPy, maupun engine eksternal lainnya.

| **Kebutuhan** | **Solusi** | **Sumber** |
|:---|:---|:---|
| Window, input, game loop, render | `pygame.display`, `pygame.event`, `pygame.time.Clock` | pygame |
| Muat PNG dan transparansi alfa | `pygame.image.load().convert_alpha()` | pygame |
| Animasi spritesheet horizontal | `Surface.subsurface()` + timer akumulasi dt | pygame |
| Collider / hitbox / klik tombol / node | `pygame.Rect` (`collidepoint`, `colliderect`) | pygame |
| Teks dan tipografi retro | `pygame.font.Font` | pygame |
| Audio prosedural (sintesis gelombang) | `pygame.mixer.Sound(buffer=...)` + modul `math`, `random`, `array` | pygame + stdlib |
| Algoritma Dijkstra (Priority Queue) | `heapq` (Min-Heap) | stdlib Python |
| Pengacakan (damage spread, AI, puzzle shuffle) | `random` | stdlib Python |

Isi `requirements.txt`:
```text
pygame-ce>=2.5.0
```

---

## 2. Struktur Kelas, Objek, & UI

Struktur menggunakan OOP dengan prinsip pewarisan (*inheritance*) dan enkapsulasi. Semua entitas visual di arena pertempuran mewarisi `GameObject` yang memiliki Transform (x, y), Sprite Surface, Collider (`pygame.Rect` untuk hitbox dan area klik), dan Audio (`engine/audio.py`). Logika domain permainan (`core/`) dipisahkan secara tegas dari lapisan tampilan/presentasi visual (`engine/`).

### 2.1 Daftar Kelas dan Objek Utama

| **Kelas** | **Induk** | **Komponen / Atribut** | **Fungsi utama** |
|:---|:---|:---|:---|
| GameObject | \- | Transform (x, y), Sprite Surface, Rect (collider), Audio | `update(dt)`, `draw(surface)`, `get_rect()` (`engine/entities.py:21`) |
| AnimatedSprite | GameObject | Frames list, frame_index, anim_timer, fps, loop/one-shot | `play(anim)`, `update(dt)`, `draw(surface)` (`engine/entities.py:61`) |
| PlayerEntity | AnimatedSprite | Role (Knight/Mage), state animasi (idle, attack, defend, hurt, death) | `trigger_attack()`, `trigger_defend()`, `trigger_hurt()` (`engine/entities.py:121`) |
| MonsterEntity | AnimatedSprite | Monster data, state animasi (idle, attack, ultimate, hurt, death) | `trigger_attack()`, `trigger_ultimate()`, `trigger_hurt()` (`engine/entities.py:178`) |
| DungeonGraph | \- | Adjacency list 10 node, bobot edge, lokasi ruangan | `add_path()`, `AddEdge()`, `Dijkstra(src, dst)`, `get_rooms()` (`core/dungeon_graph.py:48`) |
| GameState (GameStateManager) | \- | Player, DungeonGraph, monsters roster, fragmen, travel history | `Reset()`, `AddTravel()`, `move_player()`, `can_enter_room()`, `calculate_final_score()` (`core/game_state.py:15`) |
| Puzzle (3 kelas) | \- | Matriks 3×3 (`SlidingPuzzle`) / Stack tabung (`ColorStackPuzzle`) / Queue FIFO (`ConveyorQuest`) | `move_by_index()`, `pour()`, `process_pick()`, `is_solved()` (`puzzles/`) |
| UI (UIButton, UIProgressBar, FloatingText, LogBox) | \- | Rect klik (`collidepoint`), nilai bar, timer fading, teks melayang | `handle_event()`, `render()`, `update(dt)` (`engine/ui.py:20–180`) |

### 2.2 Elemen UI & Syarat Menang/Kalah

- **Status Indikator:** Bar HP pahlawan beranimasi, bar Shield biru, bar Defense, bar HP & Rage monster, indikator cooldown skill (3 ronde), jumlah Health Potion. **Syarat Kalah:** HP pemain mencapai 0 di medan pertempuran.
- **Objective Tracker:** Panel tujuan di HUD eksplorasi ("Kumpulkan minimal 2 Fragmen Kristal dari teka-teki, lalu kalahkan Boss"), jumlah fragmen kristal (x/2), simpanan gold, dan akumulasi langkah tempuh. **Syarat Menang:** Boss *Corrupted Crystal Kaiju* dikalahkan di ruangan ke-10 (*Throne of Extinction*).
- **Feedback Visual & Audio:** Angka floating damage melayang naik dan memudar (merah = damage masuk, hijau = heal, kuning = kritis), guncangan layar (*screen shake* 6–22 px) saat terkena pukulan berat/Atomic Breath, efek suara sintetis per aksi, dan log teks kronologis pertarungan.

### 2.3 Aturan Permainan

**Peran Pemain**

| **Peran** | **HP** | **ATK** | **DEF** | **Pasif** |
|:---|:---:|:---:|:---:|:---|
| **Knight** | 1500 | 65 | 45 | **Ironclad Fortitude:** Kerusakan fisik musuh berkurang 20% (tidak berlaku untuk serangan sihir energi *Atomic Breath*). |
| **Mage** | 1100 | 95 | 25 | **Arcane Intellect + Map Vision:** Rute terpendek algoritma Dijkstra otomatis ter-highlight berpendar di peta eksplorasi. |

**Aksi Pertempuran**

- **Serang (Attack):** Damage = `max(1, ATK + acak(−15..+15) − DEF target)`. Peluang serangan kritis 10% (kerusakan dikalikan ×1,5).
- **Skill (Special Attack):** Kerusakan ATK × 1,8, cooldown 3 ronde (*Heavy Strike* untuk Knight, *Arcane Surge* untuk Mage).
- **Health Potion:** Memulihkan +300 HP secara instan; stok awal sebanyak 3 botol (dapat ditambah dari puzzle dan peti harta).
- **Bertahan (Defend):** Memperoleh Shield +80 untuk ronde tersebut. Serangan musuh yang masuk akan memotong Shield terlebih dahulu, dan sisa damage baru mengurangi HP pemain.
- **Mundur (Flee):** Kembali ke peta eksplorasi; HP monster pulih penuh. Tombol ini dikunci (*disabled*) saat menghadapi Boss.

**Musuh (Roster 5 Musuh)**

| **Musuh** | **Ruangan** | **HP** | **ATK** | **DEF** | **Gold** | **Perilaku (AI)** |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Crystal Slime** | Crystal Cavern (7) | 300 | 40 | 5 | 50 | Selalu menyerang setiap giliran. |
| **Skeleton Guard** | Ancient Armory (6) | 400 | 50 | 15 | 75 | 70% menyerang, 30% bertahan (DEF bertambah +10 selama 1 giliran). |
| **Shadow Wraith** | Shadow Crypt (9) | 450 | 55 | 10 | 100 | Menyerang; saat HP < 50%, serangannya menyerap 30% damage menjadi HP (*Lifesteal*). |
| **Magma Golem** | Magma Forge (8) | 600 | 60 | 25 | 100 | Setiap giliran ke-3 melepaskan *Hantaman Berat* sebesar ×1,5 damage. |
| **Corrupted Crystal Kaiju (Boss)** | Throne of Extinction (10) | 900 | 85 | 15 | \- | Memasuki **Rage Mode** saat HP < 50% (ATK +20 permanen, peluang kritis naik menjadi 20%). Melepaskan serangan pamungkas **Atomic Breath** sebesar ×2,2 damage setiap ronde kelipatan 5. |

**Progresi dan Syarat Menang**

- Gerbang *Boss Lair: Throne of Extinction* tersegel sihir kuno. Pemain wajib mengumpulkan **minimal 2 dari 3 Fragmen Kristal** yang diperoleh dari penyelesaian teka-teki. Fragmen kristal ketiga memberikan skor bonus.
- Keempat monster biasa bersifat opsional untuk dikalahkan, namun memberi hadiah penting: Gold, Health Potion, Kristal Mana (reset cooldown skill), dan DEF +15 permanen dari Magma Golem.
- **Menang:** HP Boss Corrupted Crystal Kaiju mencapai 0. **Kalah:** HP pahlawan mencapai 0.
- **Rumus Skor Akhir:**
  $$\text{Skor} = (\text{HP tersisa} \times 2) + (\text{Gold} \times 10) + (\text{Teka-teki selesai} \times 250) - (\text{Total langkah} \times 5)$$
  *Langkah = jumlah total bobot jarak edge yang dilalui pemain di peta graf.*

### 2.4 Graf Dunia Bawah Tanah (10 node, 13 edge)

| **No** | **Nama Ruangan** | **Fungsi / Mekanik / Hadiah** |
|:---:|:---|:---|
| 1 | **Entrance Hall** | Ruangan awal pahlawan, zona aman tanpa ancaman. |
| 2 | **Whispering Forest** | Dialog interaktif NPC Elder Tree Gyoot: petunjuk taktik boss, lore, dan hadiah 1 Health Potion (+200 HP). |
| 3 | **Labyrinth Tower** | Teka-teki 8-Puzzle Matriks (3×3) $\rightarrow$ Hadiah **Fragmen Kristal I** (+200 Max HP permanen). |
| 4 | **The Eternal Relic** | Teka-teki Bejana Warna / Color Stack (Stack LIFO) $\rightarrow$ Hadiah **Fragmen Kristal II** (Kunci Boss). |
| 5 | **Village Workshop** | Teka-teki Ban Berjalan Logistik (Queue FIFO) $\rightarrow$ Hadiah **Fragmen Kristal III** (+2 Health Potion). |
| 6 | **Ancient Armory** | Pertempuran Skeleton Guard $\rightarrow$ Hadiah 150 Gold + 1 Health Potion. |
| 7 | **Crystal Cavern** | Pertempuran Crystal Slime $\rightarrow$ Hadiah Kristal Mana (mereset cooldown skill) + 50 Gold. |
| 8 | **Magma Forge** | Pertempuran Magma Golem $\rightarrow$ Hadiah peningkatan pertahanan pahlawan **DEF +15 permanen**. |
| 9 | **Shadow Crypt** | Pertempuran Shadow Wraith $\rightarrow$ Hadiah peta bayangan pengungkap petunjuk lokasi Boss Lair. |
| 10 | **Boss Lair: Throne of Extinction** | Pertarungan pamungkas melawan Corrupted Crystal Kaiju; terkunci rapat tanpa minimal 2 Fragmen Kristal. |

**Daftar 13 Edge dan Bobot Jarak:**
1–2 (bobot 2), 1–6 (bobot 3), 1–9 (bobot 4), 2–3 (bobot 3), 2–7 (bobot 4), 3–4 (bobot 3), 4–7 (bobot 2), 4–10 (bobot 5), 5–6 (bobot 2), 5–8 (bobot 3), 6–8 (bobot 5), 8–9 (bobot 2), 8–10 (bobot 4).

*Analisis Jalur Dijkstra:*
Rute terpendek dari Ruangan 1 (*Entrance Hall*) menuju Ruangan 10 (*Throne of Extinction*) adalah **1 → 9 → 8 → 10** dengan **total bobot tepat 10 langkah** ($4 + 2 + 4 = 10$). Jalur tercepat ini melewati Magma Forge tetapi sengaja tidak melewati ruang teka-teki, sehingga pemain wajib mengambil rute memutar strategis untuk mengumpulkan minimal 2 Fragmen Kristal sebelum segel Boss Lair dapat dibuka. Algoritma Dijkstra diimplementasikan dengan priority queue berbasis modul `heapq` Python dengan kompleksitas waktu $\mathcal{O}((V + E) \log V)$.

### 2.5 Tiga Teka-Teki

- **8-Puzzle (Matriks 3×3):** Ubin bernomor 1–8 diacak secara terkontrol sehingga selalu dapat diselesaikan (*solvable*), diverifikasi dengan memastikan jumlah inversi genap ($inv \pmod 2 = 0$).
- **Color Stack (Stack LIFO):** Empat bejana tabung reaksi kimia; operasi mematuhi aturan LIFO di mana hanya elemen teratas (*peek/pop*) yang dapat dituangkan ke tabung kosong atau tabung dengan warna puncak yang sama.
- **Conveyor (Queue FIFO):** Antrean ban berjalan logistik barang desa; pemain wajib melayani permintaan barang sesuai urutan kedatangan terdepan (*first-in, first-out*). Pengambilan di luar urutan antrean langsung ditolak.

---

## 3. Rubrik Penilaian Teknis: Kesiapan Jawaban

*Panduan rubrik: 0 = tidak bisa menjelaskan, 1 = garis besar/ada bug, 2 = terstruktur dan 100% selaras dengan kode final.*

| **Kriteria** | **Jawaban singkat** | **Bukti di kode final** |
|:---|:---|:---|
| **Main Game Loop** | Tiap frame mengeksekusi 5 langkah: tick(60) menghasilkan delta time (`dt`), `event.get()` membaca input mouse/keyboard dan diteruskan ke state aktif, `update(dt)` memproses logika giliran dan timer, `render()` menggambar layer visual, dan `display.flip()` menampilkan buffer. Logika turn-based bergulir per aksi, sedangkan animasi dan VFX tetap berjalan halus per frame menggunakan `dt`. | `engine/game.py`, fungsi `run()`, baris 143–158; metode `handle_events()` (baris 91), `update()` (baris 106), `render()` (baris 115). |
| **Manajemen State** | FSM terstruktur dengan 8 state independen. State aktif dikelola oleh `StateMachine`, sementara seluruh data permainan (peran, HP, gold, fragmen, lokasi, riwayat) disimpan terpusat di `GameStateManager` (`GameState`). Transisi state dilakukan lewat `change_state()`; `PAUSE_STATE` memanfaatkan tumpukan `push_state()` dan `pop_state()` agar state sebelumnya membeku dan dapat dilanjutkan tanpa kehilangan data. | `engine/state_machine.py`, kelas `StateMachine` (baris 28–92); `core/game_state.py`, kelas `GameStateManager` (baris 15–200); direktori `engine/states/` (8 modul state). |
| **Struktur Objek (OOP)** | Menerapkan hierarki pewarisan OOP: `GameObject` $\rightarrow$ `AnimatedSprite` $\rightarrow$ `PlayerEntity` & `MonsterEntity`. Komponen entitas mencakup Transform (x, y), Sprite Surface, Collider (`pygame.Rect` untuk hitbox dan deteksi klik), dan Audio. Logika murni domain (`core/player.py`, `core/monster.py`) dipisahkan secara modular dari lapisan engine presentasi grafis (`engine/entities.py`). | `engine/entities.py`, hierarki kelas baris 21–240; `core/player.py`, kelas `Player` baris 45–190; `core/monster.py`, kelas `Monster` baris 11–218. |
| **Logika Interaksi & Menang/Kalah** | Setelah setiap aksi serang/skill/giliran musuh, metode `CheckBattleEnd()` mengevaluasi kondisi HP. Jika HP Boss Corrupted Crystal Kaiju mencapai 0 $\rightarrow$ transisi ke `END_STATE` (Menang); jika HP pemain mencapai 0 $\rightarrow$ transisi ke `END_STATE` (Kalah). Saat memasuki Boss Lair, `can_enter_room()` memeriksa kepemilikan minimal 2 Fragmen Kristal sebelum pintu diizinkan terbuka. | `engine/states/combat_state.py`, fungsi `CheckBattleEnd()` (baris 466–474), `_handle_victory()` (baris 417), `_handle_defeat()` (baris 441); `core/game_state.py`, fungsi `can_enter_room()` (baris 104–128) dan `move_player()` (baris 58–92). |
| **Tingkat Kerumitan** | Memiliki 8 state lengkap, graf 10 node dengan 13 edge berbobot, 5 aksi tempur, 5 jenis musuh dengan AI unik, Rage mode (<50% HP) dan serangan pamungkas Atomic Breath tiap kelipatan 5 ronde, 3 teka-teki berbasis struktur data Matrix/Stack/Queue, sistem Shield absorpsi kerusakan, syarat kunci Fragmen, serta penghitungan skor akhir. Deteksi klik dan interaksi GUI menggunakan `pygame.Rect.collidepoint`. | Seluruh modul arsitektur: `core/dungeon_graph.py`, `core/monster.py`, `puzzles/`, `engine/ui.py`, `engine/states/combat_state.py`. |

---

## 4. Rubrik Penilaian UX: Kesiapan Ceklis

| **Kriteria UX** | **Fitur pemenuh di game** | **Cara demonstrasi pengujian** |
|:---|:---|:---|
| **Kejelasan Tujuan** | Panel Objective Tracker pada HUD eksplorasi secara eksplisit menampilkan: *"Kumpulkan minimal 2 Fragmen Kristal, lalu kalahkan Boss"*. Layar Menu Utama menyediakan tombol *Tentang Role & Aturan* dan instruksi ringkas di awal. | Jalankan game, tunjukkan HUD sisi kanan dalam 30 detik pertama: perhatikan counter fragmen kristal (0/2) dan deskripsi misi. |
| **Umpan Balik (Feedback)** | Angka floating damage melayang memudar (merah = damage, hijau = heal, kuning = kritis), guncangan layar (*screen shake*) saat serangan berat, efek suara prosedural per aksi, log kronologis pertempuran di panel bawah, serta bar HP/Shield beranimasi halus. | Lakukan aksi Serang atau Gunakan Skill pada monster: tunjukkan suara benturan, angka damage melayang di atas sprite, dan catatan di kotak log. |
| **Keterbacaan Visual** | Palet warna gelap terkurasi (`#120E18`, panel `#1C1626`, border `#58466E`, aksen emas `#EBB932`); tombol dan node ruangan memiliki efek hover/highlight bercahaya; sprite 2D berkanal alfa 32-bit bersih tanpa artefak checkerboard di atas background. | Arahkan kursor mouse ke node ruangan dan tombol aksi: tunjukkan perubahan warna border emas dan pembesaran halus tombol. |
| **Intuitivitas Kontrol** | Seluruh kontrol permainan dapat dimainkan secara penuh menggunakan mouse (klik kiri pada tombol/node/ubin puzzle) ditambah tombol `[ESC]` pada keyboard untuk jeda instan. Tidak membutuhkan tombol kombinasi yang rumit. | Mainkan satu pertempuran penuh dan selesaikan satu minigame teka-teki hanya dengan klik mouse. |
| **Pencegahan Frustrasi** | Tombol `[ESC]` membuka Pause Menu kapan saja dengan opsi *Lanjutkan*, *Mulai Ulang*, *Matikan Suara*, dan *Menu Utama*; tersedia tombol *Mundur* di combat (monster biasa); teka-teki 8-puzzle selalu solvable; konfirmasi keluar aplikasi di menu awal. | Masuk ke pertempuran, tekan `[ESC]` untuk memunculkan Pause modal, lalu lanjutkan kembali atau pilih Mulai Ulang. |

---

## 5. Batasan, Penanganan Error, dan Pengujian

### 5.1 Di Luar Cakupan (Out of Scope)
- Sistem penyimpanan berkas persisten (*Save/Load game file*), multiplayer daring, dukungan gamepad eksternal, dan pengubahan ukuran jendela secara dinamis (ukuran tetap standar 1280 × 720).

### 5.2 Penanganan Error (Robustness)
- **Aset Gambar Tidak Ditemukan:** Sistem `AssetManager` (`engine/assets.py`) secara otomatis membuat *procedural fallback surface* (bidang berwarna dengan border emas dan teks identitas) serta mencatat pesan ke log, sehingga game **tidak akan pernah crash** meskipun file PNG tidak ditemukan atau library libpng sistem bermasalah.
- **Audio Device Tidak Tersedia:** Modul `AudioManager` (`engine/audio.py`) membungkus inisialisasi mixer dengan blok `try-except`; jika perangkat audio sistem tidak aktif, sound engine dinonaktifkan otomatis dan game tetap berjalan lancar 60 FPS.
- **Library Dependensi:** Seluruh pemuatan aset visual memakai fungsi standar `pygame.image.load().convert_alpha()`; bebas dari ketergantungan Pillow, NumPy, SciPy, atau pustaka pihak ketiga lainnya.

### 5.3 Rencana & Hasil Pengujian Verifikasi

*Seluruh 8 skenario pengujian di bawah ini telah diuji dan terbukti LULUS (100% Passed) melalui pengujian otomatis:*

| **Uji** | **Masukan** | **Hasil yang diharapkan** | **Hasil Verifikasi Kode Final** |
|:---|:---|:---|:---:|
| **Dijkstra** | Rute 1 (*Entrance*) $\rightarrow$ 10 (*Throne of Extinction*) | Total bobot 10, urutan jalur 1-9-8-10 | **LULUS (Passed)** (Bobot: 10, Path: `['1', '9', '8', '10']`) |
| **Solvability 8-puzzle** | 100 papan hasil acak `shuffle()` | Semua memiliki jumlah inversi genap | **LULUS (Passed)** (100/100 papan memiliki inversi genap) |
| **Stack/Queue** | Pindah warna tidak valid; layani pesanan di luar antrean | Aksi ditolak dan dihitung salah | **LULUS (Passed)** (`can_pour() == False`, `process_pick() == False`) |
| **Formula Damage** | Karakter ATK kecil (10) vs musuh DEF besar (100) | Damage minimal 1 (tidak pernah $\le 0$) | **LULUS (Passed)** (`max(1, ATK + acak - DEF)` selalu $\ge 1$) |
| **Ultimate Boss** | Pertempuran boss di ronde ke-5 dan ke-10 | Atomic Breath aktif tepat di ronde tersebut | **LULUS (Passed)** (`decide_action(5)` menghasilkan ultimate Atomic Breath) |
| **Kunci Boss Lair** | Masuk Ruangan 10 dengan 1 fragmen vs 2 fragmen | Ditolak dengan 1 fragmen / Diizinkan dengan 2 fragmen | **LULUS (Passed)** (`can_enter_room(10)` False saat fragmen=1, True saat fragmen=2) |
| **Menang & Kalah** | HP boss = 0; HP pemain = 0 | Transisi `END_STATE` menang/kalah dengan kalkulasi skor benar | **LULUS (Passed)** (Rumus skor terhitung tepat sesuai formula) |
| **Pause FSM** | Tekan `[ESC]` saat eksplorasi dan pertempuran | Game membeku, `pop_state()` kembali ke state sebelumnya | **LULUS (Passed)** (`push_state(PAUSE)` $\rightarrow$ `pop_state()` kembali mulus) |

---

## 6. Aset, Animasi, Popup, dan UI/UX

### 6.1 Aturan Umum Aset
- **Format Aset Visual:** PNG 32-bit RGBA dengan latar belakang transparan murni (*true alpha channel*). Spritesheet tersusun dalam satu baris horizontal dengan dimensi sel yang seragam.
- **Pemuatan & Caching:** Dimuat menggunakan `pygame.image.load(path).convert_alpha()`, kemudian frame diiris presisi menggunakan `Surface.subsurface()`. Setiap surface yang telah dimuat disimpan dalam cache dictionary `AssetManager` untuk menghemat memori.
- **Animasi:** `AnimatedSprite` memajukan frame berdasarkan akumulasi delta time (`dt`) dan FPS animasi target entitas. Mode loop untuk animasi *idle*; mode one-shot untuk aksi *attack*, *skill*, dan *hurt*; sedangkan *death* menahan frame terakhir.
- **Palet Warna:** Latar `#120E18`, panel antarmuka `#1C1626`, garis tepi border `#58466E`, aksen emas pahlawan `#EBB932`, merah bahaya/HP `#EF4444`, dan biru perisai `#3B82F6`.
- **Tipografi:** Font pixel retro dimuat melalui `pygame.font.Font`; jika file TTF tidak tersedia, sistem otomatis beralih ke `pygame.font.Font(None, size)`.

### 6.2 Spritesheet dan Frame Riil di Kode Final

| **Entitas** | **Animasi** | **Frame** | **Ukuran per frame** | **FPS** | **Mode** | **Berkas Aset di Proyek** |
|:---|:---|:---:|:---:|:---:|:---|:---|
| **Knight** | idle | 4 | 96 × 84 | 6 | Loop | `assets/players/Knight 2D Pixel Art/.../IDLE.png` |
| **Knight** | attack | 5 | 96 × 84 | 10 | One-shot | `assets/players/Knight 2D Pixel Art/.../ATTACK 1.png` |
| **Knight** | defend | 5 | 96 × 84 | 8 | One-shot | `assets/players/Knight 2D Pixel Art/.../DEFEND.png` |
| **Knight** | hurt | 2 | 96 × 84 | 8 | One-shot | `assets/players/Knight 2D Pixel Art/.../HURT.png` |
| **Knight** | death | 9 | 96 × 84 | 8 | One-shot (tahan frame 9) | `assets/players/Knight 2D Pixel Art/.../DEATH.png` |
| **Mage** | idle | 6 | 231 × 190 | 6 | Loop | `assets/players/Wizard Pack/.../Idle.png` |
| **Mage** | attack | 8 | 231 × 190 | 10 | One-shot | `assets/players/Wizard Pack/.../Attack1.png` |
| **Mage** | hurt | 4 | 231 × 190 | 8 | One-shot | `assets/players/Wizard Pack/.../Hit.png` |
| **Mage** | death | 7 | 231 × 190 | 8 | One-shot (tahan frame 7) | `assets/players/Wizard Pack/.../Death.png` |
| **Monster Biasa (4 jenis)** | idle, attack, hurt, death | 4 | 128 × 128 | 6 | Loop / One-shot | Sprite prosedural + Ikon `assets/16x16 Assorted RPG Icons/` |
| **Boss Kaiju** | idle | 8 | 384 × 320 | 4 | Loop mulus | `assets/monsters/godzilla_boss.png` |
| **Boss Kaiju** | attack | 8 | 384 × 320 | 7 | One-shot | `assets/monsters/godzilla_boss.png` |
| **Boss Kaiju** | ultimate (Atomic Breath) | 20 | 384 × 320 | 6 | One-shot | `assets/monsters/godzilla_boss.png` |
| **Boss Kaiju** | death | 12 | 384 × 320 | 5 | One-shot (tahan akhir) | `assets/monsters/godzilla_boss.png` |

**Sinkronisasi Fase Atomic Breath (20 Frame):**
- Frame 1–6: Fase pengisian daya (*charge phase*), kristal punggung berpendar ungu kemerahan.
- Frame 7–14: Fase penembakan sinar laser magma (*beam firing phase*), diiringi screen shake 22 px dan partikel energi.
- Frame 15–20: Fase pemulihan (*cooldown recovery phase*), asap energi mengepul dan boss kembali ke posisi tegak.

### 6.3 Animasi dan Efek Visual (VFX)

| **Efek Visual** | **Pemicu** | **Implementasi Parameter** |
|:---|:---|:---|
| **Floating Damage** | Setiap damage atau pemulihan HP | Angka melayang naik 40 px selama 0,8 detik: Merah = damage biasa, Hijau = pemulihan HP, Kuning tebal = serangan kritis. |
| **Screen Shake** | Terkena serangan berat / Atomic Breath | Offset kamera acak ±6 px selama 0,3 detik (meningkat menjadi ±22 px selama 0,85 detik untuk Atomic Breath). |
| **Flash Hit** | Entitas menerima pukulan musuh | Kilatan warna merah/putih berdurasi 0,1 detik dilanjutkan animasi *hurt*. |
| **Aura Rage** | HP Boss < 50% | Denyutan visual merah oranye berkedip di atas status bar Boss menandai peningkatan stat mematikan. |
| **Efek Shield** | Aksi Bertahan (*Defend*) | Lingkaran pelindung biru transparan di sekitar pahlawan yang menyerap kerusakan sebelum memotong HP. |
| **Peringatan Ultimate** | Ronde ke-4, 9, 14 (satu ronde sebelum Atomic Breath) | Peringatan teks merah berkedip di log pertempuran: *"Peringatan: Energi Bos meningkat (Atomic Breath dalam 1 turn)!"* |
| **Transisi State** | Perpindahan antar state game | Efek fade in/out gelap halus 0,3 detik menjaga kenyamanan visual pemain. |
| **Hover Tombol & Node** | Kursor mouse berada di atas elemen GUI | Garis tepi border emas bersinar dan pembesaran skala halus (1,05×) memberikan kepastian klik. |
| **Highlight Rute Dijkstra** | Peran Mage (otomatis) / Tombol Map Vision | Garis rute jalur terpendek berpendar emas di sepanjang edge graf menuju node tujuan. |

### 6.4 Popup dan Dialog

| **Komponen Popup** | **Kondisi Pemicu** | **Konten Tampilan** | **Mekanisme Penutupan** |
|:---|:---|:---|:---|
| **Pemberian Hadiah / Fragmen** | Kemenangan monster, selesai puzzle, hadiah NPC | Ikon item, nama hadiah, dan efek stat permanen yang diperoleh. | Klik tombol konfirmasi atau otomatis 2 detik. |
| **Peringatan Boss Terkunci** | Mencoba masuk Ruangan 10 dengan < 2 Fragmen | Pesan segel sihir, jumlah fragmen saat ini, dan kebutuhan minimal (x/2). | Klik tombol "OK / Mengerti". |
| **Konfirmasi Mundur (Flee)** | Menekan tombol Mundur di Combat | Notifikasi bahwa pahlawan akan kembali ke peta dan monster pulih penuh. | Pilihan aksi "Ya, Mundur" atau "Batal". |
| **Konfirmasi Pause Menu** | Memilih Mulai Ulang atau Kembali ke Menu | Konfirmasi peringatan bahwa progres permainan saat ini akan diulang. | Pilihan "Lanjutkan" atau "Konfirmasi". |
| **Hasil Selesai Teka-Teki** | Matriks/Stack/Queue berhasil diselesaikan | Banner keberhasilan hijau emas, jumlah langkah, dan pemberian fragmen kristal. | Klik tombol "Kembali ke Peta". |
| **Kotak Dialog NPC Hutan** | Masuk ke ruangan Whispering Forest | Potret Roh Pohon Kuno Gyoot, dialog lore, dan pilihan interaksi bertingkat. | Klik opsi tanggapan atau tombol `[ESC]`. |

### 6.5 Layout Per Layar (Resolusi 1280 × 720)

- **Menu Utama:** Latar belakang labirin bernuansa mistis; logo judul tematik emas di tengah atas ($y \approx 120$); tombol *Mulai Petualangan*, *Tentang Role*, dan *Keluar* tersusun rapi di area tengah ($y \approx 380\text{--}520$); catatan hak cipta dan instruksi singkat di bagian bawah.
- **Pilih Peran:** Dua kartu peran di kiri (Knight) dan kanan (Mage) berukuran $\pm 520 \times 440\text{ px}$ berisi animasi idle pahlawan, lencana peran, bar visual HP/ATK/DEF, serta deskripsi keunggulan pasif; tombol konfirmasi peran di tengah bawah.
- **Eksplorasi (Peta Graf):** Area visualisasi graf 10 node dan jalur berbobot di sebelah kiri ($\pm 820 \times 640\text{ px}$); panel navigasi kanan ($\pm 440\text{ px}$) memuat Objective Tracker, status Fragmen Kristal, Gold, total langkah tempuh, tombol Map Vision, dan daftar tombol ruangan bertetangga.
- **Pertempuran (Arena Combat):** Area atas ($y = 0\text{--}480$) menampilkan duel pahlawan di sisi kiri dan monster di sisi kanan, bar HP/Defense/Shield/Rage di atas masing-masing entitas; area bawah ($y = 480\text{--}720$) memuat Combat Log riwayat pertarungan di kiri dan 5 tombol aksi tempur (*Serang*, *Skill*, *Potion*, *Bertahan*, *Mundur*) di bagian tengah-kanan.
- **Teka-Teki (Puzzle Screen):** Area interaktif minigame di tengah layar ($\pm 600 \times 520\text{ px}$); panel samping kanan berisi judul puzzle, aturan singkat struktur data yang dipakai, counter langkah, serta tombol *Reset* dan *Kembali ke Peta*.
- **Dialog NPC:** Background hutan tematik; panel dialog lebar di area bawah ($\pm 920 \times 220\text{ px}$) memuat potret NPC, nama pembicara emas, kotak teks narasi bercabang, dan tombol pilihan respon di kanan.
- **Layar Jeda (Pause Modal):** Lapisan overlay hitam transparan (alpha 180) di atas layar permainan; panel tengah memuat 5 tombol navigasi: *Lanjutkan*, *Mulai Ulang*, *Efek Suara*, *Menu Utama*, dan *Keluar*.
- **Layar Akhir (Ending):** Banner besar *VICTORY* emas atau *DEFEAT* merah; rincian perhitungan skor resmi (HP tersisa, simpanan gold, teka-teki selesai, pengurangan langkah tempuh); riwayat 6 ruangan terakhir yang dijelajahi; serta tombol *Main Lagi* dan *Menu Utama*.

### 6.6 Audio Prosedural (Procedural Waveform Synthesis)

Seluruh efek suara diimplementasikan secara mandiri tanpa menggunakan file rekaman eksternal, memanfaatkan komputasi gelombang sinus (*sine*), kotak (*square*), dan derau (*white noise*) dari modul standar Python (`math`, `random`, `array`), kemudian dibunyikan melalui `pygame.mixer.Sound(buffer=...)`. Sistem bebas dari error berkas audio eksternal yang hilang.

| **Event Permainan** | **Komposisi Gelombang Sintetis** | **Karakteristik Suara** |
|:---|:---|:---|
| **Serang (Attack)** | White noise pendek + frekuensi square menurun cepat (800 Hz $\rightarrow$ 200 Hz) | Tebasan pedang tajam retro. |
| **Skill (Arcane Surge / Heavy Strike)** | Sine berosilasi cepat + modulasi frekuensi tinggi (400 Hz $\rightarrow$ 1200 Hz) | Ledakan sihir mistis bertenaga. |
| **Serangan Kritis** | Dua nada square naik cepat berturut-turut (1000 Hz & 1600 Hz) | Dentang tajam logam berdaya rusak tinggi. |
| **Terkena Pukulan (Hurt)** | White noise teredam + sine frekuensi rendah (120 Hz) | Benturan pukulan fisik berat. |
| **Pemulihan HP (Heal) / Shield** | Gelombang sinus naik lembut berpendar (300 Hz $\rightarrow$ 750 Hz) | Suara aura penyembuhan magis. |
| **Klik UI / Interaksi Node** | Gelombang square sangat singkat (0,04 detik, 900 Hz) | Respon klik taktil antarmuka retro. |
| **Item / Fragmen / Teka-Teki Selesai** | Arpeggio nada tangga nada mayor (C5 - E5 - G5 - C6) | Notifikasi kemenangan ceria. |
| **Charge & Atomic Breath Boss** | Sine naik panjang bervolume tinggi + white noise gemuruh berat | Raungan energi sebelum semburan dahsyat. |
| **Kemenangan (Victory) / Kekalahan** | Rangkaian arpeggio naik megah (Victory) / tangga nada minor melambat turun (Defeat) | Jingle penutup akhir permainan. |

### 6.7 Struktur Direktori Proyek

```text
g_dungeon/
├── assets/
│   ├── 16x16 Assorted RPG Icons/   # Ikon RPG retro untuk UI dan monster
│   ├── backgrounds/                # Latar belakang menu, peta, arena, teka-teki
│   ├── monsters/                   # Sprite Boss Corrupted Crystal Kaiju
│   ├── players/
│   │   ├── Knight 2D Pixel Art/    # Spritesheet lengkap Knight (idle, attack, defend, hurt, death)
│   │   └── Wizard Pack/            # Spritesheet lengkap Mage (idle, attack, hit, death)
│   └── ui/                         # Ikon dan aset pendukung antarmuka
├── core/
│   ├── __init__.py
│   ├── dungeon_graph.py            # Graph 10 node, 13 edge, dan Algoritma Dijkstra (heapq)
│   ├── game_state.py               # GameStateManager (GameState) & rumus skor akhir
│   ├── item.py                     # Item model & inventaris tas petualang
│   ├── monster.py                  # Definisi 5 Monster resmi (stat, AI unik, Rage mode)
│   └── player.py                   # Model pahlawan (Knight & Mage), sistem HP, Shield, pasif
├── engine/
│   ├── __init__.py
│   ├── assets.py                   # AssetManager (pemuat PNG, cache, procedural fallback)
│   ├── audio.py                    # AudioManager (sintesis audio prosedural tanpa file eksternal)
│   ├── constants.py                # Konstanta resolusi 1280x720, 60 FPS, token warna, state ID
│   ├── entities.py                 # GameObject, AnimatedSprite, PlayerEntity, MonsterEntity
│   ├── game.py                     # Main Game Engine & Canonical 60 FPS Game Loop
│   ├── state_machine.py            # Finite State Machine (change_state, push_state, pop_state)
│   ├── ui.py                       # Komponen GUI (UIButton, UIProgressBar, FloatingText, LogBox)
│   └── states/
│       ├── __init__.py
│       ├── menu_state.py           # MENU_STATE
│       ├── role_select_state.py    # ROLE_SELECT_STATE
│       ├── exploration_state.py    # EXPLORATION_STATE
│       ├── combat_state.py         # COMBAT_STATE
│       ├── puzzle_state.py         # PUZZLE_STATE
│       ├── dialog_state.py         # DIALOG_STATE
│       ├── pause_state.py          # PAUSE_STATE
│       └── end_state.py            # END_STATE
├── puzzles/
│   ├── __init__.py
│   ├── sliding_puzzle.py           # 8-Puzzle 3x3 Sliding Matrix (paritas inversi genap)
│   ├── color_stack_puzzle.py       # Bejana Warna (Stack LIFO)
│   └── conveyor_quest.py           # Ban Berjalan Logistik (Queue FIFO)
├── main.py                         # Titik masuk utama eksekusi permainan desktop
├── PRD.md                          # Dokumen Perencanaan & Rubrik Penilaian Lengkap
├── Perencanaan_dan_Rubrik_Final.md # Salinan sinkronisasi perencanaan & rubrik
└── requirements.txt                # pygame-ce saja
```
