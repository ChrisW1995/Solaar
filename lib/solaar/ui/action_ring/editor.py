
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
import cairo
import math

from solaar.i18n import _
from .bubbles import BubbleLayout
from .renderer import BubbleRenderer
from .action_palette import ActionPalette

class ActionRingEditor(Gtk.Dialog):
    """
    Visual Editor for Action Ring configuration.
    Supports drag-and-drop from an action palette to the visual ring.
    """
    def __init__(self, device, parent=None):
        super().__init__(title=_("Action Ring Configuration"), transient_for=parent, flags=0)
        self.device = device
        self.set_default_size(900, 600)

        # Layout
        box = self.get_content_area()
        
        # Main Paned (Canvas | Palette)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(paned, True, True, 0)

        # --- Left: Visual Canvas ---
        self.canvas_frame = Gtk.Frame()
        self.canvas_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_size_request(500, 500)
        self.canvas.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        
        self.canvas_frame.add(self.canvas)
        paned.pack1(self.canvas_frame, True, False)

        # Canvas Logic
        self.layout = BubbleLayout(250, 250) # Initial center, will update on resize
        self.renderer = BubbleRenderer()
        
        # Load initial config
        self.current_config = {}
        if hasattr(self.device, 'persister') and self.device.persister:
            self.current_config = self.device.persister.get("action-ring", {}).copy()
        
        self.layout.create_primary_bubbles(8, self.current_config)

        # Signals
        self.canvas.connect("draw", self._on_draw)
        self.canvas.connect("configure-event", self._on_resize)
        self.canvas.connect("motion-notify-event", self._on_motion)
        self.canvas.connect("button-press-event", self._on_click)

        # Drag Destination Setup
        self.canvas.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.canvas.drag_dest_add_text_targets()
        self.canvas.connect("drag-data-received", self._on_drag_data_received)
        self.canvas.connect("drag-motion", self._on_drag_motion)
        self.canvas.connect("drag-leave", self._on_drag_leave)

        # --- Right: Action Palette ---
        palette_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        palette_box.set_size_request(300, -1)
        
        # Search (Placeholder)
        search_entry = Gtk.SearchEntry()
        palette_box.pack_start(search_entry, False, False, 5)

        # TreeView
        self.palette = ActionPalette()
        self.tree = Gtk.TreeView(model=self.palette.get_model())
        
        # Columns
        renderer_text = Gtk.CellRendererText()
        renderer_icon = Gtk.CellRendererPixbuf()
        
        col = Gtk.TreeViewColumn(_("Available Actions"))
        col.pack_start(renderer_icon, False)
        col.add_attribute(renderer_icon, "icon-name", 2)
        col.pack_start(renderer_text, True)
        col.add_attribute(renderer_text, "text", 0)
        self.tree.append_column(col)

        # Drag Source Setup
        self.tree.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.COPY)
        self.tree.drag_source_add_text_targets()
        self.tree.connect("drag-data-get", self._on_drag_data_get)

        scroll = Gtk.ScrolledWindow()
        scroll.add(self.tree)
        palette_box.pack_start(scroll, True, True, 0)
        
        paned.pack2(palette_box, False, False)

        # Buttons
        self.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        save_btn = self.add_button(_("Save"), Gtk.ResponseType.APPLY)
        save_btn.connect("clicked", self._on_save)

        self.show_all()

    # --- Canvas Events ---
    def _on_resize(self, widget, event):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        new_center_x = width / 2
        new_center_y = height / 2
        
        # Update layout center
        self.layout.center_x = new_center_x
        self.layout.center_y = new_center_y
        
        # Update existing bubble positions instead of recreating them
        # This preserves bubble state (label, icon, etc.)
        if self.layout.primary_bubbles:
            angle_step = 2 * 3.14159 / len(self.layout.primary_bubbles)
            start_angle = -3.14159 / 2
            
            for i, bubble in enumerate(self.layout.primary_bubbles):
                angle = start_angle + (i * angle_step)
                # Update target and actual positions
                bubble.target_x = new_center_x + self.layout.primary_radius * __import__('math').cos(angle)
                bubble.target_y = new_center_y + self.layout.primary_radius * __import__('math').sin(angle)
                bubble.x = bubble.target_x
                bubble.y = bubble.target_y
        
        return False

    def _on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Debug: Print bubble states
        for i, bubble in enumerate(self.layout.primary_bubbles):
            print(f"DEBUG _on_draw: Bubble {i} - label: {bubble.label}, icon: {bubble.icon}")
        
        # Draw solid background (Dark Gray)
        context = widget.get_style_context()
        Gtk.render_background(context, cr, 0, 0, width, height)
        
        # If theme background is not opaque/dark enough, enforce a dark background
        # This ensures it looks good regardless of theme
        cr.set_source_rgb(0.15, 0.15, 0.15) # Dark gray #262626
        cr.paint()
        
        self.renderer.render(cr, self.layout, width, height, transparent_background=False)
        return False

    def _on_motion(self, widget, event):
        self.layout.update_hover(event.x, event.y)
        widget.queue_draw()
        return False
        
    def _on_click(self, widget, event):
        bubble = self.layout.get_bubble_at_position(event.x, event.y)
        if bubble:
            # TODO: Show bubble details/editor in a popover or sidebar?
            # For now just select it
            for b in self.layout.primary_bubbles:
                b.is_selected = (b == bubble)
            widget.queue_draw()
        return False

    # --- Drag and Drop ---
    def _on_drag_data_get(self, widget, drag_context, data, info, time):
        model, iter = widget.get_selection().get_selected()
        if iter:
            # Format: "label|icon|type|data"
            label = model[iter][1]
            icon = model[iter][2]
            action_type = model[iter][3]
            action_data = model[iter][4]
            
            if not action_type: # It's a category header
                return
                
            text_data = f"{label}|{icon}|{action_type}|{action_data}"
            data.set_text(text_data, -1)

    def _on_drag_motion(self, widget, context, x, y, time):
        # Highlight bubble under cursor
        self.layout.update_hover(x, y)
        widget.queue_draw()
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True

    def _on_drag_leave(self, widget, context, time):
        self.layout.update_hover(-100, -100) # Clear hover
        widget.queue_draw()

    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        text = data.get_text()
        if not text:
            return

        try:
            label, icon, action_type, action_data = text.split("|")
        except ValueError:
            return # Invalid format

        # Find target bubble
        target_bubble = self.layout.get_bubble_at_position(x, y)
        
        print(f"DEBUG: Drag received - action_type: {action_type}, label: {label}, target: {target_bubble}")
        
        if target_bubble:
            # Get bubble index BEFORE modifying it
            index = self.layout.primary_bubbles.index(target_bubble)
            
            # Handle special configuration for "open_*" types
            if action_type.startswith("open_"):
                print(f"DEBUG: Opening config dialog for {action_type}")
                new_label, new_action_data, new_icon = self._handle_drop_config(action_type, label)
                print(f"DEBUG: Config result - label: {new_label}, data: {new_action_data}, icon: {new_icon}")
                
                if new_action_data is None: # User cancelled
                    context.finish(False, False, time)
                    return
                # Update with configured values
                label = new_label
                action_data = new_action_data
                icon = new_icon
                # Convert to execute type
                action_type = "execute"

            # Update bubble config
            target_bubble.label = label
            target_bubble.action_type = action_type
            target_bubble.action_data = action_data
            target_bubble.icon = icon 
            
            print(f"DEBUG: Updated bubble - label: {target_bubble.label}, type: {target_bubble.action_type}, icon: {target_bubble.icon}")
            
            # Update internal config dict
            self.current_config[str(index)] = {
                "label": label,
                "type": action_type,
                "data": action_data,
                "icon": icon
            }
            
            print(f"DEBUG: Saved to config index {index}")
            
            # Force immediate redraw
            widget.queue_draw()
            # Invalidate the widget's window to ensure redraw happens
            if widget.get_window():
                widget.get_window().invalidate_rect(None, True)
                widget.get_window().process_updates(True)
            
            context.finish(True, False, time)
        else:
            context.finish(False, False, time)

    def _handle_drop_config(self, action_type, default_label):
        """
        Show configuration dialog based on action type.
        Returns (new_label, action_data, icon_name) or (None, None, None) if cancelled.
        Note: All open_* types are converted to 'execute' type.
        """
        if action_type == "open_url":
            dialog = Gtk.Dialog(title=_("Configure Web Page"), transient_for=self, flags=0)
            dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL, _("Save"), Gtk.ResponseType.OK)
            
            box = dialog.get_content_area()
            box.set_spacing(10)
            box.set_margin_top(10)
            box.set_margin_bottom(10)
            box.set_margin_start(10)
            box.set_margin_end(10)
            
            box.pack_start(Gtk.Label(label=_("URL:")), False, False, 0)
            entry = Gtk.Entry()
            entry.set_text("https://")
            box.pack_start(entry, False, False, 0)
            
            dialog.show_all()
            response = dialog.run()
            url = entry.get_text()
            dialog.destroy()
            
            if response == Gtk.ResponseType.OK and url:
                # Return as execute command with web icon
                return "Web Page", f"xdg-open '{url}'", "web-browser"
                
        elif action_type == "open_app":
            dialog = Gtk.AppChooserDialog(parent=self, flags=0)
            dialog.set_heading(_("Select Application"))
            response = dialog.run()
            app_info = dialog.get_app_info()
            dialog.destroy()
            
            if response == Gtk.ResponseType.OK and app_info:
                # Get app icon
                gicon = app_info.get_icon()
                icon_name = "application-x-executable"  # Default fallback
                
                if gicon:
                    # Try to get icon name from GThemedIcon
                    if hasattr(gicon, 'get_names'):
                        names = gicon.get_names()
                        if names and len(names) > 0:
                            icon_name = names[0]
                    elif hasattr(gicon, 'to_string'):
                        # Fallback to string representation
                        icon_str = gicon.to_string()
                        # Handle themed icons like ". GThemedIcon firefox firefox-symbolic"
                        if icon_str and not icon_str.startswith('.'):
                            icon_name = icon_str
                
                display_name = app_info.get_display_name()
                command = app_info.get_commandline()
                
                print(f"DEBUG: Selected app: {display_name}, command: {command}, icon: {icon_name}")
                
                # Return as execute command with app icon
                return display_name, command, icon_name

        elif action_type == "open_file":
            dialog = Gtk.FileChooserDialog(
                title=_("Select File"), parent=self, action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL, _("Open"), Gtk.ResponseType.OK)
            
            response = dialog.run()
            filename = dialog.get_filename()
            dialog.destroy()
            
            if response == Gtk.ResponseType.OK and filename:
                import os
                # Return as execute command with file icon
                return os.path.basename(filename), f"xdg-open '{filename}'", "text-x-generic"

        elif action_type == "open_folder":
            dialog = Gtk.FileChooserDialog(
                title=_("Select Folder"), parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
            )
            dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL, _("Select"), Gtk.ResponseType.OK)
            
            response = dialog.run()
            filename = dialog.get_filename()
            dialog.destroy()
            
            if response == Gtk.ResponseType.OK and filename:
                import os
                # Return as execute command with folder icon
                return os.path.basename(filename), f"xdg-open '{filename}'", "folder"
                
        return None, None, None

    def _on_save(self, button):
        # Persist to device
        if hasattr(self.device, 'persister') and self.device.persister:
            self.device.persister["action-ring"] = self.current_config
