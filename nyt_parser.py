"""
Parser for NYT Pips puzzle JSON format.
Converts NYT format to our internal Puzzle format.
"""
import json
from typing import Dict, List, Optional, Tuple

from domino_sets import Domino, DominoSet
from grid import Puzzle, Region, PlacedDomino, Orientation, ConstraintType


def parse_nyt_puzzle(nyt_data: dict, difficulty: str = "easy") -> Puzzle:
    """
    Parse NYT Pips puzzle JSON into our Puzzle format.

    Args:
        nyt_data: Full NYT JSON with easy/medium/hard keys, or a single puzzle dict
        difficulty: Which difficulty to parse ("easy", "medium", "hard")

    Returns:
        Puzzle object
    """
    # Handle full response vs single puzzle
    if difficulty in nyt_data:
        puzzle_data = nyt_data[difficulty]
        print_date = nyt_data.get("printDate", "unknown")
    else:
        puzzle_data = nyt_data
        print_date = puzzle_data.get("printDate", "unknown")

    # Parse dominoes
    dominoes = []
    for d in puzzle_data["dominoes"]:
        low, high = sorted(d)  # Ensure low <= high
        dominoes.append(Domino(low, high))

    # Parse regions
    regions = []
    for i, r in enumerate(puzzle_data["regions"]):
        cells = [tuple(idx) for idx in r["indices"]]  # Convert to (row, col) tuples
        region_type = r["type"]
        target = r.get("target")

        # Map NYT types to our ConstraintType
        if region_type == "sum":
            constraint = ConstraintType.SUM
        elif region_type == "equals":
            constraint = ConstraintType.EQUAL
        elif region_type == "empty":
            # Empty means no constraint - we'll use SUM with None target
            constraint = ConstraintType.SUM
            target = None
        elif region_type == "less":
            constraint = ConstraintType.LESS
        elif region_type == "greater":
            constraint = ConstraintType.GREATER
        else:
            constraint = ConstraintType.SUM

        regions.append(Region(
            id=i,
            cells=cells,
            constraint_type=constraint,
            target_value=target
        ))

    # Calculate grid dimensions from all cells
    all_cells = []
    for region in regions:
        all_cells.extend(region.cells)

    if all_cells:
        max_row = max(c[0] for c in all_cells) + 1
        max_col = max(c[1] for c in all_cells) + 1
    else:
        max_row, max_col = 0, 0

    # Parse solution
    solution = []
    for i, placement in enumerate(puzzle_data.get("solution", [])):
        if i >= len(dominoes):
            break

        cell1 = tuple(placement[0])  # (row, col)
        cell2 = tuple(placement[1])  # (row, col)

        # Determine orientation
        if cell1[0] == cell2[0]:  # Same row = horizontal
            orientation = Orientation.HORIZONTAL
            # Ensure left-to-right order
            if cell1[1] > cell2[1]:
                cell1, cell2 = cell2, cell1
            row, col = cell1
        else:  # Same column = vertical
            orientation = Orientation.VERTICAL
            # Ensure top-to-bottom order
            if cell1[0] > cell2[0]:
                cell1, cell2 = cell2, cell1
            row, col = cell1

        # Figure out which end of domino goes where
        # The solution array order matches dominoes array
        domino = dominoes[i]

        solution.append(PlacedDomino(
            domino=domino,
            row=row,
            col=col,
            orientation=orientation
        ))

    # Build puzzle name
    constructor = puzzle_data.get("constructors", "NYT")
    name = f"NYT {difficulty.capitalize()} - {print_date}"

    return Puzzle(
        name=name,
        difficulty=difficulty,
        rows=max_row,
        cols=max_col,
        regions=regions,
        supply=DominoSet(dominoes),
        solution=solution
    )


