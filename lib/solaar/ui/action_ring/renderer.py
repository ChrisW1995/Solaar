"""
Cairo Renderer for Action Ring Bubbles

Handles all Cairo-based rendering including:
- Circular bubbles with gradients
- Icons and text labels
- Hover/selection highlights
- Folder expansion animations
"""

import cairo
import math
from typing import List, Tuple

from .bubbles import Bubble, BubbleLayout


class BubbleRenderer:
    """
    Renders Action Ring bubbles using Cairo.

    Implements Logitech Options+ style visual design:
    - Semi-transparent dark bubbles
    - Gradient highlights on hover
    - Smooth animations
    - Icon + text labels
    """

    def __init__(self):
        # Color scheme (matching Logitech Options+ light theme)
        self.bg_color = (1.0, 1.0, 1.0, 0.85)  # White background with more transparency
        self.hover_color = (0.2, 0.2, 0.2, 0.90)  # Dark gray/black on hover with transparency
        self.selected_color = (0.3, 0.5, 0.8, 0.95)  # Blue accent
        self.icon_color = (0.2, 0.2, 0.2, 1.0)  # Dark gray/black icons
        self.icon_hover_color = (1.0, 1.0, 1.0, 1.0)  # White icons on hover

        # Highlight colors
        self.highlight_color = (0.4, 0.6, 1.0, 0.3)  # Subtle blue glow

        # Font settings (for tooltips, not displayed on bubbles)
        self.font_family = "Sans"
        self.font_size = 12

    def render(self, cr: cairo.Context, layout: BubbleLayout, width: int, height: int):
        """
        Main render function - draws all bubbles.

        Args:
            cr: Cairo context
            layout: BubbleLayout containing bubble positions and states
            width, height: Drawing area dimensions
        """
        # Clear background with full transparency
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw center background circle (subtle)
        self._draw_center_background(cr, layout.center_x, layout.center_y, layout.primary_radius + 60)

        # Draw center close button
        self._draw_center_button(cr, layout.center_x, layout.center_y)

        # Get all visible bubbles
        bubbles = layout.get_all_visible_bubbles()

        # Draw bubbles (back to front, hovered last for proper layering)
        normal_bubbles = [b for b in bubbles if not b.is_hovered]
        hovered_bubbles = [b for b in bubbles if b.is_hovered]

        for bubble in normal_bubbles:
            self._draw_bubble(cr, bubble)

        for bubble in hovered_bubbles:
            self._draw_bubble(cr, bubble)

    def _draw_center_background(self, cr: cairo.Context, center_x: float, center_y: float, radius: float):
        """Draw subtle background circle behind all bubbles"""
        # Radial gradient from center
        gradient = cairo.RadialGradient(center_x, center_y, 0, center_x, center_y, radius)
        gradient.add_color_stop_rgba(0, 0.1, 0.1, 0.1, 0.3)  # Dark center
        gradient.add_color_stop_rgba(1, 0.1, 0.1, 0.1, 0.0)  # Fade to transparent

        cr.set_source(gradient)
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.fill()

    def _draw_center_button(self, cr: cairo.Context, center_x: float, center_y: float):
        """Draw center close button (X)"""
        button_radius = 30  # Larger button circle

        # Draw button circle
        cr.arc(center_x, center_y, button_radius, 0, 2 * math.pi)
        cr.set_source_rgba(0.2, 0.2, 0.2, 0.8)
        cr.fill_preserve()

        # Border
        cr.set_source_rgba(0.4, 0.4, 0.4, 0.9)
        cr.set_line_width(1.5)
        cr.stroke()

        # Draw X symbol (smaller relative to button)
        cr.set_source_rgba(0.9, 0.9, 0.9, 0.9)
        cr.set_line_width(2.5)

        # First line of X (smaller offset)
        offset = 8  # Reduced from 10 to make X smaller
        cr.move_to(center_x - offset, center_y - offset)
        cr.line_to(center_x + offset, center_y + offset)
        cr.stroke()

        # Second line of X
        cr.move_to(center_x + offset, center_y - offset)
        cr.line_to(center_x - offset, center_y + offset)
        cr.stroke()

    def _draw_bubble(self, cr: cairo.Context, bubble: Bubble):
        """
        Draw a single bubble with all effects.

        Logitech Options+ style:
        1. Main bubble circle (white/black based on hover)
        2. Icon only (no text on bubble)
        """
        x, y = bubble.x, bubble.y
        radius = bubble.radius * bubble.scale

        # Draw main bubble circle
        cr.arc(x, y, radius, 0, 2 * math.pi)

        # Choose color based on state (white/black inversion on hover)
        if bubble.is_selected:
            cr.set_source_rgba(*self.selected_color)
        elif bubble.is_hovered:
            cr.set_source_rgba(*self.hover_color)  # Black on hover
        else:
            cr.set_source_rgba(*self.bg_color)  # White normal

        cr.fill()

        # Draw folder indicator (if folder)
        if bubble.is_folder:
            icon_color = self.icon_hover_color if bubble.is_hovered else self.icon_color
            self._draw_folder_indicator(cr, x, y, radius, icon_color)

        # Draw icon (no text label on bubble)
        icon_color = self.icon_hover_color if bubble.is_hovered else self.icon_color
        self._draw_icon(cr, x, y, bubble.label, radius * 0.5, icon_color)

    def _draw_glow(self, cr: cairo.Context, x: float, y: float, radius: float, intensity: float):
        """Draw glowing effect around bubble"""
        glow_radius = radius * 1.3

        # Radial gradient for glow
        gradient = cairo.RadialGradient(x, y, radius, x, y, glow_radius)
        gradient.add_color_stop_rgba(0, *self.highlight_color[:3], 0)
        gradient.add_color_stop_rgba(1, *self.highlight_color[:3], self.highlight_color[3] * intensity)

        cr.set_source(gradient)
        cr.arc(x, y, glow_radius, 0, 2 * math.pi)
        cr.fill()

    def _draw_folder_indicator(self, cr: cairo.Context, x: float, y: float, radius: float, color: tuple):
        """Draw small indicator showing this is a folder"""
        # Draw three small dots in bottom-right
        dot_radius = 2
        spacing = 6
        start_x = x + radius * 0.3
        start_y = y + radius * 0.5

        cr.set_source_rgba(*color)
        for i in range(3):
            cr.arc(start_x + i * spacing, start_y, dot_radius, 0, 2 * math.pi)
            cr.fill()

    def _draw_icon(self, cr: cairo.Context, x: float, y: float, label: str, size: float, color: tuple):
        """
        Draw icon in bubble based on label.

        For now, draws first letter of label as placeholder.
        TODO: Load actual icons from icon theme or custom icons
        """
        # Draw first letter of label as icon placeholder
        cr.select_font_face(self.font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(size * 0.8)

        # Get first letter or first two letters
        icon_text = label[0:2] if len(label) >= 2 else label[0] if label else "?"

        # Get text dimensions for centering
        extents = cr.text_extents(icon_text)
        text_x = x - extents.width / 2 - extents.x_bearing
        text_y = y - extents.height / 2 - extents.y_bearing

        # Draw icon text
        cr.set_source_rgba(*color)
        cr.move_to(text_x, text_y)
        cr.show_text(icon_text)
