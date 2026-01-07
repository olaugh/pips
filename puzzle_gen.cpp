/**
 * Multithreaded domino puzzle generator.
 * Searches for puzzles with unique solutions.
 * Compile: clang++ -std=c++17 -O3 -pthread puzzle_gen.cpp -o puzzle_gen
 */

#include <iostream>
#include <vector>
#include <array>
#include <set>
#include <map>
#include <algorithm>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>
#include <optional>
#include <sstream>

using namespace std;

// Domino representation
struct Domino {
    int low, high;
    int pips() const { return low + high; }
    bool operator==(const Domino& o) const { return low == o.low && high == o.high; }
    bool operator<(const Domino& o) const {
        if (low != o.low) return low < o.low;
        return high < o.high;
    }
    string str() const {
        return "[" + to_string(low) + "|" + to_string(high) + "]";
    }
};

// Cell position
using Cell = pair<int, int>;

// Constraint types
enum class ConstraintType { SUM, EQUAL, LESS, GREATER };

// Region definition
struct Region {
    int id;
    vector<Cell> cells;
    ConstraintType type;
    int target_value = -1;       // For SUM
    int linked_region_id = -1;   // For LESS/GREATER
};

// Placed domino
struct PlacedDomino {
    Domino domino;
    int row, col;
    bool horizontal;

    Cell cell1() const { return {row, col}; }
    Cell cell2() const {
        return horizontal ? Cell{row, col + 1} : Cell{row + 1, col};
    }
};

// Solver state
struct SolverState {
    vector<PlacedDomino> placed;
    set<Domino> used_dominoes;
    set<Cell> filled_cells;
    map<Cell, int> cell_values;
};

// Global for thread coordination
mutex result_mutex;
atomic<bool> found_easy1{false};
atomic<bool> found_easy2{false};
atomic<bool> found_medium{false};
atomic<bool> found_hard{false};
atomic<int> total_attempts{0};

// Result storage
struct PuzzleResult {
    vector<Domino> dominoes;
    vector<Region> regions;
    int rows, cols;
    string name;
    vector<PlacedDomino> solution;
};

optional<PuzzleResult> easy1_result;
optional<PuzzleResult> easy2_result;
optional<PuzzleResult> medium_result;
optional<PuzzleResult> hard_result;

// Forward declarations
void print_result(const string& name, const optional<PuzzleResult>& result);

// Solver class
class Solver {
public:
    vector<Domino> dominoes;
    vector<Region> regions;
    int rows, cols;
    int max_solutions;

    map<Cell, int> cell_to_region;
    map<int, Region*> region_by_id;
    set<Cell> all_cells;

    vector<SolverState> solutions;
    set<map<Cell, int>> seen_signatures;

    Solver(const vector<Domino>& doms, const vector<Region>& regs, int r, int c, int max_sol = 2)
        : dominoes(doms), regions(regs), rows(r), cols(c), max_solutions(max_sol) {

        for (auto& reg : regions) {
            for (const auto& cell : reg.cells) {
                cell_to_region[cell] = reg.id;
                all_cells.insert(cell);
            }
            region_by_id[reg.id] = const_cast<Region*>(&reg);
        }
        // Fix region pointers after regions is done being modified
        for (auto& reg : regions) {
            region_by_id[reg.id] = &reg;
        }
    }

    int get_region_sum(int region_id, const map<Cell, int>& cell_values) {
        int total = 0;
        for (const auto& cell : region_by_id[region_id]->cells) {
            auto it = cell_values.find(cell);
            if (it != cell_values.end()) {
                total += it->second;
            }
        }
        return total;
    }

    vector<int> get_region_values(int region_id, const map<Cell, int>& cell_values) {
        vector<int> vals;
        for (const auto& cell : region_by_id[region_id]->cells) {
            auto it = cell_values.find(cell);
            if (it != cell_values.end()) {
                vals.push_back(it->second);
            }
        }
        return vals;
    }

    bool is_region_complete(int region_id, const set<Cell>& filled) {
        for (const auto& cell : region_by_id[region_id]->cells) {
            if (filled.find(cell) == filled.end()) return false;
        }
        return true;
    }