def parse_nyt_json_file(filepath: str) -> Dict[str, Puzzle]:
    """
    Parse a saved NYT JSON file and return all three puzzles.

    Returns:
        Dict with keys "easy", "medium", "hard" -> Puzzle objects
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    puzzles = {}
    for difficulty in ["easy", "medium", "hard"]:
        if difficulty in data:
            puzzles[difficulty] = parse_nyt_puzzle(data, difficulty)

    return puzzles


def parse_nyt_json_string(json_str: str) -> Dict[str, Puzzle]:
    """
    Parse NYT JSON from a string and return all puzzles.
    """
    data = json.loads(json_str)

    puzzles = {}
    for difficulty in ["easy", "medium", "hard"]:
        if difficulty in data:
            puzzles[difficulty] = parse_nyt_puzzle(data, difficulty)

    return puzzles


if __name__ == "__main__":
    # Test with sample data
    sample = '''{"printDate":"2026-01-06","editor":"Ian Livengood","easy":{"id":531,"backendId":"f647a1d2d67f514aa2e433365e3e93ae","constructors":"Ian Livengood","dominoes":[[3,6],[1,0],[6,2],[1,3],[3,4]],"regions":[{"indices":[[0,0]],"type":"sum","target":1},{"indices":[[0,1],[0,2]],"type":"sum","target":4},{"indices":[[0,3],[0,4],[1,3]],"type":"equals"},{"indices":[[1,0]],"type":"empty"},{"indices":[[1,1],[1,2]],"type":"sum","target":12},{"indices":[[1,4]],"type":"sum","target":1}],"solution":[[[1,3],[1,2]],[[0,0],[0,1]],[[1,1],[1,0]],[[1,4],[0,4]],[[0,3],[0,2]]]},"medium":{"id":555,"backendId":"0583a16fa446567cafcdabdbae3290f0","constructors":"Rodolfo Kurchan","dominoes":[[6,2],[2,5],[1,3],[2,1],[2,4],[4,5],[2,2]],"regions":[{"indices":[[0,5],[1,5]],"type":"sum","target":10},{"indices":[[0,6]],"type":"empty"},{"indices":[[1,3],[1,4],[2,3],[2,4],[2,5],[3,3]],"type":"equals"},{"indices":[[2,6]],"type":"less","target":6},{"indices":[[3,0]],"type":"empty"},{"indices":[[3,1],[3,2]],"type":"equals"},{"indices":[[3,4]],"type":"sum","target":4}],"solution":[[[1,5],[1,4]],[[2,5],[2,6]],[[3,1],[3,0]],[[3,3],[3,2]],[[2,4],[3,4]],[[0,5],[0,6]],[[1,3],[2,3]]]},"hard":{"id":577,"backendId":"56558d6f0a8e5075bd4d0a1fc62f7cb7","constructors":"Rodolfo Kurchan","dominoes":[[2,2],[1,2],[4,4],[4,0],[0,5],[3,5],[6,6],[3,0],[3,2],[2,5],[4,3],[3,6],[5,4],[3,1],[4,6],[5,5]],"regions":[{"indices":[[0,0],[0,1]],"type":"sum","target":12},{"indices":[[0,6],[1,6]],"type":"sum","target":6},{"indices":[[0,7],[1,7]],"type":"sum","target":4},{"indices":[[1,0],[1,1],[1,2],[2,1],[3,1],[4,1]],"type":"equals"},{"indices":[[1,5]],"type":"sum","target":0},{"indices":[[2,0]],"type":"sum","target":0},{"indices":[[2,2],[2,3],[2,4],[2,5],[2,6],[2,7]],"type":"equals"},{"indices":[[3,0],[4,0]],"type":"equals"},{"indices":[[3,3],[3,4]],"type":"equals"},{"indices":[[3,6],[4,6]],"type":"sum","target":5},{"indices":[[3,7]],"type":"sum","target":0},{"indices":[[4,7],[5,7]],"type":"equals"},{"indices":[[5,0],[5,1]],"type":"sum","target":12},{"indices":[[5,6]],"type":"empty"}],"solution":[[[3,3],[3,4]],[[4,7],[4,6]],[[1,1],[1,2]],[[1,0],[2,0]],[[1,5],[2,5]],[[1,6],[2,6]],[[0,0],[0,1]],[[3,6],[3,7]],[[0,6],[0,7]],[[1,7],[2,7]],[[3,1],[3,0]],[[4,0],[5,0]],[[2,2],[2,1]],[[5,6],[5,7]],[[4,1],[5,1]],[[2,3],[2,4]]]}}'''

    puzzles = parse_nyt_json_string(sample)

    for diff, puzzle in puzzles.items():
        print(f"\n=== {puzzle.name} ===")
        print(f"Grid: {puzzle.rows}x{puzzle.cols}")
        print(f"Dominoes: {len(puzzle.supply)}")
        print(f"Regions: {len(puzzle.regions)}")
        for r in puzzle.regions:
            ctype = r.constraint_type.value
            if r.target_value is not None:
                ctype += f"={r.target_value}"
            print(f"  Region {r.id}: {len(r.cells)} cells, {ctype}")

    # Render them
    from renderer import PuzzleRenderer

    for diff, puzzle in puzzles.items():
        renderer = PuzzleRenderer(puzzle)
        filename = f"nyt_{diff}_2026-01-06.pdf"
        renderer.render(filename)
