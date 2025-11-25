# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Solaar** is a Linux manager for Logitech wireless devices. Currently focusing on the **Action Ring overlay feature**—a visual circular interface for configuring device button mappings, similar to Logitech Options+.

## Current Work: Action Ring Overlay

### What is the Action Ring?
A GTK3 popup overlay that displays configurable button actions in a circular "ring" layout. Users can drag actions from a palette to position buttons around the ring, providing intuitive visual configuration for device buttons.

### Module Structure (`lib/solaar/ui/action_ring/`)
- **bubbles.py** - Data models (`Bubble`, `FolderBubble`, `BubbleLayout`) for layout calculations, circular positioning, and collision detection
- **renderer.py** - Cairo-based rendering engine for visual display (gradients, hover effects, animations)
- **overlay.py** - Main GTK window implementation: event handling, mouse interaction, tooltip management
- **editor.py** - Configuration dialog with canvas and drag-and-drop from action palette
- **action_palette.py** - Available action definitions (keymaps, commands, etc.)

### Key Components

#### BubbleLayout (`bubbles.py`)
```
- center_x, center_y: Ring center point
- primary_radius: 140px (distance from center to buttons)
- sub_radius: 60px (for folder expansions)
- bubble_size: 40px (button visual radius)
```
Creates 8 primary bubbles arranged clockwise starting from top (-90°). Supports folder expansion with nested bubbles.

#### BubbleRenderer (`renderer.py`)
Renders using Cairo with:
- Semi-transparent white bubbles (default state)
- Dark hover state with gradient
- Blue selection highlight
- Center close button
- Proper layering (non-hovered first, hovered last)

#### ActionRingOverlay (`overlay.py`)
GTK popup window with:
- Window positioning and lifecycle (show/hide/destroy)
- Mouse events: motion, click, drag detection
- Custom tooltip widget with arrow pointing direction
- Integration with device configuration persistence

#### ActionRingEditor (`editor.py`)
Configuration dialog featuring:
- Left: Visual canvas with live bubble layout
- Right: Action palette (available actions to assign)
- Drag-and-drop from palette to canvas
- Configuration persistence to device settings

## Common Development Commands

### Code Quality
```bash
make format        # Auto-format with ruff
make lint         # Check and fix style issues
make test         # Run pytest with coverage
```

### Testing
```bash
pytest tests/ -v                              # All tests verbose
pytest tests/solaar/ -v -k action_ring       # Action ring tests only
pytest --cov --cov-report=html               # Coverage report
```

### Running the Application
```bash
python -m solaar                # Run GUI
python -m solaar --help        # CLI help
```

## Architecture Context

### Device Communication Layer (`lib/logitech_receiver/`)
- `device.py` - Device representation with features and settings
- `settings.py` - Device feature definitions (what buttons/features available)
- `hidpp20.py` - HID++ 2.0 protocol implementation

### UI Layer (`lib/solaar/ui/`)
- `window.py` - Main Solaar application window
- `config_panel.py` - Device settings UI
- `action_ring/` - **The Action Ring overlay (current focus)**
- `diversion_rules.py` - Rule system for automation

## Action Ring Development Notes

### Integration Points
- **Device Configuration**: Action Ring config stored in device persister under `"action-ring"` key
- **Bubble State**: `BubbleLayout.get_all_visible_bubbles()` returns current visible bubbles (primary or sub if folder expanded)
- **Rendering Loop**: Canvas `draw` signal triggers `BubbleRenderer.render()` with current layout state

### Important Considerations

#### Layout Calculations
- Circular positioning uses angle step: `2π / 8` radians (45° between buttons)
- Starting angle: `-π/2` (top, 12 o'clock position)
- Clockwise rotation: `angle = start_angle + (i * angle_step)`
- Target position formula: `x = center_x + radius * cos(angle)`

#### Cairo Rendering
- Uses `OPERATOR_CLEAR` with paint to make backgrounds transparent (overlay requirement)
- Hovered bubbles drawn last for proper layering
- Icon colors invert on hover (dark → white)
- Gradients for smooth visual transitions

#### GTK Event Handling
- `motion-notify-event` - Hover detection and bubble highlighting
- `button-press-event` - Click handling for bubble selection/folder expansion
- `drag-data-received` - Receiving dropped actions from palette
- `configure-event` - Window resize, recalculate layout center

### Styling/Colors (BubbleRenderer)
```python
bg_color = (1.0, 1.0, 1.0, 0.5)       # Subtle white
hover_color = (0.2, 0.2, 0.2, 1.0)    # Dark gray/black
selected_color = (0.3, 0.5, 0.8, 0.95) # Blue accent
icon_color = (0.2, 0.2, 0.2, 1.0)     # Dark icons
```

## Code Style & Dependencies

- **Line Length**: 127 characters (ruff config)
- **Python Target**: 3.7+
- **Import Style**: Force single-line imports with isort
- **Key Dependencies**: `PyGObject` (GTK), `cairo`, `PyYAML`

## Testing Patterns

Tests use `pytest` with mocks (no actual devices required). When adding action ring tests:
- Mock device persister for configuration storage
- Mock Cairo context for renderer tests
- Test bubble positioning math independently
- Verify hover/selection state transitions

## Recent Commits
- `691c9da7` feat: Add Logitech Options+ style Action Ring overlay (main feature implementation)

## File Permissions Note
Some action_ring files have restrictive permissions (600/-rw-------). Ensure write access when modifying.