    bool check_constraint(const Region& region, const map<Cell, int>& cell_values,
                         const set<Cell>& filled, bool partial_ok = true) {
        bool complete = is_region_complete(region.id, filled);

        if (region.type == ConstraintType::SUM) {
            int sum = get_region_sum(region.id, cell_values);
            if (complete) return sum == region.target_value;
            return partial_ok && sum <= region.target_value;
        }
        else if (region.type == ConstraintType::EQUAL) {
            auto vals = get_region_values(region.id, cell_values);
            if (vals.empty()) return true;
            int first = vals[0];
            for (int v : vals) {
                if (v != first) return false;
            }
            return true;
        }
        else if (region.type == ConstraintType::LESS) {
            if (!complete) return partial_ok;
            if (!is_region_complete(region.linked_region_id, filled)) return partial_ok;
            int my_sum = get_region_sum(region.id, cell_values);
            int their_sum = get_region_sum(region.linked_region_id, cell_values);
            return my_sum < their_sum;
        }
        else if (region.type == ConstraintType::GREATER) {
            if (!complete) return partial_ok;
            if (!is_region_complete(region.linked_region_id, filled)) return partial_ok;
            int my_sum = get_region_sum(region.id, cell_values);
            int their_sum = get_region_sum(region.linked_region_id, cell_values);
            return my_sum > their_sum;
        }
        return true;
    }

    vector<Cell> get_adjacent(Cell cell) {
        vector<Cell> adj;
        int r = cell.first, c = cell.second;
        Cell candidates[] = {{r-1,c}, {r+1,c}, {r,c-1}, {r,c+1}};
        for (auto& n : candidates) {
            if (all_cells.count(n)) adj.push_back(n);
        }
        return adj;
    }

    Cell choose_cell(const SolverState& state) {
        Cell best = {-1, -1};
        int min_unfilled = INT_MAX;

        for (const auto& cell : all_cells) {
            if (state.filled_cells.count(cell)) continue;

            int rid = cell_to_region[cell];
            int unfilled = 0;
            for (const auto& c : region_by_id[rid]->cells) {
                if (!state.filled_cells.count(c)) unfilled++;
            }
            if (unfilled < min_unfilled) {
                min_unfilled = unfilled;
                best = cell;
            }
        }
        return best;
    }

    void backtrack(SolverState& state) {
        if (solutions.size() >= (size_t)max_solutions) return;

        if (state.filled_cells.size() == all_cells.size()) {
            // Verify all constraints
            for (const auto& region : regions) {
                if (!check_constraint(region, state.cell_values, state.filled_cells, false)) {
                    return;
                }
            }
            // Deduplicate
            if (seen_signatures.insert(state.cell_values).second) {
                solutions.push_back(state);
            }
            return;
        }

        Cell cell = choose_cell(state);
        if (cell.first < 0) return;

        for (const auto& domino : dominoes) {
            if (state.used_dominoes.count(domino)) continue;

            for (const auto& adj : get_adjacent(cell)) {
                if (state.filled_cells.count(adj)) continue;
                if (!cell_to_region.count(cell) || !cell_to_region.count(adj)) continue;

                // Try both orientations
                vector<pair<int,int>> orientations = {{domino.low, domino.high}};
                if (domino.low != domino.high) {
                    orientations.push_back({domino.high, domino.low});
                }

                for (auto [pip_cell, pip_adj] : orientations) {
                    map<Cell, int> new_values = state.cell_values;
                    new_values[cell] = pip_cell;
                    new_values[adj] = pip_adj;

                    set<Cell> new_filled = state.filled_cells;
                    new_filled.insert(cell);
                    new_filled.insert(adj);

                    // Check constraints
                    bool valid = true;
                    set<int> affected = {cell_to_region[cell], cell_to_region[adj]};
                    for (int rid : affected) {
                        if (!check_constraint(*region_by_id[rid], new_values, new_filled, true)) {
                            valid = false;
                            break;
                        }
                    }
                    if (!valid) continue;

                    // Create placement
                    bool horiz = (cell.first == adj.first);
                    int pr = min(cell.first, adj.first);
                    int pc = min(cell.second, adj.second);
                    PlacedDomino placement{domino, pr, pc, horiz};

                    SolverState new_state;
                    new_state.placed = state.placed;
                    new_state.placed.push_back(placement);
                    new_state.used_dominoes = state.used_dominoes;
                    new_state.used_dominoes.insert(domino);
                    new_state.filled_cells = new_filled;
                    new_state.cell_values = new_values;

                    backtrack(new_state);

                    if (solutions.size() >= (size_t)max_solutions) return;
                }
            }
        }
    }

