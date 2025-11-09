import asyncio
from datetime import date
from typing import List, Tuple

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import ScreenResume
from textual.widgets import MarkdownViewer

import db.crud as crud
from utils.messages import ModeSwitchedMessage, NewOrderMessage
from views.base_screen import BaseScreen


class SalesReportScreen(BaseScreen):
    """
    Sales Insights: Weekly summary + Top products by orders and by views.
    """

    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with Vertical():
            yield MarkdownViewer(id="md-top", show_table_of_contents=False)
            # yield Button("Refresh", id="btn-refresh", variant="primary")

    def on_mount(self) -> None:
        self.handle_reload()

    # @on(Button.Pressed, "#btn-refresh")
    @on(NewOrderMessage)
    @on(ScreenResume)
    @on(ModeSwitchedMessage)
    @work(exclusive=True)
    async def handle_reload(self) -> None:
        # Fetch weekly summary and top lists
        summary = await crud.weekly_sales_summary(as_of=date.today())
        top_orders = await crud.top_products_by_orders(k=3)
        top_views = await crud.top_products_by_views(k=3)

        async def enrich(items: List[Tuple[int, int]]) -> List[Tuple[int, str, int]]:
            prods = await asyncio.gather(*(crud.get_product(pid) for pid, _ in items))
            result: List[Tuple[int, str, int]] = []
            for (pid, cnt), prod in zip(items, prods):
                name = prod.name if prod else f"PID {pid}"
                result.append((pid, name, cnt))
            return result

        eo, ev = await asyncio.gather(enrich(top_orders), enrich(top_views))

        def mk_table(title: str, rows: List[Tuple[int, str, int]]) -> str:
            header = f"#### {title}\n\n| PID | Name | Count |\n|---:|:---|---:|\n"
            body = "\n".join(f"| {pid} | {name} | {cnt} |" for pid, name, cnt in rows)
            return header + body + "\n"

        weekly_md = (
            "### Weekly Sales Summary (last 7 days)\n\n"
            f"- Distinct Orders: {summary['distinct_orders']}\n"
            f"- Distinct Products Sold: {summary['distinct_products_sold']}\n"
            f"- Distinct Customers: {summary['distinct_customers']}\n"
            f"- Avg Amount per Customer: ${summary['avg_amount_per_customer']:.2f}\n"
            f"- Total Sales Amount: ${summary['total_sales_amount']:.2f}\n\n"
        )

        md = (
            weekly_md
            + "### Top Products\n\n"
            + mk_table("By Distinct Orders", eo)
            + "\n"
            + mk_table("By Views", ev)
        )
        self.query_one("#md-top", MarkdownViewer).document.update(md)
