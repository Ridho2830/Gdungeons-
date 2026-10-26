"""
Module: engine/ui.py
Description: Komponen antarmuka pengguna (UI) PyGame yang responsif: Tombol, Progress Bar, Floating Text, Objective HUD, Log Box.
"""

from typing import Any, Callable, List, Optional, Tuple
import pygame
from engine.assets import AssetManager
from engine.audio import AudioManager
from engine.constants import (
    COLOR_BTN_BORDER,
    COLOR_BTN_HOVER,
    COLOR_BTN_NORMAL,
    COLOR_GOLD,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_PANEL_HEADER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
)


class UIButton:
    """Komponen tombol interaktif dengan animasi hover, sound effect, ikon RPG, dan dukungan gambar/teks."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str = "",
        on_click: Optional[Callable[[], None]] = None,
        image_normal: Optional[str] = None,
        image_hover: Optional[str] = None,
        bg_color: Tuple[int, int, int] = COLOR_BTN_NORMAL,
        hover_color: Tuple[int, int, int] = COLOR_BTN_HOVER,
        text_color: Tuple[int, int, int] = COLOR_TEXT_WHITE,
        font_size: int = 18,
        tooltip: str = "",
        icon_name: Optional[str] = None,
        custom_icon: Optional[pygame.Surface] = None,
    ) -> None:
        self.rect: pygame.Rect = rect
        self.text: str = text
        self.on_click: Optional[Callable[[], None]] = on_click
        self.image_normal_name = image_normal
        self.image_hover_name = image_hover
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.tooltip = tooltip
        self.icon_name = icon_name
        self.custom_icon = custom_icon

        self.is_hovered: bool = False
        self.is_disabled: bool = False
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Memproses event mouse hover dan klik."""
        if self.is_disabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            prev_hover = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if not prev_hover and self.is_hovered:
                # Feedback hover halus jika diinginkan
                pass

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.audio.play("click")
                if self.on_click:
                    self.on_click()
                return True

        return False

    def render(self, surface: pygame.Surface) -> None:
        if self.image_normal_name:
            img_name = self.image_hover_name if (self.is_hovered and self.image_hover_name) else self.image_normal_name
            surf = self.assets.get_image(img_name, scale=(self.rect.width, self.rect.height))
            surface.blit(surf, self.rect.topleft)
            return

        # Render tombol bergaya tema RPG
        color = self.hover_color if self.is_hovered else self.bg_color
        if self.is_disabled:
            color = (40, 35, 45)

        # Gambar latar dan border
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        border_col = COLOR_GOLD if self.is_hovered else COLOR_BTN_BORDER
        pygame.draw.rect(surface, border_col, self.rect, width=2, border_radius=6)

        # Ambil ikon RPG jika dispesifikasikan atau gunakan custom_icon
        icon_surf = self.custom_icon
        if not icon_surf and self.icon_name:
            icon_surf = self.assets.get_rpg_icon(self.icon_name, size=(22, 22))

        # Gambar teks & ikon di tengah
        if self.text:
            font = self.assets.get_font(self.font_size, bold=self.is_hovered)
            txt_surf = font.render(self.text, True, self.text_color if not self.is_disabled else COLOR_TEXT_MUTED)

            if icon_surf:
                gap = 8
                total_w = icon_surf.get_width() + gap + txt_surf.get_width()
                start_x = self.rect.centerx - total_w // 2
                icon_y = self.rect.centery - icon_surf.get_height() // 2
                txt_y = self.rect.centery - txt_surf.get_height() // 2
                surface.blit(icon_surf, (start_x, icon_y))
                surface.blit(txt_surf, (start_x + icon_surf.get_width() + gap, txt_y))
            else:
                txt_rect = txt_surf.get_rect(center=self.rect.center)
                surface.blit(txt_surf, txt_rect)
        elif icon_surf:
            surface.blit(icon_surf, icon_surf.get_rect(center=self.rect.center))


