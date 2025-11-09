import dataclasses
from datetime import datetime

from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.validation import Number
from textual.widgets import Button, Input, Label, MarkdownViewer

from db.crud import add_to_cart, get_product, list_cart, record_view, update_cart_qty
from db.models import CartItem, Product
from utils.messages import CartChangedMessage
from utils.pure import generate_markdown_table


class ProdDetailModal(ModalScreen[bool]):
    """
    prod detail, plus ordering
    Will return true of cart changed, false if not
    """

    # TODO: remove this
    CSS = """
    #input-order-qty { 
        width: 10; 
    } 
    #btn-sub-qty { 
        min-width: 4
    }
    #btn-add-qty { 
        min-width: 4
    }
    """

    order_qty = reactive(1)

    def __init__(self, pid: int) -> None:
        super().__init__()

        self._pid = pid

        self._prod: Product = None
        self._existing_cart_item: CartItem = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="hort-prod-detail"):
            yield MarkdownViewer("", show_table_of_contents=False)
            with Vertical():
                yield Label("Order Quantity")
                with Horizontal():
                    yield Button("-", id="btn-sub-qty")
                    yield Input(value="1", id="input-order-qty", type="integer")
                    yield Button("+", id="btn-add-qty")
                with Horizontal():
                    yield Button("Go Back", id="btn-quit")
                    yield Button("Add to Cart", id="btn-addcart", variant="primary")

    async def on_mount(self):
        # get prod detail
        await record_view(
            self.app.state.uid, self.app.state.session_no, self._pid, datetime.now()
        )
        self._prod = await get_product(self._pid)

        # generate markdown table
        table_headers = ["Attribute", "Value"]
        table_align = ["l", "l"]
        table_rows = [[k, v] for k, v in dataclasses.asdict(self._prod).items()]
        md_table_str = generate_markdown_table(table_headers, table_rows, table_align)
        header_md = f"### Product Detail: {self._prod.name}\n\n"
        await self.query_one(MarkdownViewer).document.update(header_md + md_table_str)

        # update elements depending on stock cnt
        stock_cnt = self._prod.stock_count
        if stock_cnt < 1:
            order_btn = self.query_one("#btn-addcart")
            order_btn.label = "Out of Stock"
            order_btn.disabled = True
            order_btn.variant = "warning"

        self.query_one("#input-order-qty").validators = [
            Number(minimum=1, maximum=stock_cnt)
        ]

        # update elements based on cart status
        cart_items = await list_cart(self.app.state.uid, self.app.state.session_no)
        for item in cart_items:
            if item.pid == self._pid:
                self._existing_cart_item = item
                break
        if self._existing_cart_item:
            self.query_one("#input-order-qty").value = str(self._existing_cart_item.qty)
            self.query_one("#btn-addcart").label = "Update Cart"

        # other ui change
        self.query_one("#input-order-qty").focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(False)

    async def on_input_changed(self, message: Input.Changed) -> None:
        if (
            message.input.id == "input-order-qty"
            and message.input.is_valid
            and self.focused == message.input
        ):
            self.order_qty = int(message.value)

    async def watch_order_qty(self, qty: int):
        btn_sub_qty = self.query_one("#btn-sub-qty")
        btn_add_qty = self.query_one("#btn-add-qty")

        btn_sub_qty.disabled = False
        btn_add_qty.disabled = False
        if self.order_qty == 1:
            btn_sub_qty.disabled = True
        if self.order_qty == self._prod.stock_count:
            btn_add_qty.disabled = True

        input_order_qty = self.query_one("#input-order-qty")
        input_order_qty.value = str(self.order_qty)

    @on(Button.Pressed, "#btn-add-qty")
    def handle_add_qty(self):
        self.order_qty += 1

    @on(Button.Pressed, "#btn-sub-qty")
    def handle_sub_qty(self):
        self.order_qty -= 1

    @on(Button.Pressed, "#btn-quit")
    def handle_quit(self):
        self.dismiss(False)

    @on(Button.Pressed, "#btn-addcart")
    @work(exclusive=True)
    async def handle_addcart(self):
        # check if item already in cart

        # update cart
        if not self._existing_cart_item:  # item not in cart
            await add_to_cart(
                self.app.state.uid, self.app.state.session_no, self._pid, self.order_qty
            )
            self.app.notify("Item added to cart successfully.")
        else:
            await update_cart_qty(
                self.app.state.uid,
                self.app.state.session_no,
                self._existing_cart_item.pid,
                self.order_qty,
            )
            self.app.notify("Updated cart item quantity.")

        self.app.post_message(CartChangedMessage())
        self.dismiss(True)
