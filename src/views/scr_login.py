from typing import Optional

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.widgets import Button, Input, Label, TabbedContent, TabPane

import db
from utils.messages import UserLoginMessage
from views.base_screen import BaseScreen
from views.modal_dialog import QuitDialogModal, SimpleDialogModal


class LoginScreen(BaseScreen):
    """
    If login succcessful, return uid of user logged in.
    """

    # TODO:
    # input validation and indication of invalid input
    # also input should not be empty
    # responsive ui change when invalid credentials (login)
    # responsive ui change when user id is taken

    def __init__(self):
        super().__init__()
        self.configure(header_sub_title="Login", show_sidebar=False)

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with TabbedContent(id="super-tab-loginscr"):
            with TabPane("Login", id="tab-login"):
                with Vertical(id="div-login"):
                    yield Label("User ID")
                    yield Input(placeholder="1001", id="input-login-uid", type="number")
                    yield Label("Password")
                    yield Input(
                        placeholder="*********", password=True, id="input-login-pwd"
                    )
                    with Horizontal(id="div-login-btns"):
                        yield Button("Quit", id="btn-quit")
                        yield Button("Login", id="btn-login", variant="primary")

            with TabPane("Sign up", id="tab-signup"):
                with Vertical(id="div-reg"):
                    yield Label("Name")
                    yield Input(placeholder="Jane Doe", id="input-reg-name")
                    yield Label("Email")
                    yield Input(
                        placeholder="user@example.com", id="input-reg-email"
                    )
                    yield Label("Password")
                    yield Input(
                        placeholder="*********", password=True, id="input-reg-pwd"
                    )
                    with Container(id="div-reg-btns"):
                        yield Button("Register", id="btn-reg", variant="primary")

    def on_mount(self):
        self.query_one("#input-login-uid").focus()

    def on_key(self, event: Key) -> None:
        if event.key == "enter" and self.focused == self.query_one("#input-login-pwd"):
            self.handle_login_submit()
        if event.key == "enter" and self.focused == self.query_one("#input-reg-pwd"):
            self.handle_registration_submit()

    @on(Button.Pressed, "#btn-login")
    @work(exclusive=True)
    async def handle_login_submit(self) -> Optional[int]:
        uid = self.query_one("#input-login-uid", Input).value.strip()
        pwd = self.query_one("#input-login-pwd", Input).value.strip()

        if not uid or not pwd:
            self.notify("Username or password cannot be empty!", severity="error")
            return

        uid = int(uid)
        user = await db.crud.login(uid, pwd)

        if user:
            self.app.state.uid = user.uid
            self.app.state.role = user.role
            await self.app.state.start_session()

            self.notify(f"Hello {user.uid}!")
            self.app.post_message(UserLoginMessage())
            self.dismiss()
        else:
            self.notify("Invalid username or password.", severity="error")
            input_login_pwd = self.query_one("#input-login-pwd", Input)
            input_login_pwd.value = ""
            input_login_pwd.focus()
            input_login_pwd.add_class("-invalid")

    @on(Button.Pressed, "#btn-reg")
    @work(exclusive=True)
    async def handle_registration_submit(self) -> Optional[int]:
        name = self.query_one("#input-reg-name", Input).value.strip()
        email = self.query_one("#input-reg-email", Input).value.strip()
        pwd = self.query_one("#input-reg-pwd", Input).value.strip()

        if not name or not email or not pwd:
            self.notify("Make sure all inputs are filled.", severity="error")
            return

        if not await db.crud.email_available(email):
            self.notify("Email already taken.", severity="error")
        else:
            uid, cid = await db.crud.register_customer(name, email, pwd)
            await self.app.push_screen_wait(
                SimpleDialogModal(
                    f"Registration successful. uid: {uid}",
                )
            )

            self.get_child_by_type(TabbedContent).active = "tab-login"
            input_login_uid = self.query_one("#input-login-uid", Input)
            input_login_pwd = self.query_one("#input-login-pwd", Input)

            input_login_uid.value = str(uid)
            input_login_pwd.value = pwd
            input_login_pwd.focus()

            self.notify("Registration successful.")

    @on(Button.Pressed, "#btn-quit")
    def handle_quit_(self) -> None:
        self.app.push_screen(QuitDialogModal())