    int solve() {
        solutions.clear();
        seen_signatures.clear();
        SolverState initial;
        backtrack(initial);
        return solutions.size();
    }
};

// Test a puzzle configuration
int test_puzzle(const vector<Domino>& dominoes, int rows, int cols,
                vector<Region> regions, vector<PlacedDomino>* solution_out = nullptr) {
    Solver solver(dominoes, regions, rows, cols, 3);
    int count = solver.solve();
    if (count == 1 && solution_out) {
        *solution_out = solver.solutions[0].placed;
    }
    return count;
}

// Generate all combinations of n items from vec
template<typename T>
void combinations(const vector<T>& vec, int n, int start,
                 vector<T>& current, vector<vector<T>>& result) {
    if ((int)current.size() == n) {
        result.push_back(current);
        return;
    }
    for (int i = start; i < (int)vec.size(); i++) {
        current.push_back(vec[i]);
        combinations(vec, n, i + 1, current, result);
        current.pop_back();
    }
}

template<typename T>
vector<vector<T>> get_combinations(const vector<T>& vec, int n) {
    vector<vector<T>> result;
    vector<T> current;
    combinations(vec, n, 0, current, result);
    return result;
}

// Search functions for each difficulty
void search_easy_2x4_sums(int thread_id, const vector<Domino>& all_d6) {
    // 2x4 grid with 4 dominoes - try inequality chain with 4 regions
    int rows = 2, cols = 4;

    // 4 regions of 2 cells each with inequality chain
    vector<Cell> region0 = {{0,0}, {0,1}};
    vector<Cell> region1 = {{0,2}, {0,3}};
    vector<Cell> region2 = {{1,0}, {1,1}};
    vector<Cell> region3 = {{1,2}, {1,3}};

    auto combos = get_combinations(all_d6, 4);

    for (size_t i = thread_id; i < combos.size(); i += 4) {
        if (found_easy1.load()) return;

        const auto& dominoes = combos[i];
        int total = 0;
        for (const auto& d : dominoes) total += d.pips();

        // Try inequality chain A < B < C < D with different sum targets for D
        for (int target3 = 1; target3 <= 12; target3++) {
            if (found_easy1.load()) return;
            total_attempts++;

            vector<Region> regions = {
                {0, region0, ConstraintType::LESS, -1, 1},
                {1, region1, ConstraintType::LESS, -1, 2},
                {2, region2, ConstraintType::LESS, -1, 3},
                {3, region3, ConstraintType::SUM, target3, -1}
            };

            vector<PlacedDomino> solution;
            int count = test_puzzle(dominoes, rows, cols, regions, &solution);

            if (count == 1) {
                lock_guard<mutex> lock(result_mutex);
                if (!found_easy1.load()) {
                    found_easy1 = true;
                    easy1_result = PuzzleResult{
                        dominoes, regions, rows, cols, "Easy1_IneqChain", solution
                    };
                    cout << "[Thread " << thread_id << "] Found Easy1! Attempts: "
                         << total_attempts.load() << endl;
                    print_result("EASY PUZZLE 1", easy1_result);
                    cout << flush;
                }
                return;
            }
        }
    }
}

