# 12 Beads

A touch-friendly 12 Guti / Bara Tehni game built with Python and Kivy. Choose **PLAYER VS PLAYER** for local play or **PLAYER VS CPU** to play against the computer before each match. The mode stays fixed until you use **EXIT** to return to the mode menu. The game starts with 12 beads per side and the center point empty. The opening player is randomized each game; the existing 5x5 board and diagonal pattern are unchanged.

The board has 25 points on a 5x5 grid, with orthogonal links and alternating diagonals. Select one of your beads and tap a connected point to move; the board does not preview legal destinations. Capture by jumping over an adjacent opponent bead in a straight line into the empty point directly beyond it. Captures are optional when starting a turn. After a jump, that bead must continue capturing for as long as another legal jump is available; branching routes are all legal choices. The game ends when a player has no beads or no legal moves. The game has no draw rule.

The computer uses the same standalone rules engine as the game. It searches complete turns, including every branch of a multi-jump capture, with iterative-deepening minimax, alpha-beta pruning, a transposition table, capture quiescence, and a weighted position evaluation. Search runs on a background thread (650 ms desktop budget, 250 ms Android budget) so the board remains responsive. This is a strong practical opponent, not a solved or mathematically unbeatable strategy. Evaluation weights can be adjusted in `game_engine.py`.

Use **?** for the rules, and confirm before starting over or leaving a match. To add custom behavior, edit the marked `CUSTOM LOGIC HOOKS` section in `main.py`. The mode hook receives `two` or `computer`; the move hook receives source point, destination point, and side. The exit hook receives `mode_menu` or `app`. Replace `pass` with your code; by default the hooks do nothing.

## Desktop

Install Python 3.10 or newer and run:

```sh
python -m pip install -r requirements.txt
python main.py
```

## Android

Build with Buildozer from Linux or WSL:

```sh
buildozer android debug
```

The included spec targets API 36 for current Google Play submissions. Change `package.domain` and `package.name` to a unique application ID before publishing.

Android builds show an AdMob banner and request an interstitial after each completed match, then automatically deal a new game after a short pause. On desktop, the next game starts without an ad. The app currently uses Google's test IDs in [ads_config.py](ads_config.py) and `buildozer.spec`; test ads do not earn revenue. Replace them with IDs from your AdMob account before release, and use test ads during development.

## Rules and AI checks

The rules engine has no Kivy dependency. Run its unit tests with:

```sh
python -m unittest discover -s tests -v
```

Run AI self-play comparisons and decision-time/tactical metrics with:

```sh
python tools/self_play.py --games 1000 --plies 12
python tools/self_play.py --games 100 --plies 100
```

The first command compares search settings over many opening games; the second exercises longer games and endgames. The runner reports matchup win/draw rates, decision time, completed search depths, and missed immediate wins. Reaching the ply cap is counted as a benchmark draw; the game itself has no draw rule.
