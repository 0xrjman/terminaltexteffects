import random
import typing
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.base_effect import BaseEffect, BaseEffectIterator
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return BinaryPath, BinaryPathConfig


@argclass(
    name="binarypath",
    help="Binary representations of each character move through the terminal towards the home coordinate of the character.",
    description="binarypath | Binary representations of each character move through the terminal towards the home coordinate of the character.",
    epilog="""Example: terminaltexteffects binarypath --final-gradient-stops 00d500 007500 --final-gradient-steps 12 --final-gradient-direction vertical --binary-colors 044E29 157e38 45bf55 95ed87 --movement-speed 1.0 --active-binary-groups 0.05""",
)
@dataclass
class BinaryPathConfig(ArgsDataClass):
    """Configuration for the BinaryPath effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        binary_colors (tuple[graphics.Color, ...]): Tuple of colors for the binary characters. Character color is randomly assigned from this list.
        movement_speed (float): Speed of the binary groups as they travel around the terminal.
        active_binary_groups (float): Maximum number of binary groups that are active at any given time as a percentage of the total number of binary groups. Lower this to improve performance."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("00d500", "007500"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name=["--final-gradient-steps"],
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]

    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.CENTER,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]

    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    binary_colors: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--binary-colors"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("044E29", "157e38", "45bf55", "95ed87"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the binary characters. Character color is randomly assigned from this list.",
    )  # type: ignore[assignment]

    "tuple[graphics.Color, ...] : Tuple of colors for the binary characters. Character color is randomly assigned from this list."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=1.0,
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Speed of the binary groups as they travel around the terminal.",
    )  # type: ignore[assignment]

    "float : Speed of the binary groups as they travel around the terminal."

    active_binary_groups: float = ArgField(
        cmd_name="--active-binary-groups",
        type_parser=arg_validators.Ratio.type_parser,
        default=0.05,
        metavar=arg_validators.Ratio.METAVAR,
        help="Maximum number of binary groups that are active at any given time as a percentage of the total number of binary groups. Lower this to improve performance.",
    )  # type: ignore[assignment]

    "float : Maximum number of binary groups that are active at any given time as a percentage of the total number of binary groups. Lower this to improve performance."

    @classmethod
    def get_effect_class(cls):
        return BinaryPath


class _BinaryRepresentation:
    def __init__(self, character: EffectCharacter, terminal: Terminal):
        self.character = character
        self.terminal = terminal
        self.binary_string = format(ord(self.character.symbol), "08b")
        self.binary_characters: list[EffectCharacter] = []
        self.pending_binary_characters: list[EffectCharacter] = []
        self.input_coord = self.character.input_coord
        self.is_active = False

    def travel_complete(self) -> bool:
        """Determines if the binary representation has completed its travel, meaning all binary characters have reached their input coordinate.

        Returns:
            bool: True if the binary representation has completed its travel, False otherwise.
        """
        return all(bin_char.motion.current_coord == self.input_coord for bin_char in self.binary_characters)

    def deactivate(self) -> None:
        """Deactivates the binary representation by deactivating all binary characters."""
        for bin_char in self.binary_characters:
            self.terminal.set_character_visibility(bin_char, False)
        self.is_active = False

    def activate_source_character(self) -> None:
        """Activates the source character of the binary representation."""
        self.terminal.set_character_visibility(self.character, True)
        self.character.animation.activate_scene(self.character.animation.query_scene("collapse_scn"))


class BinaryPathIterator(BaseEffectIterator[BinaryPathConfig]):
    def __init__(self, effect: "BinaryPath") -> None:
        super().__init__(effect)
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._pending_binary_representations: list[_BinaryRepresentation] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}
        self._last_frame_provided = False
        self._active_binary_reps: list[_BinaryRepresentation] = []
        self._complete = False
        self._phase = "travel"
        self._final_wipe_chars = self._terminal.get_characters_grouped(
            grouping=self._terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT
        )
        self._max_active_binary_groups: int = 0

        self._build()

    def _build(self) -> None:
        final_gradient = graphics.Gradient(*self._config.final_gradient_stops, steps=self._config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self._terminal.output_area.top, self._terminal.output_area.right, self._config.final_gradient_direction
        )
        for character in self._terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]

        for character in self._terminal.get_characters():
            bin_rep = _BinaryRepresentation(character, self._terminal)
            for binary_char in bin_rep.binary_string:
                bin_rep.binary_characters.append(self._terminal.add_character(binary_char, Coord(0, 0)))
                bin_rep.pending_binary_characters.append(bin_rep.binary_characters[-1])
            self._pending_binary_representations.append(bin_rep)

        for bin_rep in self._pending_binary_representations:
            path_coords: list[Coord] = []
            starting_coord = self._terminal.output_area.random_coord(outside_scope=True)
            path_coords.append(starting_coord)
            last_orientation = random.choice(("col", "row"))
            while path_coords[-1] != bin_rep.character.input_coord:
                last_coord = path_coords[-1]
                if last_coord.column > bin_rep.character.input_coord.column:
                    column_direction = -1
                elif last_coord.column == bin_rep.character.input_coord.column:
                    column_direction = 0
                else:
                    column_direction = 1
                if last_coord.row > bin_rep.character.input_coord.row:
                    row_direction = -1
                elif last_coord.row == bin_rep.character.input_coord.row:
                    row_direction = 0
                else:
                    row_direction = 1
                max_column_distance = abs(last_coord.column - bin_rep.character.input_coord.column)
                max_row_distance = abs(last_coord.row - bin_rep.character.input_coord.row)
                if last_orientation == "col" and max_row_distance > 0:
                    next_coord = Coord(
                        last_coord.column,
                        last_coord.row
                        + (
                            random.randint(1, min(max_row_distance, max(10, int(self._terminal.input_width * 0.2))))
                            * row_direction
                        ),
                    )
                    last_orientation = "row"
                elif last_orientation == "row" and max_column_distance > 0:
                    next_coord = Coord(
                        last_coord.column + (random.randint(1, min(max_column_distance, 4)) * column_direction),
                        last_coord.row,
                    )
                    last_orientation = "col"
                else:
                    next_coord = bin_rep.character.input_coord

                path_coords.append(next_coord)

            path_coords.append(next_coord)
            final_coord = bin_rep.character.input_coord
            path_coords.append(final_coord)
            for bin_effectchar in bin_rep.binary_characters:
                bin_effectchar.motion.set_coordinate(path_coords[0])
                digital_path = bin_effectchar.motion.new_path(speed=self._config.movement_speed)
                for coord in path_coords:
                    digital_path.new_waypoint(coord)
                bin_effectchar.motion.activate_path(digital_path)
                bin_effectchar.layer = 1
                color_scn = bin_effectchar.animation.new_scene()
                color_scn.add_frame(bin_effectchar.symbol, 1, color=random.choice(self._config.binary_colors))
                bin_effectchar.animation.activate_scene(color_scn)

        for character in self._terminal.get_characters():
            collapse_scn = character.animation.new_scene(ease=easing.in_quad, id="collapse_scn")
            dim_color = character.animation.adjust_color_brightness(self._character_final_color_map[character], 0.5)
            dim_gradient = graphics.Gradient("ffffff", dim_color, steps=10)
            collapse_scn.apply_gradient_to_symbols(dim_gradient, character.input_symbol, 7)

            brighten_scn = character.animation.new_scene(id="brighten_scn")
            brighten_gradient = graphics.Gradient(dim_color, self._character_final_color_map[character], steps=10)
            brighten_scn.apply_gradient_to_symbols(brighten_gradient, character.input_symbol, 2)
        self._max_active_binary_groups = max(
            1, int(self._config.active_binary_groups * len(self._pending_binary_representations))
        )

    def __next__(self) -> str:
        if not self._complete or self._active_chars:
            if self._phase == "travel":
                while (
                    len(self._active_binary_reps) < self._max_active_binary_groups
                    and self._pending_binary_representations
                ):
                    next_binary_rep = self._pending_binary_representations.pop(
                        random.randrange(len(self._pending_binary_representations))
                    )
                    next_binary_rep.is_active = True
                    self._active_binary_reps.append(next_binary_rep)

                if self._active_binary_reps:
                    for active_rep in self._active_binary_reps:
                        if active_rep.pending_binary_characters:
                            next_char = active_rep.pending_binary_characters.pop(0)
                            self._active_chars.append(next_char)
                            self._terminal.set_character_visibility(next_char, True)
                        elif active_rep.travel_complete():
                            active_rep.deactivate()
                            active_rep.activate_source_character()
                            self._active_chars.append(active_rep.character)

                    self._active_binary_reps = [
                        binary_rep for binary_rep in self._active_binary_reps if binary_rep.is_active
                    ]

                if not self._active_chars:
                    self._phase = "wipe"

            if self._phase == "wipe":
                if self._final_wipe_chars:
                    next_group = self._final_wipe_chars.pop(0)
                    for character in next_group:
                        character.animation.activate_scene(character.animation.query_scene("brighten_scn"))
                        self._terminal.set_character_visibility(character, True)
                        self._active_chars.append(character)
                else:
                    self._complete = True
            next_frame = self._terminal.get_formatted_output_string()
            for character in self._active_chars:
                character.tick()

            self._active_chars = [character for character in self._active_chars if character.is_active]
            return next_frame
        elif not self._last_frame_provided:
            self._last_frame_provided = True
            return self._terminal.get_formatted_output_string()
        else:
            raise StopIteration


class BinaryPath(BaseEffect):
    """Effect that decodes characters into their binary form. Characters travel from outside the output area towards their input coordinate,
    moving at right angles."""

    _config_cls = BinaryPathConfig
    _iterator_cls = BinaryPathIterator

    def __init__(self, input_data: str) -> None:
        super().__init__(input_data)
