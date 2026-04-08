"""
Action Ring Overlay Window

Implements the main GTK popup window for the Action Ring overlay.
Handles window creation, positioning, and lifecycle management.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess

import logging
import math

from .bubbles import BubbleLayout, Bubble, FolderBubble
from .renderer import BubbleRenderer

logger = logging.getLogger(__name__)


class TooltipWidget(Gtk.Label):
    """Simple tooltip widget using GTK Label with CSS styling."""

    CSS = b"""
    .action-ring-tooltip {
        background-color: rgba(255, 255, 255, 0.95);
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        color: rgba(0, 0, 0, 0.9);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    """

    _css_provider = None

    def __init__(self):
        super().__init__()

        # Apply CSS styling once
        if TooltipWidget._css_provider is None:
            TooltipWidget._css_provider = Gtk.CssProvider()
            TooltipWidget._css_provider.load_from_data(TooltipWidget.CSS)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                TooltipWidget._css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        self.get_style_context().add_class("action-ring-tooltip")

    def set_direction(self, direction):
        """Kept for compatibility - no longer used."""
        pass


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

        Positions tooltip radially outward from bubble, centered on the bubble.
        """
        if bubble:
            self.tooltip_label.set_text(bubble.label)

            # Get tooltip dimensions
            self.tooltip_label.show()
            tooltip_width = self.tooltip_label.get_allocated_width()
            tooltip_height = self.tooltip_label.get_allocated_height()

            # Use minimum estimates if not yet allocated
            if tooltip_width < 10:
                tooltip_width = 100
            if tooltip_height < 10:
                tooltip_height = 36

            # Calculate angle from center to bubble
            dx = bubble.x - self._layout.center_x
            dy = bubble.y - self._layout.center_y
            angle = math.atan2(dy, dx)

            # Position tooltip radially outward from bubble
            offset = 15  # Gap between bubble and tooltip
            tooltip_distance = bubble.radius + offset

            # Calculate tooltip center position
            tooltip_center_x = bubble.x + tooltip_distance * math.cos(angle)
            tooltip_center_y = bubble.y + tooltip_distance * math.sin(angle)

            # Adjust to top-left corner (GTK uses top-left positioning)
            tooltip_x = int(tooltip_center_x - tooltip_width / 2)
            tooltip_y = int(tooltip_center_y - tooltip_height / 2)

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