class UIProgressBar:
    """Komponen bar status progres dinamis untuk HP, Defense, dan Rage (Rubrik Status Indikator)."""

    def __init__(
        self,
        rect: pygame.Rect,
        max_value: float,
        current_value: float,
        fill_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int] = (40, 30, 45),
        label: str = "HP",
        show_numeric: bool = True,
    ) -> None:
        self.rect: pygame.Rect = rect
        self.max_value: float = max_value
        self.current_value: float = current_value
        self.display_value: float = current_value
        self.fill_color: Tuple[int, int, int] = fill_color
        self.bg_color: Tuple[int, int, int] = bg_color
        self.label: str = label
        self.show_numeric: bool = show_numeric
        self.assets = AssetManager.get_instance()

    def set_value(self, current: float, max_val: Optional[float] = None) -> None:
        if max_val is not None:
            self.max_value = max(1.0, float(max_val))
        self.current_value = max(0.0, float(current))

    def update(self, dt: float) -> None:
        # Interpolasi animasi pergerakan bar agar mulus (Feedback visual)
        diff = self.current_value - self.display_value
        self.display_value += diff * min(1.0, dt * 10.0)

    def render(self, surface: pygame.Surface) -> None:
        # Latar belakang bar
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=4)

        # Isi bar
        pct = max(0.0, min(1.0, self.display_value / self.max_value)) if self.max_value > 0 else 0.0
        fill_w = int(self.rect.width * pct)
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            pygame.draw.rect(surface, self.fill_color, fill_rect, border_radius=4)

        # Garis tepi
        pygame.draw.rect(surface, (80, 70, 95), self.rect, width=2, border_radius=4)

        # Label teks di tengah bar
        font = self.assets.get_font(13, bold=True)
        if self.show_numeric:
            txt = f"{self.label}: {int(self.current_value)} / {int(self.max_value)}"
        else:
            txt = f"{self.label}: {int(pct * 100)}%"

        txt_surf = font.render(txt, True, COLOR_TEXT_WHITE)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)


class FloatingText:
    """Teks melayang untuk damage, heal, dan status penting."""

    def __init__(
        self, text: str, x: float, y: float, color: Tuple[int, int, int], lifetime: float = 1.2, vy: float = -40.0
    ) -> None:
        self.text: str = text
        self.x: float = x
        self.y: float = y
        self.color: Tuple[int, int, int] = color
        self.lifetime: float = lifetime
        self.total_life: float = lifetime
        self.vy: float = vy

    def update(self, dt: float) -> bool:
        self.lifetime -= dt
        self.y += self.vy * dt
        return self.lifetime > 0

    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        alpha = max(0, min(255, int(255 * (self.lifetime / self.total_life))))
        txt_surf = font.render(self.text, True, self.color)
        txt_surf.set_alpha(alpha)
        surface.blit(txt_surf, (int(self.x), int(self.y)))


class FloatingTextManager:
    """Mengelola banyak teks melayang di layar."""

    def __init__(self) -> None:
        self.items: List[FloatingText] = []
        self.assets = AssetManager.get_instance()

    def add(self, text: str, x: float, y: float, color: Tuple[int, int, int] = COLOR_GOLD) -> None:
        self.items.append(FloatingText(text, x, y, color))

    def update(self, dt: float) -> None:
        self.items = [item for item in self.items if item.update(dt)]

    def render(self, surface: pygame.Surface) -> None:
        font = self.assets.get_font(16, bold=True)
        for item in self.items:
            item.render(surface, font)


class ObjectiveHUD:
    """
    Banner objektif di bagian atas layar.
    Memenuhi Rubrik UX: 'Kejelasan Tujuan (Objective Clarity)' agar pemain dalam
    1 menit pertama langsung memahami tujuan akhir dan misi sekunder.
    """

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect: pygame.Rect = rect
        self.assets = AssetManager.get_instance()

    def render(
        self,
        surface: pygame.Surface,
        main_objective: str,
        sub_objectives: List[Tuple[str, bool]],
        location_name: str,
    ) -> None:
        # Background bar semi-transparan
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        bg_surf.fill((20, 16, 30, 220))
        surface.blit(bg_surf, self.rect.topleft)

        # Border bawah emas
        pygame.draw.line(
            surface,
            COLOR_GOLD,
            (self.rect.left, self.rect.bottom),
            (self.rect.right, self.rect.bottom),
            width=2,
        )

        font_title = self.assets.get_font(15, bold=True)
        font_sub = self.assets.get_font(13, bold=False)

        # Lokasi saat ini
        loc_txt = font_title.render(f">> Lokasi: {location_name}", True, COLOR_GOLD)
        surface.blit(loc_txt, (self.rect.x + 20, self.rect.y + 8))

        # Objektif utama
        obj_txt = font_title.render(f"[ MISI UTAMA ] {main_objective}", True, COLOR_TEXT_WHITE)
        surface.blit(obj_txt, (self.rect.x + 240, self.rect.y + 8))

        # Checklist sub-objektif
        start_x = self.rect.x + 240
        for text, completed in sub_objectives:
            sym = "OK" if completed else "--"
            col = (46, 204, 113) if completed else COLOR_TEXT_MUTED
            sub_surf = font_sub.render(f"[{sym}] {text}", True, col)
            surface.blit(sub_surf, (start_x, self.rect.y + 32))
            start_x += sub_surf.get_width() + 25


