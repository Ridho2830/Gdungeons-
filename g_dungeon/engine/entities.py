"""
Module: engine/entities.py
Description: Struktur kelas objek (OOP) untuk entitas visual game: Transform, Sprite, PlayerEntity, MonsterEntity.
"""

from typing import Any, Dict, List, Optional, Tuple
import math
import pygame
from engine.assets import AssetManager
from engine.constants import (
    COLOR_HP_GREEN,
    COLOR_HP_RED,
    COLOR_RAGE_ORANGE,
    COLOR_DEFENSE_BLUE,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)
from core.player import Player, PlayerRole
from core.monster import Monster


class GameObject:
    """
    Kelas dasar semua objek permainan (OOP).
    Memiliki komponen:
    - Transform (posisi x, y, rect)
    - Visual rendering
    """

    def __init__(self, x: float, y: float, width: int, height: int) -> None:
        self.x: float = x
        self.y: float = y
        self.width: int = width
        self.height: int = height
        self.rect: pygame.Rect = pygame.Rect(int(x), int(y), width, height)

    def update(self, dt: float) -> None:
        """Memperbarui status objek setiap tick frame."""
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def render(self, surface: pygame.Surface) -> None:
        """Menggambar visual objek ke layar."""
        pass


class AnimatedSprite(GameObject):
    """Komponen animasi sprite berbasis urutan frame."""

    def __init__(
        self,
        x: float,
        y: float,
        animations: Dict[str, List[pygame.Surface]],
        default_anim: str = "idle",
        fps: float = 8.0,
    ) -> None:
        anim_list = animations.get(default_anim, []) if animations else []
        first_frame = anim_list[0] if anim_list else None
        w, h = first_frame.get_size() if first_frame else (64, 64)
        super().__init__(x, y, w, h)

        self.animations: Dict[str, List[pygame.Surface]] = animations
        self.current_anim: str = default_anim
        self.current_frame_idx: float = 0.0
        self.fps: float = fps
        self.is_looping: bool = True
        self.is_finished: bool = False
        self.flip_x: bool = False

    def play(self, anim_name: str, loop: bool = True, fps: Optional[float] = None) -> None:
        """Mengganti state animasi yang sedang aktif."""
        if anim_name in self.animations and self.current_anim != anim_name:
            self.current_anim = anim_name
            self.current_frame_idx = 0.0
            self.is_looping = loop
            self.is_finished = False
            if fps is not None:
                self.fps = fps

    def update(self, dt: float) -> None:
        super().update(dt)
        frames = self.animations.get(self.current_anim, [])
        if not frames:
            return

        self.current_frame_idx += self.fps * dt
        if self.current_frame_idx >= len(frames):
            if self.is_looping:
                self.current_frame_idx = self.current_frame_idx % len(frames)
            else:
                self.current_frame_idx = float(len(frames) - 1)
                self.is_finished = True

    def render(self, surface: pygame.Surface) -> None:
        frames = self.animations.get(self.current_anim, [])
        if not frames:
            return

        idx = min(int(self.current_frame_idx), len(frames) - 1)
        frame_surf = frames[idx]
        if self.flip_x:
            frame_surf = pygame.transform.flip(frame_surf, True, False)

        surface.blit(frame_surf, (self.rect.x, self.rect.y))


