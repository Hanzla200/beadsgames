"""12 Beads (Bara Tehni) for desktop and Android with Kivy."""

from random import choice

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.utils import platform


BG = (0.055, 0.075, 0.105, 1)
PANEL = (0.095, 0.125, 0.17, 1)
LINE = (0.40, 0.48, 0.55, 1)
EMPTY = (0.15, 0.19, 0.24, 1)
RED = (0.92, 0.27, 0.30, 1)
GREEN = (0.25, 0.75, 0.42, 1)
TEXT = (0.94, 0.96, 0.98, 1)
MUTED = (0.59, 0.67, 0.75, 1)
ACCENT = (0.40, 0.78, 0.91, 1)


def make_graph():
    """Build the 5x5 Alquerque-style board from the connected lines."""
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
            # Each small square has one diagonal, alternating direction to
            # form the larger diamond pattern shown in the reference board.
            if row < 4 and col < 4:
                if (row + col) % 2 == 0:
                    connect(point, point + 6)
                else:
                    connect(point + 1, point + 5)
    return graph


GRAPH = make_graph()


class Surface(BoxLayout):
    def __init__(self, color=PANEL, radius=dp(14), **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.01, 0.018, 0.03, 0.34)
            self._shadow = RoundedRectangle(pos=self.pos, size=self.size,
                                            radius=[radius + dp(2)])
            Color(*color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._shadow.pos = (self.x, self.y - dp(2))
        self._shadow.size = self.size
        self._rect.pos = self.pos
        self._rect.size = self.size


class Board(Widget):
    anim_progress = NumericProperty(1)

    def __init__(self, game, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.anim_data = None
        self.bind(pos=self.redraw, size=self.redraw, anim_progress=self.redraw)
        self.redraw()

    def point_pos(self, index):
        row, col = divmod(index, 5)
        margin = min(self.width, self.height) * 0.075
        span_x = max(1, self.width - margin * 2)
        span_y = max(1, self.height - margin * 2)
        return self.x + margin + col * span_x / 4, self.y + self.height - margin - row * span_y / 4

    def redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0.01, 0.018, 0.03, 0.38)
            RoundedRectangle(pos=(self.x, self.y - dp(3)), size=self.size,
                             radius=[dp(20)])
            Color(0.34, 0.25, 0.16, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
            Color(*PANEL)
            RoundedRectangle(pos=(self.x + dp(3), self.y + dp(3)),
                             size=(max(0, self.width - dp(6)), max(0, self.height - dp(6))),
                             radius=[dp(16)])
            Color(*LINE)
            for point, neighbors in GRAPH.items():
                x1, y1 = self.point_pos(point)
                for neighbor in neighbors:
                    if neighbor > point:
                        x2, y2 = self.point_pos(neighbor)
                        Line(points=[x1, y1, x2, y2], width=dp(1.15))

            bead_radius = min(self.width, self.height) * 0.047
            selected = self.game.selected
            if selected is not None:
                sx, sy = self.point_pos(selected)
                Color(*ACCENT)
                Line(circle=(sx, sy, bead_radius * 1.6), width=dp(2))

            for index, owner in enumerate(self.game.cells):
                if owner is None or self._is_animated_destination(index):
                    continue
                x, y = self.point_pos(index)
                self._draw_bead(x, y, bead_radius, owner)

            if self.anim_data:
                start, end, owner = self.anim_data
                sx, sy = self.point_pos(start)
                ex, ey = self.point_pos(end)
                progress = self.anim_progress
                self._draw_bead(sx + (ex - sx) * progress,
                                sy + (ey - sy) * progress, bead_radius, owner)

            Color(*LINE)
            for index in GRAPH:
                x, y = self.point_pos(index)
                Ellipse(pos=(x - dp(3), y - dp(3)), size=(dp(6), dp(6)))

    def _draw_bead(self, x, y, radius, owner):
        Color(0.015, 0.025, 0.035, 0.42)
        Ellipse(pos=(x - radius * 0.94, y - radius * 1.12),
                size=(radius * 1.9, radius * 1.9))
        Color(*(RED if owner == "red" else GREEN))
        Ellipse(pos=(x - radius, y - radius), size=(radius * 2, radius * 2))
        Color(1, 1, 1, 0.2)
        Line(circle=(x, y, radius * 0.92), width=dp(0.7))
        Color(1, 1, 1, 0.22)
        Ellipse(pos=(x - radius * 0.5, y + radius * 0.18),
                size=(radius * 0.48, radius * 0.34))

    def _is_animated_destination(self, index):
        return self.anim_data is not None and index == self.anim_data[1]

    def animate_move(self, start, end, owner):
        Animation.cancel_all(self, "anim_progress")
        self.anim_data = (start, end, owner)
        self.anim_progress = 0
        Animation(anim_progress=1, duration=0.2, t="out_quad").start(self)
        Clock.schedule_once(self._finish_animation, 0.21)

    def _finish_animation(self, _dt):
        self.anim_data = None
        self.redraw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            nearest = min(GRAPH, key=lambda i: (self.point_pos(i)[0] - touch.x) ** 2
                          + (self.point_pos(i)[1] - touch.y) ** 2)
            x, y = self.point_pos(nearest)
            if (x - touch.x) ** 2 + (y - touch.y) ** 2 <= (min(self.width, self.height) * 0.09) ** 2:
                self.game.tap_point(nearest)
                return True
        return super().on_touch_down(touch)


class GameScreen(BoxLayout):
    def __init__(self, game, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(10),
                         padding=[dp(14), dp(12), dp(14),
                                  dp(68) if platform == "android" else dp(12)], **kwargs)
        self.game = game
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        title = BoxLayout(orientation="vertical")
        title.add_widget(Label(text="12 BEADS", color=TEXT, bold=True,
                               font_size=sp(18), halign="left"))
        title.add_widget(Label(text="PLAN YOUR MOVE. KEEP IT HIDDEN.", color=MUTED,
                               font_size=sp(9), halign="left"))
        top.add_widget(title)
        fresh = self.make_button("NEW", ACCENT, BG)
        fresh.size_hint = (None, None)
        fresh.size = (dp(58), dp(40))
        fresh.bind(on_release=lambda *_: self.game.confirm_action(
            "Start a new game?", "The current board will be cleared.", self.game.new_game))
        top.add_widget(fresh)
        leave = self.make_button("EXIT", PANEL, TEXT)
        leave.size_hint = (None, None)
        leave.size = (dp(58), dp(40))
        leave.bind(on_release=lambda *_: self.game.confirm_action(
            "Leave this game?", "The current board will be cleared.",
            self.game.exit_to_mode_menu))
        top.add_widget(leave)
        help_button = self.make_button("?", PANEL, TEXT)
        help_button.size_hint = (None, None)
        help_button.size = (dp(38), dp(40))
        help_button.bind(on_release=lambda *_: self.game.show_help())
        top.add_widget(help_button)
        self.add_widget(top)

        score_row = BoxLayout(size_hint_y=None, height=dp(65), spacing=dp(8))
        self.red_score = self.make_score(score_row, "RED", "12", RED)
        self.turn_label = self.make_score(score_row, "TO MOVE", "RED", TEXT)
        self.green_score = self.make_score(score_row, "GREEN", "12", GREEN)
        self.add_widget(score_row)

        self.status = Label(text="", color=TEXT, bold=True, font_size=sp(15),
                            size_hint_y=None, height=dp(26))
        self.add_widget(self.status)

        board_area = BoxLayout(size_hint_y=1)
        self.board = Board(game, size_hint=(1, 1))
        board_area.add_widget(self.board)
        self.add_widget(board_area)

        footer = BoxLayout(size_hint_y=None, height=dp(36))
        footer.add_widget(Label(text="Move along connected lines; jump to capture",
                                color=MUTED,
                                font_size=sp(11), halign="center"))
        self.add_widget(footer)
        self.refresh()

    @staticmethod
    def make_button(text, background, foreground):
        button = Button(text=text, bold=True, font_size=sp(11), color=foreground,
                        background_normal="", background_down="",
                        background_color=(0, 0, 0, 0))
        with button.canvas.before:
            Color(0.01, 0.018, 0.03, 0.3)
            button._shadow = RoundedRectangle(radius=[dp(10)])
            button._face_color = Color(*background)
            button._face = RoundedRectangle(radius=[dp(10)])

        def sync(widget, *_):
            widget._shadow.pos = (widget.x, widget.y - dp(2))
            widget._shadow.size = widget.size
            widget._face.pos = widget.pos
            widget._face.size = widget.size

        def paint(widget, color):
            widget._face_color.rgba = color

        button.bind(pos=sync, size=sync, background_color=paint)
        sync(button)
        return button

    @staticmethod
    def make_score(parent, caption, value, color):
        panel = Surface(orientation="vertical", spacing=0, padding=dp(4))
        panel.add_widget(Label(text=caption, color=MUTED, font_size=sp(9), bold=True))
        value_label = Label(text=value, color=color, font_size=sp(17), bold=True)
        panel.add_widget(value_label)
        parent.add_widget(panel)
        return value_label

    def refresh(self):
        game = self.game
        self.red_score.text = str(game.count("red"))
        self.green_score.text = str(game.count("green"))
        self.turn_label.text = game.turn.upper()
        self.turn_label.color = RED if game.turn == "red" else GREEN
        self.status.text = game.message
        self.board.redraw()


class TwelveBeadsApp(App):
    title = "12 Beads"

    def build(self):
        Window.clearcolor = BG
        if platform != "android":
            Window.size = (900, 820)
        self.mode = "two"
        self.cells = [None] * 25
        self.turn = "red"
        self.selected = None
        self.chain_piece = None
        self.game_over = False
        self.wins = {"red": 0, "green": 0}
        self.completed_games = 0
        self.ads = None
        self.message = ""
        self.match_started = False
        self.screen = GameScreen(self)
        self.new_game()
        Clock.schedule_once(lambda _dt: self.show_mode_menu(), 0)
        if platform == "android":
            Clock.schedule_once(self.initialize_ads, 1)
        return self.screen

    def initialize_ads(self, _dt):
        try:
            from kivmob import KivMob
            from ads_config import (ADMOB_APP_ID, BANNER_AD_UNIT_ID,
                                    INTERSTITIAL_AD_UNIT_ID)

            self.ads = KivMob(ADMOB_APP_ID)
            self.ads.new_banner(BANNER_AD_UNIT_ID, top_pos=False)
            self.ads.request_banner()
            self.ads.show_banner()
            self.ads.new_interstitial(INTERSTITIAL_AD_UNIT_ID)
            self.ads.request_interstitial()
        except Exception as error:
            print("AdMob initialization failed:", error)

    def on_resume(self):
        if self.ads:
            try:
                self.ads.request_interstitial()
            except Exception as error:
                print("AdMob interstitial reload failed:", error)

    def refresh(self):
        if hasattr(self, "screen"):
            self.screen.refresh()

    def new_game(self):
        self.cells = [None] * 25
        for index in list(range(0, 10)) + [10, 11]:
            self.cells[index] = "red"
        for index in list(range(15, 25)) + [13, 14]:
            self.cells[index] = "green"
        self.turn = choice(("red", "green"))
        self.selected = None
        self.chain_piece = None
        self.game_over = False
        self.match_started = True
        self.custom_on_new_game()
        self.message = self.turn_message()
        self.refresh()
        if self.mode == "computer" and self.turn == "green":
            Clock.schedule_once(self.computer_move, 0.65)

    def set_mode(self, mode):
        if self.match_started:
            return
        if self.mode == mode:
            return
        self.mode = mode
        self.new_game()

    def show_mode_menu(self):
        self.match_started = False
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        content.add_widget(Label(text="Choose how to play", color=TEXT, bold=True,
                                 font_size=sp(20)))
        for mode, title in (("two", "PLAYER VS PLAYER"), ("computer", "PLAYER VS CPU")):
            button = GameScreen.make_button(title, ACCENT if self.mode == mode else PANEL,
                                            BG if self.mode == mode else TEXT)
            button.bind(on_release=lambda _b, selected=mode: self.start_match(selected))
            content.add_widget(button)
        exit_app = GameScreen.make_button("EXIT GAME", PANEL, TEXT)
        exit_app.bind(on_release=lambda *_: self.request_app_exit())
        content.add_widget(exit_app)
        self.mode_popup = Popup(title="12 BEADS", content=content, size_hint=(0.86, 0.48),
                                auto_dismiss=False, separator_color=ACCENT)
        self.mode_popup.open()

    def show_help(self):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        content.add_widget(Label(
            text=("Move a bead to a connected empty point. Jump over an opponent to capture.\n\n"
                  "If the same bead can capture again, continue the capture chain.\n\n"
                  "Win when your opponent has no beads or no legal move."),
            color=TEXT, halign="left", valign="middle", text_size=(dp(300), None)))
        close = GameScreen.make_button("GOT IT", ACCENT, BG)
        popup = Popup(title="HOW TO PLAY", content=content, size_hint=(0.86, 0.5),
                      separator_color=ACCENT)
        close.bind(on_release=popup.dismiss)
        content.add_widget(close)
        popup.open()

    def confirm_action(self, title, message, action):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        content.add_widget(Label(text=message, color=TEXT, halign="center"))
        buttons = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title=title, content=content, size_hint=(0.86, 0.34),
                      separator_color=ACCENT)
        cancel = GameScreen.make_button("CANCEL", PANEL, TEXT)
        cancel.bind(on_release=popup.dismiss)
        confirm = GameScreen.make_button("CONTINUE", ACCENT, BG)
        confirm.bind(on_release=lambda *_: (popup.dismiss(), action()))
        buttons.add_widget(cancel)
        buttons.add_widget(confirm)
        content.add_widget(buttons)
        popup.open()

    def start_match(self, mode):
        self.mode = mode
        self.custom_on_mode_selected(mode)
        self.mode_popup.dismiss()
        self.new_game()

    # CUSTOM LOGIC HOOKS: add your extra behavior here; these defaults do nothing.
    def custom_on_mode_selected(self, mode):
        pass

    def custom_on_new_game(self):
        pass

    def custom_on_move(self, source, destination, side):
        pass

    def custom_on_exit(self, destination):
        pass

    def exit_to_mode_menu(self):
        self.custom_on_exit("mode_menu")
        self.show_mode_menu()

    def request_app_exit(self):
        self.custom_on_exit("app")
        self.stop()

    @staticmethod
    def count_for(cells, side):
        return sum(piece == side for piece in cells)

    def count(self, side):
        return self.count_for(self.cells, side)

    def turn_message(self):
        if self.mode == "computer":
            return "Your turn" if self.turn == "red" else "Computer's turn"
        return "Red's turn" if self.turn == "red" else "Green's turn"

    def tap_point(self, point):
        if self.game_over or (self.mode == "computer" and self.turn == "green"):
            return
        if self.selected is None:
            if self.cells[point] == self.turn:
                self.selected = point
                moves = self.destinations_for_selection(point)
                if moves:
                    self.message = ("Capture again with this bead" if self.chain_piece is not None
                                    else "Choose a connected point")
                else:
                    self.message = "This bead has no legal moves"
        elif point == self.selected:
            if self.chain_piece is not None:
                self.message = "Capture again with this bead"
            else:
                self.selected = None
                self.message = self.turn_message()
        elif self.cells[point] == self.turn and self.chain_piece is None:
            self.selected = point
            self.message = ("Choose a connected point" if self.destinations_for_selection(point)
                            else "This bead has no legal moves")
        elif point in [destination for destination, _captured
                       in self.destinations_for_selection(self.selected)]:
            self.apply_move(self.selected, point)
        else:
            self.message = "That point is not a legal move"
        self.refresh()

    def destinations_for_selection(self, source):
        moves = self.legal_destinations(source)
        if self.chain_piece == source:
            return [(destination, captured) for destination, captured in moves
                    if captured is not None]
        return moves

    def legal_destinations(self, source, cells=None):
        cells = self.cells if cells is None else cells
        side = cells[source]
        if side is None:
            return []
        moves = []
        for neighbor in GRAPH[source]:
            if cells[neighbor] is None:
                moves.append((neighbor, None))
                continue
            if cells[neighbor] == side:
                continue
            sr, sc = divmod(source, 5)
            nr, nc = divmod(neighbor, 5)
            dr, dc = nr - sr, nc - sc
            landing_row, landing_col = nr + dr, nc + dc
            if 0 <= landing_row < 5 and 0 <= landing_col < 5:
                landing = landing_row * 5 + landing_col
                if landing in GRAPH[neighbor] and cells[landing] is None:
                    moves.append((landing, neighbor))
        return moves

    def moves_for_side(self, side, cells=None):
        cells = self.cells if cells is None else cells
        moves = []
        for source, owner in enumerate(cells):
            if owner == side:
                moves.extend((source, dest, captured)
                             for dest, captured in self.legal_destinations(source, cells))
        return moves

    def apply_move(self, source, destination):
        if self.chain_piece is not None and source != self.chain_piece:
            return
        side = self.cells[source]
        options = dict((dest, captured)
                       for dest, captured in self.destinations_for_selection(source))
        if destination not in options:
            return
        captured = options[destination]
        self.custom_on_move(source, destination, side)
        self.cells[source] = None
        self.cells[destination] = side
        if captured is not None:
            self.cells[captured] = None
        if captured is not None and self.legal_captures(destination):
            self.chain_piece = destination
            self.selected = destination
            self.message = "Capture again with this bead"
            if self.mode == "computer" and self.turn == "green":
                Clock.schedule_once(self.computer_move, 0.5)
        else:
            self.chain_piece = None
            self.selected = None
            self._finish_turn()
        self.screen.board.animate_move(source, destination, side)
        self.refresh()

    def legal_captures(self, source, cells=None):
        return [(dest, captured) for dest, captured in self.legal_destinations(source, cells)
                if captured is not None]

    def _finish_turn(self):
        self.turn = "green" if self.turn == "red" else "red"
        self.selected = None
        self.chain_piece = None
        if self.count(self.turn) == 0 or not self.moves_for_side(self.turn):
            winner = "red" if self.turn == "green" else "green"
            self.game_over = True
            self.completed_games += 1
            self.wins[winner] += 1
            self.message = ("Red wins" if winner == "red" else "Green wins") + "! Start a new game."
            self.finish_game()
            return
        self.message = self.turn_message()
        if self.mode == "computer" and self.turn == "green":
            Clock.schedule_once(self.computer_move, 0.55)

    def finish_game(self):
        if self.ads:
            try:
                self.ads.show_interstitial()
                self.ads.request_interstitial()
            except Exception as error:
                print("AdMob interstitial display failed:", error)
        Clock.schedule_once(self._auto_restart, 1.5)

    def _auto_restart(self, _dt):
        if self.game_over and self.match_started:
            self.new_game()

    def computer_move(self, _dt):
        if (not self.match_started or self.mode != "computer" or self.turn != "green"
                or self.game_over):
            return
        if self.chain_piece is not None:
            source = self.chain_piece
            moves = [(source, destination, captured)
                     for destination, captured in self.legal_captures(source)]
        else:
            moves = self.moves_for_side("green")
        if not moves:
            self._finish_turn()
            self.refresh()
            return
        captures = [move for move in moves if move[2] is not None]
        source, destination, _captured = choice(captures or moves)
        self.apply_move(source, destination)

    def on_pause(self):
        return True


if __name__ == "__main__":
    TwelveBeadsApp().run()