void search_easy_3cell_regions(int thread_id, const vector<Domino>& pool) {
    // 2x4 grid with 3-cell regions (forces spanning)
    int rows = 2, cols = 4;

    vector<Cell> region0 = {{0,0}, {0,1}, {1,0}};  // 3 cells
    vector<Cell> region1 = {{0,2}, {0,3}, {1,3}};  // 3 cells
    vector<Cell> region2 = {{1,1}, {1,2}};          // 2 cells

    auto combos = get_combinations(pool, 4);

    for (size_t i = thread_id; i < combos.size(); i += 4) {
        if (found_easy2.load()) return;

        const auto& dominoes = combos[i];
        int total = 0;
        for (const auto& d : dominoes) total += d.pips();

        // Try different sum combinations
        for (int t0 = 0; t0 <= total; t0++) {
            for (int t1 = 0; t1 <= total - t0; t1++) {
                if (found_easy2.load()) return;

                int t2 = total - t0 - t1;
                total_attempts++;

                vector<Region> regions = {
                    {0, region0, ConstraintType::SUM, t0, -1},
                    {1, region1, ConstraintType::SUM, t1, -1},
                    {2, region2, ConstraintType::SUM, t2, -1}
                };

                vector<PlacedDomino> solution;
                int count = test_puzzle(dominoes, rows, cols, regions, &solution);

                if (count == 1) {
                    lock_guard<mutex> lock(result_mutex);
                    if (!found_easy2.load()) {
                        found_easy2 = true;
                        easy2_result = PuzzleResult{
                            dominoes, regions, rows, cols, "Easy2_ForcedSpan", solution
                        };
                        cout << "[Thread " << thread_id << "] Found Easy2! Attempts: "
                             << total_attempts.load() << endl;
                        print_result("EASY PUZZLE 2", easy2_result);
                        cout << flush;
                    }
                    return;
                }
            }
        }
    }
}

void search_medium(int thread_id, const vector<Domino>& all_d6) {
    // 3x4 grid with 6 dominoes - use 6 regions of 2 cells with inequality chain
    int rows = 3, cols = 4;

    // 6 regions of 2 cells each - horizontal pairs
    vector<Cell> region0 = {{0,0}, {0,1}};
    vector<Cell> region1 = {{0,2}, {0,3}};
    vector<Cell> region2 = {{1,0}, {1,1}};
    vector<Cell> region3 = {{1,2}, {1,3}};
    vector<Cell> region4 = {{2,0}, {2,1}};
    vector<Cell> region5 = {{2,2}, {2,3}};

    auto combos = get_combinations(all_d6, 6);

    for (size_t i = thread_id; i < combos.size(); i += 4) {
        if (found_medium.load()) return;

        const auto& dominoes = combos[i];

        // Get all domino sums
        vector<int> sums;
        int total = 0;
        for (const auto& d : dominoes) {
            sums.push_back(d.pips());
            total += d.pips();
        }

        // Sort sums to check if they're distinct
        vector<int> sorted_sums = sums;
        sort(sorted_sums.begin(), sorted_sums.end());

        // For inequality chain to work well, we want distinct sums
        bool distinct = true;
        for (size_t j = 1; j < sorted_sums.size(); j++) {
            if (sorted_sums[j] == sorted_sums[j-1]) {
                distinct = false;
                break;
            }
        }
        if (!distinct) continue;

        // Inequality chain: 0 < 1 < 2 < 3 < 4 < 5 with sum constraint on 5
        int max_sum = sorted_sums.back();
        for (int target5 = max_sum; target5 <= max_sum + 2; target5++) {
            if (found_medium.load()) return;
            total_attempts++;

            vector<Region> regions = {
                {0, region0, ConstraintType::LESS, -1, 1},
                {1, region1, ConstraintType::LESS, -1, 2},
                {2, region2, ConstraintType::LESS, -1, 3},
                {3, region3, ConstraintType::LESS, -1, 4},
                {4, region4, ConstraintType::LESS, -1, 5},
                {5, region5, ConstraintType::SUM, target5, -1}
            };

            vector<PlacedDomino> solution;
            int count = test_puzzle(dominoes, rows, cols, regions, &solution);

            if (count == 1) {
                lock_guard<mutex> lock(result_mutex);
                if (!found_medium.load()) {
                    found_medium = true;
                    medium_result = PuzzleResult{
                        dominoes, regions, rows, cols, "Medium_InequalityChain", solution
                    };
                    cout << "[Thread " << thread_id << "] Found Medium! Attempts: "
                         << total_attempts.load() << endl;
                    print_result("MEDIUM PUZZLE", medium_result);
                    cout << flush;
                }
                return;
            }
        }
    }
}

