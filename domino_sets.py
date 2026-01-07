"""
Domino set definitions and utilities.
"""
from dataclasses import dataclass
from typing import List, Set, Tuple
import random


@dataclass(frozen=True)
class Domino:
    """A domino tile with two pip values."""
    low: int
    high: int

    def __post_init__(self):
        # Ensure low <= high for canonical form
        if self.low > self.high:
            object.__setattr__(self, 'low', self.high)
            object.__setattr__(self, 'high', self.low)

    @property
    def pips(self) -> int:
        """Total pip count."""
        return self.low + self.high

    @property
    def is_double(self) -> bool:
        """Check if this is a double."""
        return self.low == self.high

    def __repr__(self):
        return f"[{self.low}|{self.high}]"

    def __hash__(self):
        return hash((self.low, self.high))

    def __eq__(self, other):
        if not isinstance(other, Domino):
            return False
        return self.low == other.low and self.high == other.high


class DominoSet:
    """A collection of dominoes."""

    def __init__(self, dominoes: List[Domino] = None):
        self.dominoes = list(dominoes) if dominoes else []

    @classmethod
    def double_six(cls) -> 'DominoSet':
        """Create a standard double-six set (28 tiles, 0-6)."""
        dominoes = []
        for i in range(7):
            for j in range(i, 7):
                dominoes.append(Domino(i, j))
        return cls(dominoes)

    @classmethod
    def double_nine(cls) -> 'DominoSet':
        """Create a double-nine set (55 tiles, 0-9)."""
        dominoes = []
        for i in range(10):
            for j in range(i, 10):
                dominoes.append(Domino(i, j))
        return cls(dominoes)

    @classmethod
    def double_nine_remainder(cls) -> 'DominoSet':
        """
        Create the remainder of double-nine after removing double-six.
        These are tiles with at least one side >= 7.
        (27 tiles)
        """
        dominoes = []
        for i in range(10):
            for j in range(i, 10):
                if i >= 7 or j >= 7:
                    dominoes.append(Domino(i, j))
        return cls(dominoes)

    def subset(self, n: int) -> 'DominoSet':
        """Return a random subset of n dominoes."""
        if n > len(self.dominoes):
            raise ValueError(f"Cannot select {n} from {len(self.dominoes)} dominoes")
        return DominoSet(random.sample(self.dominoes, n))

    def shuffle(self) -> 'DominoSet':
        """Return a new set with shuffled order."""
        shuffled = self.dominoes.copy()
        random.shuffle(shuffled)
        return DominoSet(shuffled)

    def __len__(self):
        return len(self.dominoes)

    def __iter__(self):
        return iter(self.dominoes)

    def __repr__(self):
        return f"DominoSet({len(self.dominoes)} tiles)"

    def display(self):
        """Pretty print the domino set."""
        for i, d in enumerate(self.dominoes):
            print(f"{d}", end="  ")
            if (i + 1) % 7 == 0:
                print()
        print()


if __name__ == "__main__":
    print("Double-Six Set (28 tiles):")
    d6 = DominoSet.double_six()
    d6.display()

    print("\nDouble-Nine Set (55 tiles):")
    d9 = DominoSet.double_nine()
    d9.display()

    print("\nDouble-Nine Remainder (27 tiles with 7, 8, or 9):")
    remainder = DominoSet.double_nine_remainder()
    remainder.display()
