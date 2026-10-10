"""Rules and search for the 5x5 12 Beads game.

The board is a tuple of 25 values (``None``, ``"red"``, or ``"green"``).
An action is a complete turn: one ordinary step, or every consecutive jump
made by the same bead until no further capture is available.
"""

from dataclasses import dataclass
from math import inf
from time import monotonic


def make_graph():
    graph = {r * 5 + c: set() for r in range(5) for c in range(5)}

    def connect(a, b):
        graph[a].add(b)
        graph[b].add(a)

    for row in range(5):
        for col in range(5):
            point = row * 5 + col
            if col < 4:
                connect(point, point + 1)
            if row < 4:
                connect(point, point + 5)
            if row < 4 and col < 4:
                if (row + col) % 2 == 0:
                    connect(point, point + 6)
                else:
                    connect(point + 1, point + 5)
    return {point: frozenset(neighbors) for point, neighbors in graph.items()}


GRAPH = make_graph()
SIDES = ("red", "green")
MATE_SCORE = 1_000_000


@dataclass(frozen=True)
class Step:
    source: int
    destination: int
    captured: int | None = None


Action = tuple[Step, ...]


def initial_board():
    cells = [None] * 25
    for point in list(range(10)) + [10, 11]:
        cells[point] = "red"
    for point in list(range(15, 25)) + [13, 14]:
        cells[point] = "green"
    return tuple(cells)


def count(cells, side):
    return sum(piece == side for piece in cells)


def legal_steps(cells, source):
    """Return (destination, captured point) pairs for one bead step."""
    side = cells[source]
    if side is None:
        return ()
    moves = []
    sr, sc = divmod(source, 5)
    for neighbor in GRAPH[source]:
        if cells[neighbor] is None:
            moves.append((neighbor, None))
            continue
        if cells[neighbor] == side:
            continue
        nr, nc = divmod(neighbor, 5)
        dr, dc = nr - sr, nc - sc
        landing_row, landing_col = nr + dr, nc + dc
        if 0 <= landing_row < 5 and 0 <= landing_col < 5:
            landing = landing_row * 5 + landing_col
            if landing in GRAPH[neighbor] and cells[landing] is None:
                moves.append((landing, neighbor))
    return tuple(moves)


def apply_step(cells, step, side=None):
    """Apply and validate one step, returning a new board tuple."""
    if not 0 <= step.source < 25 or not 0 <= step.destination < 25:
        raise ValueError("point index is outside the board")
    moving_side = cells[step.source]
    if moving_side is None or (side is not None and moving_side != side):
        raise ValueError("source does not contain the moving side's bead")
    if (step.destination, step.captured) not in legal_steps(cells, step.source):
        raise ValueError("illegal move")
    next_cells = list(cells)
    next_cells[step.source] = None
    next_cells[step.destination] = moving_side
    if step.captured is not None:
        next_cells[step.captured] = None
    return tuple(next_cells)


def apply_action(cells, action, side):
    """Apply a complete legal turn, rejecting incomplete or illegal chains."""
    if not action:
        raise ValueError("an action must contain at least one step")
    result = tuple(cells)
    for index, step in enumerate(action):
        if result[step.source] != side:
            raise ValueError("every step in a turn must use the moving side")
        if index and action[index - 1].captured is None:
            raise ValueError("an ordinary move ends the turn")
        result = apply_step(result, step, side)
        if step.captured is not None:
            more_captures = tuple((dest, victim) for dest, victim
                                  in legal_steps(result, step.destination)
                                  if victim is not None)
            has_next = index + 1 < len(action)
            if has_next and not more_captures:
                raise ValueError("capture chain continued after it ended")
            if has_next and (action[index + 1].source != step.destination or
                             (action[index + 1].destination,
                              action[index + 1].captured) not in more_captures):
                raise ValueError("capture chain must continue with the same bead")
            if not has_next and more_captures:
                raise ValueError("action ended while another capture was available")
        elif index + 1 < len(action):
            raise ValueError("ordinary moves cannot be chained")
    return result


