from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Markdown

from db.crud import get_customer
from utils.messages import ModeSwitchedMessage, UserLoginMessage, UserLogoutMessage
from utils.pure import generate_markdown_table
from views.modal_dialog import DialogModal, QuitDialogModal
from views.modal_resize import ResizeScreenPromptModal


class Sidebar(Container):
    init_mode = ""

    def compose(self) -> ComposeResult:
        # yield Button(">", id="toggle-sidebar")

        yield Label("User Info", id="label-info-1")
        yield Markdown("", id="md-userinfo")
        yield Button("Log out", id="btn-logout", variant="error")
        yield Label("Menu", id="label-info-2")
        yield ListView(id="list-menu")

    async def on_mount(self):
        self.init_mode = self.app.current_mode

        # customer info and list menus
        if self.app.state.role:
            if self.app.state.role == "customer":
                table_align = ["l", "l"]
                table_rows = [
                    ["User ID", self.app.state.uid],
                    ["Name", (await get_customer(self.app.state.uid)).name],
                    ["Role", "Customer"],
                ]
                md_table_str = generate_markdown_table(None, table_rows, table_align)
                await self.query_one(Markdown).update(md_table_str)

                list_menu: ListView = self.query_one("#list-menu")
                await list_menu.clear()
                await list_menu.extend(
                    [
                        ListItem(Label(v), id="list-menu-item-" + k)
                        for k, v in self.app.CUSTOMER_MODES.items()
                    ]
                )
            else:  # sales
                table_align = ["l", "l"]
                table_rows = [["User ID", self.app.state.uid], ["Role", "Sales Person"]]
                md_table_str = generate_markdown_table(None, table_rows, table_align)
                await self.query_one(Markdown).update(md_table_str)

                list_menu: ListView = self.query_one("#list-menu")
                await list_menu.clear()
                await list_menu.extend(
                    [
                        ListItem(Label(v), id="list-menu-item-" + k)
                        for k, v in self.app.SALES_MODES.items()
                    ]
                )

            self.highlight_item(self.init_mode)

    async def on_list_view_selected(self, event: ListView.Selected):
        selected_mode = event.item.id.removeprefix("list-menu-item-")
        print(event.item.id)
        print(selected_mode)
        self.highlight_item(self.init_mode)
        if self.app.current_mode != selected_mode:
            self.post_message(ModeSwitchedMessage(self.app.current_mode, selected_mode))
            await self.app.switch_mode(selected_mode)

    @on(Button.Pressed, "#btn-logout")
    async def handle_logout(self):
        if not await self.app.push_screen_wait(
            DialogModal(
                "Are you sure you want to log out?",
                primary_text="Yes",
                secondary_text="No",
                tone="warning",
            )
        ):
            return

        self.post_message(UserLogoutMessage())

    def highlight_item(self, mode_str: str):
        list_menu = self.query_one("#list-menu")
        for i, item in enumerate(list_menu.children):
            # if item.id == "list-menu-item-" + message.new_mode:
            if mode_str in item.id:
                item.highlighted = True  # self.app.notify(item.id)
            else:
                item.highlighted = False


class BaseScreen(Screen):
    """
    Inherited by all screens, contains common elements like
    headers, footers, sidebar, and keybindings.
    """

    BINDINGS = [
        Binding("ctrl+z", "quit", "Quit App", show=True),
    ]

    def __init__(self):
        super().__init__()

        self.configure()

    def configure(
        self,
        header_sub_title: str = "Base Screen",
        show_sidebar: bool = True,
    ) -> None:
        """
        configure behavior of the base screen
        :return:
        """

        # auto gen titles and subtitles
        self.app.title = "Super Sales Ultra Plus"
        self.sub_title = header_sub_title
        for k, v in self.app.MODES.items():
            if isinstance(self, v):
                if k in self.app.SALES_MODES:
                    self.sub_title = self.app.SALES_MODES[k]
                elif k in self.app.CUSTOMER_MODES:
                    self.sub_title = self.app.CUSTOMER_MODES[k]

        self._show_sidebar = show_sidebar

    def compose(self) -> ComposeResult:
        if self._show_sidebar:
            yield Sidebar()
        yield Header()
        yield Footer(show_command_palette=False)

    async def on_resize(self, event: Resize) -> None:
        min_width = 60
        min_height = 20
        if event.size.width < min_width or event.size.height < min_height:
            self.app.push_screen(ResizeScreenPromptModal(min_width, min_height))

    @on(UserLoginMessage)
    def handle_user_login(self):
        self.refresh()

    @work()
    async def action_quit(self):
        await self.app.push_screen_wait(QuitDialogModal())
