"""
Puzzle generator that searches for puzzles with unique solutions.
Uses reverse-engineering: start with solution, derive constraints, verify uniqueness.
"""
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import random
import itertools

from domino_sets import Domino, DominoSet
from grid import Puzzle, Region, PlacedDomino, Orientation, ConstraintType
from solver import Solver


@dataclass
class GenerationStats:
    """Statistics for puzzle generation."""
    attempts: int = 0
    unique_found: int = 0
    no_solution: int = 0
    multiple_solutions: int = 0


def place_dominoes_on_grid(
    dominoes: List[Domino],
    rows: int,
    cols: int
) -> Optional[List[PlacedDomino]]:
    """
    Place dominoes on grid using backtracking.
    Returns a valid placement or None.
    """
    total_cells = rows * cols
    if len(dominoes) * 2 != total_cells:
        return None

    placements: List[PlacedDomino] = []
    occupied: Set[Tuple[int, int]] = set()

    def backtrack(domino_idx: int) -> bool:
        if domino_idx == len(dominoes):
            return True

        domino = dominoes[domino_idx]

        # Find first empty cell
        for r in range(rows):
            for c in range(cols):
                if (r, c) in occupied:
                    continue

                # Try horizontal
                if c + 1 < cols and (r, c + 1) not in occupied:
                    occupied.add((r, c))
                    occupied.add((r, c + 1))
                    placements.append(PlacedDomino(domino, r, c, Orientation.HORIZONTAL))

                    if backtrack(domino_idx + 1):
                        return True

                    occupied.remove((r, c))
                    occupied.remove((r, c + 1))
                    placements.pop()

                # Try vertical
                if r + 1 < rows and (r + 1, c) not in occupied:
                    occupied.add((r, c))
                    occupied.add((r + 1, c))
                    placements.append(PlacedDomino(domino, r, c, Orientation.VERTICAL))

                    if backtrack(domino_idx + 1):
                        return True

                    occupied.remove((r, c))
                    occupied.remove((r + 1, c))
                    placements.pop()

                # First empty cell must be filled, so return if we couldn't place
                return False

        return False

    if backtrack(0):
        return placements
    return None


def get_cell_pip_value(placements: List[PlacedDomino], cell: Tuple[int, int]) -> int:
    """Get the pip value at a specific cell from placements."""
    r, c = cell
    for p in placements:
        if p.orientation == Orientation.HORIZONTAL:
            if (p.row, p.col) == cell:
                return p.domino.low
            if (p.row, p.col + 1) == cell:
                return p.domino.high
        else:
            if (p.row, p.col) == cell:
                return p.domino.low
            if (p.row + 1, p.col) == cell:
                return p.domino.high
    return -1


def compute_region_sum(placements: List[PlacedDomino], cells: List[Tuple[int, int]]) -> int:
    """Compute sum of pip values in region cells."""
    return sum(get_cell_pip_value(placements, c) for c in cells)


def try_constraint_config(
    dominoes: List[Domino],
    rows: int,
    cols: int,
    region_cells: List[List[Tuple[int, int]]],
    constraint_types: List[ConstraintType],
    stats: GenerationStats,
    name: str = "Puzzle"
) -> Optional[Puzzle]:
    """
    Try a specific constraint configuration.
    For SUM constraints, derives target from a valid placement.
    """
    # First, find a valid placement
    placement = place_dominoes_on_grid(dominoes, rows, cols)
    if not placement:
        return None

    # Build regions from the placement
    regions = []
    for i, (cells, ctype) in enumerate(zip(region_cells, constraint_types)):
        region = Region(
            id=i,
            cells=cells,
            constraint_type=ctype,
        )

        if ctype == ConstraintType.SUM:
            region.target_value = compute_region_sum(placement, cells)
        elif ctype == ConstraintType.LESS:
            region.linked_region_id = i + 1  # Link to next region
        elif ctype == ConstraintType.GREATER:
            region.linked_region_id = i + 1

        regions.append(region)

    stats.attempts += 1

    puzzle = Puzzle(
        name=name,
        difficulty="unknown",
        rows=rows,
        cols=cols,
        regions=regions,
        supply=DominoSet(dominoes),
        solution=placement
    )

    solver = Solver(puzzle, max_solutions=3)
    count = solver.solve()

    if count == 1:
        stats.unique_found += 1
        return puzzle
    elif count == 0:
        stats.no_solution += 1
    else:
        stats.multiple_solutions += 1

    return None