def legal_actions(cells, side, forced_source=None):
    """Generate every complete legal turn, including all branching jump paths."""
    actions = []
    sources = (forced_source,) if forced_source is not None else range(25)
    for source in sources:
        if not 0 <= source < 25 or cells[source] != side:
            continue
        for destination, victim in legal_steps(cells, source):
            first = Step(source, destination, victim)
            after = apply_step(cells, first, side)
            if victim is None:
                actions.append((first,))
                continue
            _extend_capture_chains(after, destination, side, (first,), actions)
    return tuple(actions)


def _extend_capture_chains(cells, source, side, prefix, output):
    captures = [(destination, victim) for destination, victim
                in legal_steps(cells, source) if victim is not None]
    if not captures:
        output.append(prefix)
        return
    for destination, victim in captures:
        step = Step(source, destination, victim)
        after = apply_step(cells, step, side)
        _extend_capture_chains(after, destination, side, prefix + (step,), output)


def winner(cells, side_to_move):
    """Return the winner, or None while both sides can continue."""
    other = opposite(side_to_move)
    if count(cells, side_to_move) == 0 or not legal_actions(cells, side_to_move):
        return other
    if count(cells, other) == 0 or not legal_actions(cells, other):
        return side_to_move
    return None


def opposite(side):
    return "green" if side == "red" else "red"


@dataclass(frozen=True)
class Weights:
    material: int = 150
    mobility: int = 4
    center: int = 5
    connectivity: int = 2
    threatened: int = 24
    capture_potential: int = 12


@dataclass(frozen=True)
class SearchResult:
    action: Action
    score: int
    depth: int
    nodes: int
    elapsed: float


class SearchTimeout(Exception):
    pass