class LogBox:
    """Panel riwayat aktivitas game (Combat & Travel Log)."""

    def __init__(self, rect: pygame.Rect, max_lines: int = 6) -> None:
        self.rect: pygame.Rect = rect
        self.max_lines: int = max_lines
        self.messages: List[str] = []
        self.assets = AssetManager.get_instance()

    def add_message(self, msg: str) -> None:
        self.messages.append(msg)
        if len(self.messages) > 30:
            self.messages.pop(0)

    def render(self, surface: pygame.Surface) -> None:
        # Background panel
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        bg_surf.fill((25, 20, 35, 220))
        surface.blit(bg_surf, self.rect.topleft)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=2, border_radius=6)

        font = self.assets.get_font(13)
        recent = self.messages[-self.max_lines :]
        y_offset = self.rect.y + 8
        for line in recent:
            color = COLOR_TEXT_WHITE
            if "MENANG" in line or "SELESAI" in line or "DIPULIHKAN" in line:
                color = (46, 204, 113)
            elif "KALAH" in line or "DAMAGE" in line or "Mati" in line:
                color = (231, 76, 60)
            elif "RAGE" in line or "BOS" in line:
                color = (230, 126, 34)

            txt_surf = font.render(line, True, color)
            surface.blit(txt_surf, (self.rect.x + 12, y_offset))
            y_offset += 20


