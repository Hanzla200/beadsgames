import unittest
from math import inf

from game_engine import (
    GRAPH,
    Searcher,
    Step,
    apply_action,
    apply_step,
    count,
    initial_board,
    legal_actions,
    legal_steps,
    winner,
)


def board_with(*pieces):
    cells = [None] * 25
    for point, side in pieces:
        cells[point] = side
    return tuple(cells)


class BoardRulesTests(unittest.TestCase):
    def test_initial_board_and_topology(self):
        cells = initial_board()
        self.assertEqual(len(GRAPH), 25)
        self.assertTrue(all(point in GRAPH[neighbor]
                            for point, neighbors in GRAPH.items()
                            for neighbor in neighbors))
        self.assertEqual((count(cells, "red"), count(cells, "green")), (12, 12))
        self.assertIsNone(cells[12])

    def test_single_jump_captures_adjacent_opponent(self):
        cells = board_with((0, "green"), (1, "red"))
        jump = Step(0, 2, 1)
        self.assertIn((2, 1), legal_steps(cells, 0))
        after = apply_step(cells, jump, "green")
        self.assertEqual(after[2], "green")
        self.assertIsNone(after[0])
        self.assertIsNone(after[1])
        self.assertEqual(count(after, "red"), 0)

    def test_consecutive_jumps_continue_until_no_capture(self):
        cells = board_with((12, "green"), (6, "red"), (1, "red"))
        chain = (Step(12, 0, 6), Step(0, 2, 1))
        self.assertIn(chain, legal_actions(cells, "green"))
        after = apply_action(cells, chain, "green")
        self.assertEqual(after[2], "green")
        self.assertEqual(count(after, "red"), 0)

    def test_branching_capture_chains_generate_each_route(self):
        cells = board_with((12, "green"), (6, "red"), (1, "red"), (5, "red"))
        actions = legal_actions(cells, "green")
        destinations = {
            action[1].destination for action in actions
            if len(action) == 2 and action[0] == Step(12, 0, 6)
        }
        self.assertEqual(destinations, {2, 10})
        self.assertTrue(all(len(action) == 2 for action in actions
                            if action[0] == Step(12, 0, 6)))

    def test_blocked_landing_and_own_bead_cannot_be_jumped(self):
        blocked = board_with((12, "green"), (6, "red"), (0, "green"))
        self.assertNotIn((0, 6), legal_steps(blocked, 12))
        own_piece = board_with((12, "green"), (6, "green"))
        self.assertFalse(any(victim is not None
                             for _destination, victim in legal_steps(own_piece, 12)))

    def test_rejects_occupied_landings_and_incomplete_chains(self):
        occupied = board_with((0, "green"), (1, "red"), (2, "red"))
        with self.assertRaises(ValueError):
            apply_step(occupied, Step(0, 2, 1), "green")
        chain_start = board_with((12, "green"), (6, "red"), (1, "red"))
        with self.assertRaises(ValueError):
            apply_action(chain_start, (Step(12, 0, 6),), "green")

    def test_captured_bead_cannot_be_captured_twice(self):
        cells = board_with((12, "green"), (6, "red"), (1, "red"))
        repeated = (Step(12, 0, 6), Step(0, 2, 6))
        with self.assertRaises(ValueError):
            apply_action(cells, repeated, "green")

    def test_win_when_opponent_has_no_beads_or_moves(self):
        self.assertEqual(winner(board_with((12, "green")), "red"), "green")
        blocked = ["red"] * 25
        blocked[12] = "green"
        self.assertEqual(winner(tuple(blocked), "green"), "red")


class SearchTests(unittest.TestCase):
    def test_ai_returns_a_legal_complete_turn(self):
        cells = initial_board()
        result = Searcher(max_depth=1, time_limit=1).choose(cells, "green")
        self.assertIsNotNone(result)
        self.assertIn(result.action, legal_actions(cells, "green"))
        self.assertGreaterEqual(result.depth, 1)

    def test_ai_finds_immediate_winning_capture(self):
        cells = board_with((12, "green"), (6, "red"))
        result = Searcher(max_depth=2, time_limit=1).choose(cells, "green")
        self.assertEqual(result.action[0], Step(12, 0, 6))
        self.assertEqual(count(apply_action(cells, result.action, "green"), "red"), 0)

    def test_ai_chooses_a_complete_branching_multi_jump(self):
        cells = board_with((12, "green"), (6, "red"), (1, "red"), (5, "red"))
        result = Searcher(max_depth=2, time_limit=1).choose(cells, "green")
        self.assertEqual(len(result.action), 2)
        self.assertEqual(sum(step.captured is not None for step in result.action), 2)

    def test_repeated_search_position_is_treated_as_a_draw(self):
        cells = initial_board()
        searcher = Searcher(max_depth=1, time_limit=1)
        searcher.deadline = float("inf")
        self.assertEqual(searcher._search(cells, "green", 2, -inf, inf, 0, {cells}), 0)


if __name__ == "__main__":
    unittest.main()
