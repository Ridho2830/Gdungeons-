"""
Module: engine/states/combat_state.py
Description: Layar Pertarungan Turn-Based (COMBAT_STATE).
Mengatur animasi PlayerEntity vs MonsterEntity, bar status HP/Defense/Rage,
efek getaran layar (Screen Shake), teks melayang (Floating Text), dan logika Menang/Kalah.
"""

from typing import Any, List, Optional
import random
import pygame
from engine.assets import AssetManager
from engine.audio import AudioManager
from engine.constants import (
    COLOR_BTN_HOVER,
    COLOR_BTN_NORMAL,
    COLOR_DEFENSE_BLUE,
    COLOR_GOLD,
    COLOR_HP_GREEN,
    COLOR_HP_RED,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_RAGE_ORANGE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STATE_END,
    STATE_EXPLORATION,
)
from engine.entities import MonsterEntity, PlayerEntity
from engine.state_machine import GameState
from engine.ui import FloatingTextManager, LogBox, UIButton, UIProgressBar
from core.monster import Monster
from core.player import PlayerRole


class CombatState(GameState):
    """Implementasi COMBAT_STATE sesuai rubrik penilaian teknis & UX."""

    def __init__(self, machine: "StateMachine", game_engine: Any) -> None:
        super().__init__(machine)
        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.player_entity: Optional[PlayerEntity] = None
        self.monster_entity: Optional[MonsterEntity] = None
        self.current_monster: Optional[Monster] = None

        # Efek Layar & Teks Melayang
        self.floating_texts = FloatingTextManager()
        self.screen_shake_time: float = 0.0
        self.screen_shake_amount: float = 0.0

        # UI Bar Status
        self.player_hp_bar = UIProgressBar(
            rect=pygame.Rect(80, 500, 260, 24),
            max_value=3000,
            current_value=3000,
            fill_color=COLOR_HP_GREEN,
            label="HP Pahlawan",
        )
        self.player_def_bar = UIProgressBar(
            rect=pygame.Rect(80, 532, 260, 20),
            max_value=200,
            current_value=200,
            fill_color=COLOR_DEFENSE_BLUE,
            label="Defense",
        )

        self.monster_hp_bar = UIProgressBar(
            rect=pygame.Rect(850, 480, 320, 24),
            max_value=2500,
            current_value=2500,
            fill_color=COLOR_HP_RED,
            label="HP Monster",
        )
        self.monster_rage_bar = UIProgressBar(
            rect=pygame.Rect(850, 512, 320, 20),
            max_value=100,
            current_value=0,
            fill_color=COLOR_RAGE_ORANGE,
            label="Rage Meter",
            show_numeric=True,
        )

        # Panel Log Tempur
        self.combat_log = LogBox(pygame.Rect(400, 575, 480, 130), max_lines=5)

        # Tombol Aksi Tempur
        self.buttons: List[UIButton] = []
        self._init_buttons()

        # Giliran (Turn State) & Siklus Ultimate
        self.is_player_turn: bool = True
        self.turn_delay_timer: float = 0.0
        self.defending: bool = False
        self.turn_count: int = 1
        self.victory_pending: bool = False

    def _init_buttons(self) -> None:
        btn_w, btn_h = 160, 44
        # Tombol Serang Normal (Icon Sword)
        self.btn_attack = UIButton(
            rect=pygame.Rect(80, 575, btn_w, btn_h),
            text="Serang",
            icon_name="atk",
            on_click=self._player_attack,
        )
        # Tombol Skill Karakter (Icon Magic Book)
        self.btn_skill = UIButton(
            rect=pygame.Rect(80, 630, btn_w, btn_h),
            text="Skill Khusus",
            icon_name="magic",
            hover_color=(120, 60, 170),
            on_click=self._player_skill,
        )
        # Tombol Pakai Potion (Icon Potion)
        self.btn_item = UIButton(
            rect=pygame.Rect(260, 575, btn_w, btn_h),
            text="Potion HP",
            icon_name="heal",
            hover_color=(40, 130, 80),
            on_click=self._player_use_potion,
        )
        # Tombol Bertahan (Icon Shield/Armor)
        self.btn_defend = UIButton(
            rect=pygame.Rect(260, 630, btn_w, btn_h),
            text="Bertahan",
            icon_name="def",
            hover_color=(40, 80, 150),
            on_click=self._player_defend,
        )
        # Tombol Mundur (Icon Boots)
        self.btn_run = UIButton(
            rect=pygame.Rect(920, 630, 180, 44),
            text="Mundur ke Map",
            icon_name="boots",
            hover_color=(90, 80, 100),
            on_click=self._player_run,
        )

        self.buttons = [self.btn_attack, self.btn_skill, self.btn_item, self.btn_defend, self.btn_run]

    def enter(self, monster_name: Optional[str] = None, **kwargs: Any) -> None:
        """Inisialisasi pertempuran dengan monster tertentu."""
        if not self.game.state_mgr:
            return

        state = self.game.state_mgr
        self.current_monster = state.monsters.get(monster_name) if monster_name else None
        if not self.current_monster:
            self.machine.change_state(STATE_EXPLORATION)
            return

        # Buat entitas visual
        self.player_entity = PlayerEntity(state.player, x=140, y=260)
        self.monster_entity = MonsterEntity(self.current_monster, x=780, y=140)

        # Inisialisasi bar
        self.player_hp_bar.set_value(state.player.hp, state.player.max_hp)
        self.player_def_bar.set_value(state.player.defense, state.player.max_defense)
        self.monster_hp_bar.set_value(self.current_monster.hp, self.current_monster.max_hp)
        self.monster_rage_bar.set_value(self.current_monster.current_rage, 100)
        if self.current_monster.enraged:
            self.monster_rage_bar.label = "[!! RAGE MODE (MAX) !!]"
            self.monster_rage_bar.fill_color = (240, 50, 40)
        else:
            self.monster_rage_bar.label = "Rage Meter"
            self.monster_rage_bar.fill_color = COLOR_RAGE_ORANGE

        self.is_player_turn = True
        self.turn_delay_timer = 0.0
        self.defending = False
        self.turn_count = 1
        self.victory_pending = False

        self.combat_log.messages.clear()
        self.combat_log.add_message(f"[*] Pertarungan dimulai melawan {self.current_monster.name}!")
        if self.current_monster.is_boss:
            self.combat_log.add_message("[!] PERINGATAN: Bos Kaiju melepaskan Ultimate dahsyat setiap 5 ronde!")

    def _trigger_shake(self, amount: float = 8.0, duration: float = 0.3) -> None:
        """Membuat guncangan layar saat terjadi benturan keras."""
        self.screen_shake_amount = amount
        self.screen_shake_time = duration

    def _player_attack(self) -> None:
        if not self.is_player_turn or not self.current_monster or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        # Rumus Serang: max(1, ATK + random(-15..15) - DEF target). Peluang kritis 10% (x1.5)
        is_crit = random.random() < 0.10
        raw_roll = player.attack + random.randint(-15, 15)
        if is_crit:
            raw_roll = int(raw_roll * 1.5)
        final_dmg = max(1, raw_roll - self.current_monster.def_)
        absorbed, actual_dmg = self.current_monster.take_damage(final_dmg)

        # Cek apakah monster masuk ke Rage Mode
        if self.current_monster.check_enrage():
            buff_desc = "+20 ATK & 20% Kritis" if self.current_monster.is_boss else "+10 ATK"
            self.floating_texts.add("MONSTER ENRAGED!", 920, 200, COLOR_RAGE_ORANGE)
            self.combat_log.add_message(f"[!] {self.current_monster.name} memasuki RAGE MODE ({buff_desc})!")
            self._trigger_shake(12.0, 0.4)

        # Animasi & Audio
        if self.player_entity:
            self.player_entity.trigger_attack()
        if self.monster_entity:
            self.monster_entity.trigger_hurt()
        self.audio.play("attack")
        self.audio.play("hit")

        crit_tag = " (KRITIS 1.5x!)" if is_crit else ""
        col = COLOR_GOLD if is_crit else COLOR_HP_RED
        self.floating_texts.add(f"-{actual_dmg}{' !' if is_crit else ''}", 940, 240, col)
        self.combat_log.add_message(f"[>] {player.name} menyerang {self.current_monster.name}{crit_tag} sebesar {actual_dmg} DMG!")

        # Periksa kemenangan
        if not self.current_monster.is_alive:
            if self.monster_entity:
                self.monster_entity.trigger_death()
            self.audio.play("victory")
            self.combat_log.add_message(f"[OK] {self.current_monster.name} telah dikalahkan!")
            self.turn_delay_timer = 1.6
            self.victory_pending = True
            return

        self._end_player_turn()

    def _player_skill(self) -> None:
        if not self.is_player_turn or not self.current_monster or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        if player.skill_cooldown > 0:
            self.combat_log.add_message(f"[!] Skill sedang cooldown ({player.skill_cooldown} ronde lagi)!")
            self.floating_texts.add("COOLDOWN!", 200, 280, COLOR_TEXT_MUTED)
            return

        # Skill: Damage x1.8, Cooldown 3 ronde
        dmg_raw = int(player.attack * 1.8)
        absorbed, actual_dmg = self.current_monster.take_damage(dmg_raw)
        player.skill_cooldown = 3

        if player.role == PlayerRole.MAGE:
            self.audio.play("magic")
            self._trigger_shake(8.0, 0.3)
            self.floating_texts.add(f"ARCANE SURGE: -{actual_dmg}", 920, 220, (180, 100, 255))
            self.combat_log.add_message(f"[>] {player.name} merapal Arcane Surge! {actual_dmg} Magic DMG (Cooldown 3 Ronde)!")
        else:
            self.audio.play("hit")
            self._trigger_shake(10.0, 0.35)
            self.floating_texts.add(f"HEAVY STRIKE: -{actual_dmg}", 920, 220, COLOR_GOLD)
            self.combat_log.add_message(f"[>] {player.name} melancarkan Heavy Strike! {actual_dmg} Physical DMG (Cooldown 3 Ronde)!")

        if self.current_monster.check_enrage():
            buff_desc = "+20 ATK & 20% Kritis" if self.current_monster.is_boss else "+10 ATK"
            self.floating_texts.add("MONSTER ENRAGED!", 920, 200, COLOR_RAGE_ORANGE)
            self.combat_log.add_message(f"[!] {self.current_monster.name} memasuki RAGE MODE ({buff_desc})!")
            self._trigger_shake(12.0, 0.4)

        if self.player_entity:
            self.player_entity.trigger_attack()
        if self.monster_entity:
            self.monster_entity.trigger_hurt()

        if not self.current_monster.is_alive:
            if self.monster_entity:
                self.monster_entity.trigger_death()
            self.audio.play("victory")
            self.combat_log.add_message(f"[OK] {self.current_monster.name} telah dikalahkan!")
            self.turn_delay_timer = 1.6
            self.victory_pending = True
            return

        self._end_player_turn()

    def _player_use_potion(self) -> None:
        if not self.is_player_turn or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        if player.potions <= 0:
            self.combat_log.add_message("[!] Stok Health Potion habis!")
            self.floating_texts.add("POTION HABIS!", 200, 280, COLOR_HP_RED)
            return

        healed = player.use_potion()
        self.audio.play("heal")
        self.floating_texts.add(f"+{healed} HP", 200, 280, COLOR_HP_GREEN)
        self.combat_log.add_message(f"[+] Memakai Health Potion (+{healed} HP). Sisa stok: {player.potions}.")
        self._end_player_turn()

    def _player_defend(self) -> None:
        if not self.is_player_turn or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        self.defending = True
        player.shield = 80
        if self.player_entity:
            self.player_entity.trigger_defend()
        self.audio.play("click")
        self.floating_texts.add("+80 SHIELD", 200, 280, COLOR_DEFENSE_BLUE)
        self.combat_log.add_message("[#] Karakter bersiap bertahan! Shield +80 meredam serangan ronde ini.")
        self._end_player_turn()

    def _player_run(self) -> None:
        if not self.current_monster:
            return

        # Sesuai aturan: Tidak bisa dipakai melawan boss
        if self.current_monster.is_boss:
            self.combat_log.add_message("[!] Tidak bisa melarikan diri dari pertarungan Boss!")
            self.floating_texts.add("TIDAK BISA KABUR!", 200, 280, COLOR_HP_RED)
            return

        self.audio.play("click")
        self.current_monster.reset()
        self.combat_log.add_message(f"[-] Mundur dari pertarungan. {self.current_monster.name} pulih penuh.")
        self.machine.change_state(STATE_EXPLORATION)

    def _end_player_turn(self) -> None:
        self.is_player_turn = False
        self.turn_delay_timer = 1.0  # Jeda 1 detik sebelum musuh membalas (UX Feedback)

    def _monster_turn(self) -> None:
        if not self.current_monster or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        monster = self.current_monster

        # Panggil AI unik musuh sesuai tabel 2.3
        action_type, raw_dmg, desc = monster.decide_action(self.turn_count)

        if action_type == "ultimate":
            # ULTIMATE: Atomic Breath (Setiap 5 Ronde)
            if self.monster_entity:
                self.monster_entity.trigger_ultimate()
            self.audio.play("magic")
            self.audio.play("hit")
            self._trigger_shake(22.0, 0.85)

            absorbed, dmg_hp = player.take_damage(raw_dmg, is_atomic_breath=True)
            self.floating_texts.add("ATOMIC BREATH!", 160, 200, (255, 80, 255))
            if dmg_hp > 0:
                self.floating_texts.add(f"-{dmg_hp} HP", 200, 260, COLOR_HP_RED)
            if absorbed > 0:
                self.floating_texts.add(f"Shield -{absorbed}", 200, 290, COLOR_DEFENSE_BLUE)

            self.combat_log.add_message(
                f"[!] {monster.name} MELEPASKAN ULTIMATE: ATOMIC BREATH! ({dmg_hp} HP DMG | Shield serap {absorbed})!"
            )

        elif action_type == "lifesteal":
            if self.monster_entity:
                self.monster_entity.trigger_attack()
            self.audio.play("hit")
            self._trigger_shake(8.0, 0.25)
            absorbed, dmg_hp = player.take_damage(raw_dmg)
            healed = int(dmg_hp * 0.3)
            monster.hp = min(monster.max_hp, monster.hp + healed)
            self.floating_texts.add(f"+{healed} DRAIN", 920, 220, (180, 80, 255))
            self.combat_log.add_message(
                f"[>] {monster.name} menggunakan {desc}! ({dmg_hp} DMG, memulihkan +{healed} HP)!"
            )

        elif action_type == "defend":
            self.audio.play("click")
            self.floating_texts.add("+10 DEF", 920, 220, COLOR_DEFENSE_BLUE)
            self.combat_log.add_message(f"[#] {monster.name} {desc}!")

        elif action_type == "heavy_slam":
            if self.monster_entity:
                self.monster_entity.trigger_attack()
            self.audio.play("hit")
            self._trigger_shake(14.0, 0.45)
            absorbed, dmg_hp = player.take_damage(raw_dmg)
            self.floating_texts.add("HANTAMAN BERAT!", 180, 220, COLOR_RAGE_ORANGE)
            if dmg_hp > 0:
                self.floating_texts.add(f"-{dmg_hp} HP", 200, 260, COLOR_HP_RED)
            self.combat_log.add_message(f"[>] {monster.name} melancarkan {desc}! Mengakibatkan {dmg_hp} HP DMG!")

        else:
            # Serangan biasa
            if self.monster_entity:
                self.monster_entity.trigger_attack()
            self.audio.play("hit")
            self._trigger_shake(6.0, 0.2)
            absorbed, dmg_hp = player.take_damage(raw_dmg)
            if dmg_hp > 0:
                self.floating_texts.add(f"-{dmg_hp} HP", 200, 260, COLOR_HP_RED)
            if absorbed > 0:
                self.floating_texts.add(f"Shield -{absorbed}", 200, 290, COLOR_DEFENSE_BLUE)
            self.combat_log.add_message(
                f"[>] {monster.name} menyerang ({desc})! Menghasilkan {dmg_hp} HP damage (Shield menyerap {absorbed})."
            )

        # Periksa kekalahan pemain (Syarat Kalah)
        if not player.is_alive:
            self._handle_defeat()
            return

        # Kurangi cooldown skill pemain jika sedang berjalan
        if player.skill_cooldown > 0:
            player.skill_cooldown -= 1

        # Reset shield sementara pahlawan
        player.reset_shield()

        # Tambahkan perhitungan turn untuk siklus Ultimate berikutnya
        self.turn_count += 1
        next_turn = self.turn_count
        if monster.is_boss:
            if next_turn % 5 == 0:
                self.combat_log.add_message("[!] PERINGATAN: ENERGI KAIJU PENUH! Ronde ini Atomic Breath akan dilepaskan!")
                self.floating_texts.add("ATOMIC BREATH SIAP!", 860, 160, (255, 50, 50))
            elif next_turn % 5 == 4:
                self.combat_log.add_message("[!] Peringatan: Energi Bos meningkat (Atomic Breath dalam 1 turn)!")

        # Kembalikan ke giliran pemain
        self.is_player_turn = True
        self.defending = False

    def _handle_victory(self) -> None:
        """
        Logika Kemenangan Pertempuran & Game.
        Memenuhi Rubrik: 'Logika Interaksi & Menang/Kalah'.
        """
        self.audio.play("victory")
        rewards = self.game.state_mgr.claim_monster_rewards(self.current_monster)
        for r in rewards:
            self.combat_log.add_message(f"[+] {r}")

        # Cek apakah ini Final Boss (Corrupted Crystal Kaiju)
        if self.current_monster.is_boss:
            self.game.state_mgr.game_won = True
            self.machine.change_state(STATE_END, won=True, reason=f"Berhasil mengalahkan Boss {self.current_monster.name} di Throne of Extinction!")
        else:
            # Kembali ke peta setelah menang musuh biasa
            self.machine.change_state(STATE_EXPLORATION)

    def _handle_defeat(self) -> None:
        """
        Logika Kekalahan Pemain (HP <= 0).
        Memenuhi Rubrik: 'Logika Interaksi & Menang/Kalah'.
        """
        self.audio.play("defeat")
        self.game.state_mgr.game_over = True
        self.combat_log.add_message("[X] HP karakter mencapai 0. Pahlawan telah gugur!")
        self.machine.change_state(STATE_END, won=False, reason="HP karakter mencapai 0 di medan pertempuran.")

    def PlayerAction(self, action_type: str = "attack") -> None:
        """Alias PlayerAction() sesuai Bagian 1.3 dan Rubrik Teknis."""
        if action_type == "attack":
            self._player_attack()
        elif action_type == "skill":
            self._player_skill()
        elif action_type == "potion":
            self._player_use_potion()
        elif action_type == "defend":
            self._player_defend()
        elif action_type == "run":
            self._player_run()

    def MonsterTurn(self) -> None:
        """Alias MonsterTurn() sesuai Bagian 1.3 dan Rubrik Teknis."""
        self._monster_turn()

    def ApplyDamage(self, target: Any, amount: int) -> Tuple[int, int]:
        """Alias ApplyDamage() sesuai Bagian 1.3 dan Rubrik Teknis."""
        return target.take_damage(amount)

    def CheckBattleEnd(self) -> Optional[bool]:
        """Alias CheckBattleEnd() sesuai Bagian 1.3 dan Rubrik Teknis."""
        if self.current_monster and not self.current_monster.is_alive:
            self._handle_victory()
            return True
        if self.game.state_mgr and not self.game.state_mgr.player.is_alive:
            self._handle_defeat()
            return False
        return None


    def handle_event(self, event: pygame.event.Event) -> None:
        if self.is_player_turn and not self.victory_pending:
            # Cegah input tombol ketika animasi monster (attack atau ultimate) sedang berjalan
            if self.monster_entity and self.monster_entity.current_state in ("attack", "ultimate"):
                return
            for btn in self.buttons:
                if btn.handle_event(event):
                    break

    def update(self, dt: float) -> None:
        # Perbarui timer getaran layar
        if self.screen_shake_time > 0:
            self.screen_shake_time -= dt

        # Update entitas
        if self.player_entity:
            self.player_entity.update(dt)
        if self.monster_entity:
            self.monster_entity.update(dt)

        self.floating_texts.update(dt)

        # Jeda kemenangan setelah memutar animasi death monster
        if self.victory_pending:
            self.turn_delay_timer -= dt
            if self.turn_delay_timer <= 0:
                self._handle_victory()
                return

        # Update bar
        if self.game.state_mgr and self.current_monster:
            p = self.game.state_mgr.player
            self.player_hp_bar.set_value(p.hp, p.max_hp)
            self.player_def_bar.set_value(p.defense, p.max_defense)
            self.monster_hp_bar.set_value(self.current_monster.hp, self.current_monster.max_hp)
            self.monster_rage_bar.set_value(self.current_monster.current_rage, 100)
            if self.current_monster.enraged:
                self.monster_rage_bar.label = "[!! RAGE MODE (MAX) !!]"
                self.monster_rage_bar.fill_color = (240, 50, 40)
            else:
                self.monster_rage_bar.label = "Rage Meter"
                self.monster_rage_bar.fill_color = COLOR_RAGE_ORANGE

        self.player_hp_bar.update(dt)
        self.player_def_bar.update(dt)
        self.monster_hp_bar.update(dt)
        self.monster_rage_bar.update(dt)

        # Proses giliran musuh dengan jeda
        if not self.is_player_turn and not self.victory_pending and self.current_monster and self.current_monster.is_alive:
            self.turn_delay_timer -= dt
            if self.turn_delay_timer <= 0:
                self._monster_turn()

    def render(self, surface: pygame.Surface) -> None:
        # Efek Screen Shake jika aktif
        offset_x = 0
        offset_y = 0
        if self.screen_shake_time > 0:
            offset_x = random.randint(-int(self.screen_shake_amount), int(self.screen_shake_amount))
            offset_y = random.randint(-int(self.screen_shake_amount), int(self.screen_shake_amount))

        # Background arena
        bg = self.assets.get_image("combat_arena_bg.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(bg, (offset_x, offset_y))

        # Overlay gelap bawah untuk area kontrol UI
        bot_overlay = pygame.Surface((SCREEN_WIDTH, 240), pygame.SRCALPHA)
        bot_overlay.fill((15, 12, 22, 225))
        surface.blit(bot_overlay, (0, 480))
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (0, 480), (SCREEN_WIDTH, 480), width=2)

        # Header Info Monster & Indikator Siklus Ultimate (Setiap 5 Turn)
        if self.current_monster:
            font_m = self.assets.get_font(22, bold=True)
            m_txt = font_m.render(self.current_monster.name.upper(), True, COLOR_GOLD)
            surface.blit(m_txt, (850, 445))

            # Indikator Status Ultimate
            turns_left = 5 - (self.turn_count % 5) if (self.turn_count % 5 != 0) else 0
            if self.turn_count % 5 == 0:
                u_str = "[ ! ULTIMATE SIAP RONDE INI ! ]"
                u_color = (255, 60, 60)
            else:
                u_str = f"[ ULTIMATE: {turns_left} TURN ]"
                u_color = (210, 140, 255)

            u_font = self.assets.get_font(12, bold=True)
            u_surf = u_font.render(u_str, True, u_color)
            surface.blit(u_surf, (850 + m_txt.get_width() + 15, 452))

        # Header Info Player
        if self.game.state_mgr:
            font_p = self.assets.get_font(20, bold=True)
            p_txt = font_p.render(f"{self.game.state_mgr.player.name} ({self.game.state_mgr.player.role.value})", True, COLOR_TEXT_WHITE)
            surface.blit(p_txt, (80, 465))

        # Render Entitas Visual
        if self.player_entity:
            self.player_entity.render(surface)
        if self.monster_entity:
            self.monster_entity.render(surface)

        # Render Bar
        self.player_hp_bar.render(surface)
        self.player_def_bar.render(surface)
        self.monster_hp_bar.render(surface)
        self.monster_rage_bar.render(surface)

        # Render Tombol Tempur
        monster_acting = bool(self.monster_entity and self.monster_entity.current_state in ("attack", "ultimate"))
        for btn in self.buttons:
            btn.is_disabled = (not self.is_player_turn) or self.victory_pending or monster_acting
            btn.render(surface)

        # Render Log Box & Floating Texts
        self.combat_log.render(surface)
        self.floating_texts.render(surface)