def search_for_unique_easy(stats: GenerationStats) -> Optional[Puzzle]:
    """Search for an easy puzzle with unique solution (4 dominoes)."""

    # Double-six dominoes to try
    all_d6 = [
        Domino(0, 0), Domino(0, 1), Domino(0, 2), Domino(0, 3),
        Domino(0, 4), Domino(0, 5), Domino(0, 6), Domino(1, 1),
        Domino(1, 2), Domino(1, 3), Domino(1, 4), Domino(1, 5),
        Domino(1, 6), Domino(2, 2), Domino(2, 3), Domino(2, 4),
        Domino(2, 5), Domino(2, 6), Domino(3, 3), Domino(3, 4),
        Domino(3, 5), Domino(3, 6), Domino(4, 4), Domino(4, 5),
        Domino(4, 6), Domino(5, 5), Domino(5, 6), Domino(6, 6),
    ]

    rows, cols = 2, 4  # 8 cells = 4 dominoes

    # Different region configurations to try
    region_configs = [
        # Config 1: Two 4-cell regions (left/right split)
        {
            "cells": [
                [(0, 0), (0, 1), (1, 0), (1, 1)],
                [(0, 2), (0, 3), (1, 2), (1, 3)],
            ],
            "types": [ConstraintType.SUM, ConstraintType.SUM],
        },
        # Config 2: Two 4-cell regions (top/bottom split)
        {
            "cells": [
                [(0, 0), (0, 1), (0, 2), (0, 3)],
                [(1, 0), (1, 1), (1, 2), (1, 3)],
            ],
            "types": [ConstraintType.SUM, ConstraintType.SUM],
        },
        # Config 3: Inequality chain (4 regions of 2)
        {
            "cells": [
                [(0, 0), (0, 1)],
                [(0, 2), (0, 3)],
                [(1, 0), (1, 1)],
                [(1, 2), (1, 3)],
            ],
            "types": [ConstraintType.LESS, ConstraintType.LESS, ConstraintType.LESS, ConstraintType.SUM],
        },
        # Config 4: Mixed - 2 EQUAL + 1 SUM (forces doubles)
        {
            "cells": [
                [(0, 0), (0, 1)],
                [(0, 2), (0, 3)],
                [(1, 0), (1, 1), (1, 2), (1, 3)],
            ],
            "types": [ConstraintType.LESS, ConstraintType.SUM, ConstraintType.SUM],
        },
        # Config 5: 3-cell regions (forces spanning)
        {
            "cells": [
                [(0, 0), (0, 1), (1, 0)],
                [(0, 2), (0, 3), (1, 3)],
                [(1, 1), (1, 2)],
            ],
            "types": [ConstraintType.SUM, ConstraintType.SUM, ConstraintType.SUM],
        },
    ]

    # Try different domino combinations
    for combo in itertools.combinations(all_d6, 4):
        dominoes = list(combo)

        for config in region_configs:
            puzzle = try_constraint_config(
                dominoes, rows, cols,
                config["cells"], config["types"],
                stats, "Easy Puzzle"
            )
            if puzzle:
                return puzzle

            # Also try with shuffled domino order
            random.shuffle(dominoes)
            puzzle = try_constraint_config(
                dominoes, rows, cols,
                config["cells"], config["types"],
                stats, "Easy Puzzle"
            )
            if puzzle:
                return puzzle

        if stats.attempts > 50000:
            break

    return None


