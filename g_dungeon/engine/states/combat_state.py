"""Layar pertarungan turn-based G-Dungeons."""

from typing import Any, List, Optional, Tuple
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
from engine.entities import (
    MonsterProjectile,
    MonsterEntity,
    PlayerEntity,
)
from engine.state_machine import GameState
from engine.ui import FloatingTextManager, LogBox, UIButton, UIProgressBar
from core.monster import Monster
from core.player import Player, PlayerRole


class CombatState(GameState):
    """State pertarungan pemain melawan monster."""

    def __init__(self, machine: Any, game_engine: Any) -> None:
        super().__init__(machine)

        self.game = game_engine
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        self.player_entity: Optional[PlayerEntity] = None
        self.monster_entity: Optional[MonsterEntity] = None
        self.current_monster: Optional[Monster] = None

        self.floating_texts = FloatingTextManager()
        self.screen_shake_time = 0.0
        self.screen_shake_amount = 0.0

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

        self.combat_log = LogBox(
            pygame.Rect(400, 575, 480, 130),
            max_lines=5,
        )

        self.buttons: List[UIButton] = []
        self._init_buttons()

        self.is_player_turn = True
        self.turn_delay_timer = 0.0
        self.defending = False
        self.turn_count = 1
        self.victory_pending = False

        # Mencegah lompatan dipicu berulang selama SPACE ditahan.
        self._space_was_down = False

        # Serangan proyektil monster: pemain bebas bergerak/menangkis
        # selama giliran monster berlangsung (real-time).
        self.reaction_active = False
        self.reaction_timer = 0.0
        self.reaction_end_delay = 0.0
        self.pending_attack: Optional[dict] = None
        self.projectiles: List[MonsterProjectile] = []
        self.show_hitboxes = False  # tekan F3 untuk debug hitbox

        # Status efek khusus monster.
        self.frost_hit_count = 0        # jumlah kena serangan Frost (2x = stun)
        self.stun_skip_active = False   # True saat giliran pemain dihanguskan stun

    def _init_buttons(self) -> None:
        btn_w, btn_h = 160, 44

        self.btn_attack = UIButton(
            rect=pygame.Rect(80, 575, btn_w, btn_h),
            text="Serang",
            icon_name="atk",
            on_click=self._player_attack,
        )

        self.btn_skill = UIButton(
            rect=pygame.Rect(80, 630, btn_w, btn_h),
            text="Skill Khusus",
            icon_name="magic",
            hover_color=(120, 60, 170),
            on_click=self._player_skill,
        )

        self.btn_item = UIButton(
            rect=pygame.Rect(260, 575, btn_w, btn_h),
            text="Potion HP",
            icon_name="heal",
            hover_color=(40, 130, 80),
            on_click=self._player_use_potion,
        )

        self.btn_defend = UIButton(
            rect=pygame.Rect(260, 630, btn_w, btn_h),
            text="Bertahan",
            icon_name="def",
            hover_color=(40, 80, 150),
            on_click=self._player_defend,
        )

        self.btn_run = UIButton(
            rect=pygame.Rect(920, 630, 180, 44),
            text="Mundur ke Map",
            icon_name="boots",
            hover_color=(90, 80, 100),
            on_click=self._player_run,
        )

        self.buttons = [
            self.btn_attack,
            self.btn_skill,
            self.btn_item,
            self.btn_defend,
            self.btn_run,
        ]

    def enter(
        self,
        monster_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Memulai pertempuran."""

        if not self.game.state_mgr:
            return

        state = self.game.state_mgr
        self.current_monster = (
            state.monsters.get(monster_name) if monster_name else None
        )

        if not self.current_monster:
            self.machine.change_state(STATE_EXPLORATION)
            return

        self.player_entity = PlayerEntity(
            state.player,
            x=140,
            y=260,
        )

        # REVISI: Posisi monster digeser ke kanan dan sedikit ke bawah.
        self.monster_entity = MonsterEntity(
            self.current_monster,
            x=850,
            y=165,
        )

        self.player_hp_bar.set_value(
            state.player.hp, state.player.max_hp
        )
        self.player_def_bar.set_value(
            state.player.defense, state.player.max_defense
        )
        self.monster_hp_bar.set_value(
            self.current_monster.hp, self.current_monster.max_hp
        )
        self.monster_rage_bar.set_value(
            self.current_monster.current_rage, 100
        )

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
        self._space_was_down = False

        self.reaction_active = False
        self.reaction_timer = 0.0
        self.reaction_end_delay = 0.0
        self.pending_attack = None
        self.projectiles.clear()

        state.player.clear_status()
        self.frost_hit_count = 0
        self.stun_skip_active = False

        self.combat_log.messages.clear()
        self.combat_log.add_message(
            f"[*] Pertarungan dimulai melawan "
            f"{self.current_monster.name}!"
        )

        if self.current_monster.is_boss:
            self.combat_log.add_message(
                "[!] PERINGATAN: Bos Kaiju melepaskan "
                "Ultimate setiap 5 ronde!"
            )

    def _trigger_shake(
        self,
        amount: float = 8.0,
        duration: float = 0.3,
    ) -> None:
        self.screen_shake_amount = amount
        self.screen_shake_time = duration

    def _check_enrage(self) -> None:
        if not self.current_monster:
            return

        if self.current_monster.check_enrage():
            buff_desc = (
                "+20 ATK & 20% Kritis"
                if self.current_monster.is_boss
                else "+10 ATK"
            )
            self.floating_texts.add(
                "MONSTER ENRAGED!",
                920,
                200,
                COLOR_RAGE_ORANGE,
            )
            self.combat_log.add_message(
                f"[!] {self.current_monster.name} memasuki "
                f"RAGE MODE ({buff_desc})!"
            )
            self._trigger_shake(12.0, 0.4)

    def exit(self) -> None:
        """Status efek tidak terbawa keluar dari pertarungan."""
        if self.game.state_mgr:
            self.game.state_mgr.player.clear_status()
        self.stun_skip_active = False

    def _player_attack(self) -> None:
        if (
            not self.is_player_turn
            or not self.current_monster
            or not self.game.state_mgr
            or self.victory_pending
        ):
            return

        player = self.game.state_mgr.player

        is_crit = random.random() < 0.10
        raw_roll = player.attack + random.randint(-15, 15)

        if is_crit:
            raw_roll = int(raw_roll * 1.5)

        debuffed = player.attack_debuff_turns > 0
        raw_roll = player.apply_attack_debuff(raw_roll)

        final_dmg = max(1, raw_roll - self.current_monster.def_)
        absorbed, actual_dmg = self.current_monster.take_damage(final_dmg)

        self._check_enrage()

        if self.player_entity:
            self.player_entity.trigger_attack()

        if self.monster_entity:
            self.monster_entity.trigger_hurt()

        self.audio.play("attack")
        self.audio.play("hit")

        crit_tag = " (KRITIS 1.5x!)" if is_crit else ""
        if debuffed:
            crit_tag += " (melemah -30%)"
        color = COLOR_GOLD if is_crit else COLOR_HP_RED

        self.floating_texts.add(
            f"-{actual_dmg}{' !' if is_crit else ''}",
            940,
            240,
            color,
        )

        self.combat_log.add_message(
            f"[>] {player.name} menyerang "
            f"{self.current_monster.name}{crit_tag} "
            f"sebesar {actual_dmg} DMG!"
        )

        if not self.current_monster.is_alive:
            if self.monster_entity:
                self.monster_entity.trigger_death()

            self.audio.play("victory")
            self.combat_log.add_message(
                f"[OK] {self.current_monster.name} telah dikalahkan!"
            )
            self.turn_delay_timer = 1.6
            self.victory_pending = True
            return

        self._end_player_turn()

    def _player_skill(self) -> None:
        if (
            not self.is_player_turn
            or not self.current_monster
            or not self.game.state_mgr
            or self.victory_pending
        ):
            return

        player = self.game.state_mgr.player

        if player.skill_cooldown > 0:
            self.combat_log.add_message(
                f"[!] Skill sedang cooldown "
                f"({player.skill_cooldown} ronde lagi)!"
            )
            self.floating_texts.add(
                "COOLDOWN!", 200, 280, COLOR_TEXT_MUTED
            )
            return

        dmg_raw = player.apply_attack_debuff(int(player.attack * 1.8))
        absorbed, actual_dmg = self.current_monster.take_damage(dmg_raw)
        player.skill_cooldown = 3

        if player.role == PlayerRole.MAGE:
            self.audio.play("magic")
            self._trigger_shake(8.0, 0.3)
            self.floating_texts.add(
                f"ARCANE SURGE: -{actual_dmg}",
                920,
                220,
                (180, 100, 255),
            )
            self.combat_log.add_message(
                f"[>] {player.name} merapal Arcane Surge! "
                f"{actual_dmg} Magic DMG (Cooldown 3 Ronde)!"
            )
        else:
            self.audio.play("hit")
            self._trigger_shake(10.0, 0.35)
            self.floating_texts.add(
                f"HEAVY STRIKE: -{actual_dmg}",
                920,
                220,
                COLOR_GOLD,
            )
            self.combat_log.add_message(
                f"[>] {player.name} melancarkan Heavy Strike! "
                f"{actual_dmg} Physical DMG (Cooldown 3 Ronde)!"
            )

        self._check_enrage()

        if self.player_entity:
            self.player_entity.trigger_skill()

        if self.monster_entity:
            self.monster_entity.trigger_hurt()

        if not self.current_monster.is_alive:
            if self.monster_entity:
                self.monster_entity.trigger_death()

            self.audio.play("victory")
            self.combat_log.add_message(
                f"[OK] {self.current_monster.name} telah dikalahkan!"
            )
            self.turn_delay_timer = 1.6
            self.victory_pending = True
            return

        self._end_player_turn()

    def _player_use_potion(self) -> None:
        if not self.is_player_turn or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player

        if player.potions <= 0:
            self.combat_log.add_message(
                "[!] Stok Health Potion habis!"
            )
            self.floating_texts.add(
                "POTION HABIS!", 200, 280, COLOR_HP_RED
            )
            return

        healed = player.use_potion()
        self.audio.play("heal")
        self.floating_texts.add(
            f"+{healed} HP", 200, 280, COLOR_HP_GREEN
        )
        self.combat_log.add_message(
            f"[+] Memakai Health Potion (+{healed} HP). "
            f"Sisa stok: {player.potions}."
        )
        self._end_player_turn()

    def _player_defend(self) -> None:
        if not self.is_player_turn or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        self.defending = True
        player.shield = 80
        def_gain = player.gain_defense(player.DEFEND_DEF_GAIN)

        if self.player_entity:
            self.player_entity.trigger_defend()

        self.audio.play("click")
        self.floating_texts.add(
            "+80 SHIELD", 200, 280, COLOR_DEFENSE_BLUE
        )
        if def_gain > 0:
            self.floating_texts.add(
                f"+{def_gain} DEF", 200, 310, COLOR_DEFENSE_BLUE
            )
        self.combat_log.add_message(
            "[#] Karakter bersiap bertahan! "
            f"Shield +80 meredam serangan ronde ini, DEF +{def_gain}."
        )
        self._end_player_turn()

    def _player_run(self) -> None:
        if not self.current_monster:
            return

        if self.current_monster.is_boss:
            self.combat_log.add_message(
                "[!] Tidak bisa melarikan diri dari pertarungan Boss!"
            )
            self.floating_texts.add(
                "TIDAK BISA KABUR!", 200, 280, COLOR_HP_RED
            )
            return

        self.audio.play("click")
        self.current_monster.reset()
        self.combat_log.add_message(
            f"[-] Mundur dari pertarungan. "
            f"{self.current_monster.name} pulih penuh."
        )
        self.machine.change_state(STATE_EXPLORATION)

    def _end_player_turn(self) -> None:
        # Debuff serangan berkurang 1 setiap giliran pemain yang terpakai.
        if self.game.state_mgr:
            p = self.game.state_mgr.player
            if p.attack_debuff_turns > 0:
                p.attack_debuff_turns -= 1
                if p.attack_debuff_turns == 0:
                    self.combat_log.add_message(
                        "[~] Efek serangan melemah telah hilang."
                    )
        self.is_player_turn = False
        self.turn_delay_timer = 1.0

    def _monster_turn(self) -> None:
        if not self.current_monster or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        monster = self.current_monster
        action_type, raw_dmg, desc = monster.decide_action(self.turn_count)

        # Monster dengan profil serangan proyektil (lihat MONSTER_ATTACK_PROFILES
        # di entities.py): serangan bisa dihindari atau ditangkis. Jika gambar
        # belum ada, otomatis memakai serangan instan di bawah.
        if (
            self.monster_entity
            and self.monster_entity.supports_projectile_action(action_type)
            and self._begin_projectile_attack(action_type, raw_dmg, desc)
        ):
            return

        if action_type == "ultimate":
            if self.monster_entity:
                self.monster_entity.trigger_ultimate()

            self.audio.play("magic")
            self.audio.play("hit")
            self._trigger_shake(22.0, 0.85)

            absorbed, dmg_hp = player.take_damage(
                raw_dmg, is_atomic_breath=True
            )
            self._player_hurt_feedback(dmg_hp)

            self.floating_texts.add(
                "ATOMIC BREATH!", 160, 200, (255, 80, 255)
            )

            if dmg_hp > 0:
                self.floating_texts.add(
                    f"-{dmg_hp} HP", 200, 260, COLOR_HP_RED
                )

            if absorbed > 0:
                self.floating_texts.add(
                    f"Shield -{absorbed}",
                    200,
                    290,
                    COLOR_DEFENSE_BLUE,
                )

            self.combat_log.add_message(
                f"[!] {monster.name} MELEPASKAN ULTIMATE: "
                f"ATOMIC BREATH! ({dmg_hp} HP DMG | "
                f"Shield serap {absorbed})!"
            )

        elif action_type == "lifesteal":
            if self.monster_entity:
                self.monster_entity.trigger_attack()

            self.audio.play("hit")
            self._trigger_shake(8.0, 0.25)

            absorbed, dmg_hp = player.take_damage(raw_dmg)
            self._player_hurt_feedback(dmg_hp)
            healed = int(dmg_hp * 0.3)
            monster.hp = min(monster.max_hp, monster.hp + healed)

            self.floating_texts.add(
                f"+{healed} DRAIN", 920, 220, (180, 80, 255)
            )
            self.combat_log.add_message(
                f"[>] {monster.name} menggunakan {desc}! "
                f"({dmg_hp} DMG, memulihkan +{healed} HP)!"
            )

        elif action_type == "defend":
            self.audio.play("click")
            self.floating_texts.add(
                "+10 DEF", 920, 220, COLOR_DEFENSE_BLUE
            )
            self.combat_log.add_message(
                f"[#] {monster.name} {desc}!"
            )

        elif action_type == "heavy_slam":
            if self.monster_entity:
                self.monster_entity.trigger_attack()

            self.audio.play("hit")
            self._trigger_shake(14.0, 0.45)
            absorbed, dmg_hp = player.take_damage(raw_dmg)
            self._player_hurt_feedback(dmg_hp)

            self.floating_texts.add(
                "HANTAMAN BERAT!", 180, 220, COLOR_RAGE_ORANGE
            )

            if dmg_hp > 0:
                self.floating_texts.add(
                    f"-{dmg_hp} HP", 200, 260, COLOR_HP_RED
                )

            self.combat_log.add_message(
                f"[>] {monster.name} melancarkan {desc}! "
                f"Mengakibatkan {dmg_hp} HP DMG!"
            )

        else:
            if self.monster_entity:
                self.monster_entity.trigger_attack()

            self.audio.play("hit")
            self._trigger_shake(6.0, 0.2)
            absorbed, dmg_hp = player.take_damage(raw_dmg)
            self._player_hurt_feedback(dmg_hp)

            if dmg_hp > 0:
                self.floating_texts.add(
                    f"-{dmg_hp} HP", 200, 260, COLOR_HP_RED
                )

            if absorbed > 0:
                self.floating_texts.add(
                    f"Shield -{absorbed}",
                    200,
                    290,
                    COLOR_DEFENSE_BLUE,
                )

            self.combat_log.add_message(
                f"[>] {monster.name} menyerang ({desc})! "
                f"Menghasilkan {dmg_hp} HP damage "
                f"(Shield menyerap {absorbed})."
            )

        if action_type in ("attack", "heavy_slam", "lifesteal"):
            self._apply_monster_hit_effects(dmg_hp)

        self._finish_monster_turn()

    def _apply_monster_hit_effects(self, dmg_hp: int) -> None:
        """Efek khusus monster saat serangannya BENAR-BENAR mengenai pemain.

        - Skeleton Guard : lifesteal 30% dari damage yang masuk ke HP pemain.
        - Shadow Wraith (Frost): kena 2x -> pemain STUN (hilang 1 giliran).
        - Magma Golem    : pemain terbakar (10-20 dmg/ronde selama 2 ronde).
        - Crystal Slime  : serangan pemain turun 30% selama 2 giliran.
        """
        if not self.current_monster or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        monster = self.current_monster
        name = monster.name
        tx, ty = self._player_text_anchor()

        if name == "Skeleton Guard":
            healed = int(dmg_hp * 0.30)
            if healed > 0:
                before = monster.hp
                monster.hp = min(monster.max_hp, monster.hp + healed)
                healed = monster.hp - before
                self.floating_texts.add(
                    f"+{healed} LIFESTEAL", 900, 220, (120, 255, 150)
                )
                self.combat_log.add_message(
                    f"[+] {name} menyerap jiwa: lifesteal 30% dari "
                    f"{dmg_hp} DMG, pulih +{healed} HP!"
                )

        elif name == "Shadow Wraith":
            self.frost_hit_count += 1
            if self.frost_hit_count >= 2:
                self.frost_hit_count = 0
                player.stunned = True
                self.floating_texts.add("STUN!", tx, ty - 30, (150, 225, 255))
                self.combat_log.add_message(
                    "[!] Terkena 2x serangan beku! Pahlawan STUN, "
                    "giliran berikutnya hangus!"
                )
            else:
                self.floating_texts.add(
                    "FROST 1/2", tx, ty - 30, (150, 225, 255)
                )
                self.combat_log.add_message(
                    "[~] Hawa dingin menyelimuti tubuhmu (1/2). "
                    "Satu serangan lagi akan membuatmu STUN!"
                )

        elif name == "Magma Golem":
            player.burn_turns = Player.BURN_ROUNDS
            self.floating_texts.add("BURN!", tx, ty - 30, COLOR_RAGE_ORANGE)
            self.combat_log.add_message(
                f"[!] Pahlawan TERBAKAR! Menerima "
                f"{Player.BURN_DAMAGE_RANGE[0]}-{Player.BURN_DAMAGE_RANGE[1]} "
                f"damage selama {Player.BURN_ROUNDS} ronde."
            )

        elif name == "Crystal Slime":
            player.attack_debuff_turns = Player.ATTACK_DEBUFF_ROUNDS
            self.floating_texts.add(
                "ATK -30%", tx, ty - 30, (80, 255, 160)
            )
            self.combat_log.add_message(
                "[!] Lendir asam melemahkanmu! Serangan turun 30% "
                f"selama {Player.ATTACK_DEBUFF_ROUNDS} giliran."
            )

    def _player_hurt_feedback(self, dmg_hp: int) -> None:
        """Animasi terluka pada pemain bila serangan benar-benar mengurangi HP."""
        if dmg_hp > 0 and self.player_entity:
            self.player_entity.trigger_hurt()

    def _finish_monster_turn(self) -> None:
        """Penutup giliran monster: cek kalah, cooldown, ronde berikutnya."""

        if not self.current_monster or not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        monster = self.current_monster

        if not player.is_alive:
            self._handle_defeat()
            return

        if player.skill_cooldown > 0:
            player.skill_cooldown -= 1

        player.reset_shield()

        # Burn: damage langsung ke HP (mengabaikan DEF) di awal tiap ronde.
        if player.burn_turns > 0:
            burn_dmg = random.randint(*Player.BURN_DAMAGE_RANGE)
            player.hp = max(0, player.hp - burn_dmg)
            player.burn_turns -= 1
            bx, by = self._player_text_anchor()
            self.audio.play("hit")
            self.floating_texts.add(
                f"BURN -{burn_dmg}", bx, by, COLOR_RAGE_ORANGE
            )
            self.combat_log.add_message(
                f"[~] Luka bakar membakar {player.name}: -{burn_dmg} HP "
                f"(sisa {player.burn_turns} ronde)."
            )
            if not player.is_alive:
                self._handle_defeat()
                return

        self.stun_skip_active = False
        self.turn_count += 1
        next_turn = self.turn_count

        if monster.is_boss:
            if next_turn % 5 == 0:
                self.combat_log.add_message(
                    "[!] PERINGATAN: Energi Kaiju penuh! "
                    "Atomic Breath akan dilepaskan!"
                )
                self.floating_texts.add(
                    "ATOMIC BREATH SIAP!",
                    860,
                    160,
                    (255, 50, 50),
                )
            elif next_turn % 5 == 4:
                self.combat_log.add_message(
                    "[!] Energi Bos meningkat "
                    "(Atomic Breath dalam 1 turn)!"
                )

        self.defending = False

        # Stun: giliran pemain hangus, monster langsung menyerang lagi.
        if player.stunned:
            player.stunned = False
            self.stun_skip_active = True
            self.is_player_turn = False
            self.turn_delay_timer = 1.4
            sx, sy = self._player_text_anchor()
            self.floating_texts.add("STUN! SKIP", sx, sy, (150, 225, 255))
            self.combat_log.add_message(
                f"[!] {player.name} terkena STUN dan tidak bisa bergerak "
                f"di ronde ini!"
            )
            return

        self.is_player_turn = True

    # ------------------------------------------------------------------
    # Serangan proyektil monster (menghindar / menangkis)
    # ------------------------------------------------------------------
    def _begin_projectile_attack(
        self,
        action_type: str,
        raw_dmg: int,
        desc: str,
    ) -> bool:
        """Mulai serangan proyektil. False jika monster ini tidak punya animasinya."""

        if not self.monster_entity or not self.player_entity:
            return False

        if not self.monster_entity.trigger_projectile_attack():
            return False

        self.pending_attack = {
            "type": action_type,
            "damage": raw_dmg,
            "desc": desc,
            "projectile": None,
            "resolved": False,
        }
        self.reaction_active = True
        self.reaction_timer = 0.0
        self.reaction_end_delay = 0.0
        self.projectiles.clear()

        self.combat_log.add_message(
            "[!] Serangan datang! Hindari (WASD/SPACE) "
            "atau tangkis (F)!"
        )
        return True

    def _update_projectile_attack(self, dt: float) -> None:
        """Peluncuran, gerakan, tabrakan, dan penutupan serangan proyektil."""

        attack = self.pending_attack

        if (
            attack is None
            or not self.monster_entity
            or not self.player_entity
            or not self.current_monster
        ):
            self._end_projectile_attack()
            return

        self.reaction_timer += dt
        projectile: Optional[MonsterProjectile] = attack["projectile"]

        # 1. Frame ke-4: proyektil muncul di ujung kiri frame serangan
        #    dan meluncur ke titik tempat pemain berdiri saat ini.
        if projectile is None:
            spawn = self.monster_entity.pop_projectile_launch()

            if spawn is not None:
                hurtbox = self.player_entity.get_hurtbox()
                target = (hurtbox.centerx, hurtbox.bottom - 30)
                speed = self.monster_entity.projectile_speed * (
                    1.25 if self.current_monster.enraged else 1.0
                )

                projectile = MonsterProjectile(
                    self.monster_entity.projectile_frames,
                    spawn,
                    target,
                    speed,
                    self.monster_entity.attack_profile,
                )
                attack["projectile"] = projectile
                self.projectiles.append(projectile)
                self.audio.play("magic")

        # 2. Gerakkan proyektil dan periksa tabrakan.
        else:
            projectile.update(dt)

            if projectile.is_flying:
                self._check_projectile_collision(projectile)

            if projectile.outcome == "missed" and not attack["resolved"]:
                attack["resolved"] = True
                self._on_projectile_missed()

        # 3. Akhiri giliran setelah animasi dan proyektil selesai.
        animation_done = self.monster_entity.current_state != "ranged_attack"

        if projectile is not None and projectile.is_done and animation_done:
            self.reaction_end_delay += dt
            if self.reaction_end_delay >= 0.35:
                self._end_projectile_attack()
                return

        # Pengaman agar giliran tidak pernah macet.
        if self.reaction_timer > 8.0:
            if not attack["resolved"]:
                self._on_projectile_missed()
            self._end_projectile_attack()

    def _check_projectile_collision(self, projectile: MonsterProjectile) -> None:
        if not self.player_entity or not self.pending_attack:
            return

        hitbox = projectile.get_hitbox()
        hurtbox = self.player_entity.get_hurtbox()

        # Jendela tangkis aktif: perisai sedikit lebih lebar dari tubuh.
        if self.player_entity.guard_window > 0 and hitbox.colliderect(
            hurtbox.inflate(40, 24)
        ):
            projectile.impact("parried")
            self.pending_attack["resolved"] = True
            self._on_projectile_parried()
            return

        if hitbox.colliderect(hurtbox):
            projectile.impact("hit")
            self.pending_attack["resolved"] = True
            self._on_projectile_hit()

    def _player_text_anchor(self) -> Tuple[int, int]:
        if not self.player_entity:
            return 200, 260

        hurtbox = self.player_entity.get_hurtbox()
        return hurtbox.centerx - 30, hurtbox.top - 10

    def _on_projectile_hit(self) -> None:
        if (
            not self.current_monster
            or not self.game.state_mgr
            or not self.pending_attack
        ):
            return

        player = self.game.state_mgr.player
        monster = self.current_monster
        attack = self.pending_attack
        action = attack["type"]
        text_x, text_y = self._player_text_anchor()

        absorbed, dmg_hp = player.take_damage(attack["damage"])

        self.audio.play("hit")

        if action == "heavy_slam":
            self._trigger_shake(14.0, 0.45)
            self.floating_texts.add(
                "HANTAMAN BERAT!", text_x - 40, text_y - 30, COLOR_RAGE_ORANGE
            )
        else:
            self._trigger_shake(8.0, 0.25)

        if self.player_entity:
            self.player_entity.trigger_hurt()

        if dmg_hp > 0:
            self.floating_texts.add(
                f"-{dmg_hp} HP", text_x, text_y, COLOR_HP_RED
            )

        if absorbed > 0:
            self.floating_texts.add(
                f"Shield -{absorbed}",
                text_x,
                text_y + 28,
                COLOR_DEFENSE_BLUE,
            )

        if action == "lifesteal":
            healed = int(dmg_hp * 0.3)
            monster.hp = min(monster.max_hp, monster.hp + healed)

            self.floating_texts.add(
                f"+{healed} DRAIN", 920, 220, (180, 80, 255)
            )
            self.combat_log.add_message(
                f"[>] {monster.name} menggunakan {attack['desc']}! "
                f"({dmg_hp} DMG, memulihkan +{healed} HP)!"
            )
        elif action == "heavy_slam":
            self.combat_log.add_message(
                f"[>] {monster.name} melancarkan {attack['desc']}! "
                f"Mengakibatkan {dmg_hp} HP DMG!"
            )
        else:
            self.combat_log.add_message(
                f"[>] {monster.name} menyerang ({attack['desc']})! "
                f"Menghasilkan {dmg_hp} HP damage "
                f"(Shield menyerap {absorbed})."
            )

        self._apply_monster_hit_effects(dmg_hp)

    def _on_projectile_parried(self) -> None:
        if not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        text_x, text_y = self._player_text_anchor()

        self.audio.play("attack")
        self.audio.play("click")
        self._trigger_shake(4.0, 0.15)

        self.floating_texts.add("TANGKIS!", text_x, text_y, COLOR_GOLD)
        self.combat_log.add_message(
            f"[#] {player.name} menangkis serangan tepat waktu! "
            f"Tidak ada damage."
        )

    def _on_projectile_missed(self) -> None:
        if not self.game.state_mgr:
            return

        player = self.game.state_mgr.player
        text_x, text_y = self._player_text_anchor()

        self.floating_texts.add(
            "MENGHINDAR!", text_x - 10, text_y, (140, 220, 255)
        )
        self.combat_log.add_message(
            f"[~] {player.name} berhasil menghindari serangan!"
        )

        if self.pending_attack:
            self.pending_attack["resolved"] = True

    def _end_projectile_attack(self) -> None:
        self.reaction_active = False
        self.pending_attack = None
        self.projectiles.clear()
        self._finish_monster_turn()

    def _handle_victory(self) -> None:
        self.audio.play("victory")

        if not self.game.state_mgr or not self.current_monster:
            return

        rewards = self.game.state_mgr.claim_monster_rewards(
            self.current_monster
        )

        for reward in rewards:
            self.combat_log.add_message(f"[+] {reward}")

        if self.current_monster.is_boss:
            self.game.state_mgr.game_won = True
            self.machine.change_state(
                STATE_END,
                won=True,
                reason=(
                    f"Berhasil mengalahkan Boss "
                    f"{self.current_monster.name} "
                    f"di Throne of Extinction!"
                ),
            )
        else:
            self.machine.change_state(STATE_EXPLORATION)

    def _handle_defeat(self) -> None:
        self.audio.play("defeat")

        if self.game.state_mgr:
            self.game.state_mgr.game_over = True

        self.combat_log.add_message(
            "[X] HP karakter mencapai 0. Pahlawan telah gugur!"
        )
        self.machine.change_state(
            STATE_END,
            won=False,
            reason="HP karakter mencapai 0 di medan pertempuran.",
        )

    def PlayerAction(self, action_type: str = "attack") -> None:
        """Alias PlayerAction untuk kompatibilitas."""

        actions = {
            "attack": self._player_attack,
            "skill": self._player_skill,
            "potion": self._player_use_potion,
            "defend": self._player_defend,
            "run": self._player_run,
        }

        action = actions.get(action_type)
        if action:
            action()

    def MonsterTurn(self) -> None:
        self._monster_turn()

    def ApplyDamage(self, target: Any, amount: int) -> Tuple[int, int]:
        return target.take_damage(amount)

    def CheckBattleEnd(self) -> Optional[bool]:
        if self.current_monster and not self.current_monster.is_alive:
            self._handle_victory()
            return True

        if (
            self.game.state_mgr
            and not self.game.state_mgr.player.is_alive
        ):
            self._handle_defeat()
            return False

        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        # Debug: tampilkan hitbox pemain dan proyektil.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
            self.show_hitboxes = not self.show_hitboxes
            return

        # Saat serangan proyektil berlangsung: lompat (SPACE) dan tangkis (F / klik kanan).
        if self.reaction_active:
            if not self.player_entity or self.stun_skip_active:
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.player_entity.trigger_jump()
            elif (
                event.type == pygame.KEYDOWN and event.key == pygame.K_f
            ) or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 3
            ):
                self.player_entity.trigger_guard()
            return

        if not self.is_player_turn or self.victory_pending:
            return

        if (
            self.monster_entity
            and self.monster_entity.current_state in ("attack", "ultimate")
        ):
            return

        # Lompat ketika tombol SPACE ditekan.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if self.player_entity:
                self.player_entity.trigger_jump()
            return

        for button in self.buttons:
            if button.handle_event(event):
                break

    def update(self, dt: float) -> None:
        """Update gerakan, animasi, UI, dan pergantian giliran."""

        if self.screen_shake_time > 0:
            self.screen_shake_time = max(
                0.0, self.screen_shake_time - dt
            )

        # Gerakan hanya dapat dilakukan ketika giliran pemain aktif.
        # Gerakan dan lompatan tidak menghabiskan giliran.
        if (
            self.player_entity
            and (self.is_player_turn or self.reaction_active)
            and not self.victory_pending
            and not self.stun_skip_active
        ):
            keys = pygame.key.get_pressed()
            self.player_entity.handle_movement(keys, dt)
        else:
            self._space_was_down = False

        if self.player_entity:
            self.player_entity.update(dt)

        if self.monster_entity:
            self.monster_entity.update(dt)

        if self.reaction_active:
            self._update_projectile_attack(dt)

        self.floating_texts.update(dt)

        # Tunggu animasi kematian monster sebelum kembali ke map.
        if self.victory_pending:
            self.turn_delay_timer -= dt
            if self.turn_delay_timer <= 0:
                self._handle_victory()
                return

        # Perbarui bar status.
        if self.game.state_mgr and self.current_monster:
            player = self.game.state_mgr.player

            self.player_hp_bar.set_value(
                player.hp, player.max_hp
            )
            self.player_def_bar.set_value(
                player.defense, player.max_defense
            )
            self.monster_hp_bar.set_value(
                self.current_monster.hp,
                self.current_monster.max_hp,
            )
            self.monster_rage_bar.set_value(
                self.current_monster.current_rage, 100
            )

            if self.current_monster.enraged:
                self.monster_rage_bar.label = (
                    "[!! RAGE MODE (MAX) !!]"
                )
                self.monster_rage_bar.fill_color = (240, 50, 40)
            else:
                self.monster_rage_bar.label = "Rage Meter"
                self.monster_rage_bar.fill_color = COLOR_RAGE_ORANGE

        self.player_hp_bar.update(dt)
        self.player_def_bar.update(dt)
        self.monster_hp_bar.update(dt)
        self.monster_rage_bar.update(dt)

        # Jalankan giliran monster setelah jeda.
        if (
            not self.is_player_turn
            and not self.reaction_active
            and not self.victory_pending
            and self.current_monster
            and self.current_monster.is_alive
        ):
            self.turn_delay_timer -= dt
            if self.turn_delay_timer <= 0:
                self._monster_turn()

    def render(self, surface: pygame.Surface) -> None:
        """Menggambar seluruh layar pertempuran."""

        offset_x = 0
        offset_y = 0

        if self.screen_shake_time > 0:
            offset_x = random.randint(
                -int(self.screen_shake_amount),
                int(self.screen_shake_amount),
            )
            offset_y = random.randint(
                -int(self.screen_shake_amount),
                int(self.screen_shake_amount),
            )

        
        background_by_monster = {
            "Magma Golem": "magma_arena_bg.png",
            "Shadow Wraith": "shadow_arena_bg.png",
            "Skeleton Guard": "ancient_arena_bg.png",
            "Crystal Slime": "crystal_arena_bg.png",
        }

        monster_name = (
            self.current_monster.name
            if self.current_monster
            else ""
        )

        background_file = background_by_monster.get(
            monster_name,
            "dungeon_map_bg.png",
        )

        background = self.assets.get_image(
            background_file,
            scale=(SCREEN_WIDTH, SCREEN_HEIGHT),
        )

        surface.blit(background, (offset_x, offset_y))


        bottom_overlay = pygame.Surface(
            (SCREEN_WIDTH, 240), pygame.SRCALPHA
        )
        bottom_overlay.fill((15, 12, 22, 225))
        surface.blit(bottom_overlay, (0, 480))

        pygame.draw.line(
            surface,
            COLOR_PANEL_BORDER,
            (0, 480),
            (SCREEN_WIDTH, 480),
            width=2,
        )

        # Nama monster dan informasi ultimate.
        if self.current_monster:
            monster_font = self.assets.get_font(22, bold=True)
            monster_text = monster_font.render(
                self.current_monster.name.upper(),
                True,
                COLOR_GOLD,
            )
            surface.blit(monster_text, (850, 445))

            turns_left = (
                5 - self.turn_count % 5
                if self.turn_count % 5 != 0
                else 0
            )

            if self.turn_count % 5 == 0:
                ultimate_text = "[ ! ULTIMATE SIAP RONDE INI ! ]"
                ultimate_color = (255, 60, 60)
            else:
                ultimate_text = f"[ ULTIMATE: {turns_left} TURN ]"
                ultimate_color = (210, 140, 255)

            small_font = self.assets.get_font(12, bold=True)
            ultimate_surface = small_font.render(
                ultimate_text, True, ultimate_color
            )
            surface.blit(
                ultimate_surface,
                (850 + monster_text.get_width() + 15, 452),
            )

        # Nama dan role pemain.
        if self.game.state_mgr:
            player = self.game.state_mgr.player
            player_font = self.assets.get_font(20, bold=True)
            player_text = player_font.render(
                f"{player.name} ({player.role.value})",
                True,
                COLOR_TEXT_WHITE,
            )
            surface.blit(player_text, (80, 465))

            # Chip status efek di samping nama pemain.
            chip_font = self.assets.get_font(12, bold=True)
            chips = []
            if player.stunned:
                chips.append(("STUN (giliran depan)", (150, 225, 255)))
            if player.burn_turns > 0:
                chips.append((f"BURN {player.burn_turns}R", COLOR_RAGE_ORANGE))
            if player.attack_debuff_turns > 0:
                chips.append(
                    (f"ATK -30% ({player.attack_debuff_turns})", (80, 255, 160))
                )
            if (
                self.current_monster
                and self.current_monster.name == "Shadow Wraith"
                and self.frost_hit_count > 0
            ):
                chips.append(
                    (f"FROST {self.frost_hit_count}/2", (150, 225, 255))
                )
            cx = 80 + player_text.get_width() + 14
            for label, color in chips:
                chip = chip_font.render(f"[{label}]", True, color)
                surface.blit(chip, (cx, 472))
                cx += chip.get_width() + 8

        # Entitas.
        if self.player_entity:
            self.player_entity.render(surface)

        if self.monster_entity:
            self.monster_entity.render(surface)

        # Proyektil di atas pemain dan monster.
        for projectile in self.projectiles:
            projectile.render(surface)

        if self.show_hitboxes:
            self._render_hitboxes(surface)

        # Bar status.
        self.player_hp_bar.render(surface)
        self.player_def_bar.render(surface)
        self.monster_hp_bar.render(surface)
        self.monster_rage_bar.render(surface)

        # Tombol aksi.
        monster_acting = bool(
            self.monster_entity
            and self.monster_entity.current_state
            in ("attack", "ultimate", "ranged_attack")
        )

        for button in self.buttons:
            button.is_disabled = (
                not self.is_player_turn
                or self.victory_pending
                or monster_acting
            )
            button.render(surface)

        if self.reaction_active:
            self._render_reaction_hint(surface)

        # Log dan teks damage.
        self.combat_log.render(surface)
        self.floating_texts.render(surface)

    def _render_reaction_hint(self, surface: pygame.Surface) -> None:
        """Petunjuk kontrol singkat selama serangan proyektil berlangsung."""

        font = self.assets.get_font(16, bold=True)
        ready = bool(
            self.player_entity and self.player_entity.guard_cooldown <= 0
        )

        parts = [
            ("GERAK: WASD", COLOR_TEXT_WHITE),
            ("LOMPAT: SPACE", COLOR_TEXT_WHITE),
            (
                "TANGKIS: F / Klik Kanan" if ready else "TANGKIS: ...",
                COLOR_GOLD if ready else COLOR_TEXT_MUTED,
            ),
        ]
        rendered = [font.render(text, True, color) for text, color in parts]
        gap = 28
        total = sum(r.get_width() for r in rendered) + gap * (len(rendered) - 1)

        panel = pygame.Surface((total + 32, 34), pygame.SRCALPHA)
        panel.fill((15, 12, 22, 200))
        pygame.draw.rect(
            panel, COLOR_PANEL_BORDER, panel.get_rect(), width=2
        )

        px = (SCREEN_WIDTH - panel.get_width()) // 2
        surface.blit(panel, (px, 22))

        x = px + 16
        for r in rendered:
            surface.blit(r, (x, 22 + (34 - r.get_height()) // 2))
            x += r.get_width() + gap

    def _render_hitboxes(self, surface: pygame.Surface) -> None:
        if self.player_entity:
            pygame.draw.rect(
                surface, (60, 255, 90), self.player_entity.get_hurtbox(), 2
            )

        for projectile in self.projectiles:
            pygame.draw.rect(surface, (255, 60, 60), projectile.get_hitbox(), 2)
            pygame.draw.circle(
                surface,
                (255, 255, 0),
                (int(projectile.target[0]), int(projectile.target[1])),
                5,
            )