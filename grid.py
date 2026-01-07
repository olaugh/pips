"""
Grid and puzzle generation for domino placement puzzles.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
import random

from domino_sets import Domino, DominoSet
from disjoint_set import DisjointSet


class Orientation(Enum):
    HORIZONTAL = 'H'  # Domino spans (r,c) and (r,c+1)
    VERTICAL = 'V'    # Domino spans (r,c) and (r+1,c)


@dataclass
class PlacedDomino:
    """A domino placed on the grid."""
    domino: Domino
    row: int
    col: int
    orientation: Orientation

    def cells(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Return the two cells this domino occupies."""
        if self.orientation == Orientation.HORIZONTAL:
            return ((self.row, self.col), (self.row, self.col + 1))
        else:
            return ((self.row, self.col), (self.row + 1, self.col))


class ConstraintType(Enum):
    SUM = 'sum'           # Total pips = target value
    EQUAL = 'equal'       # All pips in region are the same value
    GREATER = 'greater'   # Sum > linked region's sum
    LESS = 'less'         # Sum < linked region's sum


@dataclass
class Region:
    """A region in the puzzle grid with a constraint."""
    id: int
    cells: List[Tuple[int, int]]
    constraint_type: ConstraintType = ConstraintType.SUM
    target_value: Optional[int] = None  # For SUM constraint
    linked_region_id: Optional[int] = None  # For GREATER/LESS constraints

    def size(self) -> int:
        return len(self.cells)


@dataclass
class Puzzle:
    """A complete puzzle definition."""
    name: str
    difficulty: str
    rows: int
    cols: int
    regions: List[Region]
    supply: DominoSet
    solution: List[PlacedDomino] = field(default_factory=list)

    def get_cell_region(self, row: int, col: int) -> Optional[Region]:
        """Get the region containing a cell."""
        for region in self.regions:
            if (row, col) in region.cells:
                return region
        return None


