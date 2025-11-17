"""
Action Ring - Logitech Options+ style radial menu overlay for Solaar

This module implements a customizable on-screen overlay that displays
a circular menu of action bubbles around the mouse cursor.

Components:
- overlay.py: Main overlay window and GTK integration
- renderer.py: Cairo-based circular bubble rendering
- animations.py: Animation system (fade, scale, highlight)
- bubbles.py: Bubble layout, collision detection, and interaction
- config.py: Configuration management and GUI editor
- actions.py: Action execution system
"""

from .overlay import ActionRingOverlay

__all__ = ['ActionRingOverlay']
