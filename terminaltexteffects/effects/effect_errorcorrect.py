"""Swaps characters from an incorrect initial position to the correct position.

Classes:
    ErrorCorrect: Swaps characters from an incorrect initial position to the correct position.
    ErrorCorrectConfig: Configuration for the ErrorCorrect effect.
    ErrorCorrectIterator: Iterates over the effect. Does not normally need to be called directly.
"""

import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.argvalidators as argvalidators
from terminaltexteffects.engine import animation
from terminaltexteffects.engine.base_character import EffectCharacter, EventHandler
from terminaltexteffects.engine.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return ErrorCorrect, ErrorCorrectConfig


@argclass(
    name="errorcorrect",
    help="Some characters start in the wrong position and are corrected in sequence.",
    description="errorcorrect | Some characters start in the wrong position and are corrected in sequence.",
    epilog=f"""{argvalidators.EASING_EPILOG}
    
Example: terminaltexteffects errorcorrect --error-pairs 0.1 --swap-delay 10 --error-color e74c3c --correct-color 45bf55 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --movement-speed 0.5""",
)
@dataclass
class ErrorCorrectConfig(ArgsDataClass):
    """Configuration for the ErrorCorrect effect.

    Attributes:
        error_pairs (float): Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position. Valid values are 0 < n <= 1.0.
        swap_delay (int): Number of frames between swaps. Valid values are n >= 0.
        error_color (graphics.Color): Color for the characters that are in the wrong position.
        correct_color (graphics.Color): Color for the characters once corrected, this is a gradient from error-color and fades to final-color.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation. Valid values are n > 0.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the final gradient.
        movement_speed (float): Speed of the characters while moving to the correct position. Valid values are n > 0."""

    error_pairs: float = ArgField(
        cmd_name="--error-pairs",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.1,
        metavar="(int > 0)",
        help="Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position.",
    )  # type: ignore[assignment]
    "float : Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position."

    swap_delay: int = ArgField(
        cmd_name="--swap-delay",
        type_parser=argvalidators.PositiveInt.type_parser,
        default=10,
        metavar="(int > 0)",
        help="Number of frames between swaps.",
    )  # type: ignore[assignment]
    "int : Number of frames between swaps."

    error_color: graphics.Color = ArgField(
        cmd_name=["--error-color"],
        type_parser=argvalidators.Color.type_parser,
        default="e74c3c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters that are in the wrong position.",
    )  # type: ignore[assignment]
    "graphics.Color : Color for the characters that are in the wrong position."

    correct_color: graphics.Color = ArgField(
        cmd_name=["--correct-color"],
        type_parser=argvalidators.Color.type_parser,
        default="45bf55",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters once corrected, this is a gradient from error-color and fades to final-color.",
    )  # type: ignore[assignment]
    "graphics.Color : Color for the characters once corrected, this is a gradient from error-color and fades to final-color."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=argvalidators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the final color gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=argvalidators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar="(int > 0)",
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=argvalidators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=argvalidators.GradientDirection.METAVAR,
        help="Direction of the final gradient.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the final gradient."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=argvalidators.PositiveFloat.type_parser,
        default=0.5,
        metavar="(float > 0)",
        help="Speed of the characters while moving to the correct position. ",
    )  # type: ignore[assignment]
    "float : Speed of the characters while moving to the correct position. "

    @classmethod
    def get_effect_class(cls):
        return ErrorCorrect


class ErrorCorrectIterator(BaseEffectIterator[ErrorCorrectConfig]):
    def __init__(self, effect: "ErrorCorrect") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._swapped: list[tuple[EffectCharacter, EffectCharacter]] = []
        self._swap_delay = 0
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        for character in self._terminal.get_characters():
            spawn_scene = character.animation.new_scene()
            spawn_scene.add_frame(character.input_symbol, 1, color=self._character_final_color_map[character])
            character.animation.activate_scene(spawn_scene)
            self._terminal.set_character_visibility(character, True)
        all_characters: list[EffectCharacter] = list(self._terminal._input_characters)
        correcting_gradient = graphics.Gradient(self._config.error_color, self._config.correct_color, steps=10)
        block_symbol = "▓"
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        for _ in range(int(self._config.error_pairs * len(self._terminal.get_characters()))):
            if len(all_characters) < 2:
                break
            char1 = all_characters.pop(random.randrange(len(all_characters)))
            char2 = all_characters.pop(random.randrange(len(all_characters)))
            char1.motion.set_coordinate(char2.input_coord)
            char1_input_coord_path = char1.motion.new_path(id="input_coord", speed=self._config.movement_speed)
            char1_input_coord_path.new_waypoint(char1.input_coord)
            char2.motion.set_coordinate(char1.input_coord)
            char2_input_coord_path = char2.motion.new_path(id="input_coord", speed=self._config.movement_speed)
            char2_input_coord_path.new_waypoint(char2.input_coord)
            self._swapped.append((char1, char2))
            for character in (char1, char2):
                first_block_wipe = character.animation.new_scene()
                last_block_wipe = character.animation.new_scene()
                for block in block_wipe_start:
                    first_block_wipe.add_frame(block, 3, color=self._config.error_color)
                for block in block_wipe_end:
                    last_block_wipe.add_frame(block, 3, color=self._config.correct_color)
                initial_scene = character.animation.new_scene()
                initial_scene.add_frame(character.input_symbol, 1, color=self._config.error_color)
                character.animation.activate_scene(initial_scene)
                error_scene = character.animation.new_scene(id="error")
                for _ in range(10):
                    error_scene.add_frame(block_symbol, 3, color=self._config.error_color)
                    error_scene.add_frame(character.input_symbol, 3, color="ffffff")
                correcting_scene = character.animation.new_scene(sync=animation.SyncMetric.DISTANCE)
                correcting_scene.apply_gradient_to_symbols(correcting_gradient, "█", 3)
                final_scene = character.animation.new_scene()
                char_final_gradient = graphics.Gradient(
                    self._config.correct_color, self._character_final_color_map[character], steps=10
                )
                final_scene.apply_gradient_to_symbols(char_final_gradient, character.input_symbol, 3)
                input_coord_path = character.motion.query_path("input_coord")
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    error_scene,
                    EventHandler.Action.ACTIVATE_SCENE,
                    first_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    correcting_scene,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_PATH,
                    input_coord_path,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    1,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    0,
                )

                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    last_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    last_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    final_scene,
                )

    def __next__(self) -> str:
        if self._swapped and not self._swap_delay:
            next_pair = self._swapped.pop(0)
            for char in next_pair:
                char.animation.activate_scene(char.animation.query_scene("error"))
                self._active_chars.append(char)
            self._swap_delay = self._config.swap_delay
        elif self._swap_delay:
            self._swap_delay -= 1
        if self._active_chars:
            for character in self._active_chars:
                character.tick()
            next_frame = self._terminal.get_formatted_output_string()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            return next_frame
        else:
            raise StopIteration


class ErrorCorrect(BaseEffect[ErrorCorrectConfig]):
    """Swaps characters from an incorrect initial position to the correct position.

    Attributes:
        effect_config (ErrorCorrectConfig): Configuration for the effect.
        terminal_config (TerminalConfig): Configuration for the terminal.
    """

    _config_cls = ErrorCorrectConfig
    _iterator_cls = ErrorCorrectIterator

    def __init__(self, input_data: str) -> None:
        """Initialize the effect with the provided input data.

        Args:
            input_data (str): The input data to use for the effect."""
        super().__init__(input_data)