class GridGenerator:
    """
    Generates puzzle grids by placing dominoes and creating regions.
    """

    def __init__(self, domino_set: DominoSet):
        self.domino_set = domino_set

    def generate_connected_layout(
        self,
        num_dominoes: int,
        max_width: int = 10,
        max_height: int = 10
    ) -> Tuple[List[PlacedDomino], int, int]:
        """
        Generate a connected layout of dominoes using random growth.
        Returns (placed_dominoes, rows, cols).
        """
        dominoes = list(self.domino_set.dominoes[:num_dominoes])
        random.shuffle(dominoes)

        # Track occupied cells
        occupied: Set[Tuple[int, int]] = set()
        placements: List[PlacedDomino] = []

        # Start with first domino at center
        center_r, center_c = max_height // 2, max_width // 2

        # Use disjoint set to track connectivity
        ds = DisjointSet()

        def try_place(domino: Domino) -> Optional[PlacedDomino]:
            """Try to place a domino adjacent to existing placements."""
            if not placements:
                # First domino - place at center
                if random.random() < 0.5:
                    p = PlacedDomino(domino, center_r, center_c, Orientation.HORIZONTAL)
                else:
                    p = PlacedDomino(domino, center_r, center_c, Orientation.VERTICAL)
                return p

            # Get all cells adjacent to occupied cells
            candidates = []
            for (r, c) in occupied:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if (nr, nc) not in occupied:
                        # Try horizontal placement
                        if (nr, nc + 1) not in occupied and 0 <= nc + 1 < max_width:
                            candidates.append((nr, nc, Orientation.HORIZONTAL))
                        # Try vertical placement
                        if (nr + 1, nc) not in occupied and 0 <= nr + 1 < max_height:
                            candidates.append((nr, nc, Orientation.VERTICAL))

            random.shuffle(candidates)
            for r, c, orient in candidates:
                if 0 <= r < max_height and 0 <= c < max_width:
                    p = PlacedDomino(domino, r, c, orient)
                    cells = p.cells()
                    if cells[0] not in occupied and cells[1] not in occupied:
                        if 0 <= cells[1][0] < max_height and 0 <= cells[1][1] < max_width:
                            return p
            return None

        for domino in dominoes:
            placement = try_place(domino)
            if placement:
                placements.append(placement)
                c1, c2 = placement.cells()
                occupied.add(c1)
                occupied.add(c2)
                ds.make_set(c1)
                ds.make_set(c2)
                ds.union(c1, c2)

        # Calculate actual bounds
        if not occupied:
            return [], 0, 0

        min_r = min(c[0] for c in occupied)
        max_r = max(c[0] for c in occupied)
        min_c = min(c[1] for c in occupied)
        max_c = max(c[1] for c in occupied)

        # Normalize to 0-based
        normalized = []
        for p in placements:
            normalized.append(PlacedDomino(
                p.domino,
                p.row - min_r,
                p.col - min_c,
                p.orientation
            ))

        return normalized, max_r - min_r + 1, max_c - min_c + 1

    def create_single_domino_regions(
        self,
        placements: List[PlacedDomino]
    ) -> List[Region]:
        """
        Create regions where each region is exactly one domino.
        The constraint is the pip sum of that domino.
        """
        regions = []
        for i, p in enumerate(placements):
            cells = list(p.cells())
            regions.append(Region(
                id=i,
                cells=cells,
                target_sum=p.domino.pips
            ))
        return regions

    def create_merged_regions(
        self,
        placements: List[PlacedDomino],
        merge_probability: float = 0.3
    ) -> List[Region]:
        """
        Create regions, sometimes merging adjacent dominoes.
        Merged regions have summed constraints.
        """
        # Start with single-domino regions
        ds = DisjointSet()
        domino_cells: Dict[int, List[Tuple[int, int]]] = {}
        domino_pips: Dict[int, int] = {}
        cell_to_domino: Dict[Tuple[int, int], int] = {}

        for i, p in enumerate(placements):
            cells = p.cells()
            ds.make_set(i)
            domino_cells[i] = list(cells)
            domino_pips[i] = p.domino.pips
            for c in cells:
                cell_to_domino[c] = i

        # Find adjacent dominoes and maybe merge
        for i, p in enumerate(placements):
            for cell in p.cells():
                r, c = cell
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    neighbor = (nr, nc)
                    if neighbor in cell_to_domino:
                        j = cell_to_domino[neighbor]
                        if i != j and random.random() < merge_probability:
                            ds.union(i, j)

        # Build regions from merged groups
        groups = ds.get_sets()
        regions = []
        for region_id, (root, members) in enumerate(groups.items()):
            cells = []
            total_pips = 0
            for m in members:
                cells.extend(domino_cells[m])
                total_pips += domino_pips[m]
            regions.append(Region(
                id=region_id,
                cells=cells,
                target_sum=total_pips
            ))

        return regions

    def generate_puzzle(
        self,
        name: str,
        difficulty: str,
        num_dominoes: int,
        merge_regions: bool = False
    ) -> Puzzle:
        """Generate a complete puzzle."""
        subset = self.domino_set.subset(num_dominoes)
        placements, rows, cols = self.generate_connected_layout(num_dominoes)

        if merge_regions:
            regions = self.create_merged_regions(placements, merge_probability=0.25)
        else:
            regions = self.create_single_domino_regions(placements)

        return Puzzle(
            name=name,
            difficulty=difficulty,
            rows=rows,
            cols=cols,
            regions=regions,
            supply=DominoSet([p.domino for p in placements]),
            solution=placements
        )


if __name__ == "__main__":
    from domino_sets import DominoSet

    # Test generation
    d6 = DominoSet.double_six()
    gen = GridGenerator(d6)

    puzzle = gen.generate_puzzle("Test Easy", "easy", 6)
    print(f"Generated puzzle: {puzzle.rows}x{puzzle.cols}")
    print(f"Regions: {len(puzzle.regions)}")
    for r in puzzle.regions:
        print(f"  Region {r.id}: {r.cells} -> sum={r.target_sum}")
