"""Run reproducible AI-vs-AI 12 Beads matches and print aggregate metrics."""

import argparse
from collections import Counter
from pathlib import Path
from random import Random
import sys
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game_engine import Searcher, apply_action, initial_board, legal_actions, opposite, winner


SETTINGS = (
    ("shallow", dict(max_depth=1, time_limit=0.001, quiescence_depth=0)),
    ("medium", dict(max_depth=2, time_limit=0.003, quiescence_depth=1)),
    ("deep", dict(max_depth=3, time_limit=0.008, quiescence_depth=2)),
)


class RandomPlayer:
    def __init__(self, seed):
        self.random = Random(seed)

    def choose(self, cells, side):
        from game_engine import SearchResult
        started = monotonic()
        actions = legal_actions(cells, side)
        if not actions:
            return None
        return SearchResult(self.random.choice(actions), 0, 0, 1,
                            monotonic() - started)


def play(red_ai, green_ai, ply_limit):
    cells = initial_board()
    side = "red"
    decisions = 0
    total_time = 0.0
    depths = Counter()
    tactical_misses = 0
    while decisions < ply_limit:
        actions = legal_actions(cells, side)
        if not actions:
            return opposite(side), decisions, total_time, depths, tactical_misses
        result = (red_ai if side == "red" else green_ai).choose(cells, side)
        if result is None or result.action not in actions:
            raise RuntimeError("AI returned an illegal or missing action")
        immediate_wins = []
        for action in actions:
            after = apply_action(cells, action, side)
            if not legal_actions(after, opposite(side)):
                immediate_wins.append(action)
        if immediate_wins and result.action not in immediate_wins:
            tactical_misses += 1
        cells = apply_action(cells, result.action, side)
        decisions += 1
        total_time += result.elapsed
        depths[result.depth] += 1
        side = opposite(side)
        game_winner = winner(cells, side)
        if game_winner:
            return game_winner, decisions, total_time, depths, tactical_misses
    return "draw", decisions, total_time, depths, tactical_misses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--plies", type=int, default=120,
                        help="cap each game; reaching the cap counts as a benchmark draw")
    parser.add_argument("--progress", type=int, default=100)
    args = parser.parse_args()
    if args.games < 1 or args.plies < 1:
        parser.error("--games and --plies must be positive")

    results = Counter()
    totals = Counter()
    started = monotonic()
    matchups = (("random", "shallow"), ("shallow", "medium"),
                ("medium", "deep"), ("deep", "random"))
    for game_index in range(args.games):
        red_name, green_name = matchups[game_index % len(matchups)]
        options_by_name = dict(SETTINGS)
        # Alternate colors so a starting-side advantage does not favor one setting.
        if (game_index // len(matchups)) % 2:
            red_name, green_name = green_name, red_name

        def make_player(name, offset):
            if name == "random":
                return RandomPlayer(game_index * 2 + offset)
            return Searcher(**dict(options_by_name[name]))

        winner_name, plies, elapsed, depths, misses = play(
            make_player(red_name, 0), make_player(green_name, 1), args.plies)
        matchup = tuple(sorted((red_name, green_name)))
        result_name = ("draw" if winner_name == "draw" else
                       red_name if winner_name == "red" else green_name)
        results[(matchup, result_name)] += 1
        totals["games"] += 1
        totals["plies"] += plies
        totals["search_seconds"] += elapsed
        totals["tactical_misses"] += misses
        for depth, count in depths.items():
            totals[f"depth_{depth}"] += count
        if args.progress and (game_index + 1) % args.progress == 0:
            print(f"completed {game_index + 1}/{args.games} games")

    wall = monotonic() - started
    print(f"\nGames: {totals['games']} | wall time: {wall:.1f}s")
    print(f"Average decisions/game: {totals['plies'] / totals['games']:.1f}")
    print(f"Average decision time: {totals['search_seconds'] / max(1, totals['plies']):.4f}s")
    print(f"Missed immediate wins: {totals['tactical_misses']}")
    if totals["depth_0"]:
        print(f"Fallback decisions before depth 1: {totals['depth_0']}")
    print("Completed search depths: " + ", ".join(
        f"{depth}={totals[f'depth_{depth}']}" for depth in range(1, 9)
        if totals[f"depth_{depth}"]))
    print("Matchup results:")
    for matchup in sorted({key[0] for key in results}):
        matchup_games = sum(results[(matchup, result)]
                            for result in (*matchup, "draw"))
        summaries = []
        for result in (*matchup, "draw"):
            result_count = results[(matchup, result)]
            if result_count:
                summaries.append(f"{result} {result_count} "
                                 f"({100 * result_count / matchup_games:.1f}%)")
        print(f"  {' vs '.join(matchup)}: " + ", ".join(summaries))


if __name__ == "__main__":
    main()
