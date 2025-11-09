import dataclasses
from datetime import datetime
from math import ceil

from textual import events, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.validation import Number
from textual.widgets import DataTable, Input, Label

import db.crud
from db.models import Product
from utils.messages import CartChangedMessage
from views.base_screen import BaseScreen
from views.modal_prod_detail import ProdDetailModal


class ProdSearchScreen(BaseScreen):
    """
    prod search, for cusotmers only
    """

    # TODO: remove this
    CSS = """
    #input-page { 
        width: 16; 
    } 
    """

    # bindings here are completely useless
    # they are only here to be displayed in footer
    BINDINGS = [
        Binding("fn+shift+1", "abs(1)", "View Product", show=True, key_display="⏎"),
        Binding("escape", "abs(2)", "Exit Prod View", show=True),
    ]

    page_idx = reactive(1)
    page_cnt = reactive(1)
    query_str = reactive("")

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Input(
            id="input-search", placeholder="Start typing to search something..."
        )
        yield DataTable(id="table-search-result")
        with Horizontal():
            yield Input("1", id="input-page", type="integer")  # page idx start from 1
            yield Label(" / 1", id="label-total-page-cnt")

        # TODO:  # remove it, and use inhenritance to do it  # yield Footer(
        #  show_command_palette=False)

    def on_mount(self):
        # datatable
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        table_columns = [str(f.name) for f in dataclasses.fields(Product)]
        table.add_columns(*table_columns)

        # other
        self.query_one("#input-search").focus()

    async def on_input_changed(self, message: Input.Changed) -> None:
        if message.input.id == "input-search":
            self.query_str = message.value
            self.update_search_result(self.query_str, 1)
            self.page_idx = 1
            self.watch_page_idx(None, 1)
        if message.input.id == "input-page" and message.value:
            self.page_idx = int(message.value)

    async def on_key(self, event: events.Key) -> None:
        # view prod detail
        table = self.query_one(DataTable)
        if event.key == "enter" and self.focused == table:
            row_selected = table.get_row_at(table.cursor_row)
            pid = row_selected[0]
            if await self.app.push_screen_wait(ProdDetailModal(pid)):
                self.app.post_message(CartChangedMessage())

    def validate_page_idx(self, page_idx):
        if page_idx < 1:
            page_idx = 1
        elif page_idx > self.page_cnt:
            page_idx = self.page_cnt
        return page_idx

    # TODO:
    # page index is not updated in time
    # fix it
    def watch_page_idx(self, _, new_page_idx):
        self.query_one("#input-page").value = str(new_page_idx)
        self.update_search_result(self.query_str, new_page_idx)
        self.query_one("#input-page").validators = [
            Number(minimum=1, maximum=self.page_cnt)
        ]

    @work(exclusive=True)
    async def update_search_result(self, query: str, page: int) -> None:
        search_results = []
        total_res_cnt = 0
        if query:
            search_results, total_res_cnt = await db.crud.search_products(
                query,
                self.app.state.uid,
                self.app.state.session_no,
                datetime.now(),
                page,
            )
            search_results = [
                dataclasses.asdict(res).values() for res in search_results
            ]

        table = self.query_one(DataTable)
        table.clear()
        table.add_rows(search_results)
        self.page_cnt = max(ceil(total_res_cnt / 5), 1)
        self.query_one("#label-total-page-cnt").content = f" / {self.page_cnt}"
