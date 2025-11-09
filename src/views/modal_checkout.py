import asyncio
from datetime import datetime

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, MarkdownViewer

from db.crud import checkout, clear_cart, get_product, list_cart
from utils.pure import generate_markdown_table
from views.modal_dialog import DialogModal


class CheckoutModal(ModalScreen[str]):
    """
    A modal screen for check out, including a table of all items and an input for address line.
    Return True on success, False on failure.
    """

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield MarkdownViewer("", show_table_of_contents=False)
            yield Label("Shipping Address")
            yield Input(
                placeholder="123 Main St, Anytown, ST 00000",
                id="input-address-line",
            )
            with Horizontal():
                yield Button("Go Back", id="btn-quit")
                yield Button("Place Order", id="btn-submit", variant="primary")

    async def on_mount(self):
        # generate the order summary
        cart_items = await list_cart(self.app.state.uid, self.app.state.session_no)
        cart_prods = await asyncio.gather(
            *(get_product(item.pid) for item in cart_items)
        )
        total_cost = sum(
            prod.price * item.qty for prod, item in zip(cart_prods, cart_items)
        )
        headers = ["Product Name", "Unit Price", "Quantity", "Total Price"]
        rows = [
            [
                cart_prods[i].name,
                cart_prods[i].price,
                cart_items[i].qty,
                cart_prods[i].price * cart_items[i].qty,
            ]
            for i in range(len(cart_items))
        ]
        aligns = ["l", "c", "c", "c"]
        header_md = "### Order Summary\n\n"
        md = generate_markdown_table(headers, rows, aligns)
        md += f"\n\n**Subtotal:** ${total_cost:.2f}"
        await self.query_one(MarkdownViewer).document.update(header_md + md)
        self.query_one("#input-address-line").focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)

    @on(Button.Pressed, "#btn-submit")
    async def handle_submit(self):
        address_line = self.query_one("#input-address-line", Input).value
        if not address_line:
            self.query_one("#input-address-line", Input).focus()
            self.query_one("#input-address-line", Input).add_class("-invalid")
            self.notify("Address line is required.", severity="error")
            return

        if not await self.app.push_screen_wait(
            DialogModal(
                "Place order? This cannot be undone.",
                primary_text="Yes",
                secondary_text="No",
                tone="positive",
            )
        ):
            self.dismiss(False)
            return

        order_num = await checkout(
            self.app.state.uid, self.app.state.session_no, address_line, datetime.now()
        )
        await clear_cart(self.app.state.uid, self.app.state.session_no)
        self.notify(f"Order placed. Your order number is {order_num}.")
        self.dismiss(True)

    @on(Button.Pressed, "#btn-quit")
    def handle_quit(self):
        self.dismiss(False)