void search_hard(int thread_id, const vector<Domino>& d9_remainder, const vector<Domino>& unused_d6) {
    // 2x8 grid with 8 dominoes - simpler layout, faster to search
    // Using 4 regions of 4 cells with inequality chain
    int rows = 2, cols = 8;

    // 4 regions of 4 cells each (like Medium's 3-region version)
    vector<Cell> region0 = {{0,0}, {0,1}, {1,0}, {1,1}};
    vector<Cell> region1 = {{0,2}, {0,3}, {1,2}, {1,3}};
    vector<Cell> region2 = {{0,4}, {0,5}, {1,4}, {1,5}};
    vector<Cell> region3 = {{0,6}, {0,7}, {1,6}, {1,7}};

    auto combos = get_combinations(d9_remainder, 8);

    for (size_t i = thread_id; i < combos.size(); i += 4) {
        if (found_hard.load()) return;

        const auto& dominoes = combos[i];
        int total = 0;
        for (const auto& d : dominoes) total += d.pips();

        // Inequality chain A < B < C < D with sum on D
        for (int target3 = 1; target3 < total; target3++) {
            if (found_hard.load()) return;
            total_attempts++;

            vector<Region> regions = {
                {0, region0, ConstraintType::LESS, -1, 1},
                {1, region1, ConstraintType::LESS, -1, 2},
                {2, region2, ConstraintType::LESS, -1, 3},
                {3, region3, ConstraintType::SUM, target3, -1}
            };

            vector<PlacedDomino> solution;
            int count = test_puzzle(dominoes, rows, cols, regions, &solution);

            if (count == 1) {
                lock_guard<mutex> lock(result_mutex);
                if (!found_hard.load()) {
                    found_hard = true;
                    hard_result = PuzzleResult{
                        dominoes, regions, rows, cols, "Hard_D9Remainder", solution
                    };
                    cout << "[Thread " << thread_id << "] Found Hard! Attempts: "
                         << total_attempts.load() << endl;
                    print_result("HARD PUZZLE", hard_result);
                    cout << flush;
                }
                return;
            }
        }
    }
}

// Unicode box drawing characters
const string BOX_TL = "┌";
const string BOX_TR = "┐";
const string BOX_BL = "└";
const string BOX_BR = "┘";
const string BOX_H = "─";
const string BOX_V = "│";
const string BOX_CROSS = "┼";
const string BOX_T_DOWN = "┬";
const string BOX_T_UP = "┴";
const string BOX_T_RIGHT = "├";
const string BOX_T_LEFT = "┤";

// Thick box drawing for region boundaries
const string THICK_H = "━";
const string THICK_V = "┃";

