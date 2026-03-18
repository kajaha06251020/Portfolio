"""
ダイアログレンダラー — Dialogue Renderer

Renders FF-style dialogue windows using Pygame.
Supports typewriter text display, speaker name boxes, and choice menus.
"""

import logging
from typing import List, Optional

import pygame

from src.audio_manager import get_audio_manager
from src.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WHITE,
    BLACK,
    FONT_SIZE_SMALL,
    FONT_SIZE_MEDIUM,
    scaled,
)
from src.font import get_font

logger = logging.getLogger(__name__)

# Dialogue window colours (dark blue semi-transparent, matching battle UI)
_BG_COLOR = (10, 10, 80, 210)
_BORDER_COLOR = (200, 200, 255)
_TEXT_COLOR = WHITE
_CHOICE_CURSOR_COLOR = (255, 255, 100)
_CHOICE_HIGHLIGHT_COLOR = (60, 60, 140, 180)

# Typewriter speed: characters per frame (at 60 FPS)
_DEFAULT_TYPE_SPEED = 2

# Layout constants (pre-scale values; scaled() is applied at use-site)
_WINDOW_MARGIN_X = 24
_WINDOW_MARGIN_BOTTOM = 16
_WINDOW_HEIGHT = 120
_WINDOW_BORDER = 3
_WINDOW_PADDING_X = 16
_WINDOW_PADDING_Y = 12

_NAME_BOX_HEIGHT = 28
_NAME_BOX_PADDING_X = 12
_NAME_BOX_OFFSET_Y = 4  # gap above the main dialogue window

_CHOICE_LINE_HEIGHT = 30
_CHOICE_CURSOR_SIZE = 10

# Sound effect IDs
_SE_OPEN = "menu_select"
_SE_TEXT_SCROLL = "cursor_move"
_SE_CHOICE_MOVE = "cursor_move"
_SE_CHOICE_CONFIRM = "menu_select"


