"""
Targeted search for unique puzzles using specific constraint patterns.
"""
from typing import List, Dict, Tuple, Optional
from domino_sets import Domino, DominoSet
from grid import Puzzle, Region, PlacedDomino, Orientation, ConstraintType
from solver import Solver


def test_puzzle(dominoes, rows, cols, regions, name="Test") -> int:
    """Test a puzzle configuration and return solution count."""
    puzzle = Puzzle(
        name=name,
        difficulty="test",
        rows=rows,
        cols=cols,
        regions=regions,
        supply=DominoSet(dominoes),
        solution=[]
    )
    solver = Solver(puzzle, max_solutions=5)
    count = solver.solve()
    if count == 1:
        puzzle.solution = solver.get_solution()
    return count, puzzle if count == 1 else None


def find_easy_1():
    """
    Strategy: Use dominoes with distinct sums and ALL-SUM constraints.
    If every region has a specific sum target, and the domino sums are
    chosen so there's only one valid partition, we get uniqueness.
    """
    print("\n=== EASY PUZZLE 1: Distinct Sum Strategy ===")

    # 4 dominoes with distinct pip sums
    # Grid 2x4, two 4-cell regions
    rows, cols = 2, 4

    # Try dominoes where sums are: 1, 3, 5, 11 (total=20)
    # Region A needs sum X, Region B needs sum 20-X
    # If X can only be achieved one way, we have uniqueness

    test_sets = [
        # Set 1: Sums 0, 3, 7, 12 (total 22)
        [Domino(0, 0), Domino(1, 2), Domino(3, 4), Domino(6, 6)],
        # Set 2: Sums 1, 2, 9, 12 (total 24)
        [Domino(0, 1), Domino(0, 2), Domino(4, 5), Domino(6, 6)],
        # Set 3: Sums 0, 5, 7, 11 (total 23)
        [Domino(0, 0), Domino(2, 3), Domino(3, 4), Domino(5, 6)],
        # Set 4: Use very distinct sums: 0, 1, 11, 12 (total 24)
        [Domino(0, 0), Domino(0, 1), Domino(5, 6), Domino(6, 6)],
    ]

    region_cells = [
        [(0, 0), (0, 1), (1, 0), (1, 1)],  # Left 4 cells
        [(0, 2), (0, 3), (1, 2), (1, 3)],  # Right 4 cells
    ]

    for dominoes in test_sets:
        sums = [d.pips for d in dominoes]
        total = sum(sums)
        print(f"\n  Dominoes: {[str(d) for d in dominoes]}")
        print(f"  Sums: {sums}, Total: {total}")

        # Try each possible region A sum
        for target_a in range(total + 1):
            target_b = total - target_a

            # Check if target_a can be achieved by exactly 2 dominoes
            ways_to_make_a = []
            for i in range(len(dominoes)):
                for j in range(i + 1, len(dominoes)):
                    if sums[i] + sums[j] == target_a:
                        ways_to_make_a.append((dominoes[i], dominoes[j]))

            if len(ways_to_make_a) != 1:
                continue  # Skip if multiple ways or no way

            regions = [
                Region(0, region_cells[0], ConstraintType.SUM, target_value=target_a),
                Region(1, region_cells[1], ConstraintType.SUM, target_value=target_b),
            ]

            count, puzzle = test_puzzle(dominoes, rows, cols, regions, "Easy 1")

            if count == 1:
                print(f"  ✓ UNIQUE! Region A={target_a}, Region B={target_b}")
                print(f"    Only way: {ways_to_make_a[0]}")
                return puzzle
            elif count > 0:
                print(f"    Targets A={target_a}, B={target_b}: {count} solutions")

    return None


def find_easy_2():
    """
    Strategy: Use 3-cell regions to force domino spanning.
    When regions have odd cell counts, dominoes must span boundaries.
    """
    print("\n=== EASY PUZZLE 2: Odd Region Sizes (Forced Spanning) ===")

    rows, cols = 2, 4  # 8 cells = 4 dominoes

    # 3-cell and 3-cell and 2-cell regions
    region_cells = [
        [(0, 0), (0, 1), (1, 0)],  # 3 cells - L shape
        [(0, 2), (0, 3), (1, 3)],  # 3 cells - reversed L
        [(1, 1), (1, 2)],          # 2 cells - middle
    ]

    # Try different domino sets
    test_sets = [
        [Domino(0, 1), Domino(2, 3), Domino(4, 5), Domino(0, 6)],
        [Domino(1, 1), Domino(2, 2), Domino(3, 3), Domino(4, 4)],  # All doubles
        [Domino(0, 0), Domino(1, 1), Domino(2, 3), Domino(4, 6)],
        [Domino(0, 2), Domino(1, 3), Domino(2, 4), Domino(3, 5)],
    ]

    for dominoes in test_sets:
        sums = [d.pips for d in dominoes]
        total = sum(sums)
        print(f"\n  Dominoes: {[str(d) for d in dominoes]}")

        # Try different sum combinations for the 3 regions
        for t0 in range(total + 1):
            for t1 in range(total - t0 + 1):
                t2 = total - t0 - t1

                regions = [
                    Region(0, region_cells[0], ConstraintType.SUM, target_value=t0),
                    Region(1, region_cells[1], ConstraintType.SUM, target_value=t1),
                    Region(2, region_cells[2], ConstraintType.SUM, target_value=t2),
                ]

                count, puzzle = test_puzzle(dominoes, rows, cols, regions, "Easy 2")

                if count == 1:
                    print(f"  ✓ UNIQUE! Regions: {t0}, {t1}, {t2}")
                    return puzzle

    return None


