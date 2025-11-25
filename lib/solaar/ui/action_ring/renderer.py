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
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
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
        self.bg_color = (1.0, 1.0, 1.0, 0.5)  # White background with more transparency
        self.hover_color = (0.2, 0.2, 0.2, 1.0)  # Dark gray/black on hover with full opacity
        self.selected_color = (0.3, 0.5, 0.8, 0.95)  # Blue accent
        self.icon_color = (0.2, 0.2, 0.2, 1.0)  # Dark gray/black icons
        self.icon_hover_color = (1.0, 1.0, 1.0, 1.0)  # White icons on hover

        # Highlight colors
        self.highlight_color = (0.4, 0.6, 1.0, 0.3)  # Subtle blue glow

        # Font settings (for tooltips, not displayed on bubbles)
        self.font_family = "Sans"
        self.font_size = 12

    def render(self, cr: cairo.Context, layout: BubbleLayout, width: int, height: int, transparent_background: bool = True):
        """
        Main render function - draws all bubbles.

        Args:
            cr: Cairo context
            layout: BubbleLayout containing bubble positions and states
            width, height: Drawing area dimensions
            transparent_background: Whether to clear background to transparent (for overlay)
        """
        if transparent_background:
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

        # Draw button circle (same color as other bubbles)
        cr.arc(center_x, center_y, button_radius, 0, 2 * math.pi)
        cr.set_source_rgba(*self.bg_color)
        cr.fill()

        # Draw X symbol (smaller icon)
        cr.set_source_rgba(*self.icon_color)
        cr.set_line_width(2.5)

        # First line of X (smaller offset)
        offset = 6  # Smaller X icon
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
        self._draw_icon(cr, x, y, bubble.label, radius * 0.7, icon_color, icon_name=bubble.icon)

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

    def _draw_icon(self, cr: cairo.Context, x: float, y: float, label: str, size: float, color: tuple, icon_name: str = None):
        """
        Draw icon in bubble based on label or icon name.
        """
        cr.set_source_rgba(*color)
        
        # Try to render GTK icon if name provided
        if icon_name:
            try:
                pixbuf = None
                
                # Check if icon_name is a file path
                if icon_name.startswith('/') or icon_name.startswith('.'):
                    # It's a file path, load directly
                    try:
                        from gi.repository import GdkPixbuf
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, int(size), int(size))
                    except Exception as e:
                        print(f"DEBUG: Failed to load icon from file '{icon_name}': {e}")
                else:
                    # It's a theme icon name
                    theme = Gtk.IconTheme.get_default()
                    icon_info = theme.lookup_icon(icon_name, int(size), Gtk.IconLookupFlags.USE_BUILTIN)
                    if icon_info:
                        pixbuf = icon_info.load_icon()
                    else:
                        print(f"DEBUG: Icon '{icon_name}' not found in theme")
                
                # If we got a pixbuf, render it
                if pixbuf:
                    pw = pixbuf.get_width()
                    ph = pixbuf.get_height()
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, x - pw/2, y - ph/2)
                    cr.paint()
                    return
                    
            except Exception as e:
                print(f"DEBUG: Failed to load icon '{icon_name}': {e}")
                # Continue to fallback

        cr.set_line_width(2.0)

        # Map labels to different test icons (Legacy/Fallback)
        if "Action 1" in label:
            self._draw_arrow_up_icon(cr, x, y, size, color)
        elif "Action 2" in label:
            self._draw_settings_icon(cr, x, y, size, color)
        elif "Action 3" in label:
            self._draw_document_icon(cr, x, y, size, color)
        elif "Action 4" in label:
            self._draw_search_icon(cr, x, y, size, color)
        elif "Action 5" in label:
            self._draw_arrow_down_icon(cr, x, y, size, color)
        elif "Action 6" in label:
            self._draw_play_icon(cr, x, y, size, color)
        elif "Action 7" in label:
            self._draw_folder_icon(cr, x, y, size, color)
        elif "Action 8" in label:
            self._draw_star_icon(cr, x, y, size, color)
        else:
            # Default fallback: draw first letter
            cr.select_font_face(self.font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(size * 0.8)
            icon_text = label[0:2] if len(label) >= 2 else label[0] if label else "?"
            extents = cr.text_extents(icon_text)
            text_x = x - extents.width / 2 - extents.x_bearing
            text_y = y - extents.height / 2 - extents.y_bearing
            cr.move_to(text_x, text_y)
            cr.show_text(icon_text)

    def _draw_arrow_up_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw upward arrow icon"""
        cr.set_source_rgba(*color)
        s = size * 0.4
        # Arrow shaft
        cr.move_to(x, y - s)
        cr.line_to(x, y + s)
        cr.stroke()
        # Arrow head
        cr.move_to(x - s * 0.6, y - s * 0.4)
        cr.line_to(x, y - s)
        cr.line_to(x + s * 0.6, y - s * 0.4)
        cr.stroke()

    def _draw_arrow_down_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw downward arrow icon"""
        cr.set_source_rgba(*color)
        s = size * 0.4
        # Arrow shaft
        cr.move_to(x, y - s)
        cr.line_to(x, y + s)
        cr.stroke()
        # Arrow head
        cr.move_to(x - s * 0.6, y + s * 0.4)
        cr.line_to(x, y + s)
        cr.line_to(x + s * 0.6, y + s * 0.4)
        cr.stroke()

    def _draw_settings_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw gear/settings icon"""
        cr.set_source_rgba(*color)
        s = size * 0.35
        # Outer circle
        cr.arc(x, y, s, 0, 2 * math.pi)
        cr.stroke()
        # Inner circle
        cr.arc(x, y, s * 0.4, 0, 2 * math.pi)
        cr.stroke()
        # Gear teeth (4 lines)
        for i in range(4):
            angle = i * math.pi / 2
            x1 = x + s * 0.7 * math.cos(angle)
            y1 = y + s * 0.7 * math.sin(angle)
            x2 = x + s * 1.1 * math.cos(angle)
            y2 = y + s * 1.1 * math.sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

    def _draw_document_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw document icon"""
        cr.set_source_rgba(*color)
        s = size * 0.4
        # Document outline
        cr.move_to(x - s * 0.6, y - s)
        cr.line_to(x + s * 0.3, y - s)
        cr.line_to(x + s * 0.6, y - s * 0.7)
        cr.line_to(x + s * 0.6, y + s)
        cr.line_to(x - s * 0.6, y + s)
        cr.close_path()
        cr.stroke()
        # Corner fold
        cr.move_to(x + s * 0.3, y - s)
        cr.line_to(x + s * 0.3, y - s * 0.7)
        cr.line_to(x + s * 0.6, y - s * 0.7)
        cr.stroke()
        # Lines
        for i in range(3):
            y_pos = y - s * 0.3 + i * s * 0.4
            cr.move_to(x - s * 0.4, y_pos)
            cr.line_to(x + s * 0.4, y_pos)
            cr.stroke()

    def _draw_search_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw magnifying glass icon"""
        cr.set_source_rgba(*color)
        s = size * 0.35
        # Magnifying glass circle
        cr.arc(x - s * 0.2, y - s * 0.2, s * 0.6, 0, 2 * math.pi)
        cr.stroke()
        # Handle
        cr.move_to(x + s * 0.2, y + s * 0.2)
        cr.line_to(x + s * 0.8, y + s * 0.8)
        cr.stroke()

    def _draw_play_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw play triangle icon"""
        cr.set_source_rgba(*color)
        s = size * 0.4
        # Play triangle
        cr.move_to(x - s * 0.4, y - s * 0.7)
        cr.line_to(x + s * 0.7, y)
        cr.line_to(x - s * 0.4, y + s * 0.7)
        cr.close_path()
        cr.stroke()

    def _draw_folder_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw folder icon"""
        cr.set_source_rgba(*color)
        s = size * 0.4
        # Folder outline
        cr.move_to(x - s * 0.7, y - s * 0.3)
        cr.line_to(x - s * 0.3, y - s * 0.7)
        cr.line_to(x + s * 0.3, y - s * 0.7)
        cr.line_to(x + s * 0.7, y - s * 0.3)
        cr.line_to(x + s * 0.7, y + s * 0.7)
        cr.line_to(x - s * 0.7, y + s * 0.7)
        cr.close_path()
        cr.stroke()

    def _draw_star_icon(self, cr: cairo.Context, x: float, y: float, size: float, color: tuple):
        """Draw star icon"""
        cr.set_source_rgba(*color)
        s = size * 0.4
        # 5-pointed star
        points = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            radius = s if i % 2 == 0 else s * 0.4
            points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))

        cr.move_to(points[0][0], points[0][1])
        for point in points[1:]:
            cr.line_to(point[0], point[1])
        cr.close_path()
        cr.stroke()
