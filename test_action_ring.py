#!/usr/bin/env python3
"""
Test script for Action Ring overlay.

Run this to see the Action Ring in action.
Press 'a' to show the ring, Esc to close.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from solaar.ui.action_ring import ActionRingOverlay
from solaar.ui.action_ring.bubbles import FolderBubble

import logging
logging.basicConfig(level=logging.DEBUG)


class TestWindow(Gtk.Window):
    """Simple test window with keyboard shortcut to trigger Action Ring"""

    def __init__(self):
        super().__init__(title="Action Ring Test")
        self.set_default_size(600, 400)
        self.connect('destroy', Gtk.main_quit)

        # Create label with instructions
        label = Gtk.Label()
        label.set_markup(
            "<big><b>Action Ring Test</b></big>\n\n"
            "Press <b>'a'</b> to show Action Ring at cursor\n"
            "Press <b>Esc</b> to close\n\n"
            "Once Action Ring is open:\n"
            "• Hover over bubbles to see highlight animation\n"
            "• Click a bubble to execute action\n"
            "• Right-click to close"
        )
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)

        self.add(label)

        # Connect keyboard events
        self.connect('key-press-event', self._on_key_press)

        # Create Action Ring overlay
        self.action_ring = ActionRingOverlay()


    def _on_key_press(self, widget, event):
        """Handle keyboard shortcuts"""
        if event.keyval == Gdk.KEY_a:
            # Show Action Ring at cursor
            print("Showing Action Ring...")
            self.action_ring.show_at_cursor()

            # Customize bubbles after layout is created
            if self.action_ring._layout:
                bubbles = self.action_ring._layout.primary_bubbles
                if len(bubbles) >= 8:
                    bubbles[0].label = "Terminal"
                    bubbles[0].action_type = "execute"
                    bubbles[0].action_data = "gnome-terminal"

                    bubbles[1].label = "Browser"
                    bubbles[1].action_type = "execute"
                    bubbles[1].action_data = "firefox"

                    bubbles[2].label = "Files"
                    bubbles[2].action_type = "execute"
                    bubbles[2].action_data = "nautilus"

                    # Make bubble 3 a folder
                    from solaar.ui.action_ring.bubbles import FolderBubble
                    folder = FolderBubble(
                        x=bubbles[3].x,
                        y=bubbles[3].y,
                        radius=bubbles[3].radius,
                        label="Tools",
                        action_type="folder"
                    )
                    bubbles[3] = folder
                    self.action_ring._layout.primary_bubbles[3] = folder

                    bubbles[4].label = "Volume +"
                    bubbles[5].label = "Volume -"
                    bubbles[6].label = "Screenshot"
                    bubbles[7].label = "Lock"

            return True
        elif event.keyval == Gdk.KEY_Escape:
            # Close Action Ring or quit if not shown
            if self.action_ring._visible:
                self.action_ring.hide_overlay()
            else:
                Gtk.main_quit()
            return True

        return False


def main():
    print("Starting Action Ring Test...")
    print("Make sure you have a compositing window manager running for transparency!")

    window = TestWindow()
    window.show_all()

    Gtk.main()


if __name__ == '__main__':
    main()