void draw_puzzle_grid(const PuzzleResult& result) {
    int rows = result.rows;
    int cols = result.cols;

    // Build cell-to-region map
    map<Cell, int> cell_region;
    for (const auto& r : result.regions) {
        for (const auto& c : r.cells) {
            cell_region[c] = r.id;
        }
    }

    // Build cell-to-pip map from solution
    map<Cell, int> cell_pip;
    for (const auto& p : result.solution) {
        Cell c1 = p.cell1();
        Cell c2 = p.cell2();
        cell_pip[c1] = p.domino.low;
        cell_pip[c2] = p.domino.high;
    }

    // Region labels
    map<int, string> region_label;
    for (const auto& r : result.regions) {
        if (r.type == ConstraintType::SUM) {
            region_label[r.id] = to_string(r.target_value);
        } else if (r.type == ConstraintType::LESS) {
            region_label[r.id] = "<" + to_string(r.linked_region_id);
        } else if (r.type == ConstraintType::EQUAL) {
            region_label[r.id] = "=";
        } else if (r.type == ConstraintType::GREATER) {
            region_label[r.id] = ">" + to_string(r.linked_region_id);
        }
    }

    // Draw grid
    int cell_width = 5;
    string h_line(cell_width, '-');

    // Top border
    cout << "  ";
    for (int c = 0; c < cols; c++) {
        cout << "+" << h_line;
    }
    cout << "+" << endl;

    for (int r = 0; r < rows; r++) {
        // Cell content row
        cout << "  ";
        for (int c = 0; c < cols; c++) {
            Cell cell = {r, c};
            bool thick_left = (c == 0) ||
                (cell_region.count({r, c-1}) && cell_region[{r, c-1}] != cell_region[cell]);

            cout << (thick_left ? "|" : "|");

            // Show region label in top-left cell of region, pip value otherwise
            bool show_label = true;
            int rid = cell_region[cell];
            for (const auto& cr : result.regions[rid].cells) {
                if (cr.first < r || (cr.first == r && cr.second < c)) {
                    show_label = false;
                    break;
                }
            }

            string content;
            if (show_label && region_label.count(rid)) {
                content = region_label[rid];
            } else if (cell_pip.count(cell)) {
                content = to_string(cell_pip[cell]);
            } else {
                content = " ";
            }

            // Center content in cell
            int pad_left = (cell_width - content.length()) / 2;
            int pad_right = cell_width - content.length() - pad_left;
            cout << string(pad_left, ' ') << content << string(pad_right, ' ');
        }
        cout << "|" << endl;

        // Horizontal line between rows
        cout << "  ";
        for (int c = 0; c < cols; c++) {
            Cell above = {r, c};
            Cell below = {r + 1, c};
            bool thick = (r == rows - 1) ||
                (cell_region.count(below) && cell_region[above] != cell_region[below]);

            cout << "+" << (thick ? h_line : h_line);
        }
        cout << "+" << endl;
    }
}

void print_result(const string& name, const optional<PuzzleResult>& result) {
    if (!result) {
        cout << name << ": NOT FOUND" << endl;
        return;
    }

    cout << "\n" << string(50, '=') << endl;
    cout << name << ": FOUND!" << endl;
    cout << string(50, '=') << endl;

    cout << "Grid: " << result->rows << "x" << result->cols << endl;
    cout << "Dominoes: ";
    for (const auto& d : result->dominoes) {
        cout << d.str() << " ";
    }
    cout << endl << endl;

    // Draw puzzle grid
    cout << "PUZZLE:" << endl;
    draw_puzzle_grid(*result);

    // Draw solution with domino boundaries
    cout << endl << "SOLUTION:" << endl;
    int rows = result->rows;
    int cols = result->cols;
    int cell_width = 5;
    string h_line(cell_width, '-');
    string h_space(cell_width, ' ');

    // Build cell-to-pip and cell-to-domino maps
    map<Cell, int> cell_pip;
    map<Cell, int> cell_domino;  // Which domino each cell belongs to
    for (size_t i = 0; i < result->solution.size(); i++) {
        const auto& p = result->solution[i];
        Cell c1 = p.cell1();
        Cell c2 = p.cell2();
        cell_pip[c1] = p.domino.low;
        cell_pip[c2] = p.domino.high;
        cell_domino[c1] = i;
        cell_domino[c2] = i;
    }

    // Top border
    cout << "  ";
    for (int c = 0; c < cols; c++) cout << "+" << h_line;
    cout << "+" << endl;

    for (int r = 0; r < rows; r++) {
        // Content row
        cout << "  ";
        for (int c = 0; c < cols; c++) {
            Cell cell = {r, c};
            Cell left = {r, c - 1};

            // Vertical border: show if edge or different domino
            bool show_border = (c == 0) || !cell_domino.count(left) ||
                              cell_domino[left] != cell_domino[cell];
            cout << (show_border ? "|" : " ");

            string content = cell_pip.count(cell) ? to_string(cell_pip[cell]) : " ";
            int pad_left = (cell_width - content.length()) / 2;
            int pad_right = cell_width - content.length() - pad_left;
            cout << string(pad_left, ' ') << content << string(pad_right, ' ');
        }
        cout << "|" << endl;

        // Horizontal line: show segment if edge or different domino from below
        cout << "  ";
        for (int c = 0; c < cols; c++) {
            Cell above = {r, c};
            Cell below = {r + 1, c};

            bool show_h_border = (r == rows - 1) || !cell_domino.count(below) ||
                                 cell_domino[above] != cell_domino[below];
            cout << "+" << (show_h_border ? h_line : h_space);
        }
        cout << "+" << endl;
    }

    // Output Python code
    cout << endl << "Python code for puzzles.py:" << endl;
    cout << "  dominoes = [";
    for (size_t i = 0; i < result->dominoes.size(); i++) {
        if (i > 0) cout << ", ";
        cout << "Domino(" << result->dominoes[i].low << ", " << result->dominoes[i].high << ")";
    }
    cout << "]" << endl;

    cout << "  regions = [" << endl;
    for (const auto& r : result->regions) {
        cout << "    Region(" << r.id << ", [";
        for (size_t i = 0; i < r.cells.size(); i++) {
            if (i > 0) cout << ", ";
            cout << "(" << r.cells[i].first << ", " << r.cells[i].second << ")";
        }
        cout << "], ConstraintType.";
        if (r.type == ConstraintType::SUM) cout << "SUM, target_value=" << r.target_value;
        else if (r.type == ConstraintType::LESS) cout << "LESS, linked_region_id=" << r.linked_region_id;
        else if (r.type == ConstraintType::EQUAL) cout << "EQUAL";
        else if (r.type == ConstraintType::GREATER) cout << "GREATER, linked_region_id=" << r.linked_region_id;
        cout << ")," << endl;
    }
    cout << "  ]" << endl;
}

