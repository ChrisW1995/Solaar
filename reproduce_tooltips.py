
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import sys
import os

# Add lib to path
sys.path.append(os.path.abspath('lib'))

from solaar.ui.action_ring.overlay import ActionRingOverlay

def on_activate(app):
    win = Gtk.ApplicationWindow(application=app)
    win.set_title("Action Ring Test")
    win.set_default_size(200, 200)
    
    btn = Gtk.Button(label="Show Action Ring")
    btn.connect("clicked", lambda x: show_overlay())
    win.add(btn)
    win.show_all()

overlay = None

def show_overlay():
    global overlay
    if overlay is None:
        overlay = ActionRingOverlay()
    
    # Mock showing at center of screen
    overlay.show_at_cursor()

if __name__ == "__main__":
    app = Gtk.Application(application_id="org.solaar.ActionRingTest")
    app.connect("activate", on_activate)
    app.run(None)