def search_for_unique_medium(stats: GenerationStats) -> Optional[Puzzle]:
    """Search for a medium puzzle with unique solution (6 dominoes)."""

    all_d6 = [
        Domino(0, 0), Domino(0, 1), Domino(0, 2), Domino(0, 3),
        Domino(0, 4), Domino(0, 5), Domino(0, 6), Domino(1, 1),
        Domino(1, 2), Domino(1, 3), Domino(1, 4), Domino(1, 5),
        Domino(1, 6), Domino(2, 2), Domino(2, 3), Domino(2, 4),
        Domino(2, 5), Domino(2, 6), Domino(3, 3), Domino(3, 4),
        Domino(3, 5), Domino(3, 6), Domino(4, 4), Domino(4, 5),
        Domino(4, 6), Domino(5, 5), Domino(5, 6), Domino(6, 6),
    ]

    rows, cols = 3, 4  # 12 cells = 6 dominoes

    region_configs = [
        # Config 1: 4 regions with interesting shapes
        {
            "cells": [
                [(0, 0), (0, 1), (1, 0)],  # L-shape
                [(0, 2), (0, 3), (1, 3)],  # reversed L
                [(1, 1), (1, 2), (2, 1), (2, 2)],  # square
                [(2, 0), (2, 3)],  # corners
            ],
            "types": [ConstraintType.SUM, ConstraintType.SUM, ConstraintType.SUM, ConstraintType.SUM],
        },
        # Config 2: Inequality chain
        {
            "cells": [
                [(0, 0), (0, 1), (0, 2), (0, 3)],
                [(1, 0), (1, 1), (1, 2), (1, 3)],
                [(2, 0), (2, 1), (2, 2), (2, 3)],
            ],
            "types": [ConstraintType.LESS, ConstraintType.LESS, ConstraintType.SUM],
        },
        # Config 3: 6 regions (one per domino with tight sums)
        {
            "cells": [
                [(0, 0), (0, 1)],
                [(0, 2), (0, 3)],
                [(1, 0), (1, 1)],
                [(1, 2), (1, 3)],
                [(2, 0), (2, 1)],
                [(2, 2), (2, 3)],
            ],
            "types": [
                ConstraintType.LESS, ConstraintType.LESS, ConstraintType.LESS,
                ConstraintType.LESS, ConstraintType.LESS, ConstraintType.SUM
            ],
        },
    ]

    for combo in itertools.combinations(all_d6, 6):
        dominoes = list(combo)

        for config in region_configs:
            puzzle = try_constraint_config(
                dominoes, rows, cols,
                config["cells"], config["types"],
                stats, "Medium Puzzle"
            )
            if puzzle:
                return puzzle

        if stats.attempts > 50000:
            break

    return None


