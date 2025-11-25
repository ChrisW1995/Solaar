"""
Bubble Layout and Interaction System

Handles circular bubble layout calculation, collision detection,
and hover/selection state management.
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Bubble:
    """Represents a single action bubble in the Action Ring"""
    # Position (center coordinates)
    x: float
    y: float

    # Target position (for expand animation)
    target_x: float = 0.0
    target_y: float = 0.0

    # Size
    radius: float = 40.0

    # Content
    label: str = ""
    icon: Optional[str] = None  # Icon name or path

    # Action
    action_type: str = "keypress"  # keypress, execute, set, folder
    action_data: any = None

    # State
    is_hovered: bool = False
    is_selected: bool = False
    is_folder: bool = False

    # Animation state
    scale: float = 1.0  # For hover/selection animations
    highlight_intensity: float = 0.0  # 0.0 to 1.0


@dataclass
class FolderBubble(Bubble):
    """A bubble that expands into sub-bubbles"""
    sub_bubbles: List[Bubble] = None
    is_expanded: bool = False

    def __post_init__(self):
        self.is_folder = True
        if self.sub_bubbles is None:
            self.sub_bubbles = []


class BubbleLayout:
    """
    Manages circular layout of bubbles around a center point.

    Implements Logitech Options+ style layout:
    - 8 primary bubbles in a ring
    - Optional 9 sub-bubbles for folders (inner ring)
    """

    def __init__(self, center_x: float, center_y: float):
        self.center_x = center_x
        self.center_y = center_y

        # Layout parameters (mimicking Logitech Options+)
        self.primary_radius = 140  # Distance from center to primary bubbles (increased spacing)
        self.sub_radius = 60  # Distance from center to sub-bubbles
        self.bubble_size = 40  # Radius of each bubble (slightly smaller for more spacing)

        # Bubbles
        self.primary_bubbles: List[Bubble] = []
        self.current_folder: Optional[FolderBubble] = None

    def create_primary_bubbles(self, count: int = 8, config: dict = None) -> List[Bubble]:
        """
        Create primary bubbles in a circular layout.

        Args:
            count: Number of bubbles (default 8 for Logitech style)
            config: Configuration dictionary from device settings

        Returns:
            List of positioned bubbles
        """
        bubbles = []
        angle_step = 2 * math.pi / count

        # Start from top (90 degrees) and go clockwise
        start_angle = -math.pi / 2

        for i in range(count):
            angle = start_angle + (i * angle_step)

            # Calculate target position
            target_x = self.center_x + self.primary_radius * math.cos(angle)
            target_y = self.center_y + self.primary_radius * math.sin(angle)

            # Load config for this bubble
            bubble_config = config.get(str(i), {}) if config else {}
            label = bubble_config.get("label", f"Action {i + 1}")
            action_type = bubble_config.get("type", "keypress")
            action_data = bubble_config.get("data", None)
            icon = bubble_config.get("icon", None)

            bubble = Bubble(
                x=self.center_x,  # Start at center for expand animation
                y=self.center_y,
                target_x=target_x,
                target_y=target_y,
                radius=self.bubble_size,
                label=label,
                action_type=action_type,
                action_data=action_data,
                icon=icon
            )
            bubbles.append(bubble)

        self.primary_bubbles = bubbles
        return bubbles

    def create_sub_bubbles(self, parent: FolderBubble) -> List[Bubble]:
        """
        Create sub-bubbles for a folder.

        Logitech Options+ style: Shows only 2 bubbles when folder is opened:
        1. One visible sub-bubble (further OUT from parent, away from center)
        2. One "more" bubble (for scrolling to other sub-bubbles)

        Args:
            parent: The parent folder bubble

        Returns:
            List of 2 positioned sub-bubbles
        """
        # Calculate angle from center to parent bubble
        dx = parent.x - self.center_x
        dy = parent.y - self.center_y
        parent_angle = math.atan2(dy, dx)

        # Distance for sub-bubbles (BEYOND parent, away from center)
        # Logitech Options+ shows sub-bubbles radiating outward
        sub_distance = self.primary_radius * 1.45  # Further out from parent

        # Create the visible sub-bubble (at parent's angle, BEYOND parent)
        sub_bubble = Bubble(
            x=self.center_x + sub_distance * math.cos(parent_angle),
            y=self.center_y + sub_distance * math.sin(parent_angle),
            radius=self.bubble_size * 0.75,
            label="Sub 1",
            action_type="keypress",
            action_data=None
        )

        # Create the "more" bubble (slightly offset from sub-bubble, also outward)
        # Offset angle by about 25 degrees
        offset_angle = 0.44  # ~25 degrees in radians
        more_angle = parent_angle + offset_angle
        more_distance = self.primary_radius * 1.4

        more_bubble = Bubble(
            x=self.center_x + more_distance * math.cos(more_angle),
            y=self.center_y + more_distance * math.sin(more_angle),
            radius=self.bubble_size * 0.6,
            label="...",  # More indicator
            action_type="folder_more",
            action_data=None
        )

        bubbles = [sub_bubble, more_bubble]
        parent.sub_bubbles = bubbles
        parent._all_sub_bubbles = []  # Store all sub-bubbles for scrolling (to be implemented)
        parent._current_sub_index = 0  # Current visible sub-bubble index

        return bubbles

    def get_bubble_at_position(self, x: float, y: float) -> Optional[Bubble]:
        """
        Find which bubble (if any) is at the given position.

        Args:
            x, y: Mouse coordinates

        Returns:
            Bubble at position, or None if no bubble
        """
        # Check sub-bubbles first (if folder is expanded)
        if self.current_folder and self.current_folder.is_expanded:
            for bubble in self.current_folder.sub_bubbles:
                if self._point_in_bubble(x, y, bubble):
                    return bubble

        # Check primary bubbles
        for bubble in self.primary_bubbles:
            if self._point_in_bubble(x, y, bubble):
                return bubble

        return None

    def _point_in_bubble(self, x: float, y: float, bubble: Bubble) -> bool:
        """Check if a point is inside a bubble (circular collision)"""
        distance = math.sqrt((x - bubble.x) ** 2 + (y - bubble.y) ** 2)
        return distance <= bubble.radius * bubble.scale

    def update_hover(self, mouse_x: float, mouse_y: float) -> Optional[Bubble]:
        """
        Update hover state for all bubbles based on mouse position.

        Args:
            mouse_x, mouse_y: Current mouse coordinates

        Returns:
            The currently hovered bubble, or None
        """
        hovered = self.get_bubble_at_position(mouse_x, mouse_y)

        # Clear all hover states
        all_bubbles = self.primary_bubbles.copy()
        if self.current_folder and self.current_folder.is_expanded:
            all_bubbles.extend(self.current_folder.sub_bubbles)

        for bubble in all_bubbles:
            bubble.is_hovered = (bubble == hovered)

        return hovered

    def expand_folder(self, folder: FolderBubble):
        """Expand a folder to show its sub-bubbles"""
        if not folder.is_folder:
            return

        # Collapse any currently expanded folder
        if self.current_folder and self.current_folder != folder:
            self.current_folder.is_expanded = False

        # Expand new folder
        folder.is_expanded = True
        self.current_folder = folder

        # Create sub-bubbles if not already created
        if not folder.sub_bubbles:
            self.create_sub_bubbles(folder)

    def collapse_folder(self):
        """Collapse the currently expanded folder"""
        if self.current_folder:
            self.current_folder.is_expanded = False
            self.current_folder = None

    def get_all_visible_bubbles(self) -> List[Bubble]:
        """Get all currently visible bubbles (primary + expanded folder)"""
        bubbles = self.primary_bubbles.copy()

        if self.current_folder and self.current_folder.is_expanded:
            bubbles.extend(self.current_folder.sub_bubbles)

        return bubbles
