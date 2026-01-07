"""
Backtracking solver for domino placement puzzles.
Supports multiple constraint types: Sum, Equal, Greater, Less.
"""
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from copy import deepcopy

from domino_sets import Domino, DominoSet
from grid import Puzzle, Region, PlacedDomino, Orientation, ConstraintType


@dataclass
class SolverState:
    """Current state of the solver."""
    placed: List[PlacedDomino]
    used_dominoes: Set[Domino]
    filled_cells: Set[Tuple[int, int]]
    # Track which pip value is at each cell for constraint checking
    cell_values: Dict[Tuple[int, int], int]


class Solver:
    """
    Backtracking solver that places dominoes to satisfy region constraints.
    """

    def __init__(self, puzzle: Puzzle, max_solutions: int = 2):
        self.puzzle = puzzle
        self.max_solutions = max_solutions
        self.solutions: List[List[PlacedDomino]] = []

        # Build lookup structures
        self.cell_to_region: Dict[Tuple[int, int], int] = {}
        for region in puzzle.regions:
            for cell in region.cells:
                self.cell_to_region[cell] = region.id

        self.region_by_id: Dict[int, Region] = {r.id: r for r in puzzle.regions}

        # All cells that need to be filled
        self.all_cells: Set[Tuple[int, int]] = set()
        for region in puzzle.regions:
            self.all_cells.update(region.cells)

    def get_adjacent_cells(self, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get adjacent cells within the grid."""
        r, c = cell
        adjacent = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            neighbor = (nr, nc)
            if neighbor in self.all_cells:
                adjacent.append(neighbor)
        return adjacent

    def get_region_sum(self, region_id: int, cell_values: Dict[Tuple[int, int], int]) -> int:
        """Calculate sum of pips in a region."""
        region = self.region_by_id[region_id]
        total = 0
        for cell in region.cells:
            if cell in cell_values:
                total += cell_values[cell]
        return total

    def get_region_values(self, region_id: int, cell_values: Dict[Tuple[int, int], int]) -> List[int]:
        """Get all pip values in a region."""
        region = self.region_by_id[region_id]
        values = []
        for cell in region.cells:
            if cell in cell_values:
                values.append(cell_values[cell])
        return values

    def is_region_complete(self, region_id: int, filled_cells: Set[Tuple[int, int]]) -> bool:
        """Check if all cells in region are filled."""
        region = self.region_by_id[region_id]
        return all(cell in filled_cells for cell in region.cells)

    def check_constraint(self, region: Region, cell_values: Dict[Tuple[int, int], int],
                        filled_cells: Set[Tuple[int, int]], partial_ok: bool = True) -> bool:
        """
        Check if a region's constraint is satisfied.
        If partial_ok=True, incomplete regions pass (for mid-solve checking).
        """
        is_complete = self.is_region_complete(region.id, filled_cells)

        if region.constraint_type == ConstraintType.SUM:
            current_sum = self.get_region_sum(region.id, cell_values)
            if is_complete:
                return current_sum == region.target_value
            else:
                # Partial: sum so far shouldn't exceed target
                return partial_ok and current_sum <= region.target_value

        elif region.constraint_type == ConstraintType.EQUAL:
            values = self.get_region_values(region.id, cell_values)
            if not values:
                return True
            first = values[0]
            if not all(v == first for v in values):
                return False
            return True  # All values so far are equal

        elif region.constraint_type == ConstraintType.GREATER:
            if not is_complete:
                return partial_ok  # Can't check until complete
            linked = self.region_by_id[region.linked_region_id]
            if not self.is_region_complete(linked.id, filled_cells):
                return partial_ok
            my_sum = self.get_region_sum(region.id, cell_values)
            their_sum = self.get_region_sum(linked.id, cell_values)
            return my_sum > their_sum

        elif region.constraint_type == ConstraintType.LESS:
            if not is_complete:
                return partial_ok
            linked = self.region_by_id[region.linked_region_id]
            if not self.is_region_complete(linked.id, filled_cells):
                return partial_ok
            my_sum = self.get_region_sum(region.id, cell_values)
            their_sum = self.get_region_sum(linked.id, cell_values)
            return my_sum < their_sum

        return True

    def solve(self) -> int:
        """
        Solve the puzzle and return number of unique solutions.
        Solutions are deduplicated by which dominoes are in which regions.
        """
        self.solutions = []
        self.seen_assignments: Set[frozenset] = set()
        initial_state = SolverState(
            placed=[],
            used_dominoes=set(),
            filled_cells=set(),
            cell_values={}
        )
        self._backtrack(initial_state)
        return len(self.solutions)

    def _get_solution_signature(self, state: SolverState) -> frozenset:
        """
        Get a signature for a solution based on pip values at each cell.
        Two solutions are the same if they result in identical pip placements.
        """
        return frozenset(state.cell_values.items())

    def _backtrack(self, state: SolverState) -> None:
        """Recursive backtracking."""
        if len(self.solutions) >= self.max_solutions:
            return

        # Check if solved
        if len(state.filled_cells) == len(self.all_cells):
            # Verify all constraints
            if self._verify_all_constraints(state):
                # Deduplicate by domino-to-region assignment
                sig = self._get_solution_signature(state)
                if sig not in self.seen_assignments:
                    self.seen_assignments.add(sig)
                    self.solutions.append(deepcopy(state.placed))
            return

        # Find next unfilled cell
        cell = self._choose_cell(state)
        if cell is None:
            return

        # Try placing each unused domino
        for domino in self.puzzle.supply.dominoes:
            if domino in state.used_dominoes:
                continue

            # Try each adjacent empty cell
            for adj in self.get_adjacent_cells(cell):
                if adj in state.filled_cells:
                    continue

                # Both cells must be in valid regions (but can be DIFFERENT regions!)
                if cell not in self.cell_to_region or adj not in self.cell_to_region:
                    continue

                # Try both orientations of the domino
                orientations = [(domino.low, domino.high)]
                if domino.low != domino.high:
                    orientations.append((domino.high, domino.low))

                for pip_at_cell, pip_at_adj in orientations:
                    # Create new state
                    new_cell_values = dict(state.cell_values)
                    new_cell_values[cell] = pip_at_cell
                    new_cell_values[adj] = pip_at_adj

                    # Check constraints for affected regions
                    valid = True
                    affected_regions = {self.cell_to_region[cell], self.cell_to_region[adj]}
                    new_filled = state.filled_cells | {cell, adj}

                    for rid in affected_regions:
                        region = self.region_by_id[rid]
                        if not self.check_constraint(region, new_cell_values, new_filled, partial_ok=True):
                            valid = False
                            break

                    if not valid:
                        continue

                    # Determine grid orientation for PlacedDomino
                    if cell[0] == adj[0]:  # Same row = horizontal
                        if cell[1] < adj[1]:
                            r, c = cell
                        else:
                            r, c = adj
                        orient = Orientation.HORIZONTAL
                    else:  # Same column = vertical
                        if cell[0] < adj[0]:
                            r, c = cell
                        else:
                            r, c = adj
                        orient = Orientation.VERTICAL

                    placement = PlacedDomino(domino, r, c, orient)
                    new_state = SolverState(
                        placed=state.placed + [placement],
                        used_dominoes=state.used_dominoes | {domino},
                        filled_cells=new_filled,
                        cell_values=new_cell_values
                    )

                    self._backtrack(new_state)

                    if len(self.solutions) >= self.max_solutions:
                        return

    def _choose_cell(self, state: SolverState) -> Optional[Tuple[int, int]]:
        """Choose next unfilled cell using MRV heuristic."""
        unfilled = self.all_cells - state.filled_cells
        if not unfilled:
            return None

        # Prefer cells in regions with fewer unfilled cells (more constrained)
        def region_unfilled_count(cell):
            rid = self.cell_to_region[cell]
            region = self.region_by_id[rid]
            return sum(1 for c in region.cells if c not in state.filled_cells)

        return min(unfilled, key=region_unfilled_count)

    def _verify_all_constraints(self, state: SolverState) -> bool:
        """Verify all region constraints are satisfied."""
        for region in self.puzzle.regions:
            if not self.check_constraint(region, state.cell_values, state.filled_cells, partial_ok=False):
                return False
        return True

    def get_solution(self) -> Optional[List[PlacedDomino]]:
        """Return first solution if exists."""
        if self.solutions:
            return self.solutions[0]
        return None

    def is_unique(self) -> bool:
        """Check if puzzle has exactly one solution."""
        return len(self.solutions) == 1


def verify_puzzle_uniqueness(puzzle: Puzzle) -> Tuple[bool, int]:
    """
    Verify a puzzle has a unique solution.
    Returns (is_unique, solution_count).
    """
    solver = Solver(puzzle, max_solutions=2)
    count = solver.solve()
    return count == 1, count


if __name__ == "__main__":
    from grid import GridGenerator
    from domino_sets import DominoSet

    d6 = DominoSet.double_six()
    # Test would go here
