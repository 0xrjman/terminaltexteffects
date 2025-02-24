from __future__ import annotations

import random
import time
import typing
from collections import namedtuple
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine.animation import Animation
from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.engine.motion import Coord
from terminaltexteffects.engine.terminal import Terminal
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.graphics import Color, Gradient

MATRIX_SYMBOLS_COMMON = (
    "2",
    "5",
    "9",
    "8",
    "Z",
    "*",
    ")",
    ":",
    ".",
    '"',
    "=",
    "+",
    "-",
    "¦",
    "|",
    "_",
)
MATRIX_SYMBOLS_KATA = (
    "ｦ",
    "ｱ",
    "ｳ",
    "ｴ",
    "ｵ",
    "ｶ",
    "ｷ",
    "ｹ",
    "ｺ",
    "ｻ",
    "ｼ",
    "ｽ",
    "ｾ",
    "ｿ",
    "ﾀ",
    "ﾂ",
    "ﾃ",
    "ﾅ",
    "ﾆ",
    "ﾇ",
    "ﾈ",
    "ﾊ",
    "ﾋ",
    "ﾎ",
    "ﾏ",
    "ﾐ",
    "ﾑ",
    "ﾒ",
    "ﾓ",
    "ﾔ",
    "ﾕ",
    "ﾗ",
    "ﾘ",
    "ﾜ",
)


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return Dev, DevConfig


