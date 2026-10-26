"""Entitas visual, animasi, dan efek pertarungan G-Dungeons."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math
import os
import pygame

from engine.assets import AssetManager
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from core.player import Player, PlayerRole
from core.monster import Monster


# ---------------------------------------------------------------------------
# Konfigurasi tangkis pemain.
# ---------------------------------------------------------------------------
GUARD_WINDOW = 0.35             # lama jendela tangkis (detik)
GUARD_LOCK = 0.45               # lama pemain tertahan saat bertahan
GUARD_COOLDOWN = 0.90           # jeda sebelum bisa menangkis lagi


@dataclass(frozen=True)
class AttackProfile:
    """Data serangan proyektil satu monster (animasi + objek yang meluncur).

    Menambah monster baru cukup dengan menambah satu entri di
    MONSTER_ATTACK_PROFILES. Jika file gambar belum ada, monster otomatis
    memakai serangan lama (damage instan) tanpa error.
    """

    attack_file: str                     # sprite sheet animasi menyerang
    projectile_file: str                 # sprite sheet objek serangan
    actions: Tuple[str, ...] = ("attack",)  # aksi AI yang memakai proyektil

    # Jumlah frame; None = deteksi otomatis lewat kolom kosong di sheet.
    attack_frames: Optional[int] = None
    projectile_frames: Optional[int] = None

    launch_frame: int = 3                # indeks frame (0-based) proyektil muncul
    attack_fps: float = 8.0
    hold: float = 0.25                   # jeda setelah frame terakhir

    projectile_fps: float = 12.0
    projectile_height: int = 130         # tinggi sprite proyektil di layar (px)
    projectile_speed: float = 380.0      # px/detik (rage mode x1.25)
    flip_projectile: bool = False        # True bila gambar aslinya menghadap kanan
    projectile_align: str = "center"     # "center" atau "lead" (sisi depan di kiri)

    # Hitbox proyektil sebagai pecahan ukuran sprite.
    hitbox_w: float = 0.50
    hitbox_h: float = 0.45
    hitbox_left: Optional[float] = None  # None = di tengah; 0.04 = di sisi depan

    # Titik muncul di frame peluncuran: tepi kiri badan, tinggi relatif bbox.
    spawn_y_ratio: float = 0.5           # 0 = atas, 1 = bawah
    spawn_y_offset: int = 0

    # Penjajaran frame serangan terhadap idle: "center" atau "right".
    attack_align: str = "center"

    # Radius pencarian garis potong antar-frame (jika jumlah frame diisi).
    attack_split_radius: int = 90
    projectile_split_radius: int = 60


# Kunci = nama file sprite idle monster.
MONSTER_ATTACK_PROFILES: Dict[str, AttackProfile] = {
    # Shadow Wraith (visual Frost): tebasan es dari ujung pedang.
    "idle_frost.png": AttackProfile(
        attack_file="attack_frost.png",
        projectile_file="object_acttack_frost.png",  # nama file asli (typo)
        actions=("attack", "lifesteal"),
        attack_frames=6,
        projectile_frames=4,
        launch_frame=3,
        projectile_align="lead",
        hitbox_left=0.04,
        spawn_y_ratio=1.0,
        spawn_y_offset=-18,
        attack_align="right",
    ),
    # Skeleton Guard: jumlah frame dideteksi otomatis.
    "idle_skeleton.png": AttackProfile(
        attack_file="attack_skeleton.png",
        projectile_file="object_attack_skeleton.png",
        actions=("attack",),
        launch_frame=3,
        projectile_height=110,
        projectile_speed=400.0,
    ),
    # Crystal Slime: semburan asam.
    "idle_slime.png": AttackProfile(
        attack_file="attack_slime.png",
        projectile_file="object_attack_slime.png",
        actions=("attack",),
        launch_frame=2,
        projectile_height=90,
        projectile_speed=340.0,
    ),
    # Magma Golem: bola lava; Hantaman Berat juga memakai proyektil.
    "idle_magma.png": AttackProfile(
        attack_file="attack_magma.png",
        projectile_file="object_attack_magma.png",
        actions=("attack", "heavy_slam"),
        launch_frame=3,
        projectile_height=140,
        projectile_speed=330.0,
    ),
    # Corrupted Crystal Kaiju (Boss): serangan biasa; Atomic Breath tetap sinar.
    "idle_godzilla.png": AttackProfile(
        attack_file="attack_godzilla.png",
        projectile_file="object_attack_godzilla.png",
        actions=("attack",),
        launch_frame=3,
        projectile_height=150,
        projectile_speed=420.0,
    ),
}


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

        # Tangkis (parry) terhadap proyektil musuh.
        self.guard_window = 0.0
        self.guard_cooldown = 0.0
        self._idle_bounds: Optional[pygame.Rect] = None

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

    def trigger_guard(self) -> bool:
        """Angkat pertahanan untuk menangkis proyektil (jendela singkat)."""

        if not self.player.is_alive:
            return False

        if (
            self.guard_cooldown > 0
            or not self.grounded
            or self.hurt_timer > 0
            or self.attack_timer > 0
        ):
            return False

        # Selalu menghadap musuh (monster berada di sisi kanan arena).
        self.facing_right = True
        self.anim_sprite.flip_x = False

        self.guard_window = GUARD_WINDOW
        self.guard_cooldown = GUARD_COOLDOWN
        self.defend_timer = GUARD_LOCK
        self.move_state = "idle"

        if self.anim_sprite.animations.get("defend"):
            self.anim_sprite.restart("defend", loop=False, fps=10.0)

        return True

    def get_hurtbox(self) -> pygame.Rect:
        """Kotak tabrakan pemain (lebih kecil dari kanvas sprite)."""

        frames = self.anim_sprite.animations.get("idle") or []

        if self._idle_bounds is None:
            if frames:
                bounds = frames[0].get_bounding_rect(min_alpha=40)
                if bounds.width <= 0 or bounds.height <= 0:
                    bounds = pygame.Rect(0, 0, *frames[0].get_size())
                self._idle_bounds = bounds
            else:
                self._idle_bounds = pygame.Rect(
                    0, 0, self.width, self.height
                )

        bounds = self._idle_bounds.copy()

        if self.anim_sprite.flip_x and frames:
            bounds.x = frames[0].get_width() - bounds.right

        # Persempit sisi kiri-kanan dan atas; kaki tetap sebagai acuan.
        shrink_x = int(bounds.width * 0.30)
        shrink_top = int(bounds.height * 0.10)

        left = int(self.x + bounds.x + shrink_x // 2)
        top = int(self.y - self.jump_height + bounds.y + shrink_top)

        return pygame.Rect(
            left,
            top,
            max(8, bounds.width - shrink_x),
            max(8, bounds.height - shrink_top),
        )

    def _render_guard_effect(self, surface: pygame.Surface) -> None:
        """Perisai cahaya di depan pemain selama jendela tangkis aktif."""

        if self.guard_window <= 0:
            return

        hurtbox = self.get_hurtbox()
        strength = max(0.0, min(1.0, self.guard_window / GUARD_WINDOW))

        half_h = max(60, hurtbox.height // 2 + 22)
        layer = pygame.Surface((64, half_h * 2 + 8), pygame.SRCALPHA)

        shield_rect = pygame.Rect(2, 4, 56, half_h * 2)
        pygame.draw.ellipse(
            layer, (90, 180, 255, int(70 * strength) + 30), shield_rect
        )
        pygame.draw.ellipse(
            layer, (200, 240, 255, int(220 * strength) + 30), shield_rect, 4
        )

        surface.blit(
            layer,
            (hurtbox.right - 6, hurtbox.centery - layer.get_height() // 2),
        )

    
    def handle_movement(
        self,
        keys: pygame.key.ScancodeWrapper,
        dt: float,
    ) -> None:
        """Gerakan kiri-kanan dan lompatan saja."""

        if not self.player.is_alive:
            return

        if (
            self.attack_timer > 0
            or self.defend_timer > 0
            or self.hurt_timer > 0
        ):
            return

        # Input horizontal saja.
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        running = (
            keys[pygame.K_LSHIFT]
            or keys[pygame.K_RSHIFT]
        )

        speed = self.run_speed if running else self.move_speed
        dx = float(right) - float(left)

        # Gerakkan karakter ke kiri atau kanan.
        if dx != 0:
            self.x += dx * speed * dt
            self.facing_right = dx > 0

        # Batasi posisi horizontal dalam arena.
        self.x = max(
            0.0,
            min(self.x, SCREEN_WIDTH - self.width),
        )

        # Tidak ada perubahan self.y untuk gerakan horizontal.
        self.anim_sprite.flip_x = not self.facing_right

        # Animasi berjalan atau diam.
        if dx != 0 and self.grounded:
            animation = "run" if running else "walk"
            self.move_state = animation

            if not self.anim_sprite.animations.get(animation):
                animation = "idle"

            if self.anim_sprite.current_anim != animation:
                self.anim_sprite.restart(
                    animation,
                    loop=True,
                    fps=11.0,
                )

        elif dx == 0 and self.grounded:
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

        if self.guard_window > 0:
            self.guard_window = max(0.0, self.guard_window - dt)

        if self.guard_cooldown > 0:
            self.guard_cooldown = max(0.0, self.guard_cooldown - dt)

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

            # Efek perisai saat menangkis.
            self._render_guard_effect(surface)

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

        # Data serangan proyektil (diisi bila profil + gambar tersedia).
        self.idle_filename = ""
        self.attack_profile: Optional[AttackProfile] = None
        self.attack_frames: List[pygame.Surface] = []
        self.attack_bounds: List[pygame.Rect] = []
        self.projectile_frames: List[pygame.Surface] = []
        self.attack_time = 0.0
        self.projectile_launched = False

        # Pilih sprite sheet berdasarkan ruangan/monster, lalu animasikan 6 frame idle.
        # Shadow Crypt tetap memakai data/AI Shadow Wraith, tetapi visualnya Frost.
        self.idle_frames = self._load_monster_idle_frames()

        self._load_attack_assets()

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

        self.idle_filename = filename
        self.attack_profile = MONSTER_ATTACK_PROFILES.get(filename)

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

    # ------------------------------------------------------------------
    # Serangan proyektil (animasi menyerang + objek yang meluncur)
    # ------------------------------------------------------------------
    @staticmethod
    def _split_sheet(
        sheet: pygame.Surface,
        count: int,
        radius: int,
    ) -> List[int]:
        """Cari garis potong antar-frame pada kolom paling kosong."""

        width, height = sheet.get_size()
        mask = pygame.mask.from_surface(sheet, 20)
        strip = pygame.mask.Mask((1, height), fill=True)

        cuts = [0]
        for k in range(1, count):
            guess = round(k * width / count)
            low = max(cuts[-1] + 1, guess - radius)
            high = min(width - 1, guess + radius)

            best_x, best_value = guess, None
            for x in range(low, high + 1):
                value = mask.overlap_area(strip, (x, 0))
                if best_value is None or value < best_value:
                    best_x, best_value = x, value

            cuts.append(best_x)

        cuts.append(width)
        return cuts

    @staticmethod
    def _auto_cuts(sheet: pygame.Surface) -> List[int]:
        """Deteksi frame otomatis pada sprite sheet.

        Mencoba beberapa lebar celah kosong (dari kecil ke besar) lalu memilih
        pembagian yang jarak antar-frame-nya paling seragam. Cara ini tahan
        terhadap sprite bergaris tipis / efek glow yang celahnya tidak rata.
        Bila gagal total, sheet dibagi rata berdasarkan rasio lebar : tinggi.
        """

        width, height = sheet.get_size()
        mask = pygame.mask.from_surface(sheet, 20)
        strip = pygame.mask.Mask((1, height), fill=True)
        filled = [mask.overlap_area(strip, (x, 0)) > 0 for x in range(width)]

        def find_runs(min_gap: int) -> List[Tuple[int, int]]:
            runs: List[Tuple[int, int]] = []
            start: Optional[int] = None
            last = 0
            gap = 0
            for x, has_pixel in enumerate(filled):
                if has_pixel:
                    if start is None:
                        start = x
                    last = x
                    gap = 0
                elif start is not None:
                    gap += 1
                    if gap >= min_gap:
                        runs.append((start, last + 1))
                        start = None
            if start is not None:
                runs.append((start, last + 1))
            return [r for r in runs if r[1] - r[0] >= 8]

        best_runs: Optional[List[Tuple[int, int]]] = None
        best_key: Optional[Tuple[float, int]] = None
        for min_gap in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48):
            runs = find_runs(min_gap)
            if not 2 <= len(runs) <= 12:
                continue
            centers = [(a + b) / 2 for a, b in runs]
            spacing = [c2 - c1 for c1, c2 in zip(centers, centers[1:])]
            mean = sum(spacing) / len(spacing)
            var = sum((d - mean) ** 2 for d in spacing) / len(spacing)
            cv = (var ** 0.5) / mean if mean > 0 else 9.0
            key = (round(cv, 2), len(runs))
            if best_key is None or key < best_key:
                best_key, best_runs = key, runs

        if best_runs is None:
            count = round(width / max(1, height))
            if count < 2:
                raise ValueError(
                    "jumlah frame tidak terdeteksi otomatis; isi "
                    "attack_frames / projectile_frames di AttackProfile"
                )
            return [round(i * width / count) for i in range(count + 1)]

        cuts = [0]
        for a, b in zip(best_runs, best_runs[1:]):
            cuts.append((a[1] + b[0]) // 2)
        cuts.append(width)
        return cuts

    def _frame_cuts(
        self,
        sheet: pygame.Surface,
        count: Optional[int],
        radius: int,
    ) -> List[int]:
        if count is None:
            return self._auto_cuts(sheet)
        return self._split_sheet(sheet, count, radius)

    def _require_asset(self, filename: str) -> pygame.Surface:
        if filename.lower() not in self.assets.asset_map:
            raise ValueError(f"{filename} tidak ditemukan")
        return self.assets.get_image(filename)

    def _load_attack_assets(self) -> None:
        """Memuat animasi serangan dan sprite proyektil sesuai profil monster."""

        profile = self.attack_profile
        if profile is None:
            return

        try:
            self.attack_frames, self.attack_bounds = (
                self._build_attack_frames(profile)
            )
            self.projectile_frames = self._build_projectile_frames(profile)
            print(
                f"[MonsterEntity] {self.monster.name}: "
                f"{len(self.attack_frames)} frame serangan, "
                f"{len(self.projectile_frames)} frame proyektil."
            )
        except (pygame.error, ValueError) as exc:
            print(
                f"[MonsterEntity] {self.monster.name}: serangan proyektil "
                f"dinonaktifkan ({exc}); memakai serangan biasa."
            )
            self.attack_frames = []
            self.attack_bounds = []
            self.projectile_frames = []

    def _build_attack_frames(
        self,
        profile: AttackProfile,
    ) -> Tuple[List[pygame.Surface], List[pygame.Rect]]:
        attack_sheet = self._require_asset(profile.attack_file)

        # Skala acuan = rata-rata skala frame idle agar ukuran konsisten.
        idle_sheet = self.assets.get_image(self.idle_filename)
        idle_w, idle_h = idle_sheet.get_size()
        scales: List[float] = []
        widths: List[float] = []
        for i in range(6):
            x0 = round(i * idle_w / 6)
            x1 = round((i + 1) * idle_w / 6)
            cell = idle_sheet.subsurface(pygame.Rect(x0, 0, x1 - x0, idle_h))
            box = cell.get_bounding_rect(min_alpha=8)
            if box.width > 0 and box.height > 0:
                s = min(250 / box.width, 265 / box.height)
                scales.append(s)
                widths.append(box.width * s)

        if not scales:
            raise ValueError("sprite idle kosong")

        scale = sum(scales) / len(scales)
        right_anchor = round(self.width / 2 + (sum(widths) / len(widths)) / 2)

        cuts = self._frame_cuts(
            attack_sheet, profile.attack_frames, profile.attack_split_radius
        )
        sheet_h = attack_sheet.get_height()

        frames: List[pygame.Surface] = []
        bounds: List[pygame.Rect] = []

        for i in range(len(cuts) - 1):
            cell = attack_sheet.subsurface(
                pygame.Rect(cuts[i], 0, cuts[i + 1] - cuts[i], sheet_h)
            )
            box = cell.get_bounding_rect(min_alpha=8)
            if box.width <= 0 or box.height <= 0:
                raise ValueError(f"frame {i} di {profile.attack_file} kosong")

            cropped = cell.subsurface(box).copy()
            size = (
                max(1, round(cropped.get_width() * scale)),
                max(1, round(cropped.get_height() * scale)),
            )
            scaled = pygame.transform.scale(cropped, size)

            canvas = pygame.Surface(
                (self.width, self.height), pygame.SRCALPHA
            )

            if profile.attack_align == "right":
                x = right_anchor - size[0]
            else:
                x = (self.width - size[0]) // 2

            # Kaki sejajar dasar kanvas seperti frame idle.
            canvas.blit(scaled, (x, self.height - size[1]))

            frames.append(canvas)
            bounds.append(canvas.get_bounding_rect(min_alpha=40))

        return frames, bounds

    def _build_projectile_frames(
        self,
        profile: AttackProfile,
    ) -> List[pygame.Surface]:
        sheet = self._require_asset(profile.projectile_file)

        cuts = self._frame_cuts(
            sheet, profile.projectile_frames, profile.projectile_split_radius
        )
        sheet_h = sheet.get_height()

        crops: List[pygame.Surface] = []
        for i in range(len(cuts) - 1):
            cell = sheet.subsurface(
                pygame.Rect(cuts[i], 0, cuts[i + 1] - cuts[i], sheet_h)
            )
            box = cell.get_bounding_rect(min_alpha=12)
            if box.width <= 0 or box.height <= 0:
                raise ValueError(
                    f"frame {i} di {profile.projectile_file} kosong"
                )
            crop = cell.subsurface(box).copy()
            if profile.flip_projectile:
                crop = pygame.transform.flip(crop, True, False)
            crops.append(crop)

        scale = profile.projectile_height / max(c.get_height() for c in crops)

        scaled = [
            pygame.transform.smoothscale(
                c,
                (
                    max(1, round(c.get_width() * scale)),
                    max(1, round(c.get_height() * scale)),
                ),
            )
            for c in crops
        ]

        canvas_w = max(s.get_width() for s in scaled)
        canvas_h = max(s.get_height() for s in scaled)

        frames: List[pygame.Surface] = []
        for s in scaled:
            canvas = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
            x = 0 if profile.projectile_align == "lead" else (
                (canvas_w - s.get_width()) // 2
            )
            canvas.blit(s, (x, (canvas_h - s.get_height()) // 2))
            frames.append(canvas)

        return frames

    @property
    def has_projectile_attack(self) -> bool:
        return (
            self.attack_profile is not None
            and bool(self.attack_frames)
            and bool(self.projectile_frames)
        )

    @property
    def projectile_speed(self) -> float:
        return self.attack_profile.projectile_speed if self.attack_profile else 380.0

    def supports_projectile_action(self, action_type: str) -> bool:
        return (
            self.has_projectile_attack
            and action_type in self.attack_profile.actions
        )

    def trigger_projectile_attack(self) -> bool:
        """Mulai animasi menyerang; proyektil keluar di frame peluncuran."""

        if not self.monster.is_alive or not self.has_projectile_attack:
            return False

        profile = self.attack_profile
        self.current_state = "ranged_attack"
        self.attack_time = 0.0
        self.projectile_launched = False
        self.state_timer = (
            len(self.attack_frames) / profile.attack_fps + profile.hold
        )
        return True

    def pop_projectile_launch(self) -> Optional[Tuple[float, float]]:
        """Titik muncul proyektil (sekali saja) saat frame peluncuran tiba."""

        if (
            self.current_state != "ranged_attack"
            or self.projectile_launched
            or not self.attack_profile
        ):
            return None

        profile = self.attack_profile
        launch = min(profile.launch_frame, len(self.attack_frames) - 1)

        if int(self.attack_time * profile.attack_fps) < launch:
            return None

        self.projectile_launched = True

        bounds = self.attack_bounds[launch]
        x = self.rect.x + self.shake_offset[0]
        y = self.rect.y + self.shake_offset[1]

        # Tepi kiri frame serangan (ujung senjata / mulut / tangan).
        return (
            float(x + bounds.left),
            float(
                y + bounds.top + bounds.height * profile.spawn_y_ratio
                + profile.spawn_y_offset
            ),
        )

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

        if self.current_state == "ranged_attack":
            self.attack_time += dt

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

    # ------------------------------------------------------------------
    # Efek serangan prosedural (dipakai bila monster tidak punya sprite
    # attack_* / object_attack_*, atau sprite-nya gagal dimuat).
    # Setiap monster punya efek sendiri yang meluncur ke arah pemain.
    # ------------------------------------------------------------------
    # Perkiraan titik tubuh pemain di layar combat (pemain di x=140, y=260).
    PLAYER_TARGET = (250, 390)

    def _render_attack_effect(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
    ) -> None:
        """Efek serangan khas tiap monster saat state 'attack' (tanpa sprite)."""

        if self.current_state != "attack" or self.state_timer <= 0.0:
            return

        progress = 1.0 - self.state_timer / self.attack_duration
        if progress < 0.15:      # jeda awal: monster mengambil ancang-ancang
            return
        t = min(1.0, (progress - 0.15) / 0.85)

        effect = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SRCALPHA,
        )

        handlers = {
            "idle_skeleton.png": self._fx_sword_slash,
            "idle_slime.png": self._fx_acid_spit,
            "idle_magma.png": self._fx_lava_ball,
            "idle_godzilla.png": self._fx_kaiju_claw,
            "idle_frost.png": self._fx_ice_shards,
        }
        handler = handlers.get(self.idle_filename, self._fx_purple_claw)
        handler(effect, x, y, t)

        surface.blit(effect, (0, 0))

    def _fx_start(self, x: int, y: int) -> Tuple[float, float]:
        """Titik asal efek: bagian depan (kiri) badan monster."""
        return float(x + 40), float(y + 150)

    @staticmethod
    def _lerp_point(
        a: Tuple[float, float],
        b: Tuple[float, float],
        k: float,
        arc: float = 0.0,
    ) -> Tuple[float, float]:
        px = a[0] + (b[0] - a[0]) * k
        py = a[1] + (b[1] - a[1]) * k - math.sin(k * math.pi) * arc
        return px, py

    def _fx_purple_claw(self, fx, x, y, t) -> None:
        """Cakar ungu bawaan (cadangan untuk monster tanpa efek khusus)."""
        alpha = int(230 * (1.0 - t * 0.6))
        cx, cy = x + 35, y + 120
        for ox, oy in [(-10, -20), (10, 0), (30, 20)]:
            pts = [
                (cx + ox + 30, cy + oy - 45),
                (cx + ox - 25, cy + oy),
                (cx + ox + 15, cy + oy + 45),
            ]
            pygame.draw.lines(fx, (230, 40, 255, alpha), False, pts, 6)
            pygame.draw.lines(fx, (255, 255, 255, alpha), False, pts, 2)

    def _fx_sword_slash(self, fx, x, y, t) -> None:
        """Skeleton Guard: tiga tebasan pedang berkarat menyilang di pemain."""
        tx, ty = self.PLAYER_TARGET
        alpha = int(255 * (1.0 - max(0.0, t - 0.55) / 0.45))
        reach = min(1.0, t / 0.45)
        for i, off in enumerate((-34, 0, 34)):
            if t < i * 0.12:
                continue
            k = min(1.0, (t - i * 0.12) / 0.35)
            length = 95 * k
            sx, sy = tx + off - 40, ty - 80
            ex, ey = sx + length * 0.55, sy + length * 1.45
            pygame.draw.line(fx, (150, 200, 230, alpha), (sx, sy), (ex, ey), 9)
            pygame.draw.line(fx, (255, 255, 255, alpha), (sx, sy), (ex, ey), 3)
        # Riak tebasan dari monster ke pemain.
        if reach < 1.0:
            sx, sy = self._fx_start(x, y)
            px, py = self._lerp_point((sx, sy), (tx, ty), reach)
            pygame.draw.line(fx, (200, 230, 255, 140), (sx, sy), (px, py), 3)

    def _fx_acid_spit(self, fx, x, y, t) -> None:
        """Crystal Slime: semburan asam hijau melengkung lalu memercik."""
        start = self._fx_start(x, y)
        target = self.PLAYER_TARGET
        fly = min(1.0, t / 0.65)
        if t < 0.65:
            for n in range(6):          # ekor tetesan
                k = max(0.0, fly - n * 0.06)
                px, py = self._lerp_point(start, target, k, arc=120)
                r = max(3, 17 - n * 2)
                pygame.draw.circle(fx, (60, 255, 150, 230 - n * 30), (int(px), int(py)), r)
            px, py = self._lerp_point(start, target, fly, arc=120)
            pygame.draw.circle(fx, (200, 255, 230, 255), (int(px) - 4, int(py) - 4), 5)
        else:
            k = (t - 0.65) / 0.35
            alpha = int(230 * (1.0 - k))
            for i in range(10):         # percikan asam
                ang = i * math.tau / 10
                d = 18 + 55 * k
                px = target[0] + math.cos(ang) * d
                py = target[1] + math.sin(ang) * d * 0.7 + 25 * k * k
                pygame.draw.circle(fx, (70, 255, 160, alpha), (int(px), int(py)), max(2, int(9 * (1 - k))))
            pygame.draw.ellipse(
                fx, (40, 200, 120, int(alpha * 0.6)),
                (target[0] - 40, target[1] + 20, 80, 24),
            )

    def _fx_lava_ball(self, fx, x, y, t) -> None:
        """Magma Golem: bola lava berapi meluncur lalu meledak."""
        start = self._fx_start(x, y)
        target = self.PLAYER_TARGET
        fly = min(1.0, t / 0.6)
        if t < 0.6:
            for n in range(7):
                k = max(0.0, fly - n * 0.05)
                px, py = self._lerp_point(start, target, k, arc=50)
                r = max(4, 26 - n * 3)
                col = (255, 140 - n * 10, 20, 235 - n * 28)
                pygame.draw.circle(fx, col, (int(px), int(py)), r)
            px, py = self._lerp_point(start, target, fly, arc=50)
            pygame.draw.circle(fx, (255, 235, 120, 255), (int(px), int(py)), 11)
        else:
            k = (t - 0.6) / 0.4
            alpha = int(240 * (1.0 - k))
            radius = int(25 + 85 * k)
            pygame.draw.circle(fx, (255, 120, 20, alpha), target, radius, 8)
            pygame.draw.circle(fx, (255, 220, 90, int(alpha * 0.7)), target, int(radius * 0.55))
            for i in range(8):          # percikan bara
                ang = i * math.tau / 8 + 0.4
                d = radius * 1.1
                pygame.draw.circle(
                    fx, (255, 170, 40, alpha),
                    (int(target[0] + math.cos(ang) * d), int(target[1] + math.sin(ang) * d)),
                    4,
                )

    def _fx_kaiju_claw(self, fx, x, y, t) -> None:
        """Corrupted Crystal Kaiju: cakar merah + gelombang kejut di tanah."""
        tx, ty = self.PLAYER_TARGET
        alpha = int(255 * (1.0 - max(0.0, t - 0.6) / 0.4))
        # Gelombang kejut menjalar di tanah menuju pemain.
        ground = ty + 95
        sx = x + 30
        head = sx + (tx - sx) * min(1.0, t / 0.6)
        pygame.draw.line(fx, (255, 90, 120, int(alpha * 0.8)), (sx, ground), (head, ground), 6)
        pygame.draw.ellipse(fx, (255, 150, 170, int(alpha * 0.7)), (head - 30, ground - 14, 60, 28), 3)
        # Tiga goresan cakar kristal di pemain.
        if t > 0.4:
            k = min(1.0, (t - 0.4) / 0.3)
            for off in (-36, 0, 36):
                a = (tx + off + 30, ty - 90)
                b = (tx + off - 20 * k, ty - 90 + 170 * k)
                pygame.draw.line(fx, (255, 60, 110, alpha), a, b, 11)
                pygame.draw.line(fx, (255, 235, 245, alpha), a, b, 4)

    def _fx_ice_shards(self, fx, x, y, t) -> None:
        """Frost (cadangan bila proyektil es gagal dimuat): pecahan es."""
        start = self._fx_start(x, y)
        target = self.PLAYER_TARGET
        fly = min(1.0, t / 0.7)
        alpha = int(240 * (1.0 - max(0.0, t - 0.7) / 0.3))
        for i, dy in enumerate((-40, 0, 40)):
            px, py = self._lerp_point(start, (target[0], target[1] + dy), fly)
            pts = [(px - 34, py), (px + 14, py - 9), (px + 14, py + 9)]
            pygame.draw.polygon(fx, (150, 225, 255, alpha), pts)
            pygame.draw.polygon(fx, (255, 255, 255, alpha), pts, 2)

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

        # Animasi menyerang dari sprite sheet attack_* milik profil monster.
        if (
            self.current_state == "ranged_attack"
            and self.attack_frames
            and self.attack_profile
            and self.monster.is_alive
        ):
            attack_index = min(
                int(self.attack_time * self.attack_profile.attack_fps),
                len(self.attack_frames) - 1,
            )
            display_sprite = self.attack_frames[attack_index]

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


class MonsterProjectile(GameObject):
    """Objek serangan monster yang meluncur ke titik tempat pemain berdiri."""

    FADE_TIME = 0.30
    SHATTER_TIME = 0.25

    def __init__(
        self,
        frames: List[pygame.Surface],
        start: Tuple[float, float],
        target: Tuple[float, float],
        speed: float,
        profile: AttackProfile,
    ):
        width, height = frames[0].get_size()
        super().__init__(
            start[0] - width / 2, start[1] - height / 2, width, height
        )

        self.frames = frames
        self.profile = profile
        self.cx = float(start[0])
        self.cy = float(start[1])
        self.target = (float(target[0]), float(target[1]))
        self.speed = speed

        dx = self.target[0] - self.cx
        dy = self.target[1] - self.cy
        distance = math.hypot(dx, dy)

        self.remaining = distance
        self.direction = (
            (dx / distance, dy / distance) if distance > 0 else (-1.0, 0.0)
        )

        self.state = "flying"   # flying -> fade | shatter -> done
        self.state_time = 0.0
        self.anim_time = 0.0
        self.outcome: Optional[str] = None  # hit | parried | missed

    @property
    def is_flying(self) -> bool:
        return self.state == "flying"

    @property
    def is_done(self) -> bool:
        return self.state == "done"

    def get_hitbox(self) -> pygame.Rect:
        """Hitbox sesuai profil (dapat digeser ke sisi depan sprite)."""

        w = int(self.width * self.profile.hitbox_w)
        h = int(self.height * self.profile.hitbox_h)

        if self.profile.hitbox_left is None:
            left = int(self.cx - w / 2)
        else:
            left = int(
                self.cx - self.width / 2
                + self.width * self.profile.hitbox_left
            )

        return pygame.Rect(left, int(self.cy - h / 2), w, h)

    def impact(self, outcome: str) -> None:
        """Proyektil mengenai pemain atau ditangkis: pecah di tempat."""

        if self.state != "flying":
            return

        self.outcome = outcome
        self.state = "shatter"
        self.state_time = 0.0

    def update(self, dt: float) -> None:
        self.anim_time += dt

        if self.state == "flying":
            step = min(self.speed * dt, self.remaining)
            self.cx += self.direction[0] * step
            self.cy += self.direction[1] * step
            self.remaining -= step

            # Sampai di titik tujuan tanpa mengenai siapa pun: meleset.
            if self.remaining <= 0:
                self.outcome = "missed"
                self.state = "fade"
                self.state_time = 0.0

        else:
            self.state_time += dt
            limit = (
                self.SHATTER_TIME
                if self.state == "shatter"
                else self.FADE_TIME
            )
            if self.state_time >= limit:
                self.state = "done"

        self.x = self.cx - self.width / 2
        self.y = self.cy - self.height / 2
        super().update(dt)

    def render(self, surface: pygame.Surface) -> None:
        if self.state == "done":
            return

        frame = self.frames[
            int(self.anim_time * self.profile.projectile_fps)
            % len(self.frames)
        ]

        alpha = 255
        if self.state == "fade":
            alpha = int(255 * (1.0 - self.state_time / self.FADE_TIME))
        elif self.state == "shatter":
            t = self.state_time / self.SHATTER_TIME
            alpha = int(255 * (1.0 - t))
            grow = 1.0 + 0.35 * t
            frame = pygame.transform.smoothscale(
                frame,
                (
                    max(1, int(frame.get_width() * grow)),
                    max(1, int(frame.get_height() * grow)),
                ),
            )

        if alpha < 255:
            frame = frame.copy()
            frame.set_alpha(max(0, alpha))

        surface.blit(
            frame,
            (
                int(self.cx - frame.get_width() / 2),
                int(self.cy - frame.get_height() / 2),
            ),
        )


# Alias lama agar kode yang masih memakai nama Frost tetap jalan.
FrostProjectile = MonsterProjectile