class PlayerEntity(GameObject):
    """
    Entitas grafis Playable Character.
    Menghubungkan model logika Player (core/player.py) dengan animasi sprite 2D.
    """

    def __init__(self, player_model: Player, x: float = 200, y: float = 300) -> None:
        super().__init__(x, y, 128, 128)
        self.player: Player = player_model
        self.assets = AssetManager.get_instance()
        self.anim_sprite: AnimatedSprite = self._create_animations(x, y)
        self.hurt_timer: float = 0.0

    def _create_animations(self, x: float, y: float) -> AnimatedSprite:
        anims: Dict[str, List[pygame.Surface]] = {}
        if self.player.role == PlayerRole.KNIGHT:
            # Sprite sheet Knight: frame width 96, height 84, scale 2.4
            scale = 2.4
            anims["idle"] = self.assets.load_sprite_sheet("IDLE.png", 96, 84, scale)
            anims["attack"] = self.assets.load_sprite_sheet("ATTACK 1.png", 96, 84, scale)
            anims["attack2"] = self.assets.load_sprite_sheet("ATTACK 2.png", 96, 84, scale)
            anims["defend"] = self.assets.load_sprite_sheet("DEFEND.png", 96, 84, scale)
            anims["hurt"] = self.assets.load_sprite_sheet("HURT.png", 96, 84, scale)
            anims["death"] = self.assets.load_sprite_sheet("DEATH.png", 96, 84, scale)
        else:
            # Sprite sheet Wizard: frame width 231, height 190, scale 1.4
            scale = 1.4
            anims["idle"] = self.assets.load_sprite_sheet("Idle.png", 231, 190, scale)
            anims["attack"] = self.assets.load_sprite_sheet("Attack1.png", 231, 190, scale)
            anims["attack2"] = self.assets.load_sprite_sheet("Attack2.png", 231, 190, scale)
            anims["hurt"] = self.assets.load_sprite_sheet("Hit.png", 231, 190, scale)
            anims["death"] = self.assets.load_sprite_sheet("Death.png", 231, 190, scale)

        return AnimatedSprite(x, y, anims, default_anim="idle", fps=9.0)

    def trigger_attack(self) -> None:
        """Memutar animasi menyerang."""
        self.anim_sprite.play("attack", loop=False, fps=12.0)

    def trigger_hurt(self) -> None:
        """Memutar animasi terkena serangan musuh."""
        self.hurt_timer = 0.3
        self.anim_sprite.play("hurt", loop=False, fps=10.0)

    def trigger_defend(self) -> None:
        """Memutar animasi bertahan (Fighter)."""
        if "defend" in self.anim_sprite.animations:
            self.anim_sprite.play("defend", loop=False, fps=8.0)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.anim_sprite.x = self.x
        self.anim_sprite.y = self.y
        self.anim_sprite.update(dt)

        if self.hurt_timer > 0:
            self.hurt_timer -= dt

        # Kembali ke idle jika animasi sekali putar sudah selesai
        if self.anim_sprite.is_finished and self.player.is_alive:
            self.anim_sprite.play("idle", loop=True, fps=8.0)
        elif not self.player.is_alive and self.anim_sprite.current_anim != "death":
            self.anim_sprite.play("death", loop=False, fps=8.0)

    def render(self, surface: pygame.Surface) -> None:
        # Efek kedip merah saat terkena serangan (Hurt Feedback)
        if self.hurt_timer > 0 and int(self.hurt_timer * 20) % 2 == 0:
            tint_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            tint_surf.fill((255, 50, 50, 90))
            self.anim_sprite.render(surface)
            surface.blit(tint_surf, (self.rect.x, self.rect.y))
        else:
            self.anim_sprite.render(surface)


