from __future__ import annotations

import dataclasses
from typing import List, Optional

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.validation import Number
from textual.widgets import Button, Input, Label, MarkdownViewer, OptionList

from db.crud import get_product, mixed_product_search_sales, update_product_price_stock
from db.models import Product
from utils.pure import generate_markdown_table
from views.base_screen import BaseScreen


class SalesManageProductScreen(BaseScreen):
    """
    Sales can enter a PID to view product details and update price/stock.
    """

    current_pid: Optional[int] = None

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with Vertical():
            yield Input(id="input-search", placeholder="Search for product...")
            yield OptionList(id="optlist-prods")
            yield MarkdownViewer(id="md-prod", show_table_of_contents=False)
            with Horizontal(id="hort-controls"):
                with Horizontal(id="div-new-inputs"):
                    with Vertical():
                        yield Label("New Price ($):")
                        yield Input(
                            placeholder="leave blank to keep",
                            id="input-price",
                            type="number",
                            validators=[Number(minimum=0.0)],
                        )

                    with Vertical():
                        yield Label("New Stock:")
                        yield Input(
                            placeholder="leave blank to keep",
                            id="input-stock",
                            type="integer",
                            validators=[Number(minimum=0)],
                        )
                with Horizontal(id="div-button"):
                    yield Button("Update", id="btn-update", variant="success")

    def on_mount(self) -> None:
        self.query_one("#input-search", Input).focus()
        self.query_one("#optlist-prods").add_class("hidden")
        self.query_one("#md-prod").add_class("hidden")
        self.query_one("#hort-controls").add_class("hidden")

    def on_input_changed(self, message: Input.Changed) -> None:
        if message.input.id == "input-search":
            self.query_one("#optlist-prods").remove_class("hidden")
            self.update_optlist(message.value)

    def on_option_list_option_selected(self, message: OptionList.OptionSelected):
        pid = int(message.option.prompt.split(" ")[0])

        self.current_pid = pid
        self.render_product()

        self.query_one("#optlist-prods").add_class("hidden")
        self.query_one("#md-prod").remove_class("hidden")
        self.query_one("#hort-controls").remove_class("hidden")

    @work(exclusive=True)
    async def update_optlist(self, query: str):
        """
        fill option list with search results
        """
        search_results: List[Product] = await mixed_product_search_sales(query)

        opt_list = self.query_one("#optlist-prods")
        opt_list.clear_options()
        opt_list.add_options([f"{p.pid} {p.name}" for p in search_results])

    @work(exclusive=True)
    async def render_product(self) -> None:
        prod = await get_product(self.current_pid)

        headers = ["Attribute", "Value"]
        rows = [[k, v] for k, v in dataclasses.asdict(prod).items()]
        md_table = generate_markdown_table(headers, rows, ["l", "l"])
        await self.query_one("#md-prod", MarkdownViewer).document.update(
            f"### Product Detail: {prod.name}\n\n" + md_table
        )

        # prefill inputs with current values for convenience
        self.query_one("#input-price", Input).value = f"{prod.price:.2f}"
        self.query_one("#input-stock", Input).value = str(prod.stock_count)

    @on(Button.Pressed, "#btn-update")
    @work(exclusive=True)
    async def handle_update(self) -> None:
        prod = await get_product(self.current_pid)

        price_input = self.query_one("#input-price", Input)
        stock_input = self.query_one("#input-stock", Input)

        if not price_input:
            price_input.focus()
            price_input.add_class("-invalid")
            return

        if not stock_input:
            stock_input.focus()
            stock_input.add_class("-invalid")

        new_price = float(price_input.value)
        new_stock = int(stock_input.value)

        if new_price == prod.price and new_stock == prod.stock_count:
            self.notify("Nothing to update.", severity="warning")
            return

        if await update_product_price_stock(prod.pid, new_price, new_stock):
            self.notify("Product updated successfully.")
        else:
            self.notify("Update failed.", severity="error")

        self.render_product()
