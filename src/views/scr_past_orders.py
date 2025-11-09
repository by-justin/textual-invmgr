import asyncio
from math import ceil
from typing import List, Tuple

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import ScreenResume
from textual.reactive import reactive
from textual.validation import Number
from textual.widgets import Button, DataTable, Input, Label, MarkdownViewer

import db.crud
from db.models import Order, OrderLine, Product
from utils.messages import ModeSwitchedMessage, NewOrderMessage
from views.base_screen import BaseScreen


class PastOrdersScreen(BaseScreen):
    """
    Customers can browse their past orders with pagination and view details.

    Layout:
    - Markdown detail view at the top, showing selected order details.
    - Orders table below (reverse chronological), 5 per page with Prev/Next.
    """

    # TODO:
    # this screens somehow has a leaky thread
    # check the awaits

    # Show some hints in footer
    BINDINGS = [
        Binding("enter", "noop", "View Order Detail", show=True, key_display="⏎"),
        Binding("escape", "noop", "Back", show=True),
    ]

    page_idx = reactive(1)
    page_cnt = reactive(1)
    selected_ono = reactive[int | None](None)

    def __init__(self) -> None:
        super().__init__()
        self._orders: List[Order] = []

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with Vertical():
            yield MarkdownViewer(id="md-order-detail", show_table_of_contents=False)
            yield DataTable(id="table-orders")
        with Horizontal(id="hort-table-control"):
            yield Button("Refresh", id="btn-refresh")
            yield Button("<", id="btn-prev")
            yield Input("1", id="input-page", type="integer")
            yield Label(" / 1", id="label-total-page-cnt")
            yield Button(">", id="btn-next")

    def on_mount(self) -> None:
        # Setup orders table
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Order No", "Date", "Shipping Address", "Total ($)")

        self.page_idx = 1

    @on(Button.Pressed, "#btn-refresh")
    @on(ModeSwitchedMessage)
    @on(ScreenResume)
    @on(NewOrderMessage)
    async def handle_refresh(self):
        self._load_orders(1)

    @on(DataTable.RowHighlighted)
    async def handle_row_highlight(self) -> None:
        # Update detail when cursor moves
        self._update_detail_for_cursor()

    @work()
    async def _update_detail_for_cursor(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            self._render_detail(None, [], 0.0)
            return
        cursor_row = table.cursor_row
        if cursor_row is None:
            return
        row_values = table.get_row_at(cursor_row)
        if not row_values:
            return
        ono = int(row_values[0])
        self._load_and_render_detail(ono)

    def watch_page_idx(self, old: int, new: int) -> None:
        # sync page input and enable/disable buttons; trigger load
        self.query_one("#input-page", Input).value = str(new)
        self._refresh_buttons()
        self._load_orders(new)

    def _refresh_buttons(self) -> None:
        btn_prev = self.query_one("#btn-prev", Button)
        btn_next = self.query_one("#btn-next", Button)
        btn_prev.disabled = self.page_idx <= 1
        btn_next.disabled = self.page_idx >= self.page_cnt
        self.query_one("#input-page", Input).validators = [
            Number(minimum=1, maximum=self.page_cnt)
        ]

    @on(Button.Pressed, "#btn-prev")
    def handle_prev(self) -> None:
        if self.page_idx > 1:
            self.page_idx -= 1

    @on(Button.Pressed, "#btn-next")
    def handle_next(self) -> None:
        if self.page_idx < self.page_cnt:
            self.page_idx += 1

    @on(Input.Changed, "#input-page")
    def handle_page_input(self, ev: Input.Changed) -> None:
        if ev.value and ev.value.isdigit():
            new_idx = int(ev.value)
            new_idx = max(1, min(new_idx, self.page_cnt))
            if new_idx != self.page_idx:
                self.page_idx = new_idx

    @work(exclusive=True, group="orders")
    async def _load_orders(self, page: int) -> None:
        orders, total = await db.crud.list_orders(self.app.state.uid, page)
        # compute totals (N requests, but page size is 5)
        totals = await asyncio.gather(
            *(db.crud.compute_order_total(o.ono) for o in orders)
        )
        # populate table
        table = self.query_one(DataTable)
        table.clear()
        for o, t in zip(orders, totals):
            table.add_row(
                o.ono,
                o.odate,
                o.shipping_address,
                f"{t:.2f}",
            )
        self._orders = orders
        self.page_cnt = max(ceil(total / 5), 1)
        self.query_one("#label-total-page-cnt", Label).content = f" / {self.page_cnt}"
        self._refresh_buttons()
        # update detail for first row on page
        if orders:
            # ensure cursor at first row
            table.cursor_coordinate = (0, 0)
            self._update_detail_for_cursor()
        else:
            self._render_detail(None, [], 0.0)

    @work(exclusive=True)
    async def _load_and_render_detail(self, ono: int) -> None:
        order, lines = await db.crud.get_order_detail(ono)
        if not order:
            self._render_detail(None, [], 0.0)
            return
        # fetch product info for names & categories
        prods = await asyncio.gather(*(db.crud.get_product(ol.pid) for ol in lines))
        grand_total = await db.crud.compute_order_total(ono)
        # build a combined list with product fields
        detailed_lines: List[Tuple[OrderLine, Product | None]] = list(zip(lines, prods))
        self._render_detail(order, detailed_lines, grand_total)

    def _render_detail(
        self,
        order: Order | None,
        lines_with_prod: List[Tuple[OrderLine, Product | None]],
        grand_total: float,
    ) -> None:
        if not order:
            md = """### Select an order to view its details."""
            self.query_one("#md-order-detail", MarkdownViewer).document.update(md)
            return

        header = (
            f"### Order #{order.ono}\n"
            f"Date: {order.odate}  \n"
            f"Ship To: {order.shipping_address}\n\n"
        )
        # Build items table in Markdown
        rows = [
            "| Product | Category | Qty | Unit Price | Line Total |",
            "|---|---:|---:|---:|---:|",
        ]
        for ol, prod in lines_with_prod:
            name = prod.name if prod else f"PID {ol.pid}"
            cat = prod.category if prod else "-"
            line_total = ol.qty * ol.uprice
            rows.append(
                f"| {name} | {cat} | {ol.qty} | {ol.uprice:.2f} | {line_total:.2f} |"
            )
        footer = f"\n\n**Grand Total:** ${grand_total:.2f}"
        md = header + "\n".join(rows) + footer
        self.query_one("#md-order-detail", MarkdownViewer).document.update(md)