class Searcher:
    """Iterative-deepening negamax with alpha-beta and a transposition table."""

    def __init__(self, weights=None, max_depth=8, time_limit=0.45,
                 quiescence_depth=4):
        self.weights = weights or Weights()
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.quiescence_depth = quiescence_depth
        self.table = {}
        self.nodes = 0
        self.deadline = 0

    def choose(self, cells, side, forced_source=None):
        started = monotonic()
        self.deadline = started + self.time_limit
        self.table.clear()
        self.nodes = 0
        actions = legal_actions(cells, side, forced_source)
        if not actions:
            return None
        # Always have a legal fallback, even if the time budget is tiny.
        best_action = self._ordered_actions(cells, side, actions)[0]
        best_score, completed_depth = 0, 0
        for depth in range(1, self.max_depth + 1):
            try:
                score, action = self._root(cells, side, actions, depth, best_action)
            except SearchTimeout:
                break
            best_score, best_action, completed_depth = score, action, depth
            if abs(score) >= MATE_SCORE - 100:
                break
        return SearchResult(best_action, best_score, completed_depth,
                            self.nodes, monotonic() - started)

    def _check_time(self):
        self.nodes += 1
        if (self.nodes & 127) == 0 and monotonic() >= self.deadline:
            raise SearchTimeout

    def _root(self, cells, side, actions, depth, previous_best):
        alpha, beta = -inf, inf
        best_score, best_action = -inf, previous_best
        ordered = self._ordered_actions(cells, side, actions, previous_best)
        for action in ordered:
            self._check_time()
            next_cells = apply_action(cells, action, side)
            score = -self._search(next_cells, opposite(side), depth - 1,
                                  -beta, -alpha, 1, {cells})
            if score > best_score:
                best_score, best_action = score, action
            alpha = max(alpha, best_score)
        return best_score, best_action

    def _search(self, cells, side, depth, alpha, beta, ply, path):
        self._check_time()
        if cells in path:
            return 0
        key = (cells, side)
        original_alpha, original_beta = alpha, beta
        entry = self.table.get(key)
        if entry and entry[0] >= depth:
            _, score, flag, table_action = entry
            if flag == "exact":
                return score
            if flag == "lower":
                alpha = max(alpha, score)
            else:
                beta = min(beta, score)
            if alpha >= beta:
                return score
        else:
            table_action = entry[3] if entry else None

        if not legal_actions(cells, side):
            return -MATE_SCORE + ply
        if depth <= 0:
            return self._quiescence(cells, side, alpha, beta,
                                    self.quiescence_depth, ply, path)

        actions = legal_actions(cells, side)
        best = -inf
        best_action = None
        child_path = path | {cells}
        for action in self._ordered_actions(cells, side, actions, table_action):
            next_cells = apply_action(cells, action, side)
            score = -self._search(next_cells, opposite(side), depth - 1,
                                  -beta, -alpha, ply + 1, child_path)
            if score > best:
                best, best_action = score, action
            alpha = max(alpha, best)
            if alpha >= beta:
                break

        flag = ("upper" if best <= original_alpha else
                "lower" if best >= original_beta else "exact")
        self.table[key] = (depth, best, flag, best_action)
        return best

    def _quiescence(self, cells, side, alpha, beta, remaining, ply, path):
        available = legal_actions(cells, side)
        if not available:
            return -MATE_SCORE + ply
        stand_pat = self.evaluate(cells, side)
        if remaining <= 0:
            return stand_pat
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
        capture_actions = tuple(action for action in available
                                if action[0].captured is not None)
        if not capture_actions:
            return stand_pat
        child_path = path | {cells}
        for action in self._ordered_actions(cells, side, capture_actions):
            self._check_time()
            next_cells = apply_action(cells, action, side)
            score = -self._quiescence(next_cells, opposite(side), -beta, -alpha,
                                      remaining - 1, ply + 1, child_path)
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _ordered_actions(self, cells, side, actions, preferred=None):
        def rank(action):
            if action == preferred:
                return (1, 0, 0, 0)
            captured = sum(step.captured is not None for step in action)
            landing_center = -sum(abs(divmod(step.destination, 5)[0] - 2) +
                                  abs(divmod(step.destination, 5)[1] - 2)
                                  for step in action)
            resulting = apply_action(cells, action, side)
            enemy_mobility = sum(len(legal_steps(resulting, point))
                                 for point, owner in enumerate(resulting)
                                 if owner == opposite(side))
            return (0, captured, -enemy_mobility, landing_center)

        return sorted(actions, key=rank, reverse=True)

    def evaluate(self, cells, perspective):
        weights = self.weights
        enemy = opposite(perspective)
        own_count, enemy_count = count(cells, perspective), count(cells, enemy)
        remaining = own_count + enemy_count
        material_weight = weights.material + max(0, 12 - remaining) * 12
        score = (own_count - enemy_count) * material_weight

        own_steps, enemy_steps = [], []
        for source, owner in enumerate(cells):
            if owner not in SIDES:
                continue
            for destination, victim in legal_steps(cells, source):
                target = own_steps if owner == perspective else enemy_steps
                target.append((source, destination, victim))
        score += (len(own_steps) - len(enemy_steps)) * weights.mobility
        own_victims = {victim for _src, _dst, victim in own_steps if victim is not None}
        enemy_victims = {victim for _src, _dst, victim in enemy_steps if victim is not None}
        score += (len(own_victims) - len(enemy_victims)) * weights.capture_potential

        for point, owner in enumerate(cells):
            if owner not in SIDES:
                continue
            row, col = divmod(point, 5)
            center_value = 4 - abs(row - 2) - abs(col - 2)
            sign = 1 if owner == perspective else -1
            score += sign * center_value * weights.center
            friendly_neighbors = sum(cells[n] == owner for n in GRAPH[point])
            score += sign * friendly_neighbors * weights.connectivity
            if owner == perspective and point in enemy_victims:
                score -= weights.threatened
            elif owner == enemy and point in own_victims:
                score += weights.threatened
        return int(score)