class MonsterEntity(GameObject):
    """
    Entitas grafis Monster / Boss Kaiju (Godzilla).
    Menggunakan aset monster resmi assets/monsters/godzilla_boss.png
    dengan sistem animasi prosedural dinamis (idle float, attack lunge & slash,
    ultimate atomic blast beam, dan death collapse) serta pendaran aura rage.
    """

    def __init__(self, monster_model: Monster, x: float = 780, y: float = 140) -> None:
        super().__init__(x, y, 320, 320)
        self.monster: Monster = monster_model
        self.assets = AssetManager.get_instance()
        self.sprite = self.assets.get_monster_sprite(self.monster.name, size=(self.width, self.height))

        self.current_state: str = "idle"  # idle, attack, ultimate, death
        self.state_timer: float = 0.0
        self.hurt_timer: float = 0.0
        self.time_counter: float = 0.0
        self.shake_offset: Tuple[int, int] = (0, 0)

    def trigger_idle(self) -> None:
        """Memutar animasi idle berulang."""
        if self.monster.is_alive:
            self.current_state = "idle"
            self.state_timer = 0.0

    def trigger_attack(self) -> None:
        """Memutar animasi serangan cakar normal."""
        if self.monster.is_alive:
            self.current_state = "attack"
            self.state_timer = 0.55

    def trigger_ultimate(self) -> None:
        """Memutar animasi ultimate Atomic Blast."""
        if self.monster.is_alive:
            self.current_state = "ultimate"
            self.state_timer = 0.95

    def trigger_death(self) -> None:
        """Memutar animasi kehancuran monster."""
        self.current_state = "death"
        self.state_timer = 1.6

    def trigger_hurt(self) -> None:
        """Efek feedback saat monster menerima pukulan."""
        self.hurt_timer = 0.35

    def update(self, dt: float) -> None:
        super().update(dt)
        self.time_counter += dt

        # Update timer status
        if self.state_timer > 0:
            self.state_timer -= dt
            if self.state_timer <= 0 and self.monster.is_alive:
                self.current_state = "idle"

        # Efek guncangan (shake) saat terkena damage
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
            offset_x = int(math.sin(self.hurt_timer * 40) * 10)
            self.shake_offset = (offset_x, 0)
        else:
            # Idle breathing float effect
            if self.current_state == "idle" and self.monster.is_alive:
                float_y = int(math.sin(self.time_counter * 2.5) * 4)
                self.shake_offset = (0, float_y)
            else:
                self.shake_offset = (0, 0)

    def render(self, surface: pygame.Surface) -> None:
        pos_x = self.rect.x + self.shake_offset[0]
        pos_y = self.rect.y + self.shake_offset[1]

        # Offset tambahan saat menerjang menyerang (lunge ke kiri)
        if self.current_state == "attack" and self.monster.is_alive:
            t_progress = 1.0 - (self.state_timer / 0.55)
            lunge_dx = -int(math.sin(t_progress * math.pi) * 42)
            pos_x += lunge_dx

        # Efek visual aura membara saat Monster dalam kondisi RAGE
        if self.monster.enraged and self.monster.is_alive:
            aura_radius = 165 + int(math.sin(self.time_counter * 6) * 14)
            aura_surf = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                aura_surf,
                (240, 50, 40, 65),
                (aura_radius, aura_radius),
                aura_radius,
            )
            surface.blit(aura_surf, (pos_x + 160 - aura_radius, pos_y + 160 - aura_radius))

        # Render sprite monster berdasarkan kondisi (normal, hurt, atau death)
        if not self.monster.is_alive or self.current_state == "death":
            # Animasi kematian: roboh ke bawah, redup ke abu-abu, dan larut
            alpha_ratio = max(0.0, min(1.0, self.state_timer / 1.6))
            slump_dy = int((1.0 - alpha_ratio) * 35)

            death_surf = self.sprite.copy()
            death_surf.set_alpha(int(alpha_ratio * 255))
            surface.blit(death_surf, (pos_x, pos_y + slump_dy))

            # Percikan bara api melayang ke atas saat hancur
            ember_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for i in range(15):
                bx = pos_x + 60 + (i * 17) % 200
                by = pos_y + slump_dy + 150 - int((1.0 - alpha_ratio) * 120) - (i * 9) % 50
                pygame.draw.circle(ember_surf, (255, 120, 30, int(alpha_ratio * 200)), (bx, by), 2)
            surface.blit(ember_surf, (0, 0))
            return

        # Render sprite hidup
        if self.hurt_timer > 0 and int(self.hurt_timer * 20) % 2 == 0:
            flash_surf = self.sprite.copy()
            flash_surf.fill((220, 60, 60, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(flash_surf, (pos_x, pos_y))
        else:
            surface.blit(self.sprite, (pos_x, pos_y))

        # Efek visual tebasan cakar energi saat ATTACK
        if self.current_state == "attack" and self.state_timer > 0.1:
            claw_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            cx = pos_x + 40
            cy = pos_y + 120
            for ox, oy in [(-10, -20), (10, 0), (30, 20)]:
                pts = [
                    (cx + ox + 30, cy + oy - 45),
                    (cx + ox - 25, cy + oy),
                    (cx + ox + 15, cy + oy + 45),
                ]
                pygame.draw.lines(claw_surf, (230, 40, 255, 200), False, pts, 6)
                pygame.draw.lines(claw_surf, (255, 255, 255, 240), False, pts, 2)
            surface.blit(claw_surf, (0, 0))

        # Efek berkas sinar kosmis kolosal melintang ke pemain saat ULTIMATE
        if self.current_state == "ultimate" and self.monster.is_alive:
            mouth_x = int(pos_x + 86)
            mouth_y = int(pos_y + 88)
            target_x = 180
            target_y = 310

            beam_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            beam_w = 60

            # 1. Outer cosmic magenta aura
            pygame.draw.polygon(
                beam_surf,
                (240, 50, 180, 90),
                [(mouth_x, mouth_y - 12), (0, target_y - beam_w - 30), (0, target_y + beam_w + 30), (mouth_x, mouth_y + 12)]
            )
            # 2. Mid violet-blue energy cone
            pygame.draw.polygon(
                beam_surf,
                (160, 90, 255, 150),
                [(mouth_x, mouth_y - 8), (0, target_y - beam_w), (0, target_y + beam_w), (mouth_x, mouth_y + 8)]
            )
            # 3. Inner laser line
            pygame.draw.line(beam_surf, (220, 240, 255, 230), (mouth_x, mouth_y), (0, target_y), 18)
            pygame.draw.line(beam_surf, (255, 255, 255, 255), (mouth_x, mouth_y), (0, target_y), 8)

            # 4. Glowing Plasma Orb di mulut Godzilla
            pygame.draw.circle(beam_surf, (255, 100, 220, 200), (mouth_x, mouth_y), 24)
            pygame.draw.circle(beam_surf, (255, 255, 255, 255), (mouth_x, mouth_y), 12)

            # 5. Impact Detonation Burst di area pemain
            pygame.draw.circle(beam_surf, (255, 120, 240, 130), (target_x, target_y), 65)
            pygame.draw.circle(beam_surf, (255, 255, 255, 200), (target_x, target_y), 35)

            surface.blit(beam_surf, (0, 0))




