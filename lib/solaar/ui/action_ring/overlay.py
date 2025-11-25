"""
Action Ring Overlay Window

Implements the main GTK popup window for the Action Ring overlay.
Handles window creation, positioning, and lifecycle management.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo
import subprocess

import logging
import math

from .bubbles import BubbleLayout, Bubble, FolderBubble
from .renderer import BubbleRenderer

logger = logging.getLogger(__name__)


class TooltipWidget(Gtk.DrawingArea):
    """Custom tooltip widget with message bubble style and pointing arrow."""

    def __init__(self):
        super().__init__()
        self.text = ""
        self.direction = "top"  # Direction where arrow points: top, bottom, left, right
        self.set_size_request(100, 40)
        self.connect("draw", self._on_draw)

    def set_text(self, text):
        """Set tooltip text."""
        self.text = text
        # Adjust size based on text length (rough estimate)
        text_width = max(100, len(text) * 9)
        self.set_size_request(text_width, 40)
        self.queue_draw()

    def set_direction(self, direction):
        """Set arrow direction: top, bottom, left, right, top-left, top-right, bottom-left, bottom-right."""
        self.direction = direction
        self.queue_draw()

    def _on_draw(self, widget, cr):
        """Draw tooltip with arrow using Cairo."""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Clear background
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Tooltip dimensions
        padding = 12
        corner_radius = 12
        arrow_size = 8

        # Calculate bubble rectangle (leaving space for arrow)
        # Default values
        bubble_x = 0
        bubble_y = 0
        bubble_width = width
        bubble_height = height

        # Adjust based on arrow direction
        if self.direction in ["top", "top-left", "top-right"]:
            bubble_y = arrow_size
            bubble_height = height - arrow_size
        elif self.direction in ["bottom", "bottom-left", "bottom-right"]:
            bubble_height = height - arrow_size

        if self.direction in ["left", "bottom-left", "top-left"]:
            bubble_x = arrow_size
            bubble_width = width - arrow_size
        elif self.direction in ["right", "bottom-right", "top-right"]:
            bubble_width = width - arrow_size

        # Draw drop shadow with same shape as tooltip (including arrow)
        cr.save()
        cr.set_source_rgba(0, 0, 0, 0.15)
        self._draw_tooltip_shape(cr, bubble_x + 2, bubble_y + 2, bubble_width, bubble_height, corner_radius, arrow_size)
        cr.fill()
        cr.restore()

        # Draw tooltip background with arrow
        cr.set_source_rgba(1, 1, 1, 0.98)
        self._draw_tooltip_shape(cr, bubble_x, bubble_y, bubble_width, bubble_height, corner_radius, arrow_size)
        cr.fill_preserve()

        # Draw border
        cr.set_source_rgba(0, 0, 0, 0.1)
        cr.set_line_width(1)
        cr.stroke()

        # Draw text
        cr.set_source_rgba(0, 0, 0, 0.9)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(14)

        extents = cr.text_extents(self.text)
        text_x = bubble_x + (bubble_width - extents.width) / 2
        text_y = bubble_y + (bubble_height + extents.height) / 2

        cr.move_to(text_x, text_y)
        cr.show_text(self.text)

    def _draw_rounded_rect(self, cr, x, y, width, height, radius):
        """Draw a rounded rectangle path."""
        cr.new_path()
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.arc(x + width - radius, y + radius, radius, 3 * math.pi / 2, 0)
        cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + height - radius, radius, math.pi / 2, math.pi)
        cr.close_path()

    def _draw_tooltip_shape(self, cr, x, y, width, height, radius, arrow_size):
        """Draw tooltip shape with arrow pointing in specified direction.

        All paths are drawn clockwise around the perimeter.
        """
        cr.new_path()

        # Helper to draw corners
        def draw_corner(cx, cy, start_angle, end_angle):
            cr.arc(cx, cy, radius, start_angle, end_angle)

        if self.direction == "top":
            # Arrow points up (tooltip below bubble)
            arrow_x = x + width / 2
            cr.move_to(arrow_x, y - arrow_size)  # Tip
            cr.line_to(arrow_x + arrow_size, y)  # Right base
            cr.line_to(x + width - radius, y)    # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, y + height - radius) # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(x + radius, y + height)   # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, y + radius)            # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(arrow_x - arrow_size, y)  # Top edge to arrow left base
            cr.close_path()

        elif self.direction == "bottom":
            # Arrow points down (tooltip above bubble)
            arrow_x = x + width / 2
            cr.move_to(arrow_x, y + height + arrow_size) # Tip
            cr.line_to(arrow_x - arrow_size, y + height) # Left base
            cr.line_to(x + radius, y + height)           # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, y + radius)                    # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(x + width - radius, y)            # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, y + height - radius)   # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(arrow_x + arrow_size, y + height) # Bottom edge to arrow right base
            cr.close_path()

        elif self.direction == "left":
            # Arrow points left (tooltip to right of bubble)
            arrow_y = y + height / 2
            cr.move_to(x - arrow_size, arrow_y)  # Tip
            cr.line_to(x, arrow_y - arrow_size)  # Top base
            cr.line_to(x, y + radius)            # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(x + width - radius, y)    # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, y + height - radius) # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(x + radius, y + height)   # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, arrow_y + arrow_size)  # Left edge to arrow bottom base
            cr.close_path()

        elif self.direction == "right":
            # Arrow points right (tooltip to left of bubble)
            arrow_y = y + height / 2
            cr.move_to(x + width + arrow_size, arrow_y) # Tip
            cr.line_to(x + width, arrow_y + arrow_size) # Bottom base
            cr.line_to(x + width, y + height - radius)  # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(x + radius, y + height)          # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, y + radius)                   # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(x + width - radius, y)           # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, arrow_y - arrow_size) # Right edge to arrow top base
            cr.close_path()

        elif self.direction == "top-left":
            # Arrow points to top-left
            cr.move_to(x - arrow_size, y - arrow_size) # Tip
            cr.line_to(x + arrow_size, y)              # Right base (on top edge)
            cr.line_to(x + width - radius, y)          # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, y + height - radius) # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(x + radius, y + height)         # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, y + radius)                  # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL (partial)
            cr.line_to(x, y + arrow_size)              # Left edge to arrow base
            cr.close_path()

        elif self.direction == "top-right":
            # Arrow points to top-right
            cr.move_to(x + width + arrow_size, y - arrow_size) # Tip
            cr.line_to(x + width, y + arrow_size)              # Bottom base (on right edge)
            cr.line_to(x + width, y + height - radius)         # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(x + radius, y + height)                 # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, y + radius)                          # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(x + width - radius, y)                  # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR (partial)
            cr.line_to(x + width - arrow_size, y)              # Top edge to arrow base
            cr.close_path()

        elif self.direction == "bottom-left":
            # Arrow points to bottom-left
            cr.move_to(x - arrow_size, y + height + arrow_size) # Tip
            cr.line_to(x, y + height - arrow_size)              # Top base (on left edge)
            cr.line_to(x, y + radius)                           # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(x + width - radius, y)                   # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, y + height - radius)          # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR
            cr.line_to(x + radius, y + height)                  # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL (partial)
            cr.line_to(x + arrow_size, y + height)              # Bottom edge to arrow base
            cr.close_path()

        elif self.direction == "bottom-right":
            # Arrow points to bottom-right
            cr.move_to(x + width + arrow_size, y + height + arrow_size) # Tip
            cr.line_to(x + width - arrow_size, y + height)              # Left base (on bottom edge)
            cr.line_to(x + radius, y + height)                          # Bottom edge
            draw_corner(x + radius, y + height - radius, math.pi / 2, math.pi) # BL
            cr.line_to(x, y + radius)                                   # Left edge
            draw_corner(x + radius, y + radius, math.pi, 3 * math.pi / 2) # TL
            cr.line_to(x + width - radius, y)                           # Top edge
            draw_corner(x + width - radius, y + radius, 3 * math.pi / 2, 0) # TR
            cr.line_to(x + width, y + height - radius)                  # Right edge
            draw_corner(x + width - radius, y + height - radius, 0, math.pi / 2) # BR (partial)
            cr.line_to(x + width, y + height - arrow_size)              # Right edge to arrow base
            cr.close_path()

        else:
            # Fallback - simple rounded rect
            self._draw_rounded_rect(cr, x, y, width, height, radius)


class ActionRingOverlay(Gtk.Window):
    """
    Main Action Ring overlay window.

    Creates a transparent, undecorated popup window that displays
    at the mouse cursor position with circular action bubbles.
    """

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)

        # Window properties
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(True)  # Must accept focus to detect clicks outside

        # Set window type hint for proper behavior
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_keep_above(True)  # Always stay on top of other windows

        # Enable transparency (requires compositing)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            logger.info("Compositing enabled - transparency available")
        else:
            logger.warning("Compositing not available - transparency disabled")

        # Set window size (larger to accommodate all bubbles)
        self._window_width = 500
        self._window_height = 500
        self.set_default_size(self._window_width, self._window_height)

        # Drawing area for Cairo rendering
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect('draw', self._on_draw)

        # Create custom tooltip with arrow (message bubble style)
        self.tooltip_label = TooltipWidget()
        self.tooltip_label.set_halign(Gtk.Align.START)
        self.tooltip_label.set_valign(Gtk.Align.START)

        # Use overlay to position tooltip
        overlay = Gtk.Overlay()
        overlay.add(self.drawing_area)
        overlay.add_overlay(self.tooltip_label)

        self.add(overlay)

        # Mouse event handlers - bind to main window instead of drawing_area
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.connect('motion-notify-event', self._on_mouse_move)
        self.connect('button-press-event', self._on_button_press)
        self.connect('leave-notify-event', self._on_mouse_leave)

        # Close when focus is lost (clicking outside)
        self.connect('focus-out-event', self._on_focus_out)

        # State
        self._visible = False
        self._opacity = 0.0
        self._animation_id = None
        self._hover_animation_id = None
        self._hovered_bubble = None
        self._cursor_x = 0  # Mouse cursor position in window
        self._cursor_y = 0
        self._device = None  # Store device for haptic feedback
        self._tooltip_timer_id = None  # Timer for delayed tooltip display
        self._animation_complete = False  # Track if expand animation is complete
        self._last_mouse_x = 0  # Track mouse movement
        self._last_mouse_y = 0

        # Bubble system (will be initialized when showing)
        self._layout = None
        self._renderer = BubbleRenderer()

        logger.info("ActionRingOverlay initialized")

    def show_at_cursor(self, device=None):
        """
        Show the Action Ring overlay at the current mouse cursor position.
        Plays fade-in + scale animation from center.

        Args:
            device: Logitech device for haptic feedback (optional)
        """
        # Store device for haptic feedback
        self._device = device

        # Reset animation state
        self._animation_complete = False

        # Clean up tooltip state before showing
        if self._tooltip_timer_id:
            GLib.source_remove(self._tooltip_timer_id)
            self._tooltip_timer_id = None

        # Clear hover state
        if self._hovered_bubble:
            self._hovered_bubble.is_hovered = False
            self._hovered_bubble = None

        # Get current mouse position
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        screen, x, y = pointer.get_position()

        # Record initial mouse position to detect movement
        self._last_mouse_x = x
        self._last_mouse_y = y

        # Use fixed window size (get_allocated_* may return wrong values before show)
        width = self._window_width
        height = self._window_height

        # Position window so mouse is at center
        window_x = int(x - width / 2)
        window_y = int(y - height / 2)
        self.move(window_x, window_y)

        # Mouse cursor is now at window center
        self._cursor_x = width / 2
        self._cursor_y = height / 2

        # Initialize bubble layout centered at cursor position
        if self._layout is None:
            self._layout = BubbleLayout(self._cursor_x, self._cursor_y)
            
        # Update layout center to cursor position
        self._layout.center_x = self._cursor_x
        self._layout.center_y = self._cursor_y

        # Recalculate bubble positions around new center
        # This sets bubbles at center with target positions
        
        # Load config
        config = {}
        if self._device and hasattr(self._device, 'persister') and self._device.persister:
            config = self._device.persister.get("action-ring", {})
            
        self._layout.create_primary_bubbles(8, config)

        # Show window
        self.show_all()
        self._visible = True

        # Ensure tooltip is hidden (show_all() shows all widgets)
        self.tooltip_label.hide()

        # Start fade-in and expand animations
        self._animate_fade_in()
        self._animate_bubbles_expand()

        logger.info(f"Action Ring shown at cursor position ({x}, {y})")

    def _animate_bubbles_expand(self, step: int = 0):
        """Animate bubbles expanding from center to their target positions"""
        max_steps = 15  # ~250ms at 60fps

        if step >= max_steps:
            # Ensure all bubbles are at target position
            for bubble in self._layout.primary_bubbles:
                bubble.x = bubble.target_x
                bubble.y = bubble.target_y
                bubble.scale = 1.0
            self.drawing_area.queue_draw()
            # Animation complete - can now show tooltips
            self._animation_complete = True
            return False

        # Ease-out cubic interpolation
        progress = step / max_steps
        eased = 1 - (1 - progress) ** 3

        # Move bubbles from center to target position
        for bubble in self._layout.primary_bubbles:
            # Interpolate position
            bubble.x = self._cursor_x + (bubble.target_x - self._cursor_x) * eased
            bubble.y = self._cursor_y + (bubble.target_y - self._cursor_y) * eased
            bubble.scale = 1.0  # Always full scale

        self.drawing_area.queue_draw()
        GLib.timeout_add(16, self._animate_bubbles_expand, step + 1)
        return False

    def hide_overlay(self):
        """
        Hide the Action Ring overlay with fade-out animation.
        """
        if not self._visible:
            return

        # Clean up tooltip state
        if self._tooltip_timer_id:
            GLib.source_remove(self._tooltip_timer_id)
            self._tooltip_timer_id = None
        self.tooltip_label.hide()

        # Clear hover state
        if self._hovered_bubble:
            self._hovered_bubble.is_hovered = False
            self._hovered_bubble = None

        self._animate_fade_out()
        logger.info("Action Ring hiding")

    def _animate_fade_in(self, opacity=0.0):
        """Fade in animation (0.0 -> 1.0 over ~250ms)"""
        if opacity >= 1.0:
            self.set_opacity(1.0)
            self._animation_id = None
            return False

        self.set_opacity(opacity)
        self._opacity = opacity

        # ~60fps, increment for 250ms total duration
        self._animation_id = GLib.timeout_add(16, self._animate_fade_in, opacity + 0.064)
        return False

    def _animate_fade_out(self, opacity=1.0):
        """Fade out animation (1.0 -> 0.0 over ~250ms)"""
        if opacity <= 0.0:
            self.set_opacity(0.0)
            self.hide()
            self._visible = False
            self._animation_id = None
            return False

        self.set_opacity(opacity)
        self._opacity = opacity

        # ~60fps, decrement for 250ms total duration
        self._animation_id = GLib.timeout_add(16, self._animate_fade_out, opacity - 0.064)
        return False

    def _trigger_haptic(self, waveform=0x04):
        """
        Trigger haptic feedback on the device.

        Args:
            waveform: Haptic waveform ID (default: SUBTLE_COLLISION = 0x04)
                      0x04 = SUBTLE_COLLISION (for hover)
                      0x00 = SHARP_STATE_CHANGE (for click)
                      0x07 = COMPLETED (for click)
                      0x1B = WHISPER_COLLISION (very subtle)
        """
        if not self._device:
            return

        try:
            # Find the haptic-play setting
            setting = next((s for s in self._device.settings if s.name == "haptic-play"), None)
            if setting:
                # Write the waveform value to trigger haptic feedback
                setting.write(waveform)
                logger.debug(f"Haptic feedback triggered: waveform {waveform}")
            else:
                logger.debug("Haptic setting not found on device")
        except Exception as e:
            logger.warning(f"Failed to trigger haptic feedback: {e}")

    def _on_draw(self, widget, cr):
        """
        Cairo drawing callback - renders all bubbles.
        """
        if self._layout is None:
            return False

        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Render bubbles (center is at cursor position)
        self._renderer.render(cr, self._layout, width, height)

        return False

    def _on_mouse_move(self, widget, event):
        """Handle mouse movement for hover detection"""
        if not self._layout or not self._animation_complete:
            # Don't process hover until animation is complete
            return

        # Calculate distance moved from initial position
        distance_moved = ((event.x - self._last_mouse_x) ** 2 + (event.y - self._last_mouse_y) ** 2) ** 0.5

        # Only process hover if mouse has moved more than 5 pixels from initial position
        # This prevents tooltips from appearing when ring first opens
        if distance_moved < 5:
            return

        # Update hover state
        previously_hovered = self._hovered_bubble
        self._hovered_bubble = self._layout.update_hover(event.x, event.y)

        # Trigger hover animation if bubble changed
        if self._hovered_bubble != previously_hovered:
            # Cancel any pending tooltip timer
            if self._tooltip_timer_id:
                GLib.source_remove(self._tooltip_timer_id)
                self._tooltip_timer_id = None

            if self._hovered_bubble:
                # Start hover animation for new bubble
                self._animate_bubble_hover(self._hovered_bubble, entering=True)

                # Schedule tooltip to show after 1 second
                self._tooltip_timer_id = GLib.timeout_add(
                    1000,  # 1 second delay
                    self._show_tooltip_delayed,
                    self._hovered_bubble,
                    event.x,
                    event.y
                )

                # Trigger subtle haptic feedback on hover
                self._trigger_haptic(waveform=0x04)  # SUBTLE_COLLISION
                logger.debug(f"Hovering over bubble: {self._hovered_bubble.label}")
            elif previously_hovered:
                # End hover animation for previous bubble
                self._animate_bubble_hover(previously_hovered, entering=False)

                # Hide tooltip immediately
                self.tooltip_label.hide()

        # Redraw
        self.drawing_area.queue_draw()

    def _on_button_press(self, widget, event):
        """Handle mouse clicks for bubble selection"""
        logger.debug(f"Button press: button={event.button}, x={event.x}, y={event.y}")

        # Right click always closes
        if event.button == 3:
            logger.info("Right click - closing Action Ring")
            self.hide_overlay()
            return True

        if event.button == 1:  # Left click
            if not self._layout:
                logger.warning("Button press but layout not initialized")
                return True

            # Check if clicked on center close button
            center_x = self._layout.center_x
            center_y = self._layout.center_y
            distance_to_center = ((event.x - center_x) ** 2 + (event.y - center_y) ** 2) ** 0.5

            logger.debug(f"Distance to center: {distance_to_center}, center=({center_x}, {center_y})")

            if distance_to_center <= 30:  # Close button radius (match renderer)
                logger.info("Center close button clicked")
                # Trigger haptic feedback for close action
                self._trigger_haptic(waveform=0x00)  # SHARP_STATE_CHANGE
                self.hide_overlay()
                return True

            bubble = self._layout.get_bubble_at_position(event.x, event.y)
            if bubble:
                logger.info(f"Clicked bubble: {bubble.label}")

                # Trigger haptic feedback on click (stronger than hover)
                self._trigger_haptic(waveform=0x07)  # COMPLETED

                # Handle folder expansion
                if bubble.is_folder:
                    folder = bubble
                    if folder.is_expanded:
                        self._layout.collapse_folder()
                    else:
                        self._layout.expand_folder(folder)
                    self.drawing_area.queue_draw()
                else:
                    # Execute action
                    if bubble.action_type == "execute" and bubble.action_data:
                        try:
                            logger.info(f"Executing command: {bubble.action_data}")
                            subprocess.Popen(bubble.action_data, shell=True)
                        except Exception as e:
                            logger.error(f"Failed to execute command '{bubble.action_data}': {e}")
                    
                    elif bubble.action_type == "keypress" and bubble.action_data:
                        try:
                            logger.info(f"Executing keypress: {bubble.action_data}")
                            
                            # Key mapping for xdotool
                            key_map = {
                                "KEY_COPY": "ctrl+c",
                                "KEY_PASTE": "ctrl+v",
                                "KEY_CUT": "ctrl+x",
                                "KEY_UNDO": "ctrl+z",
                                "KEY_REDO": "ctrl+shift+z",
                                "KEY_PRINT": "Print",
                                "KEY_PLAYPAUSE": "XF86AudioPlay",
                                "KEY_NEXTSONG": "XF86AudioNext",
                                "KEY_PREVIOUSSONG": "XF86AudioPrev",
                                "KEY_VOLUMEUP": "XF86AudioRaiseVolume",
                                "KEY_VOLUMEDOWN": "XF86AudioLowerVolume",
                                "KEY_MUTE": "XF86AudioMute",
                                "KEY_BACK": "Alt+Left",
                                "KEY_FORWARD": "Alt+Right",
                                "KEY_HOMEPAGE": "Alt+Home",
                                "KEY_SCALE": "Super+s",  # Task view/Expose
                            }
                            
                            # Get mapped key or convert KEY_xxx to lowercase
                            if bubble.action_data in key_map:
                                key_name = key_map[bubble.action_data]
                            else:
                                key_name = bubble.action_data.replace("KEY_", "").lower()
                            
                            # Use xdotool to simulate key press
                            subprocess.Popen(["xdotool", "key", key_name])
                        except Exception as e:
                            logger.error(f"Failed to execute keypress '{bubble.action_data}': {e}")
                    
                    # Close overlay after action
                    self.hide_overlay()
                return True
            else:
                logger.debug("Clicked outside bubbles")

        return False

    def _on_mouse_leave(self, widget, event):
        """Handle mouse leaving the window"""
        if not self._layout:
            return

        # Clear hover state
        if self._hovered_bubble:
            self._animate_bubble_hover(self._hovered_bubble, entering=False)
            self._hovered_bubble = None

        # Update all bubbles to not hovered
        for bubble in self._layout.get_all_visible_bubbles():
            bubble.is_hovered = False

        # Hide tooltip
        self.tooltip_label.hide()

        self.drawing_area.queue_draw()

    def _show_tooltip_delayed(self, bubble, mouse_x, mouse_y):
        """Show tooltip after delay - callback for GLib.timeout_add"""
        # Only show if still hovering over the same bubble
        if bubble == self._hovered_bubble and self._visible:
            self._update_tooltip(bubble, mouse_x, mouse_y)
        self._tooltip_timer_id = None
        return False  # Don't repeat timer

    def _update_tooltip(self, bubble, mouse_x, mouse_y):
        """
        Update custom tooltip position and text.

        Positions tooltip in radial direction from center, matching Logitech Options+ style.
        """
        if bubble:
            self.tooltip_label.set_text(bubble.label)

            # Calculate angle from center to bubble
            dx = bubble.x - self._layout.center_x
            dy = bubble.y - self._layout.center_y
            angle = math.atan2(dy, dx)  # -π to π

            # Convert to degrees for easier understanding
            angle_deg = math.degrees(angle)  # -180 to 180

            # Determine tooltip direction based on angle (8 directions)
            # Different offset for left/right vs other directions
            # Note: arrow_size is 8 pixels (defined in TooltipWidget._on_draw)
            if -22.5 <= angle_deg < 22.5 or 157.5 <= angle_deg or angle_deg < -157.5:
                offset = 100  # Increased distance for left/right to account for arrow (90 + 10 extra spacing)
            else:
                offset = 50  # Standard distance for other directions

            tooltip_distance = bubble.radius + offset

            # Get actual tooltip dimensions (show it first to measure)
            self.tooltip_label.show()
            tooltip_width = self.tooltip_label.get_allocated_width()
            tooltip_height = self.tooltip_label.get_allocated_height()

            # Use minimum estimates if not yet allocated
            if tooltip_width < 10:
                tooltip_width = 100
            if tooltip_height < 10:
                tooltip_height = 40  # Increased for arrow space

            # Calculate base position along radial direction
            tooltip_center_x = bubble.x + tooltip_distance * math.cos(angle)
            tooltip_center_y = bubble.y + tooltip_distance * math.sin(angle)

            # Determine arrow direction and adjust position
            # Note: In GTK, Y-axis points DOWN, so:
            #   - Top bubbles have negative dy (angle around -90°)
            #   - Bottom bubbles have positive dy (angle around +90°)

            if -22.5 <= angle_deg < 22.5:  # Right (0°)
                arrow_direction = "left"
                tooltip_x = int(tooltip_center_x)
                tooltip_y = int(tooltip_center_y - tooltip_height / 2)
            elif 22.5 <= angle_deg < 67.5:  # Bottom-Right (+45°)
                arrow_direction = "top-left"
                tooltip_x = int(tooltip_center_x - tooltip_width / 4)
                tooltip_y = int(tooltip_center_y)
            elif 67.5 <= angle_deg < 112.5:  # Bottom (+90°) - center horizontally on bubble
                arrow_direction = "top"
                tooltip_x = int(bubble.x - tooltip_width / 2)
                tooltip_y = int(bubble.y + bubble.radius + offset)
            elif 112.5 <= angle_deg < 157.5:  # Bottom-Left (+135°)
                arrow_direction = "top-right"
                tooltip_x = int(tooltip_center_x - 3 * tooltip_width / 4)
                tooltip_y = int(tooltip_center_y)
            elif 157.5 <= angle_deg or angle_deg < -157.5:  # Left (±180°)
                arrow_direction = "right"
                tooltip_x = int(tooltip_center_x - tooltip_width)
                tooltip_y = int(tooltip_center_y - tooltip_height / 2)
            elif -157.5 <= angle_deg < -112.5:  # Top-Left (-135°)
                arrow_direction = "bottom-right"
                tooltip_x = int(tooltip_center_x - 3 * tooltip_width / 4)
                tooltip_y = int(tooltip_center_y - tooltip_height)
            elif -112.5 <= angle_deg < -67.5:  # Top (-90°) - center horizontally on bubble
                arrow_direction = "bottom"
                tooltip_x = int(bubble.x - tooltip_width / 2)
                tooltip_y = int(bubble.y - bubble.radius - offset - tooltip_height)
            else:  # -67.5 to -22.5: Top-Right (-45°)
                arrow_direction = "bottom-left"
                tooltip_x = int(tooltip_center_x - tooltip_width / 4)
                tooltip_y = int(tooltip_center_y - tooltip_height)

            # Set arrow direction
            self.tooltip_label.set_direction(arrow_direction)

            # Ensure tooltip stays within window bounds
            width = self.get_allocated_width()
            height = self.get_allocated_height()

            tooltip_x = max(5, min(tooltip_x, width - tooltip_width - 5))
            tooltip_y = max(5, min(tooltip_y, height - tooltip_height - 5))

            # Move tooltip to calculated position
            self.tooltip_label.set_margin_start(tooltip_x)
            self.tooltip_label.set_margin_top(tooltip_y)

            # Show tooltip
            self.tooltip_label.show()
        else:
            self.tooltip_label.hide()

    def _on_focus_out(self, widget, event):
        """Close Action Ring when focus is lost (clicked outside)"""
        logger.info("Focus lost - closing Action Ring")
        self.hide_overlay()
        return False

    def _animate_bubble_hover(self, bubble: Bubble, entering: bool, step: int = 0):
        """
        Animate bubble hover effect (scale and highlight).

        Mimics Logitech Options+ hover animation:
        - Smooth scale up to 1.1x
        - Glow intensity fade in
        - Duration: ~150ms
        """
        max_steps = 10  # ~150ms at 60fps
        target_scale = 1.1 if entering else 1.0
        target_highlight = 1.0 if entering else 0.0

        if step >= max_steps:
            bubble.scale = target_scale
            bubble.highlight_intensity = target_highlight
            self.drawing_area.queue_draw()
            return False

        # Ease-out interpolation
        progress = step / max_steps
        eased = 1 - (1 - progress) ** 3  # Cubic ease-out

        bubble.scale = 1.0 + (target_scale - 1.0) * eased
        bubble.highlight_intensity = target_highlight * eased

        # Queue redraw and continue animation
        self.drawing_area.queue_draw()
        GLib.timeout_add(16, self._animate_bubble_hover, bubble, entering, step + 1)
        return False
