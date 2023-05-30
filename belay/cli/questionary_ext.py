from typing import Any, Dict, Optional, Sequence, Union

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style, merge_styles
from questionary import utils
from questionary.constants import (
    DEFAULT_QUESTION_PREFIX,
    DEFAULT_SELECTED_POINTER,
    DEFAULT_STYLE,
)
from questionary.prompts import common
from questionary.prompts.common import Choice, InquirerControl
from questionary.question import Question


def press_any_key_to_continue(
    message: str = "Press any key to continue...",
    style: Optional[Style] = None,
    **kwargs,
):
    """Wait until user presses any key to continue.

    Example:
        >>> import questionary
        >>> questionary.press_any_key_to_continue().ask()
         Press any key to continue...
        None

    Args:
        message: Question text.

        style: A custom color and style for the question parts. You can
               configure colors as well as font types for different elements.
    """
    merged_style = merge_styles([DEFAULT_STYLE, style])

    def get_prompt_tokens():
        tokens = []

        tokens.append(("class:question", f" {message} "))

        return to_formatted_text(tokens)

    def exit_with_result(event):
        event.app.exit(result=None)

    bindings = KeyBindings()

    @bindings.add(Keys.Any)
    def any_key(event):
        exit_with_result(event)

    return Question(PromptSession(get_prompt_tokens, key_bindings=bindings, style=merged_style, **kwargs).app)


def select_table(
    message: str,
    header: str,
    choices: Sequence[Union[str, Choice, Dict[str, Any]]],
    default: Optional[Union[str, Choice, Dict[str, Any]]] = None,
    qmark: str = DEFAULT_QUESTION_PREFIX,
    pointer: Optional[str] = DEFAULT_SELECTED_POINTER,
    style: Optional[Style] = None,
    use_indicator: bool = False,
    **kwargs: Any,
) -> Question:
    """A list of items to select **one** option from.

    Simplified to work better with a formatted table.

    Args:
        message: Question text
        header: Table header text
        choices: Items shown in the selection, this can contain :class:`Choice` or
                 or :class:`Separator` objects or simple items as strings. Passing
                 :class:`Choice` objects, allows you to configure the item more
                 (e.g. preselecting it or disabling it).
        default: A value corresponding to a selectable item in the choices,
                 to initially set the pointer position to.
        qmark: Question prefix displayed in front of the question.
               By default this is a ``?``.
        pointer: Pointer symbol in front of the currently highlighted element.
                 By default this is a ``»``.
                 Use ``None`` to disable it.
        style: A custom color and style for the question parts. You can
               configure colors as well as font types for different elements.
        use_indicator: Flag to enable the small indicator in front of the
                       list highlighting the current location of the selection
                       cursor.

    Returns
    -------
        :class:`Question`: Question instance, ready to be prompted (using ``.ask()``).
    """
    if choices is None or len(choices) == 0:
        raise ValueError("A list of choices needs to be provided.")

    merged_style = merge_styles([DEFAULT_STYLE, style])

    ic = InquirerControl(
        choices,
        default,
        pointer=pointer,
        use_indicator=use_indicator,
        initial_choice=default,
    )

    def get_prompt_tokens():
        # noinspection PyListCreation
        tokens = [
            ("class:qmark", qmark),
            ("class:question", f" {message} "),
            ("class:question", "\n   " + header),
        ]

        if ic.is_answered:
            tokens.append(("class:answer", "\n   " + ic.get_pointed_at().title))

        return tokens

    layout = common.create_inquirer_layout(ic, get_prompt_tokens, **kwargs)

    bindings = KeyBindings()

    @bindings.add(Keys.ControlQ, eager=True)
    @bindings.add(Keys.ControlC, eager=True)
    def _(event):
        event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    @bindings.add(Keys.Down, eager=True)
    @bindings.add("j", eager=True)
    @bindings.add(Keys.ControlN, eager=True)
    def move_cursor_down(event):
        ic.select_next()
        while not ic.is_selection_valid():
            ic.select_next()

    @bindings.add(Keys.Up, eager=True)
    @bindings.add("k", eager=True)
    @bindings.add(Keys.ControlP, eager=True)
    def move_cursor_up(event):
        ic.select_previous()
        while not ic.is_selection_valid():
            ic.select_previous()

    @bindings.add(Keys.ControlM, eager=True)
    def set_answer(event):
        ic.is_answered = True
        event.app.exit(result=ic.get_pointed_at().value)

    @bindings.add(Keys.Any)
    def other(event):
        """Disallow inserting other text."""

    return Question(
        Application(
            layout=layout,
            key_bindings=bindings,
            style=merged_style,
            **utils.used_kwargs(kwargs, Application.__init__),
        )
    )
