#!/usr/bin/env python3
"""
Domino Pips Puzzle Generator

Generates domino placement puzzles using disjoint sets for region management.
- Easy: 6 dominoes from double-six set
- Medium: 8 dominoes from double-six (subset of double-nine)
- Hard: 10 dominoes from double-nine remainder (7, 8, 9 tiles)

Usage:
    python main.py              # Generate all puzzles
    python main.py --validate   # Validate puzzle uniqueness
    python main.py --generate   # Generate new random puzzles
"""

import argparse
import os
from pathlib import Path

from domino_sets import DominoSet
from puzzles import (
    get_all_puzzles,
    validate_all_puzzles,
    PuzzleGenerator,
    create_easy_puzzle_1,
    create_easy_puzzle_2,
    create_medium_puzzle,
    create_hard_puzzle,
)
from renderer import PuzzleRenderer
from solver import verify_puzzle_uniqueness


def render_all_puzzles(output_dir: str = "output"):
    """Render all pre-defined puzzles to PDF."""
    os.makedirs(output_dir, exist_ok=True)

    puzzles = get_all_puzzles()

    for puzzle in puzzles:
        # Validate first
        is_unique, count = verify_puzzle_uniqueness(puzzle)
        status = "✓" if is_unique else f"✗ ({count} solutions)"
        print(f"Rendering: {puzzle.name} [{puzzle.difficulty}] {status}")

        # Generate filename
        safe_name = puzzle.name.lower().replace(" ", "_")
        filename = f"{safe_name}_{puzzle.difficulty}.pdf"
        filepath = os.path.join(output_dir, filename)

        # Render
        renderer = PuzzleRenderer(puzzle)
        renderer.render(filepath, include_solution=True)

    print(f"\nAll puzzles saved to: {output_dir}/")


def generate_random_puzzles(output_dir: str = "output"):
    """Generate new random puzzles with unique solutions."""
    os.makedirs(output_dir, exist_ok=True)

    configs = [
        ("Random Easy 1", "easy", DominoSet.double_six(), 6),
        ("Random Easy 2", "easy", DominoSet.double_six(), 6),
        ("Random Medium", "medium", DominoSet.double_six(), 8),
        ("Random Hard", "hard", DominoSet.double_nine_remainder(), 10),
    ]

    for name, difficulty, domino_set, num_dominoes in configs:
        print(f"\nGenerating: {name}")
        gen = PuzzleGenerator(domino_set)
        puzzle = gen.generate_unique_puzzle(name, difficulty, num_dominoes)

        if puzzle:
            safe_name = name.lower().replace(" ", "_")
            filename = f"{safe_name}.pdf"
            filepath = os.path.join(output_dir, filename)

            renderer = PuzzleRenderer(puzzle)
            renderer.render(filepath, include_solution=True)
        else:
            print(f"  Failed to generate unique puzzle")


def display_puzzle_info():
    """Display information about the puzzle sets."""
    print("=" * 60)
    print("DOMINO PIPS PUZZLE GENERATOR")
    print("=" * 60)

    print("\n📦 DOMINO SETS:")
    print("-" * 40)

    d6 = DominoSet.double_six()
    print(f"  Double-Six:      {len(d6)} tiles (0-6)")

    d9 = DominoSet.double_nine()
    print(f"  Double-Nine:     {len(d9)} tiles (0-9)")

    remainder = DominoSet.double_nine_remainder()
    print(f"  D9 Remainder:    {len(remainder)} tiles (has 7, 8, or 9)")

    print("\n🧩 PUZZLE DIFFICULTIES:")
    print("-" * 40)
    print("  Easy:   6 dominoes, single-domino regions")
    print("  Medium: 8 dominoes, some merged regions")
    print("  Hard:   10 dominoes from high-pip set, complex regions")

    print("\n📄 PRE-DEFINED PUZZLES:")
    print("-" * 40)
    puzzles = get_all_puzzles()
    for p in puzzles:
        print(f"  • {p.name} ({p.difficulty}): {len(p.supply)} tiles, {len(p.regions)} regions")


def main():
    parser = argparse.ArgumentParser(
        description="Domino Pips Puzzle Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Render all pre-defined puzzles
  python main.py --validate         # Check puzzle uniqueness
  python main.py --generate         # Generate new random puzzles
  python main.py --info             # Display puzzle information
        """
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate that all puzzles have unique solutions'
    )
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate new random puzzles (may take time)'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Display information about puzzle sets'
    )
    parser.add_argument(
        '--output', '-o',
        default='output',
        help='Output directory for PDF files (default: output)'
    )

    args = parser.parse_args()

    if args.info:
        display_puzzle_info()
    elif args.validate:
        print("Validating puzzle uniqueness...\n")
        validate_all_puzzles()
    elif args.generate:
        print("Generating random puzzles with unique solutions...")
        generate_random_puzzles(args.output)
    else:
        print("Rendering pre-defined puzzles...\n")
        render_all_puzzles(args.output)


if __name__ == "__main__":
    main()
