"""
レイヤー遷移エフェクト — Layer Transition

Manages visual fade effects when the player moves between world layers
(physical / depth / dream).
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Layer-specific tint colours applied during fade
LAYER_TINTS = {
    "physical": (0, 0, 0),
    "depth": (20, 0, 40),
    "dream": (40, 40, 60),
}

# Duration of a full fade-out + fade-in cycle (in frames at 60 FPS)
DEFAULT_FADE_FRAMES = 60


class LayerTransition:
    """Handles visual transitions between world layers.

    Typical usage inside a scene's update loop::

        if transition.is_transitioning:
            transition.update()
        # ... in draw:
        alpha, tint = transition.get_overlay()
    """

    def __init__(self, world_state_manager: Optional[object] = None, fade_frames: int = DEFAULT_FADE_FRAMES):
        self._wsm = world_state_manager
        self._fade_frames = fade_frames

        # Transition state
        self._active: bool = False
        self._target_layer: Optional[str] = None
        self._frame: int = 0
        self._half: int = fade_frames // 2  # fade-out then fade-in

        # When True, the layer switch happens at the midpoint (screen fully dark)
        self._layer_switched: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start_transition(self, target_layer: str) -> None:
        """Begin a layer transition to *target_layer*."""
        if self._active:
            logger.warning("Transition already in progress — ignoring request to %s", target_layer)
            return

        self._target_layer = target_layer
        self._active = True
        self._frame = 0
        self._layer_switched = False
        logger.info("Starting layer transition to %s", target_layer)

    def update(self) -> None:
        """Advance the transition by one frame.  Call once per game tick."""
        if not self._active:
            return

        self._frame += 1

        # At the midpoint, switch the actual layer
        if not self._layer_switched and self._frame >= self._half:
            self._layer_switched = True
            if self._wsm is not None and self._target_layer is not None:
                self._wsm.change_layer(self._target_layer)
            logger.debug("Layer switched at midpoint (frame %d)", self._frame)

        # Transition complete
        if self._frame >= self._fade_frames:
            self._active = False
            self._target_layer = None
            logger.debug("Layer transition complete")

    @property
    def is_transitioning(self) -> bool:
        """True while a fade is in progress."""
        return self._active

    def get_overlay(self) -> Tuple[int, Tuple[int, int, int]]:
        """Return (alpha, tint_colour) for the current frame.

        *alpha* ranges from 0 (transparent) to 255 (fully opaque).
        During the first half the overlay fades *in*; during the second
        half it fades *out*.  The tint colour is determined by the
        *target* layer.
        """
        if not self._active:
            return 0, (0, 0, 0)

        tint = LAYER_TINTS.get(self._target_layer, (0, 0, 0))

        if self._frame <= self._half:
            # Fading out (overlay getting more opaque)
            progress = self._frame / max(self._half, 1)
            alpha = int(255 * progress)
        else:
            # Fading in (overlay getting more transparent)
            progress = (self._frame - self._half) / max(self._half, 1)
            alpha = int(255 * (1.0 - progress))

        return min(alpha, 255), tint

    @property
    def target_layer(self) -> Optional[str]:
        """The layer we are transitioning to (or None if idle)."""
        return self._target_layer