def find_medium():
    """
    Strategy: 6 dominoes on 3x4 grid with inequality chain.
    """
    print("\n=== MEDIUM PUZZLE: 3x4 Grid with Inequalities ===")

    rows, cols = 3, 4  # 12 cells = 6 dominoes

    # Use dominoes with strictly increasing sums
    # Sums: 1, 2, 4, 6, 9, 12
    dominoes = [
        Domino(0, 1),  # 1
        Domino(0, 2),  # 2
        Domino(1, 3),  # 4
        Domino(2, 4),  # 6
        Domino(4, 5),  # 9
        Domino(6, 6),  # 12
    ]
    print(f"  Dominoes: {[str(d) for d in dominoes]}")
    print(f"  Sums: {[d.pips for d in dominoes]}")

    # 3 horizontal strips
    region_cells = [
        [(0, 0), (0, 1), (0, 2), (0, 3)],  # Row 0
        [(1, 0), (1, 1), (1, 2), (1, 3)],  # Row 1
        [(2, 0), (2, 1), (2, 2), (2, 3)],  # Row 2
    ]

    # Try different inequality patterns and sum targets
    # A < B < C with C having a specific sum
    total = sum(d.pips for d in dominoes)

    for target_c in range(1, total):
        regions = [
            Region(0, region_cells[0], ConstraintType.LESS, linked_region_id=1),
            Region(1, region_cells[1], ConstraintType.LESS, linked_region_id=2),
            Region(2, region_cells[2], ConstraintType.SUM, target_value=target_c),
        ]

        count, puzzle = test_puzzle(dominoes, rows, cols, regions, "Medium")

        if count == 1:
            print(f"  ✓ UNIQUE! A < B < C, C sum={target_c}")
            return puzzle
        elif count > 0 and count <= 3:
            print(f"    C sum={target_c}: {count} solutions")

    # Try with 6 regions (one per domino position)
    print("\n  Trying 6-region layout...")
    region_cells_6 = [
        [(0, 0), (0, 1)],
        [(0, 2), (0, 3)],
        [(1, 0), (1, 1)],
        [(1, 2), (1, 3)],
        [(2, 0), (2, 1)],
        [(2, 2), (2, 3)],
    ]

    # Full inequality chain
    regions = [
        Region(0, region_cells_6[0], ConstraintType.LESS, linked_region_id=1),
        Region(1, region_cells_6[1], ConstraintType.LESS, linked_region_id=2),
        Region(2, region_cells_6[2], ConstraintType.LESS, linked_region_id=3),
        Region(3, region_cells_6[3], ConstraintType.LESS, linked_region_id=4),
        Region(4, region_cells_6[4], ConstraintType.LESS, linked_region_id=5),
        Region(5, region_cells_6[5], ConstraintType.SUM, target_value=12),
    ]

    count, puzzle = test_puzzle(dominoes, rows, cols, regions, "Medium")
    if count == 1:
        print(f"  ✓ UNIQUE! Full chain with 6 regions")
        return puzzle
    else:
        print(f"    6-region chain: {count} solutions")

    return None


def find_hard():
    """
    Strategy: 8 dominoes from double-nine remainder on 4x4 grid.
    """
    print("\n=== HARD PUZZLE: 4x4 Grid with High Pips ===")

    rows, cols = 4, 4  # 16 cells = 8 dominoes

    # Use dominoes with at least one 7, 8, or 9
    # Choose 8 with strictly increasing sums
    dominoes = [
        Domino(0, 7),  # 7
        Domino(1, 7),  # 8
        Domino(0, 9),  # 9
        Domino(2, 8),  # 10
        Domino(4, 7),  # 11
        Domino(5, 7),  # 12
        Domino(7, 7),  # 14
        Domino(9, 9),  # 18
    ]
    print(f"  Dominoes: {[str(d) for d in dominoes]}")
    print(f"  Sums: {[d.pips for d in dominoes]}")

    # 4 quadrants
    region_cells = [
        [(0, 0), (0, 1), (1, 0), (1, 1)],  # Top-left
        [(0, 2), (0, 3), (1, 2), (1, 3)],  # Top-right
        [(2, 0), (2, 1), (3, 0), (3, 1)],  # Bottom-left
        [(2, 2), (2, 3), (3, 2), (3, 3)],  # Bottom-right
    ]

    total = sum(d.pips for d in dominoes)

    # Try inequality chain with sum on last region
    for target_d in range(1, total):
        regions = [
            Region(0, region_cells[0], ConstraintType.LESS, linked_region_id=1),
            Region(1, region_cells[1], ConstraintType.LESS, linked_region_id=2),
            Region(2, region_cells[2], ConstraintType.LESS, linked_region_id=3),
            Region(3, region_cells[3], ConstraintType.SUM, target_value=target_d),
        ]

        count, puzzle = test_puzzle(dominoes, rows, cols, regions, "Hard")

        if count == 1:
            print(f"  ✓ UNIQUE! A < B < C < D, D sum={target_d}")
            return puzzle
        elif count > 0 and count <= 3:
            print(f"    D sum={target_d}: {count} solutions")

    return None


if __name__ == "__main__":
    print("=" * 60)
    print("TARGETED SEARCH FOR UNIQUE DOMINO PUZZLES")
    print("=" * 60)

    easy1 = find_easy_1()
    easy2 = find_easy_2()
    medium = find_medium()
    hard = find_hard()

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    results = [
        ("Easy 1", easy1),
        ("Easy 2", easy2),
        ("Medium", medium),
        ("Hard", hard),
    ]

    for name, puzzle in results:
        if puzzle:
            print(f"✓ {name}: FOUND")
        else:
            print(f"✗ {name}: NOT FOUND")
