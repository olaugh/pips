"""
Disjoint Set (Union-Find) data structure for managing puzzle regions.
"""
from typing import Dict, List, Set, Any, Optional


class DisjointSet:
    """
    Union-Find data structure with path compression and union by rank.
    Used to manage connected regions in the puzzle grid.
    """

    def __init__(self):
        self.parent: Dict[Any, Any] = {}
        self.rank: Dict[Any, int] = {}

    def make_set(self, x: Any) -> None:
        """Create a new set containing only x."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x: Any) -> Any:
        """Find the representative of x's set with path compression."""
        if x not in self.parent:
            self.make_set(x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x: Any, y: Any) -> bool:
        """
        Merge the sets containing x and y.
        Returns True if they were in different sets, False if already same set.
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False  # Already in same set

        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        return True

    def connected(self, x: Any, y: Any) -> bool:
        """Check if x and y are in the same set."""
        return self.find(x) == self.find(y)

    def get_sets(self) -> Dict[Any, Set[Any]]:
        """Return all sets as a dict mapping representative -> members."""
        sets: Dict[Any, Set[Any]] = {}
        for x in self.parent:
            root = self.find(x)
            if root not in sets:
                sets[root] = set()
            sets[root].add(x)
        return sets

    def get_set(self, x: Any) -> Set[Any]:
        """Return all members of x's set."""
        root = self.find(x)
        return {y for y in self.parent if self.find(y) == root}

    def set_size(self, x: Any) -> int:
        """Return the size of x's set."""
        return len(self.get_set(x))

    def num_sets(self) -> int:
        """Return the number of disjoint sets."""
        return len(self.get_sets())


class RegionManager:
    """
    Manages puzzle regions using disjoint sets.
    Each region has a constraint (e.g., sum of pips).
    """

    def __init__(self):
        self.ds = DisjointSet()
        self.constraints: Dict[Any, int] = {}  # region_id -> target sum
        self.cell_to_region: Dict[tuple, Any] = {}  # (row, col) -> region_id

    def add_cell(self, row: int, col: int, region_id: Any) -> None:
        """Add a cell to a region."""
        cell = (row, col)
        self.ds.make_set(cell)
        self.cell_to_region[cell] = region_id

    def merge_cells(self, cell1: tuple, cell2: tuple) -> None:
        """Merge two cells into the same region."""
        self.ds.union(cell1, cell2)

    def set_constraint(self, region_id: Any, target_sum: int) -> None:
        """Set the target sum constraint for a region."""
        self.constraints[region_id] = target_sum

    def get_constraint(self, region_id: Any) -> Optional[int]:
        """Get the target sum for a region."""
        return self.constraints.get(region_id)

    def get_region_cells(self, region_id: Any) -> List[tuple]:
        """Get all cells belonging to a region."""
        return [cell for cell, rid in self.cell_to_region.items() if rid == region_id]

    def get_all_regions(self) -> Set[Any]:
        """Get all unique region IDs."""
        return set(self.cell_to_region.values())


if __name__ == "__main__":
    # Demo
    ds = DisjointSet()

    # Create some sets
    for i in range(6):
        ds.make_set(i)

    print("Initial sets:", ds.get_sets())

    # Union some
    ds.union(0, 1)
    ds.union(2, 3)
    ds.union(0, 2)

    print("After unions:", ds.get_sets())
    print("0 and 3 connected?", ds.connected(0, 3))
    print("0 and 4 connected?", ds.connected(0, 4))
