from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import LoadingIndicator

from utils.messages import ModeSwitchedMessage, QuitRequestedMessage, UserLogoutMessage
from utils.state import GlobalState
from views.scr_cart import CartScreen
from views.scr_login import LoginScreen
from views.scr_past_orders import PastOrdersScreen
from views.scr_prod_search import ProdSearchScreen
from views.scr_sales_manage_product import SalesManageProductScreen
from views.scr_sales_report import SalesReportScreen


class InvMgrApp(App):
    BINDINGS = [
        Binding("ctrl+t", "switch_light", "Toggle Theme", show=True),
    ]

    MODES = {
        "prod_search": ProdSearchScreen,
        "cart": CartScreen,
        "past_orders": PastOrdersScreen,
        "ss_mgr": SalesManageProductScreen,
        "ss_top": SalesReportScreen,
    }

    SALES_MODES = {"ss_mgr": "Inventory Management", "ss_top": "Sales Report"}
    CUSTOMER_MODES = {
        "prod_search": "Search Products",
        "cart": "Cart",
        "past_orders": "Past Orders",
    }

    CSS_PATH = [
        "styles/index.tcss",
        "styles/login.tcss",
        "styles/search_prod.tcss",
        "styles/cart.tcss",
        "styles/past_orders.tcss",
        "styles/ss_mgr.tcss",
        "styles/ss_top.tcss",
    ]

    state: GlobalState

    def __init__(self):
        super().__init__()
        self.state = GlobalState()

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()

    async def on_mount(self) -> None:
        self.main_flow()

    def action_switch_light(self):
        if self.theme == "textual-dark":
            self.theme = "solarized-light"
        else:
            self.theme = "textual-dark"
        self.notify(f"Theme changed to {self.theme}")

    @on(UserLogoutMessage)
    @work
    async def handle_user_logout(self):
        await self.state.end_session()
        self.notify("Logout successful.")
        self.main_flow()

    @on(QuitRequestedMessage)
    @work
    async def handle_quit(self):
        if self.state.uid:
            await self.state.end_session()
        self.exit()

    @work
    async def main_flow(self):
        await self.push_screen_wait(LoginScreen())
        # self.state.uid = 9001
        # self.state.role = "sales"
        # self.state.start_session()
        if self.state.role == "customer":
            self.app.post_message(
                ModeSwitchedMessage(self.app.current_mode, "prod_search")
            )
            await self.switch_mode("prod_search")
        elif self.state.role == "sales":
            self.app.post_message(
                ModeSwitchedMessage(self.app.current_mode, "sales_top")
            )
            await self.switch_mode("ss_top")


if __name__ == "__main__":
    app = InvMgrApp()
    app.run()
