"""Entitas visual dan sistem animasi sprite untuk G-Dungeons."""

from typing import Dict, List, Optional, Tuple
import math
import os
import pygame

from engine.assets import AssetManager
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core.player import Player, PlayerRole
from core.monster import Monster


class GameObject:
    """Kelas dasar objek game."""

    def __init__(self, x: float, y: float, width: int, height: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.rect = pygame.Rect(int(x), int(y), width, height)

    def update(self, dt: float) -> None:
        self.rect.topleft = (int(self.x), int(self.y))

    def render(self, surface: pygame.Surface) -> None:
        pass


class AnimatedSprite(GameObject):
    """Sprite animasi berbasis sprite sheet."""

    def __init__(
        self,
        x: float,
        y: float,
        animations: Dict[str, List[pygame.Surface]],
        default_anim: str = "idle",
        fps: float = 8.0,
    ) -> None:
        frames = animations.get(default_anim, [])
        first = frames[0] if frames else None
        width, height = first.get_size() if first else (64, 64)

        super().__init__(x, y, width, height)

        self.animations = animations
        self.current_anim = default_anim
        self.current_frame_idx = 0.0
        self.fps = fps
        self.is_looping = True
        self.is_finished = False
        self.flip_x = False

    def play(
        self,
        anim_name: str,
        loop: bool = True,
        fps: Optional[float] = None,
    ) -> None:
        frames = self.animations.get(anim_name, [])
        if not frames:
            return

        self.current_anim = anim_name
        self.current_frame_idx = 0.0
        self.is_looping = loop
        self.is_finished = False

        if fps is not None:
            self.fps = fps

    def update(self, dt: float) -> None:
        super().update(dt)

        frames = self.animations.get(self.current_anim, [])
        if not frames or (self.is_finished and not self.is_looping):
            return

        self.current_frame_idx += self.fps * dt

        if self.current_frame_idx >= len(frames):
            if self.is_looping:
                self.current_frame_idx %= len(frames)
            else:
                self.current_frame_idx = float(len(frames) - 1)
                self.is_finished = True

    def render(self, surface: pygame.Surface) -> None:
        frames = self.animations.get(self.current_anim, [])
        if not frames:
            return

        index = min(int(self.current_frame_idx), len(frames) - 1)
        frame = frames[index]

        if self.flip_x:
            frame = pygame.transform.flip(frame, True, False)

        surface.blit(frame, self.rect.topleft)


class PlayerEntity(GameObject):
    """Entitas visual pemain Knight atau Wizard."""

    def __init__(
        self,
        player_model: Player,
        x: float = 200,
        y: float = 300,
    ) -> None:
        super().__init__(x, y, 128, 128)

        self.player = player_model
        self.assets = AssetManager.get_instance()
        self.anim_sprite = self._create_animations(x, y)

        # Timer animasi.
        self.hurt_timer = 0.0
        self.defend_timer = 0.0
        self.attack_duration = 0.62
        self.attack_timer = 0.0
        self.attack_distance = 0.0
        self.attack_offset = 0.0
        self.attack_kind = "normal"
        self.attack_variant = 0

        # Gerakan karakter.
        self.move_speed = 220.0
        self.run_speed = 340.0
        self.facing_right = True
        self.move_state = "idle"

        # Lompatan visual.
        self.jump_height = 0.0
        self.jump_velocity = 0.0
        self.jump_strength = 430.0
        self.gravity = 1150.0
        self.grounded = True

    def _load_sheet(
        self,
        path: str,
        frame_w: int,
        frame_h: int,
        scale: float,
    ) -> List[pygame.Surface]:
        try:
            return self.assets.load_sprite_sheet(
                path, frame_w, frame_h, scale
            )
        except (FileNotFoundError, pygame.error, OSError) as exc:
            print(f"[PlayerEntity] Gagal memuat {path}: {exc}")
            return []

    def _create_animations(
        self,
        x: float,
        y: float,
    ) -> AnimatedSprite:
        animations: Dict[str, List[pygame.Surface]] = {}

        if self.player.role == PlayerRole.KNIGHT:
            scale = 2.4
            frame_w, frame_h = 96, 84

            base = os.path.join(
                "players",
                "Knight 2D Pixel Art",
                "Knight 2D Pixel Art",
            )

            files = {
                "idle": "IDLE.png",
                "attack": "ATTACK 1.png",
                "attack2": "ATTACK 2.png",
                "attack3": "ATTACK 3.png",
                "walk": "WALK.png",
                "run": "RUN.png",
                "jump": "JUMP.png",
                "defend": "DEFEND.png",
                "hurt": "HURT.png",
                "death": "DEATH.png",
            }
        else:
            scale = 1.4
            frame_w, frame_h = 231, 190

            base = os.path.join("players", "Wizard Pack", "Wizard Pack")

            files = {
                "idle": "Idle.png",
                "attack": "Attack1.png",
                "attack2": "Attack2.png",
                "hurt": "Hit.png",
                "death": "Death.png",
            }

        for name, filename in files.items():
            path = os.path.join(base, filename)
            animations[name] = self._load_sheet(
                path, frame_w, frame_h, scale
            )
            print(
                f"[PlayerEntity] {name}: "
                f"{len(animations[name])} frame"
            )

        # Fallback agar animasi tidak kosong jika suatu aset tidak tersedia.
        if not animations.get("idle"):
            placeholder = pygame.Surface((128, 128), pygame.SRCALPHA)
            pygame.draw.rect(
                placeholder, (220, 220, 220), (20, 10, 88, 118)
            )
            animations["idle"] = [placeholder]

        return AnimatedSprite(
            x, y, animations, default_anim="idle", fps=8.0
        )

    def _play_if_available(
        self,
        animation: str,
        loop: bool,
        fps: float,
    ) -> None:
        if self.anim_sprite.animations.get(animation):
            self.anim_sprite.play(animation, loop=loop, fps=fps)

    def _start_attack(
        self,
        animation_name: str,
        kind: str,
        distance: float,
        fps: float,
    ) -> None:
        if not self.player.is_alive:
            return

        if not self.anim_sprite.animations.get(animation_name):
            animation_name = "attack"

        if not self.anim_sprite.animations.get(animation_name):
            return

        self.attack_kind = kind
        self.attack_timer = self.attack_duration
        self.attack_distance = distance
        self.attack_offset = 0.0
        self.defend_timer = 0.0
        self.move_state = "idle"

        self.anim_sprite.play(animation_name, loop=False, fps=fps)

    def trigger_attack(self) -> None:
        """Serangan normal; Knight menggunakan variasi tiga animasi."""

        if self.player.role == PlayerRole.KNIGHT:
            variants = ["attack", "attack2", "attack3"]
            available = [
                name for name in variants
                if self.anim_sprite.animations.get(name)
            ]

            if available:
                animation = available[
                    self.attack_variant % len(available)
                ]
                self.attack_variant += 1
            else:
                animation = "attack"

            self._start_attack(
                animation, "normal", distance=180.0, fps=12.0
            )
        else:
            self._start_attack(
                "attack", "normal", distance=70.0, fps=10.0
            )

    def trigger_skill(self) -> None:
        """Skill khusus dengan animasi serangan berbeda."""

        if self.player.role == PlayerRole.KNIGHT:
            self._start_attack(
                "attack3", "skill", distance=220.0, fps=15.0
            )
        else:
            self._start_attack(
                "attack2", "skill", distance=70.0, fps=11.0
            )

    def trigger_hurt(self) -> None:
        self.hurt_timer = 0.3

        if self.anim_sprite.animations.get("hurt"):
            self._play_if_available("hurt", False, 10.0)

    def trigger_defend(self) -> None:
        self.attack_timer = 0.0
        self.attack_offset = 0.0
        self.defend_timer = 0.65
        self.move_state = "idle"
        self._play_if_available("defend", False, 8.0)

    def trigger_jump(self) -> None:
        """Memulai lompatan ketika pemain menekan SPACE."""

        if not self.player.is_alive:
            return

        if not self.grounded:
            return

        if self.attack_timer > 0 or self.defend_timer > 0:
            return

        self.grounded = False
        self.jump_velocity = 430.0

        if self.anim_sprite.animations.get("jump"):
            self.anim_sprite.play("jump", loop=False, fps=10.0)

    def handle_movement(
        self,
        keys: pygame.key.ScancodeWrapper,
        dt: float,
    ) -> None:
        """Memproses gerakan bebas ketika giliran pemain aktif."""

        if not self.player.is_alive:
            return

        if (
            self.attack_timer > 0
            or self.defend_timer > 0
            or self.hurt_timer > 0
        ):
            return

        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        up = keys[pygame.K_w] or keys[pygame.K_UP]
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        speed = self.run_speed if running else self.move_speed
        dx = float(right) - float(left)
        dy = float(down) - float(up)

        if dx != 0:
            self.x += dx * speed * dt
            self.facing_right = dx > 0

        # Batasi karakter agar tetap di area arena di atas panel UI.
        self.x = max(0.0, min(self.x, SCREEN_WIDTH - self.width))
        self.y = max(90.0, min(self.y, 440.0 - self.height))

        self.anim_sprite.flip_x = not self.facing_right

        if dx != 0 or dy != 0:
            self.move_state = "run" if running else "walk"

            if self.grounded:
                animation = "run" if running else "walk"
                if not self.anim_sprite.animations.get(animation):
                    animation = "idle"

                if self.anim_sprite.current_anim != animation:
                    self._play_if_available(animation, True, 11.0)
        elif self.grounded:
            self.move_state = "idle"

            if self.anim_sprite.current_anim in ("walk", "run"):
                self._play_if_available("idle", True, 8.0)

    def update(self, dt: float) -> None:
        super().update(dt)

        if self.attack_timer > 0:
            self.attack_timer = max(0.0, self.attack_timer - dt)
            progress = 1.0 - self.attack_timer / self.attack_duration

            # Bergerak maju ketika serangan mencapai bagian tengah animasi.
            direction = 1 if self.facing_right else -1
            self.attack_offset = (
                direction
                * math.sin(progress * math.pi)
                * self.attack_distance
            )
        else:
            self.attack_offset = 0.0

        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)

        if self.defend_timer > 0:
            self.defend_timer = max(0.0, self.defend_timer - dt)

        # Fisika lompatan: jump_height adalah offset gambar, bukan posisi tanah.
        if not self.grounded:
            self.jump_height += self.jump_velocity * dt
            self.jump_velocity -= self.gravity * dt

            if self.jump_height <= 0:
                self.jump_height = 0.0
                self.jump_velocity = 0.0
                self.grounded = True

        self.anim_sprite.x = self.x
        self.anim_sprite.y = self.y
        self.anim_sprite.update(dt)

        if not self.player.is_alive:
            if self.anim_sprite.current_anim != "death":
                self.attack_timer = 0.0
                self.attack_offset = 0.0
                self._play_if_available("death", False, 8.0)
            return

        if self.attack_timer > 0:
            return

        if self.defend_timer > 0:
            if self.anim_sprite.current_anim != "defend":
                self._play_if_available("defend", False, 8.0)
            return

        if self.hurt_timer > 0:
            return

        if not self.grounded:
            if self.anim_sprite.current_anim != "jump":
                self._play_if_available("jump", False, 10.0)
            return

        if self.anim_sprite.is_finished or self.anim_sprite.current_anim in (
            "attack", "attack2", "attack3", "hurt", "defend", "jump"
        ):
            self._play_if_available("idle", True, 8.0)

    def render(self, surface: pygame.Surface) -> None:
        original_rect = self.anim_sprite.rect.copy()

        self.anim_sprite.rect.x = int(self.x + self.attack_offset)
        self.anim_sprite.rect.y = int(self.y - self.jump_height)

        try:
            self.anim_sprite.render(surface)

            if (
                self.hurt_timer > 0
                and int(self.hurt_timer * 20) % 2 == 0
            ):
                frames = self.anim_sprite.animations.get(
                    self.anim_sprite.current_anim, []
                )
                if frames:
                    width, height = frames[0].get_size()
                    tint = pygame.Surface(
                        (width, height), pygame.SRCALPHA
                    )
                    tint.fill((255, 50, 50, 75))
                    surface.blit(tint, self.anim_sprite.rect.topleft)

            # Efek benturan saat skill Knight.
            if self.attack_kind == "skill" and self.attack_timer > 0:
                progress = (
                    1.0 - self.attack_timer / self.attack_duration
                )

                if 0.42 <= progress <= 0.68:
                    direction = 1 if self.facing_right else -1
                    x = self.anim_sprite.rect.centerx + direction * 50
                    y = self.anim_sprite.rect.centery

                    pygame.draw.circle(
                        surface, (255, 220, 100), (x, y), 22, 3
                    )
                    pygame.draw.line(
                        surface,
                        (255, 255, 255),
                        (x - 15, y + 15),
                        (x + 18, y - 18),
                        4,
                    )
        finally:
            self.anim_sprite.rect = original_rect