@argclass(
    name="dev",
    help="effect_description",
    description="effect_description",
    epilog="""
    """,
)
@dataclass
class DevConfig(ArgsDataClass):
    highlight_color: Color = ArgField(
        cmd_name=["--highlight-color"],
        type_parser=argvalidators.ColorArg.type_parser,
        default=Color("dbffdb"),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Color for the bottom of the rain column.",
    )  # type: ignore[assignment]
    "Color : Color for the bottom of the rain column."

    rain_color_gradient: tuple[Color, ...] = ArgField(
        cmd_name=["--rain-color-gradient"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("92be92"), Color("185318")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the rain gradient. Colors are selected from the gradient randomly. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the rain gradient. If only one color is provided, the characters will be displayed in that color."

    rain_symbols: tuple[str, ...] = ArgField(
        cmd_name=["--rain-symbols"],
        nargs="+",
        type_parser=argvalidators.Symbol.type_parser,
        default=MATRIX_SYMBOLS_COMMON + MATRIX_SYMBOLS_KATA,
        metavar=argvalidators.Symbol.METAVAR,
        help="Space separated, unquoted, list of symbols to use for the rain.",
    )  # type: ignore[assignment]
    "tuple[str, ...] : Tuple of symbols to use for the rain."

    rain_fall_delay: tuple[int, int] = ArgField(
        cmd_name=["--rain-fall-delay"],
        nargs=2,
        type_parser=argvalidators.IntRange.type_parser,
        default=(4, 20),
        metavar=argvalidators.IntRange.METAVAR,
        help="Delay, in frames, to wait between dropping new rain columns. Columns are dropped in groups sized between 1-3. Actual delay is randomly selected from the range.",
    )  # type: ignore[assignment]
    "tuple[int, int] : Delay, in frames, to wait between dropping new rain columns. Columns are dropped in groups sized between 1-3. Actual delay is randomly selected from the range."

    rain_time: int = ArgField(
        cmd_name="--rain-time",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=15,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Time, in seconds, to display the rain effect before transitioning to the input text.",
    )  # type: ignore[assignment]
    "int : Time, in seconds, to display the rain effect before transitioning to the input text."

    final_gradient_stops: tuple[Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.ColorArg.type_parser,
        nargs="+",
        default=(Color("8A008A"), Color("00D1FF"), Color("FFFFFF")),
        metavar=argvalidators.ColorArg.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] | int = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=12,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] | int : Int or Tuple of ints for the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=5,
        metavar=argvalidators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step. Increase to slow down the gradient animation.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step. Increase to slow down the gradient animation."

    final_gradient_direction: Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "Gradient.Direction : Direction of the final gradient."

    @classmethod
    def get_effect_class(cls):
        return Dev


class DevIterator(BaseEffectIterator[DevConfig]):
    RAIN_COLORS = Gradient(*DevConfig.rain_color_gradient, steps=6)
    CharacterAppearance = namedtuple("CharacterAppearance", ["color", "symbol"])

    class RainColumn:
        def __init__(
            self,
            characters: list[EffectCharacter],
            terminal: Terminal,
            config: DevConfig,
        ) -> None:
            self.terminal = terminal
            self.config = config
            self.characters: list[EffectCharacter] = characters
            self.pending_characters: list[EffectCharacter] = []
            self.matrix_symbols: tuple[str, ...] = config.rain_symbols
            self.setup_column()

        def setup_column(self) -> None:
            for character in self.characters:
                self.terminal.set_character_visibility(character, False)
                self.pending_characters.append(character)
                character.motion.current_coord = character.input_coord
            self.visible_characters: list[EffectCharacter] = []
            self.base_rain_fall_delay = random.randint(self.config.rain_fall_delay[0], self.config.rain_fall_delay[1])
            self.random_rain_fall_delay = 0
            self.length = random.randint(max(1, int(len(self.characters) * 0.1)), len(self.characters))
            self.hold_time = 0
            if self.length == len(self.characters):
                self.hold_time = random.randint(20, 45)

        def trim_column(self) -> None:
            popped_char = self.visible_characters.pop(0)
            self.terminal.set_character_visibility(popped_char, False)
            if len(self.visible_characters) > 1:
                self.fade_last_character()

        def drop_column(self) -> None:
            for character in self.visible_characters:
                character.motion.current_coord = Coord(
                    character.motion.current_coord.column, character.motion.current_coord.row - 1
                )

        def fade_last_character(self) -> None:
            darker_color = Animation.adjust_color_brightness(random.choice(DevIterator.RAIN_COLORS[-3:]), 0.65)  # type: ignore
            self.visible_characters[0].animation.set_appearance(
                self.visible_characters[0].animation.current_character_visual.symbol, darker_color
            )

        def tick(self) -> None:
            if not self.random_rain_fall_delay:
                if self.pending_characters:
                    next_char = self.pending_characters.pop(0)
                    next_char.animation.set_appearance(random.choice(self.matrix_symbols), self.config.highlight_color)
                    previous_character = self.visible_characters[-1] if self.visible_characters else None
                    # if there is a previous character, remove the highlight
                    if previous_character:
                        previous_character.animation.set_appearance(
                            previous_character.animation.current_character_visual.symbol,
                            random.choice(DevIterator.RAIN_COLORS),
                        )
                    self.terminal.set_character_visibility(next_char, True)
                    self.visible_characters.append(next_char)

                # if no pending characters, but still visible characters, trim the column
                # unless the column is the full height of the canvas, then respect the hold
                # time before trimming
                else:
                    if self.visible_characters:
                        # adjust the bottom character color to remove the lightlight.
                        # always do this on the first hold frame, then
                        # randomly adjust the bottom character's color
                        # this is separately handled from the rest to prevent the
                        # highlight color from being replaced before appropriate
                        if (
                            self.visible_characters[-1].animation.current_character_visual.color
                            == self.config.highlight_color
                        ):
                            self.visible_characters[-1].animation.set_appearance(
                                self.visible_characters[-1].animation.current_character_visual.symbol,
                                random.choice(DevIterator.RAIN_COLORS),
                            )

                        if self.hold_time:
                            self.hold_time -= 1
                        else:
                            if random.random() < 0.05:
                                self.drop_column()
                            self.trim_column()

                # if the column is longer than the preset length while still adding characters, trim it
                if len(self.visible_characters) > self.length:
                    self.trim_column()
                self.random_rain_fall_delay = self.base_rain_fall_delay

            else:
                self.random_rain_fall_delay -= 1

            # randomly change the symbol and/or color of the characters
            next_color: Color | None
            for character in self.visible_characters:
                if random.random() < 0.005:
                    next_symbol = random.choice(self.matrix_symbols)
                else:
                    next_symbol = character.animation.current_character_visual.symbol
                if random.random() < 0.001:
                    next_color = random.choice(DevIterator.RAIN_COLORS)
                else:
                    next_color = character.animation.current_character_visual.color
                character.animation.set_appearance(next_symbol, next_color)

    def __init__(self, effect: Dev) -> None:
        super().__init__(effect)
        self.pending_columns: list[DevIterator.RainColumn] = []
        self.character_final_color_map: dict[EffectCharacter, Color] = {}
        self.active_columns: list[DevIterator.RainColumn] = []
        self.column_delay = 0
        self.phase = "rain"
        self.build()
        self.rain_start = time.time()

    def add_character_to_active_characters(self, character: EffectCharacter) -> None:
        self.active_characters.append(character)

    def build(self) -> None:
        final_gradient = Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.canvas.top, self.terminal.canvas.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            resolve_scn = character.animation.new_scene(id="resolve")
            for color in Gradient(self.config.highlight_color, final_gradient_mapping[character.input_coord], steps=8):
                resolve_scn.add_frame(character.input_symbol, self.config.final_gradient_frames, color=color)

        for column_chars in self.terminal.get_characters_grouped(
            self.terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT, fill_chars=True
        ):
            column_chars.reverse()
            self.pending_columns.append(DevIterator.RainColumn(column_chars, self.terminal, self.config))
        random.shuffle(self.pending_columns)

    def __next__(self) -> str:
        if self.phase == "rain":
            if self.pending_columns and not self.column_delay:
                for _ in range(random.randint(1, 3)):
                    if self.pending_columns:
                        self.active_columns.append(self.pending_columns.pop(0))
                self.column_delay = random.randint(5, 15)
            else:
                self.column_delay -= 1
            for column in self.active_columns:
                column.tick()
                if not column.visible_characters and not column.pending_characters:
                    self.pending_columns.append(column)
                    column.setup_column()
            self.active_columns = [
                column for column in self.active_columns if column.visible_characters or column.pending_characters
            ]

            self.update()
            if time.time() - self.rain_start > self.config.rain_time:
                self.phase = "resolve"
            return self.frame

        else:
            raise StopIteration


class Dev(BaseEffect[DevConfig]):
    """Effect description."""

    _config_cls = DevConfig
    _iterator_cls = DevIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
