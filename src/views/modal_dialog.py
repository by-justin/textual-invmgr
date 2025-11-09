from typing import Dict, Literal, Tuple, override

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from utils.messages import QuitRequestedMessage


class DialogModal(ModalScreen[bool]):
    """
    A simple dialog box,
    """

    # CSS_PATH = "modal_quit.tcss"
    VARIANT_MAP: Dict[
        str, Tuple[Literal["primary", "default", "success", "warning", "error"]]
    ] = {
        "default": ("primary", "default"),
        "positive": ("success", "default"),
        "warning": ("warning", "default"),
        "error": ("error", "primary"),
    }

    def __init__(
        self,
        caption: str,
        primary_text: str = "OK",
        secondary_text: str = "",
        tone: Literal["default", "positive", "warning", "error"] = "default",
    ):
        super().__init__()
        self.caption = caption
        self.primary_text = primary_text
        self.secondary_text = secondary_text
        self.tone = tone

    def compose(self) -> ComposeResult:
        with Container(id="div-dialog"):
            yield Label(self.caption, id="caption")
            with Horizontal(id="dialog"):
                if self.secondary_text:
                    yield Button(
                        self.secondary_text,
                        variant=DialogModal.VARIANT_MAP[self.tone][1],
                        id="btn-secondary",
                    )
                yield Button(
                    self.primary_text,
                    variant=DialogModal.VARIANT_MAP[self.tone][0],
                    id="btn-primary",
                )

    def on_mount(self):
        # set focus
        if not self.secondary_text or not self.tone == "error":
            self.query_one("#btn-primary").focus()
        else:
            self.query_one("#btn-secondary").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-primary":
            self.dismiss(True)
        if event.button.id == "btn-secondary":
            self.dismiss(False)


class SimpleDialogModal(DialogModal):
    def __init__(self, caption: str):
        super().__init__(caption)


class QuitDialogModal(DialogModal):
    def __init__(self):
        super().__init__("Are you sure you want to quit?", "Yes", "No", "error")

    @override
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-primary":
            self.post_message(QuitRequestedMessage())
            self.dismiss(True)
        else:
            self.dismiss(False)