class MonsterEntity(GameObject):
    """Entitas visual monster dengan efek serangan, ultimate, dan kematian."""

    def __init__(
        self,
        monster_model: Monster,
        x: float = 780,
        y: float = 140,
    ) -> None:
        super().__init__(x, y, 320, 320)

        self.monster = monster_model
        self.assets = AssetManager.get_instance()
        self.sprite = self.assets.get_monster_sprite(
            self.monster.name, size=(self.width, self.height)
        )

        self.current_state = "idle"
        self.state_timer = 0.0
        self.hurt_timer = 0.0
        self.time_counter = 0.0
        self.shake_offset: Tuple[int, int] = (0, 0)

    def trigger_idle(self) -> None:
        if self.monster.is_alive:
            self.current_state = "idle"
            self.state_timer = 0.0

    def trigger_attack(self) -> None:
        if self.monster.is_alive:
            self.current_state = "attack"
            self.state_timer = 0.55

    def trigger_ultimate(self) -> None:
        if self.monster.is_alive:
            self.current_state = "ultimate"
            self.state_timer = 0.95

    def trigger_death(self) -> None:
        self.current_state = "death"
        self.state_timer = 1.6

    def trigger_hurt(self) -> None:
        self.hurt_timer = 0.35

    def update(self, dt: float) -> None:
        super().update(dt)
        self.time_counter += dt

        if self.state_timer > 0:
            self.state_timer = max(0.0, self.state_timer - dt)
            if self.state_timer <= 0 and self.monster.is_alive:
                self.current_state = "idle"

        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
            offset_x = int(math.sin(self.hurt_timer * 40) * 10)
            self.shake_offset = (offset_x, 0)
        elif self.current_state == "idle" and self.monster.is_alive:
            float_y = int(math.sin(self.time_counter * 2.5) * 4)
            self.shake_offset = (0, float_y)
        else:
            self.shake_offset = (0, 0)

    def render(self, surface: pygame.Surface) -> None:
        pos_x = self.rect.x + self.shake_offset[0]
        pos_y = self.rect.y + self.shake_offset[1]

        if self.current_state == "attack" and self.monster.is_alive:
            progress = 1.0 - self.state_timer / 0.55
            pos_x -= int(math.sin(progress * math.pi) * 42)

        if self.monster.enraged and self.monster.is_alive:
            radius = 165 + int(math.sin(self.time_counter * 6) * 14)
            aura = pygame.Surface(
                (radius * 2, radius * 2), pygame.SRCALPHA
            )
            pygame.draw.circle(
                aura,
                (240, 50, 40, 65),
                (radius, radius),
                radius,
            )
            surface.blit(
                aura, (pos_x + 160 - radius, pos_y + 160 - radius)
            )

        if not self.monster.is_alive or self.current_state == "death":
            alpha = max(0.0, min(1.0, self.state_timer / 1.6))
            death_surface = self.sprite.copy()
            death_surface.set_alpha(int(alpha * 255))
            surface.blit(
                death_surface,
                (pos_x, pos_y + int((1.0 - alpha) * 35)),
            )
            return

        if self.hurt_timer > 0 and int(self.hurt_timer * 20) % 2 == 0:
            flash = self.sprite.copy()
            flash.fill(
                (220, 60, 60, 0),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
            surface.blit(flash, (pos_x, pos_y))
        else:
            surface.blit(self.sprite, (pos_x, pos_y))

        if self.current_state == "attack" and self.state_timer > 0.1:
            claw = pygame.Surface(
                (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
            )
            cx = pos_x + 40
            cy = pos_y + 120

            for ox, oy in [(-10, -20), (10, 0), (30, 20)]:
                points = [
                    (cx + ox + 30, cy + oy - 45),
                    (cx + ox - 25, cy + oy),
                    (cx + ox + 15, cy + oy + 45),
                ]
                pygame.draw.lines(
                    claw, (230, 40, 255, 200), False, points, 6
                )
                pygame.draw.lines(
                    claw, (255, 255, 255, 240), False, points, 2
                )

            surface.blit(claw, (0, 0))

        if self.current_state == "ultimate" and self.monster.is_alive:
            mouth_x = int(pos_x + 86)
            mouth_y = int(pos_y + 88)
            target_x = 180
            target_y = 310
            beam = pygame.Surface(
                (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
            )
            width = 60

            pygame.draw.polygon(
                beam,
                (240, 50, 180, 90),
                [
                    (mouth_x, mouth_y - 12),
                    (0, target_y - width - 30),
                    (0, target_y + width + 30),
                    (mouth_x, mouth_y + 12),
                ],
            )
            pygame.draw.polygon(
                beam,
                (160, 90, 255, 150),
                [
                    (mouth_x, mouth_y - 8),
                    (0, target_y - width),
                    (0, target_y + width),
                    (mouth_x, mouth_y + 8),
                ],
            )
            pygame.draw.line(
                beam, (220, 240, 255, 230),
                (mouth_x, mouth_y), (0, target_y), 18
            )
            pygame.draw.line(
                beam, (255, 255, 255, 255),
                (mouth_x, mouth_y), (0, target_y), 8
            )
            pygame.draw.circle(
                beam, (255, 100, 220, 200), (mouth_x, mouth_y), 24
            )
            pygame.draw.circle(
                beam, (255, 255, 255, 255), (mouth_x, mouth_y), 12
            )
            pygame.draw.circle(
                beam, (255, 120, 240, 130), (target_x, target_y), 65
            )
            pygame.draw.circle(
                beam, (255, 255, 255, 200), (target_x, target_y), 35
            )
            surface.blit(beam, (0, 0))