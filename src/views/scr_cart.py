import asyncio

from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, HorizontalGroup, VerticalScroll
from textual.events import ScreenResume
from textual.message import Message
from textual.widgets import Button, Input, Label, Rule

from db.crud import clear_cart, get_product, list_cart, remove_from_cart
from db.models import CartItem, Product
from utils.messages import CartChangedMessage, ModeSwitchedMessage
from views.base_screen import BaseScreen
from views.modal_checkout import CheckoutModal
from views.modal_dialog import DialogModal
from views.modal_prod_detail import ProdDetailModal


class CartItemActionEditMessage(Message):
    bubble = True


class CartItemActionRemoveMessage(Message):
    bubble = True


class CartItemActionLabel(Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def action_edit(self):
        self.post_message(CartItemActionEditMessage())

    def action_remove(self):
        self.post_message(CartItemActionRemoveMessage())


class CartItemWidget(HorizontalGroup):
    def __init__(self, state, item: CartItem):
        super().__init__()

        self.app.state = state
        self.item = item

        self._prod: Product = None

    def compose(self):
        with Container(id="div-cart-item-group"):
            with Container(id="div-item"):
                yield Label(content="placeholder", id="label-item-name")
                yield Label(content=str(self.item.qty), id="label-item-qty")
                yield Label(content="-1", id="label-item-price")
            with Container(id="div-actions"):
                yield CartItemActionLabel(
                    content="[@click=edit()]Edit[/]", id="link-item-edit"
                )
                yield CartItemActionLabel(
                    content="[@click=remove()]Remove[/]", id="link-item-remove"
                )

    async def on_mount(self):
        self._prod = await get_product(self.item.pid)
        self.query_one("#label-item-name").content = self._prod.name
        self.query_one("#label-item-price").content = "$" + str(
            round(self._prod.price, 2)
        )

    # @on(Button.Pressed, "#btn-item-details")
    @on(CartItemActionEditMessage)
    async def handle_edit_item(self):
        is_cart_changed = await self.app.push_screen_wait(
            ProdDetailModal(self.item.pid)
        )
        if is_cart_changed:
            self.post_message(CartChangedMessage())

    # @on(Button.Pressed, "#btn-item-remove")
    @on(CartItemActionRemoveMessage)
    @work()
    async def handle_remove_item(self):
        remove_confirmed = await self.app.push_screen_wait(
            DialogModal(
                "Do you really want to remove this item from cart?",
                primary_text="Yes",
                secondary_text="No",
                tone="warning",
            )
        )

        if remove_confirmed:
            await remove_from_cart(
                self.app.state.uid, self.app.state.session_no, self.item.pid
            )
            self.post_message(CartChangedMessage())
            self.notify("Item removed from cart.", severity="information")


class CartScreen(BaseScreen):
    """
    prod detail, plus ordering
    """

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield VerticalScroll(id="vertscroll-content")
        yield Label("Total Cart Value: $0", id="label-cart-total")
        yield Rule(line_style="dashed")
        with Horizontal(id="hort-buttons"):
            yield Button("Clear Cart", id="btn-clear-cart")
            yield Button("Refresh", id="btn-refresh")
            yield Button("Checkout", id="btn-checkout", variant="primary")

    async def on_mount(self):
        # get cart items and list them
        self.handle_cart_change()
        # self.stop_refresh()
        # self.add_refresh()

    # refresh every 1 second
    # TODO:
    # dis hack is disgusting, remove it in futures
    def add_refresh(self):
        self._cart_refresh = self.set_interval(
            1.0,  # seconds
            self.handle_cart_change,
            pause=False,
            # keep running as long as screen is active
        )

    def stop_refresh(self):
        try:
            self._cart_refresh.stop()
        except:
            pass

    async def on_unmount(self):
        # stop the interval when screen is no longer visible
        if hasattr(self, "_cart_refresh"):
            self.stop_refresh()

    # TODO:
    # posting from another screen will not work
    # therefore, added a dirty hack to refresh cart every 1 second
    @on(CartChangedMessage)
    @on(ModeSwitchedMessage)
    @on(ScreenResume)
    @on(Button.Pressed, "#btn-refresh")
    @work(exclusive=True)  # must exclusive, else might race cond and gen duplicate
    async def handle_cart_change(self):
        """
        Watch for cart change messsage, update the reactive attribute cart_items
        """
        cart_items = await list_cart(self.app.state.uid, self.app.state.session_no)
        cart_items.sort(key=lambda x: x.pid)

        content = self.query_one("#vertscroll-content")
        content_items = [c.item for c in content.children]
        content_items.sort(key=lambda x: x.pid)

        if content_items == cart_items:
            return

        await content.remove_children()
        entries = [CartItemWidget(self.app.state, item) for item in cart_items]
        await content.mount_all(entries)

        if not cart_items:
            content.add_class("no-items")
        else:
            content.remove_class("no-items")

        products = await asyncio.gather(*(get_product(item.pid) for item in cart_items))
        total_value = round(
            sum(p.price * item.qty for p, item in zip(products, cart_items)), 2
        )
        self.query_one(
            "#label-cart-total"
        ).content = f"Total Cart Value: ${total_value}"

        self.refresh()

    @on(Button.Pressed, "#btn-clear-cart")
    async def handle_clear_cart(self) -> None:
        cart_items = await list_cart(self.app.state.uid, self.app.state.session_no)
        if not cart_items:
            self.app.notify("Cart is empty.", severity="warning")
            return

        remove_confirmed = await self.app.push_screen_wait(
            DialogModal(
                "Do you really want to remove all items from cart?",
                primary_text="Yes",
                secondary_text="No",
                tone="error",
            )
        )
        if remove_confirmed:
            await clear_cart(self.app.state.uid, self.app.state.session_no)
            self.post_message(CartChangedMessage())

    @on(Button.Pressed, "#btn-checkout")
    async def handle_checkout(self) -> None:
        """
        Open up checkout screen
        """
        cart_items = await list_cart(self.app.state.uid, self.app.state.session_no)
        if not cart_items:
            self.app.notify("Cart is empty.", severity="warning")
            return

        await self.app.push_screen_wait(CheckoutModal())
        self.post_message(CartChangedMessage())

    def on_key(self, event: events.Key) -> None:
        pass

    def on_input_changed(self, message: Input.Changed) -> None:
        pass
