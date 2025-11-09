import os
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from db import crud
from db import database as db_database

# Ensure project src/ is on sys.path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
src_path = os.path.join(ROOT, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class CrudTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Point the DB to a temporary file and force re-initialization
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.sqlite")
        db_database.DB_PATH = self.db_path
        db_database._initialized = False

    async def asyncSetUp(self):
        # Touch initialization by opening a connection
        async with db_database.connect() as conn:
            cur = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )
            await cur.fetchall()
            await cur.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    # ---------- Auth & registration ----------

    async def test_email_available_and_register_login_and_roles(self):
        # From dummy-data.sql, alice@example.com exists; a new email should be available
        self.assertFalse(await crud.email_available("alice@example.com"))
        self.assertTrue(await crud.email_available("new@example.com"))

        # Register a new user and login
        uid, cid = await crud.register_customer("Charlie", "charlie@example.com", "pw")
        self.assertIsInstance(uid, int)
        self.assertEqual(uid, cid)

        # Able to login; wrong password fails
        user = await crud.login(uid, "pw")
        self.assertIsNotNone(user)
        self.assertEqual(user.uid, uid)
        self.assertIsNone(await crud.login(uid, "wrong"))

        # Roles and user/customer lookups
        self.assertEqual(await crud.get_user_role(uid), "customer")
        self.assertEqual(await crud.get_user_role(9999999), None)

        got_user = await crud.get_user(uid)
        self.assertEqual(got_user.role, "customer")
        self.assertIsNone(await crud.get_user(424242))

        cust = await crud.get_customer(uid)
        self.assertEqual(cust.email, "charlie@example.com")
        self.assertIsNone(await crud.get_customer(424242))

    async def test_generate_uid_fallback_path(self):
        # Patch connect so all candidate UIDs appear taken, and patch fallback to a stubbed value.
        class FakeCursor:
            async def fetchone(self):
                return (1,)  # always "exists"

            async def close(self):
                return None

        class FakeConn:
            async def execute(self, *_args, **_kwargs):
                return FakeCursor()

        @asynccontextmanager
        async def fake_connect_for_generate_uid():
            # Used inside generate_uid's for-loop
            yield FakeConn()

        orig_connect = crud.connect
        orig_fallback = crud._generate_uid_unique
        try:
            crud.connect = fake_connect_for_generate_uid  # type: ignore

            async def fake_fallback():
                return 555555

            crud._generate_uid_unique = fake_fallback  # type: ignore
            uid = await crud.generate_uid("Name", "email@example.com")
            self.assertEqual(uid, 555555)
        finally:
            crud.connect = orig_connect  # restore
            crud._generate_uid_unique = orig_fallback  # restore

    # ---------- Sessions ----------

    async def test_start_and_end_session(self):
        # Use existing customer 1001
        start = datetime(2025, 11, 1, 12, 0, 0)
        session_no = await crud.start_session(1001, start)
        self.assertIsInstance(session_no, int)
        end = start + timedelta(hours=1)
        await crud.end_session(1001, session_no, end)
        # No exception means success; optionally verify via a direct query
        async with db_database.connect() as conn:
            cur = await conn.execute(
                "SELECT end_time FROM sessions WHERE cid=? AND sessionNo=?;",
                (1001, session_no),
            )
            row = await cur.fetchone()
            await cur.close()
            self.assertIsNotNone(row[0])

    # ---------- Products & search ----------

    async def test_search_products_and_view_and_get(self):
        now = datetime(2025, 11, 1, 13, 0, 0)
        # Empty keyword should return nothing but still record the search
        products, total = await crud.search_products(
            "   ", 1001, 2, now, page=1, page_size=5
        )
        self.assertEqual(total, 0)
        self.assertEqual(products, [])

        # Multi-word phrase includes whole phrase and tokens
        now2 = now + timedelta(seconds=1)
        products2, total2 = await crud.search_products(
            "mechanical keyboard", 1001, 2, now2, 1, 10
        )
        self.assertGreaterEqual(total2, 1)
        self.assertTrue(any("Keyboard" in p.name for p in products2))

        # Single term search
        now3 = now + timedelta(seconds=2)
        products3, total3 = await crud.search_products("speaker", 1001, 2, now3, 1, 10)
        self.assertGreaterEqual(total3, 1)
        self.assertTrue(any("Speaker" in p.name for p in products3))

        # record_view and get_product
        await crud.record_view(1001, 2, 2001, now + timedelta(seconds=3))
        prod = await crud.get_product(2001)
        self.assertIsNotNone(prod)
        self.assertEqual(prod.pid, 2001)
        self.assertIsNone(await crud.get_product(999999))

    # ---------- Cart ----------

    async def test_cart_operations(self):
        cid, session_no = 1001, 2

        # list_cart (seed has two items for 1001 in session 2)
        items = await crud.list_cart(cid, session_no)
        self.assertGreaterEqual(len(items), 1)

        # add_to_cart caps by stock and consolidates across sessions
        # First, set stock low and add large qty
        await crud.update_product_price_stock(2003, None, 2)  # USB-C Cable stock -> 2
        await crud.add_to_cart(cid, session_no, 2003, 10)  # should cap to 2 total
        items = await crud.list_cart(cid, session_no)
        qty_2003 = {i.pid: i.qty for i in items}.get(2003)
        self.assertEqual(qty_2003, 2)

        # update_cart_qty: negative -> error; zero -> remove; positive -> set (capped)
        with self.assertRaises(ValueError):
            await crud.update_cart_qty(cid, session_no, 2003, -1)

        await crud.update_cart_qty(cid, session_no, 2003, 0)
        items = await crud.list_cart(cid, session_no)
        self.assertNotIn(2003, {i.pid for i in items})

        await crud.update_product_price_stock(2006, None, 5)  # stock 5
        await crud.update_cart_qty(cid, session_no, 2006, 100)  # capped to 5
        items = await crud.list_cart(cid, session_no)
        self.assertEqual({i.pid: i.qty for i in items}.get(2006), 5)

        # remove_from_cart and clear_cart
        await crud.remove_from_cart(cid, session_no, 2006)
        items = await crud.list_cart(cid, session_no)
        self.assertNotIn(2006, {i.pid for i in items})

        # Add two items then clear
        await crud.update_cart_qty(cid, session_no, 2001, 1)
        await crud.update_cart_qty(cid, session_no, 2002, 1)
        await crud.clear_cart(cid, session_no)
        items = await crud.list_cart(cid, session_no)
        self.assertEqual(items, [])

        # set_cart_qty_if_in_stock
        ok = await crud.set_cart_qty_if_in_stock(cid, session_no, 2001, -5)
        self.assertFalse(ok)
        ok = await crud.set_cart_qty_if_in_stock(cid, session_no, 2001, 10_000)
        self.assertFalse(ok)
        ok = await crud.set_cart_qty_if_in_stock(cid, session_no, 2001, 2)
        self.assertTrue(ok)

    # ---------- Orders ----------

    async def test_checkout_and_orders(self):
        cid, session_no = 1002, 1

        # Ensure empty cart checkout still creates an order without lines
        ono_empty = await crud.checkout(cid, session_no, "Addr", datetime(2025, 11, 1))
        order_empty, lines_empty = await crud.get_order_detail(ono_empty)
        self.assertEqual(lines_empty, [])

        # Add items and checkout, verify stock deduction and cart cleared
        await crud.update_cart_qty(cid, session_no, 2004, 2)
        await crud.update_cart_qty(cid, session_no, 2005, 1)
        ono = await crud.checkout(cid, session_no, "Somewhere", datetime(2025, 11, 2))
        order, lines = await crud.get_order_detail(ono)
        self.assertEqual(order.cid, cid)
        self.assertGreaterEqual(len(lines), 1)

        # order total
        total = await crud.compute_order_total(ono)
        self.assertGreater(total, 0)

        # cart is empty for cid after checkout
        self.assertEqual(await crud.list_cart(cid, session_no), [])

        # list_orders pagination
        orders_p1, total_count = await crud.list_orders(cid, page=1, page_size=1)
        self.assertGreaterEqual(total_count, 1)
        self.assertEqual(len(orders_p1), 1)

        # get_order_detail for a missing ono
        order_none, lines_none = await crud.get_order_detail(9999999)
        self.assertIsNone(order_none)
        self.assertEqual(lines_none, [])

    # ---------- Reports & helpers ----------

    async def test_reports_and_helpers(self):
        # product_exists/product_stock
        self.assertTrue(await crud.product_exists(2001))
        self.assertFalse(await crud.product_exists(999999))
        self.assertIsInstance(await crud.product_stock(2001), int)
        self.assertIsNone(await crud.product_stock(999999))

        # update_product_price_stock: no-op and non-existent
        self.assertFalse(await crud.update_product_price_stock(999999, None, None))

        # Update only price, then only stock, then both
        self.assertTrue(await crud.update_product_price_stock(2001, 19.99, None))
        self.assertTrue(await crud.update_product_price_stock(2001, None, 50))
        self.assertTrue(await crud.update_product_price_stock(2001, 21.0, 55))

        # Top products by orders/views, including ties and empty cases
        # Ensure some activity exists
        top_orders = await crud.top_products_by_orders(k=2, include_ties_at_k=True)
        self.assertIsInstance(top_orders, list)
        top_orders_no_ties = await crud.top_products_by_orders(
            k=1, include_ties_at_k=False
        )
        self.assertLessEqual(len(top_orders_no_ties), 1)
        self.assertEqual(
            await crud.top_products_by_orders(k=0, include_ties_at_k=True), []
        )

        top_views = await crud.top_products_by_views(k=2, include_ties_at_k=True)
        self.assertIsInstance(top_views, list)
        top_views_no_ties = await crud.top_products_by_views(
            k=1, include_ties_at_k=False
        )
        self.assertLessEqual(len(top_views_no_ties), 1)
        self.assertEqual(
            await crud.top_products_by_views(k=0, include_ties_at_k=True), []
        )

        # Make empty cases by clearing tables
        async with db_database.connect() as conn:
            await conn.execute("DELETE FROM orderlines;")
            await conn.execute("DELETE FROM viewedProduct;")
            await conn.commit()
        self.assertEqual(await crud.top_products_by_orders(), [])
        self.assertEqual(await crud.top_products_by_views(), [])

        # Weekly summary over seed + a new order inside window
        as_of = date(2025, 11, 5)
        # Create an order with a line today to ensure non-zero stats
        ono = await crud.checkout(1001, 2, "Here", datetime(2025, 11, 5))
        _ = await crud.compute_order_total(ono)
        summary = await crud.weekly_sales_summary(as_of)
        self.assertIn("distinct_orders", summary)
        self.assertIn("total_sales_amount", summary)

    # ---------- tiny helper coverage ----------

    def test__to_int_helper(self):
        self.assertEqual(crud._to_int("3"), 3)
        self.assertIsNone(crud._to_int("nan"))
        self.assertIsNone(crud._to_int(None))

    # ---------- mixed_product_search_sales (new helper) ----------

    async def test_mixed_product_search_sales_behaviors(self):
        # Ensure the seed is loaded in temp DB
        async with db_database.connect() as conn:
            cur = await conn.execute("SELECT COUNT(*) FROM products;")
            n = (await cur.fetchone())[0]
            await cur.close()
        self.assertGreaterEqual(n, 6)

        # 1) Empty string -> all products ordered by pid
        res = await crud.mixed_product_search_sales("   ")
        pids = [p.pid for p in res]
        self.assertEqual(sorted(pids), pids)  # ascending
        # Expect all 6 seeded products
        self.assertGreaterEqual(len(pids), 6)
        self.assertTrue({2001, 2002, 2003, 2004, 2005, 2006}.issubset(set(pids)))

        # 2) Numeric-only with exact PID present -> returns that product only (no fallback)
        res = await crud.mixed_product_search_sales("2003")
        self.assertEqual([p.pid for p in res], [2003])

        # 3) Numeric-only with no exact PID -> fallback to keyword (likely none)
        res = await crud.mixed_product_search_sales("9999")
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 0)

        # 4) Multi-word: exact phrase first, then tokens; de-dup
        res = await crud.mixed_product_search_sales("mechanical keyboard")
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0].pid, 2002)  # Mechanical Keyboard
        # Ensure de-dup didn't create duplicates of the same PID
        self.assertEqual(len({p.pid for p in res}), len(res))

        # 5) Single non-numeric word
        res = await crud.mixed_product_search_sales("speaker")
        self.assertTrue(any(p.pid == 2006 for p in res))

        # 6) Case-insensitive and trimmed
        res = await crud.mixed_product_search_sales("  SPEAKER  ")
        self.assertTrue(any(p.pid == 2006 for p in res))

    async def test_mixed_product_search_sales_does_not_record(self):
        # Count existing search logs
        async with db_database.connect() as conn:
            cur = await conn.execute("SELECT COUNT(*) FROM search;")
            before = (await cur.fetchone())[0]
            await cur.close()
        # Perform several sales searches
        _ = await crud.mixed_product_search_sales("")
        _ = await crud.mixed_product_search_sales("2001")
        _ = await crud.mixed_product_search_sales("mechanical keyboard")
        _ = await crud.mixed_product_search_sales("speaker")
        # Count again, should be unchanged
        async with db_database.connect() as conn:
            cur = await conn.execute("SELECT COUNT(*) FROM search;")
            after = (await cur.fetchone())[0]
            await cur.close()
        self.assertEqual(before, after)