class DialogueRenderer:
    """Renders dialogue windows and choice menus.

    State machine:
        idle -> typing -> waiting -> idle   (for say)
        idle -> choosing -> idle            (for choice)
    """

    def __init__(self):
        self._state: str = "idle"  # idle | typing | waiting | choosing

        # Text display
        self._speaker: str = ""
        self._full_text: str = ""
        self._displayed_chars: int = 0
        self._type_speed: int = _DEFAULT_TYPE_SPEED

        # Choice display
        self._choices: List[str] = []
        self._choice_cursor: int = 0
        self._choice_result: Optional[int] = None  # 1-based for Lua

        # Cancellation
        self._is_cancelled: bool = False

        # Fonts
        self._font_text = get_font(scaled(FONT_SIZE_SMALL))
        self._font_name = get_font(scaled(FONT_SIZE_SMALL))

        # Audio
        self._audio = get_audio_manager()

        # Surfaces (created once, reused)
        self._window_surface: Optional[pygame.Surface] = None
        self._name_surface: Optional[pygame.Surface] = None

        # Pre-compute layout rects
        self._compute_layout()

        # Typewriter sound throttle
        self._text_sound_counter: int = 0

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _compute_layout(self) -> None:
        """Pre-compute window rects."""
        margin_x = scaled(_WINDOW_MARGIN_X)
        margin_bottom = scaled(_WINDOW_MARGIN_BOTTOM)
        win_h = scaled(_WINDOW_HEIGHT)
        border = scaled(_WINDOW_BORDER)

        self._win_rect = pygame.Rect(
            margin_x,
            SCREEN_HEIGHT - margin_bottom - win_h,
            SCREEN_WIDTH - margin_x * 2,
            win_h,
        )

        # Name box sits above the main window
        name_h = scaled(_NAME_BOX_HEIGHT)
        name_gap = scaled(_NAME_BOX_OFFSET_Y)
        self._name_rect = pygame.Rect(
            self._win_rect.x + scaled(8),
            self._win_rect.y - name_h - name_gap,
            scaled(160),
            name_h,
        )

        self._border = border
        self._pad_x = scaled(_WINDOW_PADDING_X)
        self._pad_y = scaled(_WINDOW_PADDING_Y)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_dialogue(self, speaker: str, text: str) -> None:
        """Start typewriter display of dialogue text."""
        self._speaker = speaker
        self._full_text = text
        self._displayed_chars = 0
        self._is_cancelled = False
        self._state = "typing"
        self._text_sound_counter = 0
        self._audio.play_se(_SE_OPEN)

    def show_choice(self, options: List[str]) -> None:
        """Show a choice menu."""
        self._choices = list(options)
        self._choice_cursor = 0
        self._choice_result = None
        self._is_cancelled = False
        self._state = "choosing"
        self._audio.play_se(_SE_OPEN)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a keyboard event. Returns True if the event was consumed."""
        if self._state == "idle":
            return False

        if event.type != pygame.KEYDOWN:
            return False

        confirm_keys = (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)

        if self._state == "typing":
            if event.key in confirm_keys:
                # Instant-reveal remaining text
                self._displayed_chars = len(self._full_text)
                self._state = "waiting"
                return True
            if event.key == pygame.K_ESCAPE:
                self._is_cancelled = True
                self._state = "idle"
                return True
            return True  # consume all keys while typing

        if self._state == "waiting":
            if event.key in confirm_keys:
                # Advance — signal completion to caller
                self._state = "idle"
                return True
            if event.key == pygame.K_ESCAPE:
                self._is_cancelled = True
                self._state = "idle"
                return True
            return True

        if self._state == "choosing":
            if event.key == pygame.K_UP:
                self._choice_cursor = (self._choice_cursor - 1) % len(self._choices)
                self._audio.play_se(_SE_CHOICE_MOVE)
                return True
            if event.key == pygame.K_DOWN:
                self._choice_cursor = (self._choice_cursor + 1) % len(self._choices)
                self._audio.play_se(_SE_CHOICE_MOVE)
                return True
            if event.key in confirm_keys:
                self._choice_result = self._choice_cursor + 1  # 1-based
                self._audio.play_se(_SE_CHOICE_CONFIRM)
                self._state = "idle"
                return True
            # Escape is ignored during choice (must select)
            return True

        return False

    def update(self) -> None:
        """Advance typewriter effect by one frame."""
        if self._state != "typing":
            return

        old_chars = self._displayed_chars
        self._displayed_chars = min(
            len(self._full_text),
            self._displayed_chars + self._type_speed,
        )

        # Play text scroll sound every few characters
        if self._displayed_chars > old_chars:
            self._text_sound_counter += self._displayed_chars - old_chars
            if self._text_sound_counter >= 4:
                self._text_sound_counter = 0
                self._audio.play_se(_SE_TEXT_SCROLL)

        if self._displayed_chars >= len(self._full_text):
            self._state = "waiting"

    def draw(self, screen: pygame.Surface) -> None:
        """Render the dialogue UI onto the screen."""
        if self._state == "idle":
            return

        if self._state in ("typing", "waiting"):
            self._draw_dialogue_window(screen)
        elif self._state == "choosing":
            self._draw_choice_window(screen)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True if dialogue or choice is currently displayed."""
        return self._state != "idle"

    @property
    def is_cancelled(self) -> bool:
        """True if the player pressed Escape during a say display."""
        return self._is_cancelled

    @property
    def state(self) -> str:
        return self._state

    def get_choice_result(self) -> Optional[int]:
        """Return the selected choice index (1-based for Lua), or None."""
        return self._choice_result

    def reset(self) -> None:
        """Force-reset to idle state."""
        self._state = "idle"
        self._is_cancelled = False
        self._choice_result = None
        self._choices = []
        self._full_text = ""
        self._speaker = ""

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_box(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw a dark-blue semi-transparent box with white border."""
        box_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        box_surf.fill(_BG_COLOR)
        screen.blit(box_surf, rect.topleft)
        pygame.draw.rect(screen, _BORDER_COLOR, rect, self._border)

    def _draw_dialogue_window(self, screen: pygame.Surface) -> None:
        """Draw the main dialogue window with speaker name and text."""
        # Draw name box
        if self._speaker:
            # Measure name text to size the box
            name_text = self._font_name.render(self._speaker, True, _TEXT_COLOR)
            name_box_w = name_text.get_width() + scaled(_NAME_BOX_PADDING_X) * 2
            name_rect = pygame.Rect(
                self._name_rect.x,
                self._name_rect.y,
                max(name_box_w, self._name_rect.width),
                self._name_rect.height,
            )
            self._draw_box(screen, name_rect)
            name_x = name_rect.x + (name_rect.width - name_text.get_width()) // 2
            name_y = name_rect.y + (name_rect.height - name_text.get_height()) // 2
            screen.blit(name_text, (name_x, name_y))

        # Draw main window
        self._draw_box(screen, self._win_rect)

        # Draw text (with word wrapping)
        visible_text = self._full_text[: self._displayed_chars]
        self._draw_wrapped_text(
            screen,
            visible_text,
            self._win_rect.x + self._pad_x,
            self._win_rect.y + self._pad_y,
            self._win_rect.width - self._pad_x * 2,
        )

        # Draw advance indicator when waiting
        if self._state == "waiting":
            indicator_x = self._win_rect.right - self._pad_x
            indicator_y = self._win_rect.bottom - self._pad_y
            arrow_size = scaled(6)
            points = [
                (indicator_x - arrow_size, indicator_y - arrow_size * 2),
                (indicator_x + arrow_size, indicator_y - arrow_size * 2),
                (indicator_x, indicator_y),
            ]
            pygame.draw.polygon(screen, _CHOICE_CURSOR_COLOR, points)

    def _draw_choice_window(self, screen: pygame.Surface) -> None:
        """Draw the choice selection window."""
        line_h = scaled(_CHOICE_LINE_HEIGHT)
        pad_x = self._pad_x
        pad_y = self._pad_y
        cursor_size = scaled(_CHOICE_CURSOR_SIZE)

        # Calculate choice window height
        num_choices = len(self._choices)
        choice_height = pad_y * 2 + line_h * num_choices

        choice_rect = pygame.Rect(
            self._win_rect.x,
            self._win_rect.y + self._win_rect.height - choice_height,
            self._win_rect.width,
            choice_height,
        )

        # Adjust main window to sit above choice
        main_rect = pygame.Rect(
            self._win_rect.x,
            self._win_rect.y,
            self._win_rect.width,
            self._win_rect.height - choice_height,
        )

        # Draw main dialogue window (showing the last dialogue text if any)
        if self._full_text:
            self._draw_box(screen, main_rect)

            # Speaker name
            if self._speaker:
                name_text = self._font_name.render(self._speaker, True, _TEXT_COLOR)
                name_box_w = name_text.get_width() + scaled(_NAME_BOX_PADDING_X) * 2
                name_rect = pygame.Rect(
                    self._name_rect.x,
                    main_rect.y - self._name_rect.height - scaled(_NAME_BOX_OFFSET_Y),
                    max(name_box_w, self._name_rect.width),
                    self._name_rect.height,
                )
                self._draw_box(screen, name_rect)
                name_x = name_rect.x + (name_rect.width - name_text.get_width()) // 2
                name_y = name_rect.y + (name_rect.height - name_text.get_height()) // 2
                screen.blit(name_text, (name_x, name_y))

            self._draw_wrapped_text(
                screen,
                self._full_text,
                main_rect.x + pad_x,
                main_rect.y + pad_y,
                main_rect.width - pad_x * 2,
            )

        # Draw choice box
        self._draw_box(screen, choice_rect)

        for i, choice_text in enumerate(self._choices):
            text_y = choice_rect.y + pad_y + i * line_h

            # Highlight selected
            if i == self._choice_cursor:
                highlight_rect = pygame.Rect(
                    choice_rect.x + pad_x - scaled(4),
                    text_y - scaled(2),
                    choice_rect.width - pad_x * 2 + scaled(8),
                    line_h,
                )
                hl_surf = pygame.Surface(
                    (highlight_rect.width, highlight_rect.height), pygame.SRCALPHA
                )
                hl_surf.fill(_CHOICE_HIGHLIGHT_COLOR)
                screen.blit(hl_surf, highlight_rect.topleft)

                # Draw cursor triangle
                cx = choice_rect.x + pad_x
                cy = text_y + line_h // 2
                tri_points = [
                    (cx, cy - cursor_size // 2),
                    (cx, cy + cursor_size // 2),
                    (cx + cursor_size, cy),
                ]
                pygame.draw.polygon(screen, _CHOICE_CURSOR_COLOR, tri_points)

            rendered = self._font_text.render(choice_text, True, _TEXT_COLOR)
            screen.blit(rendered, (choice_rect.x + pad_x + cursor_size + scaled(8), text_y))

    def _draw_wrapped_text(
        self, screen: pygame.Surface, text: str, x: int, y: int, max_width: int
    ) -> None:
        """Render text with basic line wrapping."""
        line_height = self._font_text.get_linesize()
        current_y = y

        # Split on explicit newlines first
        for paragraph in text.split("\n"):
            if not paragraph:
                current_y += line_height
                continue

            # Simple character-based wrapping for Japanese text
            line = ""
            for ch in paragraph:
                test_line = line + ch
                test_w = self._font_text.size(test_line)[0]
                if test_w > max_width and line:
                    rendered = self._font_text.render(line, True, _TEXT_COLOR)
                    screen.blit(rendered, (x, current_y))
                    current_y += line_height
                    line = ch
                else:
                    line = test_line

            if line:
                rendered = self._font_text.render(line, True, _TEXT_COLOR)
                screen.blit(rendered, (x, current_y))
                current_y += line_height
