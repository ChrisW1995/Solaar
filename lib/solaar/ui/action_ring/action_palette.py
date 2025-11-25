
from gi.repository import Gtk, GdkPixbuf

class ActionPalette:
    """
    Helper class to manage the list of available actions for the Action Ring.
    """
    def __init__(self):
        # TreeStore: Category, Label, Icon Name, Action Type, Action Data
        self.store = Gtk.TreeStore(str, str, str, str, str)
        self._populate()

    def _populate(self):
        # Categories
        media = self.store.append(None, ["Media & Volume", "", "applications-multimedia", "", ""])
        self._add_item(media, "Play/Pause", "media-playback-start", "keypress", "KEY_PLAYPAUSE")
        self._add_item(media, "Next Track", "media-skip-forward", "keypress", "KEY_NEXTSONG")
        self._add_item(media, "Previous Track", "media-skip-backward", "keypress", "KEY_PREVIOUSSONG")
        self._add_item(media, "Volume Up", "audio-volume-high", "keypress", "KEY_VOLUMEUP")
        self._add_item(media, "Volume Down", "audio-volume-low", "keypress", "KEY_VOLUMEDOWN")
        self._add_item(media, "Mute", "audio-volume-muted", "keypress", "KEY_MUTE")

        _open = self.store.append(None, ["Open", "", "document-open", "", ""])
        self._add_item(_open, "Open Application", "system-run", "open_app", "")
        self._add_item(_open, "Open File", "text-x-generic", "open_file", "")
        self._add_item(_open, "Open Folder", "folder", "open_folder", "")
        self._add_item(_open, "Web Page", "web-browser", "open_url", "")

        nav = self.store.append(None, ["Navigation", "", "input-mouse", "", ""])
        self._add_item(nav, "Back", "go-previous", "keypress", "KEY_BACK")
        self._add_item(nav, "Forward", "go-next", "keypress", "KEY_FORWARD")
        self._add_item(nav, "Home", "go-home", "keypress", "KEY_HOMEPAGE")
        self._add_item(nav, "Task View", "view-grid", "keypress", "KEY_SCALE") # Expose/Overview

        sys = self.store.append(None, ["System", "", "preferences-system", "", ""])
        self._add_item(sys, "Copy", "edit-copy", "keypress", "KEY_COPY")
        self._add_item(sys, "Paste", "edit-paste", "keypress", "KEY_PASTE")
        self._add_item(sys, "Cut", "edit-cut", "keypress", "KEY_CUT")
        self._add_item(sys, "Undo", "edit-undo", "keypress", "KEY_UNDO")
        self._add_item(sys, "Redo", "edit-redo", "keypress", "KEY_REDO")
        self._add_item(sys, "Print", "document-print", "keypress", "KEY_PRINT")
        
        utils = self.store.append(None, ["Utilities", "", "applications-utilities", "", ""])
        self._add_item(utils, "Calculator", "accessories-calculator", "execute", "gnome-calculator")
        self._add_item(utils, "Terminal", "utilities-terminal", "execute", "gnome-terminal")
        self._add_item(utils, "Screenshot", "camera-photo", "keypress", "KEY_PRINT")

    def _add_item(self, parent, label, icon, action_type, action_data):
        self.store.append(parent, [label, label, icon, action_type, action_data])

    def get_model(self):
        return self.store
