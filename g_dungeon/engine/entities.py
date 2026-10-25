"""Entitas visual, animasi, dan efek pertarungan G-Dungeons."""

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

    def __init__(self, x: float, y: float, width: int, height: int):
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
    """Sprite animasi dari kumpulan frame."""

    def __init__(
        self,
        x: float,
        y: float,
        animations: Dict[str, List[pygame.Surface]],
        default_anim: str = "idle",
        fps: float = 8.0,
    ):
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
        if not self.animations.get(anim_name):
            return

        # Jangan ulang animasi setiap frame jika animasinya sama.
        if (
            self.current_anim == anim_name
            and self.is_looping == loop
            and not self.is_finished
        ):
            if fps is not None:
                self.fps = fps
            return

        self.current_anim = anim_name
        self.current_frame_idx = 0.0
        self.is_looping = loop
        self.is_finished = False

        if fps is not None:
            self.fps = fps

    def restart(
        self,
        anim_name: str,
        loop: bool = False,
        fps: Optional[float] = None,
    ) -> None:
        """Paksa animasi dimulai dari frame pertama."""

        if not self.animations.get(anim_name):
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

        if not frames or (
            self.is_finished and not self.is_looping
        ):
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
    """Entitas visual pemain Knight dan Wizard/Mage."""

    def __init__(
        self,
        player_model: Player,
        x: float = 200,
        y: float = 300,
    ):
        super().__init__(x, y, 128, 128)

        self.player = player_model
        self.assets = AssetManager.get_instance()
        self.anim_sprite = self._create_animations(x, y)

        self.hurt_timer = 0.0
        self.defend_timer = 0.0

        # Serangan.
        self.attack_duration = 0.62
        self.attack_timer = 0.0
        self.attack_distance = 0.0
        self.attack_offset = 0.0
        self.attack_kind = "normal"
        self.attack_variant = 0

        # Gerakan.
        self.move_speed = 220.0
        self.run_speed = 340.0
        self.facing_right = True
        self.move_state = "idle"

        # Lompatan.
        self.jump_height = 0.0
        self.jump_velocity = 0.0
        self.jump_strength = 430.0
        self.gravity = 1150.0
        self.grounded = True

        # Efek visual Mage.
        self.projectile_color = (80, 190, 255)
        self.projectile_radius = 10

    def _load_sheet(
        self,
        path: str,
        frame_w: int,
        frame_h: int,
        scale: float,
    ) -> List[pygame.Surface]:
        try:
            return self.assets.load_sprite_sheet(
                path,
                frame_w,
                frame_h,
                scale,
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

            base = os.path.join(
                "players",
                "Wizard Pack",
                "Wizard Pack",
            )

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
                path,
                frame_w,
                frame_h,
                scale,
            )
            print(
                f"[PlayerEntity] {name}: "
                f"{len(animations[name])} frame"
            )

        if not animations.get("idle"):
            placeholder = pygame.Surface(
                (128, 128),
                pygame.SRCALPHA,
            )
            pygame.draw.rect(
                placeholder,
                (220, 220, 220),
                (20, 10, 88, 118),
            )
            animations["idle"] = [placeholder]

        return AnimatedSprite(
            x,
            y,
            animations,
            default_anim="idle",
            fps=8.0,
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

        # Efek proyektil menggunakan animasi serangan Mage.
        if kind == "ranged":
            self.projectile_color = (80, 190, 255)
            self.projectile_radius = 10
        elif kind == "ranged_skill":
            self.projectile_color = (190, 100, 255)
            self.projectile_radius = 17

        self.anim_sprite.restart(
            animation_name,
            loop=False,
            fps=fps,
        )

    def trigger_attack(self) -> None:
        """Serangan biasa: Knight menyerang dengan pedang, Mage dari jauh."""

        if self.player.role == PlayerRole.KNIGHT:
            variants = ["attack", "attack2", "attack3"]

            available = [
                name
                for name in variants
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
                animation_name=animation,
                kind="normal",
                distance=180.0,
                fps=12.0,
            )
        else:
            # Mage tetap di tempat; proyektil bergerak ke arah monster.
            self._start_attack(
                animation_name="attack",
                kind="ranged",
                distance=0.0,
                fps=10.0,
            )

    def trigger_skill(self) -> None:
        """Skill khusus Knight dan Mage."""

        if self.player.role == PlayerRole.KNIGHT:
            self._start_attack(
                animation_name="attack3",
                kind="skill",
                distance=220.0,
                fps=15.0,
            )
        else:
            self._start_attack(
                animation_name="attack2",
                kind="ranged_skill",
                distance=0.0,
                fps=11.0,
            )

    def trigger_hurt(self) -> None:
        self.hurt_timer = 0.3

        if self.anim_sprite.animations.get("hurt"):
            self.anim_sprite.restart(
                "hurt",
                loop=False,
                fps=10.0,
            )

    def trigger_defend(self) -> None:
        self.attack_timer = 0.0
        self.attack_offset = 0.0
        self.defend_timer = 0.65
        self.move_state = "idle"

        if self.anim_sprite.animations.get("defend"):
            self.anim_sprite.restart(
                "defend",
                loop=False,
                fps=8.0,
            )

    def trigger_jump(self) -> None:
        """Melompat jika pemain sedang menyentuh tanah."""

        if not self.player.is_alive:
            return

        if not self.grounded:
            return

        if (
            self.attack_timer > 0
            or self.defend_timer > 0
            or self.hurt_timer > 0
        ):
            return

        self.grounded = False
        self.jump_velocity = self.jump_strength

        if self.anim_sprite.animations.get("jump"):
            self.anim_sprite.restart(
                "jump",
                loop=False,
                fps=10.0,
            )

    def handle_movement(
        self,
        keys: pygame.key.ScancodeWrapper,
        dt: float,
    ) -> None:
        """Gerakan bebas pemain selama giliran pemain."""

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

        running = (
            keys[pygame.K_LSHIFT]
            or keys[pygame.K_RSHIFT]
        )

        speed = self.run_speed if running else self.move_speed
        dx = float(right) - float(left)
        dy = float(down) - float(up)

        if dx != 0:
            self.x += dx * speed * dt
            self.facing_right = dx > 0

        if dy != 0:
            self.y += dy * speed * dt

        # Batasi karakter ke area arena, bukan panel bawah.
        self.x = max(
            0.0,
            min(self.x, SCREEN_WIDTH - self.width),
        )
        self.y = max(
            90.0,
            min(self.y, 440.0 - self.height),
        )

        self.anim_sprite.flip_x = not self.facing_right

        if dx != 0 or dy != 0:
            self.move_state = "run" if running else "walk"

            if self.grounded:
                animation = "run" if running else "walk"

                if not self.anim_sprite.animations.get(animation):
                    animation = "idle"

                if self.anim_sprite.current_anim != animation:
                    self.anim_sprite.restart(
                        animation,
                        loop=True,
                        fps=11.0,
                    )
        elif self.grounded:
            self.move_state = "idle"

            if self.anim_sprite.current_anim in ("walk", "run"):
                self.anim_sprite.restart(
                    "idle",
                    loop=True,
                    fps=8.0,
                )

    def update(self, dt: float) -> None:
        super().update(dt)

        # Animasi serangan maju lalu kembali ke posisi awal.
        if self.attack_timer > 0:
            self.attack_timer = max(
                0.0,
                self.attack_timer - dt,
            )

            progress = 1.0 - (
                self.attack_timer / self.attack_duration
            )

            direction = 1 if self.facing_right else -1

            self.attack_offset = (
                direction
                * math.sin(progress * math.pi)
                * self.attack_distance
            )
        else:
            self.attack_offset = 0.0

        if self.hurt_timer > 0:
            self.hurt_timer = max(
                0.0,
                self.hurt_timer - dt,
            )

        if self.defend_timer > 0:
            self.defend_timer = max(
                0.0,
                self.defend_timer - dt,
            )

        # Fisika lompatan.
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

                if self.anim_sprite.animations.get("death"):
                    self.anim_sprite.restart(
                        "death",
                        loop=False,
                        fps=8.0,
                    )
            return

        if self.attack_timer > 0:
            return

        if self.defend_timer > 0:
            if self.anim_sprite.current_anim != "defend":
                self._play_if_available(
                    "defend",
                    False,
                    8.0,
                )
            return

        if self.hurt_timer > 0:
            return

        if not self.grounded:
            if self.anim_sprite.current_anim != "jump":
                self.anim_sprite.restart(
                    "jump",
                    loop=False,
                    fps=10.0,
                )
            return

        # Setelah mendarat, kembalikan ke idle jika animasi lompat selesai.
        if self.anim_sprite.is_finished or self.anim_sprite.current_anim in (
            "attack",
            "attack2",
            "attack3",
            "hurt",
            "defend",
            "jump",
        ):
            self.anim_sprite.restart(
                "idle",
                loop=True,
                fps=8.0,
            )

    def _render_mage_projectile(
        self,
        surface: pygame.Surface,
    ) -> None:
        """Efek proyektil Mage yang meluncur ke arah hadapnya."""

        if self.attack_timer <= 0:
            return

        if self.attack_kind not in ("ranged", "ranged_skill"):
            return

        progress = 1.0 - (
            self.attack_timer / self.attack_duration
        )

        direction = 1 if self.facing_right else -1

        start_x = self.anim_sprite.rect.centerx
        start_y = self.anim_sprite.rect.centery - 15

        # Proyektil bergerak sepanjang arena.
        projectile_distance = 520.0 * min(
            progress * 2.5,
            1.0,
        )

        projectile_x = int(
            start_x + direction * projectile_distance
        )

        color = self.projectile_color
        radius = self.projectile_radius

        # Jejak sihir.
        pygame.draw.line(
            surface,
            color,
            (start_x, start_y),
            (projectile_x, start_y),
            5,
        )

        # Aura luar.
        pygame.draw.circle(
            surface,
            color,
            (projectile_x, start_y),
            radius + 7,
            2,
        )

        # Inti proyektil.
        pygame.draw.circle(
            surface,
            color,
            (projectile_x, start_y),
            radius,
        )

        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (projectile_x, start_y),
            max(3, radius // 2),
        )

    def render(self, surface: pygame.Surface) -> None:
        original_rect = self.anim_sprite.rect.copy()

        self.anim_sprite.rect.x = int(
            self.x + self.attack_offset
        )
        self.anim_sprite.rect.y = int(
            self.y - self.jump_height
        )

        try:
            self.anim_sprite.render(surface)

            # Efek saat pemain terkena serangan.
            if (
                self.hurt_timer > 0
                and int(self.hurt_timer * 20) % 2 == 0
            ):
                frames = self.anim_sprite.animations.get(
                    self.anim_sprite.current_anim,
                    [],
                )

                if frames:
                    width, height = frames[0].get_size()

                    tint = pygame.Surface(
                        (width, height),
                        pygame.SRCALPHA,
                    )
                    tint.fill((255, 50, 50, 75))

                    surface.blit(
                        tint,
                        self.anim_sprite.rect.topleft,
                    )

            # Efek tebasan skill Knight.
            if (
                self.player.role == PlayerRole.KNIGHT
                and self.attack_kind == "skill"
                and self.attack_timer > 0
            ):
                progress = 1.0 - (
                    self.attack_timer / self.attack_duration
                )

                if 0.35 <= progress <= 0.72:
                    direction = 1 if self.facing_right else -1

                    x = (
                        self.anim_sprite.rect.centerx
                        + direction * 55
                    )
                    y = self.anim_sprite.rect.centery

                    pygame.draw.arc(
                        surface,
                        (255, 210, 70),
                        pygame.Rect(x - 35, y - 35, 70, 70),
                        0.4,
                        5.5,
                        5,
                    )

                    pygame.draw.line(
                        surface,
                        (255, 255, 255),
                        (x - 20, y + 15),
                        (x + 20, y - 15),
                        4,
                    )

            # Efek proyektil Mage.
            if self.player.role == PlayerRole.MAGE:
                self._render_mage_projectile(surface)

        finally:
            self.anim_sprite.rect = original_rect


class MonsterEntity(GameObject):
    """Entitas monster dengan animasi gerak dan efek pertarungan."""

    def __init__(
        self,
        monster_model: Monster,
        x: float = 780,
        y: float = 140,
    ):
        # Ukuran visual monster disesuaikan agar tidak memenuhi arena.
        super().__init__(x, y, 280, 280)

        self.monster = monster_model
        self.assets = AssetManager.get_instance()

        # Pilih sprite sheet berdasarkan ruangan/monster, lalu animasikan 6 frame idle.
        # Shadow Crypt tetap memakai data/AI Shadow Wraith, tetapi visualnya Frost.
        self.idle_frames = self._load_monster_idle_frames()

        if self.idle_frames:
            self.sprite = self.idle_frames[0]
        else:
            self.sprite = self.assets.get_monster_sprite(
                self.monster.name,
                size=(self.width, self.height),
            )

        self.current_state = "idle"
        self.state_timer = 0.0
        self.hurt_timer = 0.0
        self.time_counter = 0.0

        self.shake_offset: Tuple[int, int] = (0, 0)

        self.attack_duration = 0.55
        self.ultimate_duration = 0.95
        self.death_duration = 1.6

    
    def _load_monster_idle_frames(self) -> List[pygame.Surface]:
        """Memuat dan memotong enam frame idle dari sprite sheet monster."""
        room_name = (getattr(self.monster, "room_name", "") or "").lower()
        monster_name = (getattr(self.monster, "name", "") or "").lower()

        # Ruangan diprioritaskan agar Shadow Wraith di Shadow Crypt tampil sebagai Frost.
        if "ancient armory" in room_name or "skeleton" in monster_name:
            filename = "idle_skeleton.png"
        elif "shadow crypt" in room_name or "frost" in monster_name:
            filename = "idle_frost.png"
        elif "magma forge" in room_name or "magma" in monster_name or "golem" in monster_name:
            filename = "idle_magma.png"
        elif "crystal cavern" in room_name or "slime" in monster_name:
            filename = "idle_slime.png"
        elif "throne of extinction" in room_name or "kaiju" in monster_name or "godzilla" in monster_name:
            filename = "idle_godzilla.png"
        else:
            return []

        sheet = self.assets.get_image(filename)
        sheet_width, sheet_height = sheet.get_size()
        if sheet_width < 6 or sheet_height < 1:
            return []

        frames: List[pygame.Surface] = []
        for i in range(6):
            x0 = round(i * sheet_width / 6)
            x1 = round((i + 1) * sheet_width / 6)
            cell = sheet.subsurface(
                pygame.Rect(x0, 0, x1 - x0, sheet_height)
            ).copy()

            # Potong transparansi di sekeliling monster agar karakter terlihat besar.
            bounds = cell.get_bounding_rect(min_alpha=8)
            if bounds.width <= 0 or bounds.height <= 0:
                continue
            cropped = cell.subsurface(bounds).copy()

            # Pertahankan proporsi, sisakan sedikit ruang di dalam kanvas combat.
            scale = min(
                250 / max(1, cropped.get_width()),
                265 / max(1, cropped.get_height()),
            )
            new_size = (
                max(1, round(cropped.get_width() * scale)),
                max(1, round(cropped.get_height() * scale)),
            )
            scaled = pygame.transform.scale(cropped, new_size)

            canvas = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            canvas.blit(
                scaled,
                ((self.width - new_size[0]) // 2,
                 self.height - new_size[1]),
            )
            frames.append(canvas)

        return frames

    def trigger_idle(self) -> None:
        if self.monster.is_alive:
            self.current_state = "idle"
            self.state_timer = 0.0

    def trigger_attack(self) -> None:
        """Monster memasuki animasi serangan."""

        if self.monster.is_alive:
            self.current_state = "attack"
            self.state_timer = self.attack_duration

    def trigger_ultimate(self) -> None:
        if self.monster.is_alive:
            self.current_state = "ultimate"
            self.state_timer = self.ultimate_duration

    def trigger_death(self) -> None:
        self.current_state = "death"
        self.state_timer = self.death_duration

    def trigger_hurt(self) -> None:
        self.hurt_timer = 0.35

    def update(self, dt: float) -> None:
        super().update(dt)

        self.time_counter += dt

        if self.state_timer > 0:
            self.state_timer = max(
                0.0,
                self.state_timer - dt,
            )

            if (
                self.state_timer <= 0
                and self.monster.is_alive
            ):
                self.current_state = "idle"

        if self.hurt_timer > 0:
            self.hurt_timer = max(
                0.0,
                self.hurt_timer - dt,
            )

            shake_x = int(
                math.sin(self.hurt_timer * 40) * 8
            )
            self.shake_offset = (shake_x, 0)

        elif (
            self.current_state == "idle"
            and self.monster.is_alive
        ):
            # Gerakan napas monster saat idle.
            float_y = int(
                math.sin(self.time_counter * 2.5) * 4
            )
            self.shake_offset = (0, float_y)

        else:
            self.shake_offset = (0, 0)

    def _render_aura(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
    ) -> None:
        """Aura merah saat monster memasuki rage mode."""

        if not self.monster.enraged or not self.monster.is_alive:
            return

        radius = 145 + int(
            math.sin(self.time_counter * 6) * 10
        )

        aura = pygame.Surface(
            (radius * 2, radius * 2),
            pygame.SRCALPHA,
        )

        pygame.draw.circle(
            aura,
            (240, 50, 40, 55),
            (radius, radius),
            radius,
        )

        pygame.draw.circle(
            aura,
            (255, 100, 30, 100),
            (radius, radius),
            radius - 20,
            3,
        )

        surface.blit(
            aura,
            (
                x + self.width // 2 - radius,
                y + self.height // 2 - radius,
            ),
        )

    def _render_attack_effect(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
    ) -> None:
        """Efek cakar berwarna ungu ketika monster menyerang."""

        if (
            self.current_state != "attack"
            or self.state_timer <= 0.1
        ):
            return

        effect = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SRCALPHA,
        )

        cx = x + 35
        cy = y + 120

        for ox, oy in [(-10, -20), (10, 0), (30, 20)]:
            points = [
                (cx + ox + 30, cy + oy - 45),
                (cx + ox - 25, cy + oy),
                (cx + ox + 15, cy + oy + 45),
            ]

            pygame.draw.lines(
                effect,
                (230, 40, 255, 200),
                False,
                points,
                6,
            )

            pygame.draw.lines(
                effect,
                (255, 255, 255, 230),
                False,
                points,
                2,
            )

        surface.blit(effect, (0, 0))

    def _render_ultimate(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
    ) -> None:
        """Efek Atomic Breath ketika monster menggunakan ultimate."""

        if (
            self.current_state != "ultimate"
            or not self.monster.is_alive
        ):
            return

        mouth_x = int(x + 76)
        mouth_y = int(y + 78)

        target_x = 180
        target_y = 310
        width = 60

        beam = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SRCALPHA,
        )

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
            beam,
            (220, 240, 255, 230),
            (mouth_x, mouth_y),
            (0, target_y),
            18,
        )

        pygame.draw.line(
            beam,
            (255, 255, 255, 255),
            (mouth_x, mouth_y),
            (0, target_y),
            8,
        )

        pygame.draw.circle(
            beam,
            (255, 100, 220, 200),
            (mouth_x, mouth_y),
            24,
        )

        pygame.draw.circle(
            beam,
            (255, 255, 255, 255),
            (mouth_x, mouth_y),
            12,
        )

        pygame.draw.circle(
            beam,
            (255, 120, 240, 130),
            (target_x, target_y),
            65,
        )

        pygame.draw.circle(
            beam,
            (255, 255, 255, 200),
            (target_x, target_y),
            35,
        )

        surface.blit(beam, (0, 0))

    def render(self, surface: pygame.Surface) -> None:
        x = self.rect.x + self.shake_offset[0]
        y = self.rect.y + self.shake_offset[1]
        
        # Animasi idle Skeleton Guard: 6 frame, 5 FPS.
        display_sprite = self.sprite

        if (
            self.idle_frames
            and self.current_state == "idle"
            and self.hurt_timer <= 0
            and self.monster.is_alive
        ):
            frame_index = int(self.time_counter * 5) % len(
                self.idle_frames
            )
            display_sprite = self.idle_frames[frame_index]

        # Monster bergerak maju ketika menyerang.
        if (
            self.current_state == "attack"
            and self.monster.is_alive
        ):
            progress = 1.0 - (
                self.state_timer / self.attack_duration
            )

            x -= int(
                math.sin(progress * math.pi) * 35
            )

        # Aura monster.
        self._render_aura(surface, x, y)

        # Animasi kematian.
        if (
            not self.monster.is_alive
            or self.current_state == "death"
        ):
            alpha = max(
                0.0,
                min(
                    1.0,
                    self.state_timer / self.death_duration,
                ),
            )

            death_sprite = self.sprite.copy()
            death_sprite.set_alpha(int(alpha * 255))

            surface.blit(
                death_sprite,
                (
                    x,
                    y + int((1.0 - alpha) * 35),
                ),
            )
            return

        # Flash merah saat terkena damage.
        if (
            self.hurt_timer > 0
            and int(self.hurt_timer * 20) % 2 == 0
        ):
            flash = self.sprite.copy()
            flash.fill(
                (220, 60, 60, 0),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
            surface.blit(flash, (x, y))
        else:
            surface.blit(display_sprite, (x, y))

        self._render_attack_effect(surface, x, y)
        self._render_ultimate(surface, x, y)