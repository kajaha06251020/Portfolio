"""UIパネルコンポーネント"""

from pathlib import Path
import pygame

from src.constants import WHITE, scaled


class UIPanel:
    """シンプルな角丸パネル描画コンポーネント"""

    _texture_cache = {}

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str = "",
        bg_color=(20, 28, 70),
        border_color=WHITE,
        border_width: int = 2,
        border_radius: int = 8,
        padding: int = 12,
        texture_path: str | None = None,
        texture_scale: float = 1.0,
        texture_repeat: bool = True,
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.border_radius = border_radius
        self.padding = padding
        default_texture = Path(__file__).resolve().parents[2] / "assets" / "images" / "UI" / "UIPanel.png"
        self.texture_path = texture_path or str(default_texture)
        self.texture_scale = max(0.1, texture_scale)
        self.texture_repeat = texture_repeat

    @classmethod
    def _get_panel_texture(
        cls,
        texture_path: str | None,
        texture_scale: float,
        target_size: tuple[int, int] | None = None,
    ):
        if not texture_path:
            return None

        if target_size is None:
            key = (texture_path, round(texture_scale, 2), None)
        else:
            key = (texture_path, round(texture_scale, 2), target_size)
        if key in cls._texture_cache:
            return cls._texture_cache[key]

        try:
            texture = pygame.image.load(texture_path).convert_alpha()
            if target_size is None:
                width = max(1, int(texture.get_width() * texture_scale))
                height = max(1, int(texture.get_height() * texture_scale))
                if width != texture.get_width() or height != texture.get_height():
                    texture = pygame.transform.smoothscale(texture, (width, height))
            else:
                width = max(1, target_size[0])
                height = max(1, target_size[1])
                texture = pygame.transform.smoothscale(texture, (width, height))
            cls._texture_cache[key] = texture
            return texture
        except (pygame.error, FileNotFoundError):
            cls._texture_cache[key] = None
            return None

    def draw(self, screen: pygame.Surface, title_font=None, title_color=WHITE) -> pygame.Rect:
        """パネルを描画し、コンテンツ描画可能領域を返す"""
        if self.texture_repeat:
            texture = self._get_panel_texture(self.texture_path, self.texture_scale)
        else:
            texture = self._get_panel_texture(self.texture_path, self.texture_scale, self.rect.size)

        if texture is None:
            pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=self.border_radius)
        elif self.texture_repeat:
            tiled_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            tw, th = texture.get_size()
            for px in range(0, self.rect.w, tw):
                for py in range(0, self.rect.h, th):
                    tiled_surface.blit(texture, (px, py))

            if self.border_radius > 0:
                mask_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                pygame.draw.rect(
                    mask_surface,
                    (255, 255, 255, 255),
                    pygame.Rect(0, 0, self.rect.w, self.rect.h),
                    border_radius=self.border_radius,
                )
                tiled_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            screen.blit(tiled_surface, self.rect.topleft)
        else:
            if self.border_radius > 0:
                texture_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                texture_surface.blit(texture, (0, 0))

                mask_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                pygame.draw.rect(
                    mask_surface,
                    (255, 255, 255, 255),
                    pygame.Rect(0, 0, self.rect.w, self.rect.h),
                    border_radius=self.border_radius,
                )
                texture_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(texture_surface, self.rect.topleft)
            else:
                screen.blit(texture, self.rect.topleft)

        pygame.draw.rect(
            screen,
            self.border_color,
            self.rect,
            self.border_width,
            border_radius=self.border_radius,
        )

        top_offset = self.padding
        if self.title and title_font is not None:
            title_surface = title_font.render(self.title, True, title_color)
            title_x = self.rect.x + self.padding
            title_y = self.rect.y + self.padding
            screen.blit(title_surface, (title_x, title_y))
            top_offset += title_surface.get_height() + scaled(8)

        return pygame.Rect(
            self.rect.x + self.padding,
            self.rect.y + top_offset,
            self.rect.w - self.padding * 2,
            self.rect.h - top_offset - self.padding,
        )
