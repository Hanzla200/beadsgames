# 12 Beads

A touch-friendly 12 Guti / Bara Tehni game built with Python and Kivy. Choose **PLAYER VS PLAYER** for local play or **PLAYER VS CPU** to play against the computer before each match. The mode stays fixed until you use **EXIT** to return to the mode menu. The game starts with 12 beads per side and the center point empty. The opening player is randomized each game; the existing 5x5 board and diagonal pattern are unchanged.

Select one of your beads and tap a connected point to move; the board does not preview legal destinations. Move along a line on the 5x5 board, including its diagonal links. Capture by jumping over an adjacent opponent bead into the empty point directly beyond it. If the same bead can capture again, it stays selected and must continue jumping; choose the next connected landing point. The game ends when a player has no beads or no legal moves.

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