void print_usage() {
    cout << "Usage: puzzle_gen [mode]" << endl;
    cout << "Modes:" << endl;
    cout << "  easy        - Generate Easy1 + Easy2 (Easy2 from remainder after Easy1)" << endl;
    cout << "  medium-hard - Generate Medium + Hard (Hard from remainder after Medium)" << endl;
    cout << "  easy1       - Generate Easy1 only" << endl;
    cout << "  easy2 [d1] [d2] [d3] [d4] - Generate Easy2 excluding specified dominoes" << endl;
    cout << "  medium      - Generate Medium only" << endl;
    cout << "  hard [d1] ... [d6] - Generate Hard excluding specified dominoes" << endl;
    cout << "  all         - Generate all puzzles (default)" << endl;
    cout << "\nDomino format: low-high (e.g., 0-0, 1-2, 3-6)" << endl;
}

vector<Domino> exclude_dominoes(const vector<Domino>& pool, const vector<Domino>& exclude) {
    vector<Domino> result;
    for (const auto& d : pool) {
        bool found = false;
        for (const auto& e : exclude) {
            if (d == e) { found = true; break; }
        }
        if (!found) result.push_back(d);
    }
    return result;
}

Domino parse_domino(const string& s) {
    size_t dash = s.find('-');
    if (dash == string::npos) return {-1, -1};
    int low = stoi(s.substr(0, dash));
    int high = stoi(s.substr(dash + 1));
    if (low > high) swap(low, high);
    return {low, high};
}

