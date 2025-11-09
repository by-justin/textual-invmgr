from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import Label


class ResizeScreenPromptModal(ModalScreen[bool]):
    """
    A simple dialog box,
    """

    def __init__(self, min_width: int = 40, min_height: int = 60) -> None:
        super().__init__()
        self.min_width = min_width
        self.min_height = min_height

    def compose(self) -> ComposeResult:
        with Container(id="div-resize"):
            yield Label("Resize to fit the content", id="prompt")

    def on_resize(self, event: Resize) -> None:
        if not (
            event.size.width < self.min_width or event.size.height < self.min_height
        ):
            self.dismiss()
