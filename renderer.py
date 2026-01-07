"""
PDF renderer for domino puzzles using fpdf2.
Styled to match NYT Pips visual design.
"""
from typing import List, Dict, Tuple, Optional, Set
from fpdf import FPDF
import math

from domino_sets import Domino, DominoSet
from grid import Puzzle, Region, PlacedDomino, Orientation, ConstraintType


class PuzzleRenderer:
    """Renders puzzles to PDF in NYT Pips style."""

    CELL_SIZE = 27  # Size of each grid cell in mm (~1.06 inches, fits 1" domino with visible borders)

    # NYT-style pastel color palette (RGB)
    REGION_COLORS = [
        (200, 182, 210),  # Purple/lavender
        (242, 200, 200),  # Pink
        (240, 210, 180),  # Peach/orange
        (195, 215, 210),  # Teal/sage
        (200, 210, 220),  # Gray-blue
        (220, 200, 180),  # Tan
        (210, 225, 200),  # Light green
        (225, 200, 210),  # Rose
        (200, 200, 190),  # Gray
        (215, 210, 225),  # Periwinkle
    ]

    # Darker versions for borders (print-friendly, high contrast)
    BORDER_COLORS = [
        (90, 60, 120),    # Purple (darkened)
        (160, 80, 90),    # Pink (darkened)
        (170, 110, 60),   # Orange (darkened)
        (60, 110, 100),   # Teal (darkened)
        (60, 90, 130),    # Gray-blue (darkened)
        (140, 100, 60),   # Tan (darkened)
        (90, 130, 70),    # Green (darkened)
        (150, 90, 110),   # Rose (darkened)
        (100, 100, 90),   # Gray (darkened)
        (100, 90, 140),   # Periwinkle (darkened)
    ]

    # Badge colors (more saturated versions)
    BADGE_COLORS = [
        (140, 100, 170),  # Purple
        (200, 80, 100),   # Pink/magenta
        (210, 130, 60),   # Orange
        (60, 140, 140),   # Teal
        (80, 110, 150),   # Blue-gray
        (180, 130, 70),   # Tan/brown
        (90, 140, 80),    # Green
        (180, 100, 130),  # Rose
        (120, 120, 110),  # Gray
        (100, 90, 150),   # Periwinkle
    ]

    # Pip positions (relative to cell, normalized 0-1)
    PIP_POSITIONS = {
        0: [],
        1: [(0.5, 0.5)],
        2: [(0.3, 0.3), (0.7, 0.7)],
        3: [(0.3, 0.3), (0.5, 0.5), (0.7, 0.7)],
        4: [(0.3, 0.3), (0.7, 0.3), (0.3, 0.7), (0.7, 0.7)],
        5: [(0.3, 0.3), (0.7, 0.3), (0.5, 0.5), (0.3, 0.7), (0.7, 0.7)],
        6: [(0.3, 0.25), (0.7, 0.25), (0.3, 0.5), (0.7, 0.5), (0.3, 0.75), (0.7, 0.75)],
        7: [(0.3, 0.25), (0.7, 0.25), (0.3, 0.5), (0.5, 0.5), (0.7, 0.5), (0.3, 0.75), (0.7, 0.75)],
        8: [(0.25, 0.25), (0.5, 0.25), (0.75, 0.25), (0.25, 0.5), (0.75, 0.5), (0.25, 0.75), (0.5, 0.75), (0.75, 0.75)],
        9: [(0.25, 0.25), (0.5, 0.25), (0.75, 0.25), (0.25, 0.5), (0.5, 0.5), (0.75, 0.5), (0.25, 0.75), (0.5, 0.75), (0.75, 0.75)],
    }

    def __init__(self, puzzle: Puzzle):
        self.puzzle = puzzle
        self.pdf = FPDF(orientation='P', unit='mm', format='letter')
        self.pdf.set_auto_page_break(auto=False)

    def _draw_rounded_rect(self, x: float, y: float, w: float, h: float,
                           r: float, fill: bool = True, stroke: bool = True):
        """Draw a rectangle with rounded corners using arc segments."""
        # Clamp radius to half the smallest dimension
        r = min(r, w / 2, h / 2)

        # Build path points for rounded rectangle
        # Using polygon approximation for corners
        points = []
        steps = 6  # Segments per corner

        # Top-left corner
        for i in range(steps + 1):
            angle = math.pi + (math.pi / 2) * (i / steps)
            px = x + r + r * math.cos(angle)
            py = y + r + r * math.sin(angle)
            points.append((px, py))

        # Top-right corner
        for i in range(steps + 1):
            angle = 3 * math.pi / 2 + (math.pi / 2) * (i / steps)
            px = x + w - r + r * math.cos(angle)
            py = y + r + r * math.sin(angle)
            points.append((px, py))

        # Bottom-right corner
        for i in range(steps + 1):
            angle = 0 + (math.pi / 2) * (i / steps)
            px = x + w - r + r * math.cos(angle)
            py = y + h - r + r * math.sin(angle)
            points.append((px, py))

        # Bottom-left corner
        for i in range(steps + 1):
            angle = math.pi / 2 + (math.pi / 2) * (i / steps)
            px = x + r + r * math.cos(angle)
            py = y + h - r + r * math.sin(angle)
            points.append((px, py))

        style = ''
        if fill and stroke:
            style = 'DF'
        elif fill:
            style = 'F'
        elif stroke:
            style = 'D'

        self.pdf.polygon(points, style=style)

    def _draw_dashed_line(self, x1: float, y1: float, x2: float, y2: float,
                          dash_len: float = 2.0, gap_len: float = 2.0):
        """Draw a dashed line between two points."""
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return

        # Normalize direction
        dx /= length
        dy /= length

        pos = 0
        drawing = True
        while pos < length:
            seg_len = dash_len if drawing else gap_len
            end_pos = min(pos + seg_len, length)

            if drawing:
                sx = x1 + dx * pos
                sy = y1 + dy * pos
                ex = x1 + dx * end_pos
                ey = y1 + dy * end_pos
                self.pdf.line(sx, sy, ex, ey)

            pos = end_pos
            drawing = not drawing

    def _draw_semicircle_badge(self, cx: float, cy: float, size: float,
                               color: Tuple[int, int, int], label: str,
                               edge: str = "bottom"):
        """Draw a semicircle badge with a rectangular tab that protrudes into the region.

        Args:
            edge: Which edge the badge abuts ("top", "bottom", "left", "right")
        """
        radius = size / 2
        tab_width = size  # Full width to match circle diameter
        tab_depth = size / 7  # How far the tab goes into the region (scales with size)
        steps = 16  # Smoothness of the arc

        self.pdf.set_fill_color(*color)
        self.pdf.set_draw_color(*color)

        points = []

        if edge == "bottom":
            # Tab protrudes up into region, semicircle hangs below
            tab_top = cy - tab_depth
            tab_bottom = cy
            # Start at top-left of tab
            points.append((cx - tab_width / 2, tab_top))
            points.append((cx + tab_width / 2, tab_top))
            # Right side of tab down to semicircle
            points.append((cx + tab_width / 2, tab_bottom))
            # Right edge to start of arc
            points.append((cx + radius, tab_bottom))
            # Semicircle arc (bottom half)
            for i in range(steps + 1):
                angle = 0 - math.pi * (i / steps)
                px = cx + radius * math.cos(angle)
                py = tab_bottom - radius * math.sin(angle)
                points.append((px, py))
            # Left edge back to tab
            points.append((cx - radius, tab_bottom))
            points.append((cx - tab_width / 2, tab_bottom))

        elif edge == "top":
            # Tab protrudes down into region, semicircle above
            tab_top = cy
            tab_bottom = cy + tab_depth
            # Semicircle arc (top half)
            for i in range(steps + 1):
                angle = math.pi + math.pi * (i / steps)
                px = cx + radius * math.cos(angle)
                py = tab_top + radius * math.sin(angle)
                points.append((px, py))
            # Right edge down to tab
            points.append((cx + radius, tab_top))
            points.append((cx + tab_width / 2, tab_top))
            # Tab rectangle
            points.append((cx + tab_width / 2, tab_bottom))
            points.append((cx - tab_width / 2, tab_bottom))
            points.append((cx - tab_width / 2, tab_top))
            points.append((cx - radius, tab_top))

        elif edge == "right":
            # Tab protrudes left into region, semicircle to the right
            tab_left = cx - tab_depth
            tab_right = cx
            # Start at top of tab
            points.append((tab_left, cy - tab_width / 2))
            points.append((tab_left, cy + tab_width / 2))
            # Bottom of tab to semicircle
            points.append((tab_right, cy + tab_width / 2))
            points.append((tab_right, cy + radius))
            # Semicircle arc (right half)
            for i in range(steps + 1):
                angle = math.pi / 2 - math.pi * (i / steps)
                px = tab_right + radius * math.cos(angle)
                py = cy + radius * math.sin(angle)
                points.append((px, py))
            # Back to tab
            points.append((tab_right, cy - radius))
            points.append((tab_right, cy - tab_width / 2))

        elif edge == "left":
            # Tab protrudes right into region, semicircle to the left
            tab_left = cx
            tab_right = cx + tab_depth
            # Semicircle arc (left half)
            for i in range(steps + 1):
                angle = -math.pi / 2 - math.pi * (i / steps)
                px = tab_left + radius * math.cos(angle)
                py = cy + radius * math.sin(angle)
                points.append((px, py))
            # Down to tab
            points.append((tab_left, cy + radius))
            points.append((tab_left, cy + tab_width / 2))
            # Tab rectangle
            points.append((tab_right, cy + tab_width / 2))
            points.append((tab_right, cy - tab_width / 2))
            points.append((tab_left, cy - tab_width / 2))
            points.append((tab_left, cy - radius))

        else:
            # Full circle fallback
            for i in range(steps):
                angle = 2 * math.pi * (i / steps)
                px = cx + radius * math.cos(angle)
                py = cy + radius * math.sin(angle)
                points.append((px, py))

        # Draw filled polygon
        self.pdf.polygon(points, style='F')

        # Draw white text for contrast on colored backgrounds
        self.pdf.set_text_color(255, 255, 255)
        font_size = max(7, int(size * 0.875))  # Scale font with badge size (25% larger)
        self.pdf.set_font('Helvetica', 'B', font_size)

        # Center text in the semicircle part
        text_w = self.pdf.get_string_width(label)
        text_h = 4  # Approximate text height

        if edge == "bottom":
            text_cx = cx
            text_cy = cy + radius * 0.35
        elif edge == "top":
            text_cx = cx
            text_cy = cy - radius * 0.35
        elif edge == "right":
            text_cx = cx + radius * 0.35
            text_cy = cy
        elif edge == "left":
            text_cx = cx - radius * 0.35
            text_cy = cy
        else:
            text_cx, text_cy = cx, cy

        # Center the text properly
        self.pdf.set_xy(text_cx - text_w / 2, text_cy - text_h / 2)
        self.pdf.cell(text_w, text_h, label, align='C')

    def _get_region_bounds(self, region: Region) -> Tuple[float, float, float, float]:
        """Get bounding box of region cells (min_row, min_col, max_row, max_col)."""
        rows = [c[0] for c in region.cells]
        cols = [c[1] for c in region.cells]
        return min(rows), min(cols), max(rows), max(cols)

    def _find_badge_position(self, region: Region, x_start: float, y_start: float,
                             cell_size: float, all_cells: Set[Tuple[int, int]],
                             used_positions: List[Tuple[float, float]] = None) -> Tuple[float, float, str]:
        """Find optimal position for region's constraint badge outside the grid.

        Returns:
            (cx, cy, edge) - center position and which edge it abuts
        """
        if used_positions is None:
            used_positions = []

        # Get grid boundaries
        grid_min_r = min(c[0] for c in all_cells)
        grid_max_r = max(c[0] for c in all_cells)
        grid_min_c = min(c[1] for c in all_cells)
        grid_max_c = max(c[1] for c in all_cells)

        region_cells = set(region.cells)

        # Find region cells on each outer edge of the GRID
        # These are cells where placing a badge outside won't overlap the grid
        bottom_edge_cells = [(r, c) for (r, c) in region.cells
                            if r == grid_max_r or (r + 1, c) not in all_cells]
        right_edge_cells = [(r, c) for (r, c) in region.cells
                           if c == grid_max_c or (r, c + 1) not in all_cells]
        top_edge_cells = [(r, c) for (r, c) in region.cells
                         if r == grid_min_r or (r - 1, c) not in all_cells]
        left_edge_cells = [(r, c) for (r, c) in region.cells
                          if c == grid_min_c or (r, c - 1) not in all_cells]

        # Try each edge in priority order, picking the one with least conflicts
        # badge_offset should match tab_depth (size/7) so badges are flush
        # Since badge_size = 14 * scale and tab_depth = size/7, badge_offset = 2 * scale
        scale = cell_size / self.CELL_SIZE
        badge_offset = 2 * scale
        candidates = []

        def calc_position(edge_cells, edge_type):
            if not edge_cells:
                return None

            # Find contiguous groups of edge cells and pick the largest
            # For simplicity, just pick the cell that's most "outward" on this edge
            if edge_type == "bottom":
                # Pick the cell with the highest row (most bottom)
                best_cell = max(edge_cells, key=lambda c: (c[0], c[1]))
                r, c = best_cell
                cx = x_start + (c + 0.5) * cell_size
                cy = y_start + (r + 1) * cell_size + badge_offset
            elif edge_type == "right":
                # Pick the cell with the highest column (most right)
                best_cell = max(edge_cells, key=lambda c: (c[1], c[0]))
                r, c = best_cell
                cx = x_start + (c + 1) * cell_size + badge_offset
                cy = y_start + (r + 0.5) * cell_size
            elif edge_type == "top":
                # Pick the cell with the lowest row (most top)
                best_cell = min(edge_cells, key=lambda c: (c[0], -c[1]))
                r, c = best_cell
                cx = x_start + (c + 0.5) * cell_size
                cy = y_start + r * cell_size - badge_offset
            elif edge_type == "left":
                # Pick the cell with the lowest column (most left)
                best_cell = min(edge_cells, key=lambda c: (c[1], c[0]))
                r, c = best_cell
                cx = x_start + c * cell_size - badge_offset
                cy = y_start + (r + 0.5) * cell_size
            return (cx, cy, edge_type)

        # Add candidates in priority order: bottom, right, top, left
        for edge_cells, edge_type in [(bottom_edge_cells, "bottom"),
                                       (right_edge_cells, "right"),
                                       (top_edge_cells, "top"),
                                       (left_edge_cells, "left")]:
            pos = calc_position(edge_cells, edge_type)
            if pos:
                candidates.append(pos)

        # If no candidates (interior region), use region's own boundary
        if not candidates:
            # Find the region's own edges (cells on region boundary)
            min_r = min(r for r, _ in region.cells)
            max_r = max(r for r, _ in region.cells)
            min_c = min(c for _, c in region.cells)
            max_c = max(c for _, c in region.cells)

            # Top of region
            top_cells = [(r, c) for r, c in region.cells if r == min_r]
            # Bottom of region
            bottom_cells = [(r, c) for r, c in region.cells if r == max_r]
            # Use top edge, place badge above (may overlap grid but necessary)
            if top_cells:
                center_c = sum(c for _, c in top_cells) / len(top_cells)
                cx = x_start + (center_c + 0.5) * cell_size
                cy = y_start + min_r * cell_size - badge_offset
                candidates.append((cx, cy, "top"))

        # Pick first candidate (already in priority order)
        if candidates:
            return candidates[0]

        # Ultimate fallback
        center_r = sum(r for r, _ in region.cells) / len(region.cells)
        center_c = sum(c for _, c in region.cells) / len(region.cells)
        cx = x_start + (center_c + 0.5) * cell_size
        cy = y_start + center_r * cell_size - badge_offset
        return cx, cy, "top"

    def draw_pip(self, x: float, y: float, radius: float = 1.8, color: Tuple[int, int, int] = (40, 40, 40)):
        """Draw a single pip (filled circle)."""
        self.pdf.set_fill_color(*color)
        self.pdf.ellipse(x - radius, y - radius, radius * 2, radius * 2, style='F')

    def draw_pips_in_cell(self, x: float, y: float, cell_size: float, pip_count: int,
                          color: Tuple[int, int, int] = (40, 40, 40)):
        """Draw pips for a value in a single cell (half of a domino)."""
        pip_radius = cell_size * 0.08
        for px, py in self.PIP_POSITIONS.get(pip_count, []):
            pip_x = x + px * cell_size
            pip_y = y + py * cell_size
            self.draw_pip(pip_x, pip_y, pip_radius, color)

    def draw_domino_tile(self, x: float, y: float, domino: Domino,
                         horizontal: bool = True, cell_size: float = None,
                         with_shadow: bool = True):
        """Draw a domino tile in NYT style."""
        if cell_size is None:
            cell_size = self.CELL_SIZE * 0.8

        corner_r = 3.0

        if horizontal:
            w, h = cell_size * 2, cell_size
        else:
            w, h = cell_size, cell_size * 2

        # Draw shadow
        if with_shadow:
            self.pdf.set_fill_color(200, 200, 200)
            self._draw_rounded_rect(x + 1.5, y + 1.5, w, h, corner_r, fill=True, stroke=False)

        # Draw domino body (white with gray border)
        self.pdf.set_fill_color(255, 255, 255)
        self.pdf.set_draw_color(180, 180, 180)
        self.pdf.set_line_width(0.8)
        self._draw_rounded_rect(x, y, w, h, corner_r, fill=True, stroke=True)

        # Draw divider line
        self.pdf.set_draw_color(180, 180, 180)
        self.pdf.set_line_width(0.5)
        if horizontal:
            self.pdf.line(x + cell_size, y + 3, x + cell_size, y + h - 3)
        else:
            self.pdf.line(x + 3, y + cell_size, x + w - 3, y + cell_size)

        # Draw pips on first half (low value)
        pip_radius = cell_size * 0.07
        for px, py in self.PIP_POSITIONS.get(domino.low, []):
            pip_x = x + px * cell_size
            pip_y = y + py * cell_size
            self.draw_pip(pip_x, pip_y, pip_radius)

        # Draw pips on second half (high value)
        for px, py in self.PIP_POSITIONS.get(domino.high, []):
            if horizontal:
                pip_x = x + cell_size + px * cell_size
                pip_y = y + py * cell_size
            else:
                pip_x = x + px * cell_size
                pip_y = y + cell_size + py * cell_size
            self.draw_pip(pip_x, pip_y, pip_radius)

    def draw_grid(self, x_start: float, y_start: float, with_solution: bool = False,
                  label: str = None, scale: float = 1.0):
        """Draw the puzzle grid with NYT-style regions.

        Args:
            label: Optional label to show in top-left corner of grid background
            scale: Scale factor for the grid (1.0 = normal, 0.75 = 75% size)
        """
        cell_size = self.CELL_SIZE * scale

        # Build cell-to-region mapping
        cell_region: Dict[Tuple[int, int], int] = {}
        for region in self.puzzle.regions:
            for cell in region.cells:
                cell_region[cell] = region.id

        # Calculate grid bounds for outer background
        all_cells = list(cell_region.keys())
        if all_cells:
            min_r = min(c[0] for c in all_cells)
            max_r = max(c[0] for c in all_cells)
            min_c = min(c[1] for c in all_cells)
            max_c = max(c[1] for c in all_cells)

            # Draw outer background (pinkish-beige)
            padding = 4
            bg_x = x_start + min_c * cell_size - padding
            bg_y = y_start + min_r * cell_size - padding
            bg_w = (max_c - min_c + 1) * cell_size + padding * 2
            bg_h = (max_r - min_r + 1) * cell_size + padding * 2

            self.pdf.set_fill_color(235, 225, 220)  # Pinkish-beige
            self._draw_rounded_rect(bg_x, bg_y, bg_w, bg_h, 6, fill=True, stroke=False)

            # Draw difficulty label in top-left corner if provided
            if label:
                font_size = max(8, int(12 * scale))
                self.pdf.set_font('Helvetica', 'B', font_size)
                self.pdf.set_text_color(180, 170, 165)  # Subtle color matching background
                label_x = bg_x + 3 * scale
                label_y = bg_y + 1 * scale
                self.pdf.set_xy(label_x, label_y)
                self.pdf.cell(0, 5 * scale, label)

        # Draw region fills
        for region in self.puzzle.regions:
            # Check if this is an unconstrained "empty" region
            is_empty = (region.constraint_type == ConstraintType.SUM and
                       region.target_value is None)

            if is_empty:
                # Disabled look - light gray
                self.pdf.set_fill_color(225, 220, 215)
            else:
                color = self.REGION_COLORS[region.id % len(self.REGION_COLORS)]
                self.pdf.set_fill_color(*color)

            # Draw each cell
            for (r, c) in region.cells:
                x = x_start + c * cell_size
                y = y_start + r * cell_size
                self.pdf.rect(x, y, cell_size, cell_size, style='F')

        # Draw internal grid lines (thin solid grey for cell boundaries)
        # This ensures kids can see exactly where to place domino tiles
        self.pdf.set_draw_color(160, 160, 160)  # Medium grey
        self.pdf.set_line_width(0.3 * scale)  # Thin but visible
        for (r, c) in cell_region.keys():
            x = x_start + c * cell_size
            y = y_start + r * cell_size
            # Draw all four edges of every cell
            self.pdf.rect(x, y, cell_size, cell_size, style='D')

        # Collect all unique edges with their bordering regions
        # Edge key: (x1, y1, x2, y2) normalized so (x1,y1) < (x2,y2)
        edges: Dict[Tuple[float, float, float, float], List[int]] = {}

        def get_region_border_info(region_id):
            """Get border color and style for a region (print-optimized)."""
            region = self.puzzle.regions[region_id]
            is_empty = (region.constraint_type == ConstraintType.SUM and
                       region.target_value is None)
            if is_empty:
                return (140, 135, 130), 1.0, 1.5, 2.5  # color, width, dash, gap (darker gray)
            else:
                color = self.BORDER_COLORS[region_id % len(self.BORDER_COLORS)]
                return color, 1.5, 3, 3  # Thicker line for print visibility

        for region in self.puzzle.regions:
            for (r, c) in region.cells:
                x = x_start + c * cell_size
                y = y_start + r * cell_size

                # Check each edge
                edge_defs = [
                    ((r - 1, c), (x, y, x + cell_size, y)),          # Top
                    ((r + 1, c), (x, y + cell_size, x + cell_size, y + cell_size)),  # Bottom
                    ((r, c - 1), (x, y, x, y + cell_size)),          # Left
                    ((r, c + 1), (x + cell_size, y, x + cell_size, y + cell_size)),  # Right
                ]

                for neighbor, (x1, y1, x2, y2) in edge_defs:
                    if neighbor not in cell_region or cell_region[neighbor] != region.id:
                        # Normalize edge key
                        edge_key = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                        if edge_key not in edges:
                            edges[edge_key] = []
                        if region.id not in edges[edge_key]:
                            edges[edge_key].append(region.id)

        # Merge collinear edges that share the same region pair into longer segments
        # Group by: (region_ids tuple, orientation, fixed coordinate)
        def region_key(rids):
            return tuple(sorted(rids))

        merged_edges: Dict[Tuple, List[Tuple[float, float, float, float]]] = {}
        for (x1, y1, x2, y2), region_ids in edges.items():
            rkey = region_key(region_ids)
            is_horizontal = (y1 == y2)
            if is_horizontal:
                group_key = (rkey, 'H', y1)
            else:
                group_key = (rkey, 'V', x1)
            if group_key not in merged_edges:
                merged_edges[group_key] = []
            merged_edges[group_key].append((x1, y1, x2, y2))

        # For each group, merge contiguous segments
        final_edges = []  # List of (x1, y1, x2, y2, region_ids)
        for group_key, segs in merged_edges.items():
            rkey, orientation, _ = group_key
            region_ids = list(rkey)

            if orientation == 'H':
                # Sort by x coordinate, merge contiguous
                segs.sort(key=lambda s: s[0])
                merged = []
                for seg in segs:
                    if merged and abs(merged[-1][2] - seg[0]) < 0.01:
                        # Extend previous segment
                        merged[-1] = (merged[-1][0], merged[-1][1], seg[2], seg[3])
                    else:
                        merged.append(list(seg))
                for seg in merged:
                    final_edges.append((seg[0], seg[1], seg[2], seg[3], region_ids))
            else:
                # Sort by y coordinate, merge contiguous
                segs.sort(key=lambda s: s[1])
                merged = []
                for seg in segs:
                    if merged and abs(merged[-1][3] - seg[1]) < 0.01:
                        # Extend previous segment
                        merged[-1] = (merged[-1][0], merged[-1][1], seg[2], seg[3])
                    else:
                        merged.append(list(seg))
                for seg in merged:
                    final_edges.append((seg[0], seg[1], seg[2], seg[3], region_ids))

        # Draw all edges with alternating colors for shared borders
        for (x1, y1, x2, y2, region_ids) in final_edges:
            if len(region_ids) == 1:
                # Single region border - draw full line
                color, width, dash, gap = get_region_border_info(region_ids[0])
                self.pdf.set_draw_color(*color)
                self.pdf.set_line_width(width)
                self._draw_dashed_line(x1, y1, x2, y2, dash, gap)
            else:
                # Shared border - alternating dashes in each region's color
                color1, width1, dash1, _ = get_region_border_info(region_ids[0])
                color2, width2, dash2, _ = get_region_border_info(region_ids[1])

                # Use consistent dash length, no gaps (colors alternate instead)
                dash_len = 3 * scale
                dx = x2 - x1
                dy = y2 - y1
                length = math.sqrt(dx * dx + dy * dy)
                if length == 0:
                    continue

                # Normalize direction
                dx /= length
                dy /= length

                pos = 0
                color_idx = 0
                colors = [color1, color2]
                widths = [width1, width2]

                while pos < length:
                    end_pos = min(pos + dash_len, length)
                    sx = x1 + dx * pos
                    sy = y1 + dy * pos
                    ex = x1 + dx * end_pos
                    ey = y1 + dy * end_pos

                    self.pdf.set_draw_color(*colors[color_idx])
                    self.pdf.set_line_width(widths[color_idx])
                    self.pdf.line(sx, sy, ex, ey)

                    pos = end_pos
                    color_idx = 1 - color_idx  # Alternate colors

        # Draw placed dominoes if showing solution
        if with_solution and self.puzzle.solution:
            for placement in self.puzzle.solution:
                cells = placement.cells()
                r1, c1 = cells[0]
                r2, c2 = cells[1]

                # Calculate domino bounding box
                min_r, max_r = min(r1, r2), max(r1, r2)
                min_c, max_c = min(c1, c2), max(c1, c2)

                x = x_start + min_c * cell_size
                y = y_start + min_r * cell_size
                w = (max_c - min_c + 1) * cell_size
                h = (max_r - min_r + 1) * cell_size

                # Draw domino outline (rounded rect with subtle border)
                inset = 1.5 * scale
                self.pdf.set_draw_color(120, 120, 120)
                self.pdf.set_line_width(1.0 * scale)
                self._draw_rounded_rect(x + inset, y + inset, w - 2*inset, h - 2*inset,
                                       3 * scale, fill=False, stroke=True)

                # Draw divider line between the two halves
                self.pdf.set_draw_color(150, 150, 150)
                self.pdf.set_line_width(0.5 * scale)
                if r1 == r2:  # Horizontal domino
                    mid_x = x + cell_size
                    self.pdf.line(mid_x, y + inset + 2*scale, mid_x, y + h - inset - 2*scale)
                else:  # Vertical domino
                    mid_y = y + cell_size
                    self.pdf.line(x + inset + 2*scale, mid_y, x + w - inset - 2*scale, mid_y)

                # Draw pips
                x1 = x_start + c1 * cell_size
                y1 = y_start + r1 * cell_size
                self.draw_pips_in_cell(x1, y1, cell_size, placement.domino.low)

                x2 = x_start + c2 * cell_size
                y2 = y_start + r2 * cell_size
                self.draw_pips_in_cell(x2, y2, cell_size, placement.domino.high)

        # Collect all badge info first (for collision detection)
        all_cells_set = set(cell_region.keys())
        badge_size = 14 * scale
        badges = []  # List of (cx, cy, edge, color, label, region_id)

        for region in self.puzzle.regions:
            # Format label based on constraint type
            if region.constraint_type == ConstraintType.SUM:
                if region.target_value is not None:
                    label = str(region.target_value)
                else:
                    continue  # Skip "empty" regions with no constraint
            elif region.constraint_type == ConstraintType.EQUAL:
                label = "="
            elif region.constraint_type == ConstraintType.LESS:
                if region.target_value is not None:
                    label = f"< {region.target_value}"
                else:
                    label = "<"
            elif region.constraint_type == ConstraintType.GREATER:
                label = ">"
            else:
                label = "?"

            badge_color = self.BADGE_COLORS[region.id % len(self.BADGE_COLORS)]
            cx, cy, edge = self._find_badge_position(region, x_start, y_start, cell_size, all_cells_set)
            badges.append([cx, cy, edge, badge_color, label, region.id])

        # Resolve collisions - nudge overlapping badges apart
        min_dist = badge_size * 1.2  # Minimum distance between badge centers
        max_iterations = 10

        for _ in range(max_iterations):
            moved = False
            for i in range(len(badges)):
                for j in range(i + 1, len(badges)):
                    cx1, cy1, edge1 = badges[i][0], badges[i][1], badges[i][2]
                    cx2, cy2, edge2 = badges[j][0], badges[j][1], badges[j][2]

                    dx = cx2 - cx1
                    dy = cy2 - cy1
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist < min_dist and dist > 0:
                        # Push apart along the direction between them
                        overlap = (min_dist - dist) / 2
                        dx /= dist
                        dy /= dist

                        # Move along the edge direction primarily
                        if edge1 in ("top", "bottom"):
                            badges[i][0] -= overlap * (1 if dx > 0 else -1)
                            badges[j][0] += overlap * (1 if dx > 0 else -1)
                        else:  # left, right
                            badges[i][1] -= overlap * (1 if dy > 0 else -1)
                            badges[j][1] += overlap * (1 if dy > 0 else -1)
                        moved = True

            if not moved:
                break

        # Draw all badges
        for cx, cy, edge, badge_color, label, _ in badges:
            self._draw_semicircle_badge(cx, cy, badge_size, badge_color, label, edge)

    def draw_supply(self, x_start: float, y_start: float, max_width: float,
                    placed_dominoes: Optional[Set[Tuple[int, int]]] = None):
        """Draw the domino supply area in NYT style.

        Args:
            placed_dominoes: Set of (low, high) tuples for dominoes that have been placed.
                             These will be shown as faded placeholders.
        """
        cell_size = self.CELL_SIZE * 0.7
        domino_w = cell_size * 2 + 8
        domino_h = cell_size + 8

        # Calculate how many per row
        cols = max(1, int(max_width / domino_w))

        dominoes = list(self.puzzle.supply.dominoes)
        total_width = min(len(dominoes), cols) * domino_w
        start_x = x_start + (max_width - total_width) / 2

        if placed_dominoes is None:
            placed_dominoes = set()

        for i, domino in enumerate(dominoes):
            col = i % cols
            row = i // cols
            x = start_x + col * domino_w
            y = y_start + row * domino_h

            # Check if this domino has been placed
            domino_key = (domino.low, domino.high)
            is_placed = domino_key in placed_dominoes

            if is_placed:
                # Draw faded placeholder
                self._draw_empty_domino_slot(x, y, cell_size)
            else:
                self.draw_domino_tile(x, y, domino, horizontal=True, cell_size=cell_size)

    def _draw_empty_domino_slot(self, x: float, y: float, cell_size: float):
        """Draw a faded empty slot where a domino was."""
        corner_r = 3.0
        w, h = cell_size * 2, cell_size

        # Faded pinkish-beige color
        self.pdf.set_fill_color(235, 225, 220)
        self._draw_rounded_rect(x, y, w, h, corner_r, fill=True, stroke=False)

    def render(self, output_path: str, include_solution: bool = True):
        """Render the complete puzzle to PDF."""
        # Calculate grid dimensions
        all_cells = []
        for region in self.puzzle.regions:
            all_cells.extend(region.cells)

        if not all_cells:
            print("No cells to render!")
            return

        min_r = min(c[0] for c in all_cells)
        max_r = max(c[0] for c in all_cells)
        min_c = min(c[1] for c in all_cells)
        max_c = max(c[1] for c in all_cells)

        grid_rows = max_r - min_r + 1
        grid_cols = max_c - min_c + 1
        grid_width = grid_cols * self.CELL_SIZE
        grid_height = grid_rows * self.CELL_SIZE

        # Determine if we need landscape and/or split pages
        margin = 30
        supply_cell_size = self.CELL_SIZE * 0.7
        supply_rows = math.ceil(len(self.puzzle.supply.dominoes) / 4)
        supply_height = supply_rows * (supply_cell_size + 8)

        # Total height needed: title + grid + badges + separator + supply
        total_height = 50 + grid_height + 30 + 15 + supply_height

        # Check if it fits in portrait (letter: 279mm height, 216mm width)
        portrait_h, portrait_w = 279, 216
        landscape_h, landscape_w = 216, 279

        # Decide orientation and whether to split
        use_landscape = False
        split_pages = False

        # Need landscape if grid is too wide or too tall for portrait
        if grid_width + 60 > portrait_w or total_height > portrait_h:
            use_landscape = True

        # If using landscape, always split pages (supply on separate page)
        if use_landscape:
            split_pages = True

        # Create new PDF with correct orientation
        orientation = 'L' if use_landscape else 'P'
        self.pdf = FPDF(orientation=orientation, unit='mm', format='letter')
        self.pdf.set_auto_page_break(auto=False)

        page_w = landscape_w if use_landscape else portrait_w
        page_h = landscape_h if use_landscape else portrait_h

        # Page 1: Grid (no label - clean for solving)
        self.pdf.add_page()

        # Grid (centered with printer safety margins)
        # Badges extend ~10mm beyond grid, need ~15mm from page edge = 25mm minimum
        safety_margin = 25
        grid_x = max(safety_margin, (page_w - grid_width) / 2)
        grid_y = safety_margin + 10  # Extra top margin for any top badges

        self.draw_grid(grid_x, grid_y, with_solution=False)

        if split_pages:
            # Page 2: Supply (separate page)
            self.pdf.add_page()

            self.pdf.set_font('Helvetica', 'B', 20)
            self.pdf.set_text_color(40, 40, 40)
            self.pdf.set_xy(0, 15)
            self.pdf.cell(0, 10, self.puzzle.difficulty.upper(), align='C')

            supply_y = 45
            supply_width = page_w - 2 * margin
            self.draw_supply(margin, supply_y, supply_width, placed_dominoes=set())
        else:
            # Supply on same page
            sep_y = grid_y + grid_height + 25
            self.pdf.set_draw_color(200, 200, 200)
            self.pdf.set_line_width(0.5)
            self.pdf.line(margin, sep_y, page_w - margin, sep_y)

            supply_y = sep_y + 15
            supply_width = page_w - 2 * margin
            self.draw_supply(margin, supply_y, supply_width, placed_dominoes=set())

        # Solution page (smaller grid since we don't need to write on it)
        if include_solution and self.puzzle.solution:
            self.pdf.add_page()

            # Centered header like supply page
            self.pdf.set_font('Helvetica', 'B', 20)
            self.pdf.set_text_color(40, 40, 40)
            self.pdf.set_xy(0, 15)
            self.pdf.cell(0, 10, f"{self.puzzle.difficulty.upper()} SOLUTION", align='C')

            solution_scale = 0.75
            solution_grid_width = grid_width * solution_scale
            solution_grid_x = (page_w - solution_grid_width) / 2
            solution_y = 45
            self.draw_grid(solution_grid_x, solution_y, with_solution=True,
                          scale=solution_scale)

        self.pdf.output(output_path)
        print(f"Saved puzzle to: {output_path}")


if __name__ == "__main__":
    from puzzles import get_all_puzzles

    # Render all puzzles
    puzzles = get_all_puzzles()
    for puzzle in puzzles:
        renderer = PuzzleRenderer(puzzle)
        filename = f"{puzzle.name.lower().replace(' ', '_')}.pdf"
        renderer.render(filename)