class RolesGuideModal:
    """
    Modal pop-up interaktif untuk Panduan Lengkap Role & Karakter (Mage vs Fighter).
    Menampilkan animasi sprite hidup (live idle animation) dari kedua kelas,
    perbandingan atribut, skill khusus, dan rekomendasi gaya bermain.
    """

    def __init__(self, on_close: Optional[Callable[[], None]] = None) -> None:
        self.on_close = on_close
        self.assets = AssetManager.get_instance()
        self.audio = AudioManager.get_instance()

        # Ukuran Modal Utama (980 x 630)
        from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
        self.rect = pygame.Rect((SCREEN_WIDTH - 980) // 2, (SCREEN_HEIGHT - 630) // 2, 980, 630)

        # Sprite Animasi Knight & Wizard yang telah di-crop presisi
        knight_frames = self.assets.get_cropped_knight_idle_frames((110, 120))
        wizard_frames = self.assets.get_cropped_wizard_idle_frames((120, 110))

        from engine.entities import AnimatedSprite
        # Posisi sprite di dalam kartu masing-masing
        self.wizard_sprite = AnimatedSprite(
            x=self.rect.x + 35 + (440 - 120) // 2,
            y=self.rect.y + 130,
            animations={"idle": wizard_frames},
            default_anim="idle",
            fps=7.0,
        )
        self.knight_sprite = AnimatedSprite(
            x=self.rect.right - 35 - 440 + (440 - 110) // 2,
            y=self.rect.y + 125,
            animations={"idle": knight_frames},
            default_anim="idle",
            fps=8.0,
        )

        # Tombol Tutup
        btn_w, btn_h = 240, 42
        self.btn_close = UIButton(
            rect=pygame.Rect(self.rect.centerx - btn_w // 2, self.rect.bottom - 54, btn_w, btn_h),
            text="Tutup Panduan",
            font_size=16,
            hover_color=(70, 80, 100),
            on_click=self._close,
        )

    def _close(self) -> None:
        self.audio.play("click")
        if self.on_close:
            self.on_close()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            self._close()
            return True

        if self.btn_close.handle_event(event):
            return True

        # Cegah klik menembus ke latar belakang
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            return True

        return False

    def update(self, dt: float) -> None:
        self.knight_sprite.update(dt)
        self.wizard_sprite.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT
        # Dim background
        dim_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim_surf.fill((0, 0, 0, 205))
        surface.blit(dim_surf, (0, 0))

        # Main Card Panel
        pygame.draw.rect(surface, (15, 17, 26), self.rect, border_radius=14)
        pygame.draw.rect(surface, COLOR_GOLD, self.rect, width=2, border_radius=14)

        # Header Title
        font_h = self.assets.get_font(22, bold=True)
        h_surf = font_h.render("PANDUAN LENGKAP ROLE & KELAS HERO", True, COLOR_GOLD)
        surface.blit(h_surf, h_surf.get_rect(center=(self.rect.centerx, self.rect.y + 24)))

        font_sub = self.assets.get_font(13)
        sub_surf = font_sub.render(
            "Pelajari perbedaan atribut, spesialisasi tempur, dan keunggulan taktis di G-Dungeons.",
            True,
            COLOR_TEXT_MUTED,
        )
        surface.blit(sub_surf, sub_surf.get_rect(center=(self.rect.centerx, self.rect.y + 48)))

        # 2 Kolom Side-by-Side: Kiri = Mage, Kanan = Fighter
        card_w = 440
        card_h = 490
        card_y = self.rect.y + 70

        # Render Kartu Mage
        self._render_class_card(
            surface,
            rect=pygame.Rect(self.rect.x + 35, card_y, card_w, card_h),
            title="MAGE (Penyihir)",
            subtitle="Arcane Intellect & Path Navigator",
            badge="Min-Heap Dijkstra Specialist",
            border_color=(139, 92, 246),
            icon_key="robe_arcane",
            sprite=self.wizard_sprite,
            stats=[("HP", 1100, "hp"), ("ATK", 95, "atk"), ("DEF", 25, "def")],
            skill_title="Pasif: Map Vision & Arcane Intellect",
            skill_icon="book_gold",
            skill_desc="Rute terpendek Dijkstra otomatis ter-highlight di peta labirin. Skill: Arcane Surge menghasilkan 180% Damage tembus armor.",
            playstyle="Taktis, navigasi cerdas, pencari rute terpendek.",
        )

        # Render Kartu Knight
        self._render_class_card(
            surface,
            rect=pygame.Rect(self.rect.right - 35 - card_w, card_y, card_w, card_h),
            title="KNIGHT (Ksatria)",
            subtitle="Ironclad Fortitude & Shield Master",
            badge="Frontline Tank & Boss Crusher",
            border_color=(239, 68, 68),
            icon_key="armor_iron",
            sprite=self.knight_sprite,
            stats=[("HP", 1500, "hp"), ("ATK", 65, "atk"), ("DEF", 45, "def")],
            skill_title="Pasif: Ironclad Fortitude",
            skill_icon="armor_emerald",
            skill_desc="Damage fisik musuh berkurang 20% otomatis. Aksi Bertahan memberi Shield +80. Skill: Heavy Strike menghasilkan 180% Damage.",
            playstyle="Kokoh, peredam pukulan berat, tangguh di garis depan.",
        )

        # Tombol Tutup
        self.btn_close.render(surface)

    def _render_class_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        subtitle: str,
        badge: str,
        border_color: Tuple[int, int, int],
        icon_key: str,
        sprite: Any,
        stats: List[Tuple[str, int, str]],
        skill_title: str,
        skill_icon: str,
        skill_desc: str,
        playstyle: str,
    ) -> None:
        pygame.draw.rect(surface, (20, 23, 36), rect, border_radius=10)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)

        # Header Title
        font_t = self.assets.get_font(18, bold=True)
        icon_s = self.assets.get_rpg_icon(icon_key, size=(22, 22))
        txt_t = font_t.render(title, True, border_color)

        top_w = (icon_s.get_width() + 8 + txt_t.get_width()) if icon_s else txt_t.get_width()
        start_x = rect.centerx - top_w // 2
        if icon_s:
            surface.blit(icon_s, (start_x, rect.y + 12))
            surface.blit(txt_t, (start_x + icon_s.get_width() + 8, rect.y + 12))
        else:
            surface.blit(txt_t, txt_t.get_rect(center=(rect.centerx, rect.y + 22)))

        font_sub = self.assets.get_font(12)
        sub_s = font_sub.render(subtitle, True, COLOR_TEXT_MUTED)
        surface.blit(sub_s, sub_s.get_rect(center=(rect.centerx, rect.y + 38)))

        # Sprite Box Frame
        box_rect = pygame.Rect(rect.x + 16, rect.y + 56, rect.width - 32, 126)
        pygame.draw.rect(surface, (9, 11, 18), box_rect, border_radius=8)
        pygame.draw.rect(surface, (40, 48, 70), box_rect, width=1, border_radius=8)

        # Render sprite di dalam box
        sprite.render(surface)

        # Badge di bawah sprite box
        badge_rect = pygame.Rect(rect.x + 24, rect.y + 188, rect.width - 48, 22)
        pygame.draw.rect(surface, (30, 36, 54), badge_rect, border_radius=4)
        font_b = self.assets.get_font(11, bold=True)
        b_surf = font_b.render(f"[ {badge} ]", True, COLOR_GOLD)
        surface.blit(b_surf, b_surf.get_rect(center=badge_rect.center))

        # Stat Box
        stat_rect = pygame.Rect(rect.x + 16, rect.y + 218, rect.width - 32, 50)
        pygame.draw.rect(surface, (26, 30, 47), stat_rect, border_radius=8)
        col_w = stat_rect.width // 3
        font_stat = self.assets.get_font(14, bold=True)
        font_slbl = self.assets.get_font(11)

        for idx, (label, val, s_icon) in enumerate(stats):
            cx = stat_rect.x + idx * col_w + col_w // 2
            i_surf = self.assets.get_rpg_icon(s_icon, size=(16, 16))
            v_surf = font_stat.render(f"{val}", True, COLOR_TEXT_WHITE)
            l_surf = font_slbl.render(label, True, COLOR_TEXT_MUTED)

            if i_surf:
                surface.blit(i_surf, (cx - 24, stat_rect.y + 7))
                surface.blit(v_surf, (cx - 4, stat_rect.y + 6))
            else:
                surface.blit(v_surf, v_surf.get_rect(center=(cx, stat_rect.y + 14)))
            surface.blit(l_surf, l_surf.get_rect(center=(cx, stat_rect.y + 32)))

        # Skill & Keahlian Box
        skill_box = pygame.Rect(rect.x + 16, rect.y + 276, rect.width - 32, 134)
        pygame.draw.rect(surface, (16, 19, 31), skill_box, border_radius=8)
        pygame.draw.rect(surface, (38, 44, 66), skill_box, width=1, border_radius=8)

        # Skill Title with icon
        sk_icon_s = self.assets.get_rpg_icon(skill_icon, size=(18, 18))
        font_sk = self.assets.get_font(13, bold=True)
        sk_title_s = font_sk.render(f" {skill_title}", True, border_color)
        if sk_icon_s:
            surface.blit(sk_icon_s, (skill_box.x + 10, skill_box.y + 10))
            surface.blit(sk_title_s, (skill_box.x + 10 + sk_icon_s.get_width(), skill_box.y + 10))
        else:
            surface.blit(sk_title_s, (skill_box.x + 10, skill_box.y + 10))

        # Word-wrapped skill description
        font_d = self.assets.get_font(12)
        words = skill_desc.split()
        lines = []
        cur_l = ""
        for w in words:
            if len(cur_l + " " + w) > 42:
                lines.append(cur_l)
                cur_l = w
            else:
                cur_l = (cur_l + " " + w).strip()
        if cur_l:
            lines.append(cur_l)

        dy = skill_box.y + 34
        for line in lines[:3]:
            l_surf = font_d.render(line, True, (200, 205, 220))
            surface.blit(l_surf, (skill_box.x + 10, dy))
            dy += 18

        # Playstyle
        font_ps = self.assets.get_font(11, bold=False)
        ps_surf = font_ps.render(f"Rekomendasi Taktik: {playstyle}", True, COLOR_GOLD)
        surface.blit(ps_surf, (rect.x + 18, rect.bottom - 24))