int main(int argc, char* argv[]) {
    string mode = "all";
    vector<Domino> exclude_list;

    if (argc > 1) {
        mode = argv[1];
        if (mode == "-h" || mode == "--help") {
            print_usage();
            return 0;
        }
        // Parse excluded dominoes
        for (int i = 2; i < argc; i++) {
            Domino d = parse_domino(argv[i]);
            if (d.low >= 0) exclude_list.push_back(d);
        }
    }

    cout << "==================================================" << endl;
    cout << "MULTITHREADED DOMINO PUZZLE GENERATOR (C++)" << endl;
    cout << "Mode: " << mode << endl;
    cout << "==================================================" << endl;

    // Build domino sets
    vector<Domino> all_d6;
    for (int i = 0; i <= 6; i++) {
        for (int j = i; j <= 6; j++) {
            all_d6.push_back({i, j});
        }
    }

    vector<Domino> d9_remainder;
    for (int i = 0; i <= 9; i++) {
        for (int j = i; j <= 9; j++) {
            if (i >= 7 || j >= 7) {
                d9_remainder.push_back({i, j});
            }
        }
    }

    cout << "Double-six set: " << all_d6.size() << " dominoes" << endl;
    cout << "D9 remainder: " << d9_remainder.size() << " dominoes" << endl;

    if (!exclude_list.empty()) {
        cout << "Excluding: ";
        for (const auto& d : exclude_list) cout << d.str() << " ";
        cout << endl;
    }

    auto start = chrono::high_resolution_clock::now();
    vector<thread> threads;

    bool do_easy1 = (mode == "all" || mode == "easy" || mode == "easy1");
    bool do_easy2 = (mode == "all" || mode == "easy" || mode == "easy2");
    bool do_medium = (mode == "all" || mode == "medium-hard" || mode == "medium");
    bool do_hard = (mode == "all" || mode == "medium-hard" || mode == "hard");

    // Easy 1
    if (do_easy1) {
        cout << "\nSearching for Easy1..." << endl;
        for (int i = 0; i < 4; i++) {
            threads.emplace_back(search_easy_2x4_sums, i, ref(all_d6));
        }
        for (auto& t : threads) t.join();
        threads.clear();
    }

    // Easy 2 - use remainder after Easy1
    if (do_easy2) {
        vector<Domino> easy2_pool = all_d6;

        // Exclude Easy1 dominoes if we found them
        if (easy1_result) {
            easy2_pool = exclude_dominoes(all_d6, easy1_result->dominoes);
            cout << "\nSearching for Easy2 (excluding Easy1 dominoes: " << easy2_pool.size() << " remaining)..." << endl;
        } else if (!exclude_list.empty()) {
            easy2_pool = exclude_dominoes(all_d6, exclude_list);
            cout << "\nSearching for Easy2 (excluding specified dominoes: " << easy2_pool.size() << " remaining)..." << endl;
        } else {
            cout << "\nSearching for Easy2..." << endl;
        }

        for (int i = 0; i < 4; i++) {
            threads.emplace_back(search_easy_3cell_regions, i, ref(easy2_pool));
        }
        for (auto& t : threads) t.join();
        threads.clear();
    }

    // Medium
    if (do_medium) {
        cout << "\nSearching for Medium..." << endl;
        for (int i = 0; i < 4; i++) {
            threads.emplace_back(search_medium, i, ref(all_d6));
        }
        for (auto& t : threads) t.join();
        threads.clear();
    }

    // Hard - use d9_remainder + unused d6
    if (do_hard) {
        vector<Domino> hard_pool = d9_remainder;

        // Add unused d6 dominoes (those not used by medium)
        vector<Domino> unused_d6 = all_d6;
        if (medium_result) {
            unused_d6 = exclude_dominoes(all_d6, medium_result->dominoes);
        } else if (!exclude_list.empty()) {
            unused_d6 = exclude_dominoes(all_d6, exclude_list);
        }

        // Combine d9_remainder with unused d6
        for (const auto& d : unused_d6) {
            hard_pool.push_back(d);
        }

        cout << "\nSearching for Hard (d9_remainder + unused d6: " << hard_pool.size() << " dominoes)..." << endl;
        for (int i = 0; i < 4; i++) {
            threads.emplace_back(search_hard, i, ref(d9_remainder), ref(unused_d6));
        }
        for (auto& t : threads) t.join();
    }

    auto end = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::milliseconds>(end - start);

    cout << "\n==================================================" << endl;
    cout << "FINAL SUMMARY (Total time: " << duration.count() << "ms)" << endl;
    cout << "Total attempts: " << total_attempts.load() << endl;
    cout << "==================================================" << endl;

    if (do_easy1) cout << "Easy1: " << (easy1_result ? "FOUND" : "NOT FOUND") << endl;
    if (do_easy2) cout << "Easy2: " << (easy2_result ? "FOUND" : "NOT FOUND") << endl;
    if (do_medium) cout << "Medium: " << (medium_result ? "FOUND" : "NOT FOUND") << endl;
    if (do_hard) cout << "Hard: " << (hard_result ? "FOUND" : "NOT FOUND") << endl;

    return 0;
}