def search_for_unique_hard(stats: GenerationStats) -> Optional[Puzzle]:
    """Search for a hard puzzle with unique solution (8 dominoes from double-nine remainder)."""

    # Double-nine remainder: tiles with at least one side >= 7
    d9_remainder = [
        Domino(0, 7), Domino(0, 8), Domino(0, 9),
        Domino(1, 7), Domino(1, 8), Domino(1, 9),
        Domino(2, 7), Domino(2, 8), Domino(2, 9),
        Domino(3, 7), Domino(3, 8), Domino(3, 9),
        Domino(4, 7), Domino(4, 8), Domino(4, 9),
        Domino(5, 7), Domino(5, 8), Domino(5, 9),
        Domino(6, 7), Domino(6, 8), Domino(6, 9),
        Domino(7, 7), Domino(7, 8), Domino(7, 9),
        Domino(8, 8), Domino(8, 9),
        Domino(9, 9),
    ]

    rows, cols = 4, 4  # 16 cells = 8 dominoes

    region_configs = [
        # Config 1: Quadrants with inequality
        {
            "cells": [
                [(0, 0), (0, 1), (1, 0), (1, 1)],
                [(0, 2), (0, 3), (1, 2), (1, 3)],
                [(2, 0), (2, 1), (3, 0), (3, 1)],
                [(2, 2), (2, 3), (3, 2), (3, 3)],
            ],
            "types": [ConstraintType.LESS, ConstraintType.LESS, ConstraintType.LESS, ConstraintType.SUM],
        },
        # Config 2: Horizontal strips
        {
            "cells": [
                [(0, 0), (0, 1), (0, 2), (0, 3)],
                [(1, 0), (1, 1), (1, 2), (1, 3)],
                [(2, 0), (2, 1), (2, 2), (2, 3)],
                [(3, 0), (3, 1), (3, 2), (3, 3)],
            ],
            "types": [ConstraintType.LESS, ConstraintType.LESS, ConstraintType.LESS, ConstraintType.SUM],
        },
    ]

    for combo in itertools.combinations(d9_remainder, 8):
        dominoes = list(combo)

        for config in region_configs:
            puzzle = try_constraint_config(
                dominoes, rows, cols,
                config["cells"], config["types"],
                stats, "Hard Puzzle"
            )
            if puzzle:
                return puzzle

        if stats.attempts > 100000:
            break

    return None


if __name__ == "__main__":
    print("=" * 60)
    print("PUZZLE GENERATION - SEARCHING FOR UNIQUE SOLUTIONS")
    print("=" * 60)

    # Easy puzzle
    print("\n--- EASY (4 dominoes, 2x4 grid) ---")
    easy_stats = GenerationStats()
    easy_puzzle = search_for_unique_easy(easy_stats)

    if easy_puzzle:
        print(f"✓ Found unique puzzle after {easy_stats.attempts} attempts!")
        print(f"  (No solution: {easy_stats.no_solution}, Multiple: {easy_stats.multiple_solutions})")
        print(f"  Dominoes: {[str(d) for d in easy_puzzle.supply.dominoes]}")
        print(f"  Regions: {len(easy_puzzle.regions)}")
        for r in easy_puzzle.regions:
            if r.target_value:
                print(f"    Region {r.id}: {r.constraint_type.value}={r.target_value}")
            elif r.linked_region_id is not None:
                print(f"    Region {r.id}: {r.constraint_type.value} region {r.linked_region_id}")
            else:
                print(f"    Region {r.id}: {r.constraint_type.value}")
    else:
        print(f"✗ No unique puzzle found after {easy_stats.attempts} attempts")
        print(f"  (No solution: {easy_stats.no_solution}, Multiple: {easy_stats.multiple_solutions})")

    # Medium puzzle
    print("\n--- MEDIUM (6 dominoes, 3x4 grid) ---")
    medium_stats = GenerationStats()
    medium_puzzle = search_for_unique_medium(medium_stats)

    if medium_puzzle:
        print(f"✓ Found unique puzzle after {medium_stats.attempts} attempts!")
        print(f"  (No solution: {medium_stats.no_solution}, Multiple: {medium_stats.multiple_solutions})")
    else:
        print(f"✗ No unique puzzle found after {medium_stats.attempts} attempts")
        print(f"  (No solution: {medium_stats.no_solution}, Multiple: {medium_stats.multiple_solutions})")

    # Hard puzzle
    print("\n--- HARD (8 dominoes from double-nine remainder, 4x4 grid) ---")
    hard_stats = GenerationStats()
    hard_puzzle = search_for_unique_hard(hard_stats)

    if hard_puzzle:
        print(f"✓ Found unique puzzle after {hard_stats.attempts} attempts!")
        print(f"  (No solution: {hard_stats.no_solution}, Multiple: {hard_stats.multiple_solutions})")
    else:
        print(f"✗ No unique puzzle found after {hard_stats.attempts} attempts")
        print(f"  (No solution: {hard_stats.no_solution}, Multiple: {hard_stats.multiple_solutions})")
