# src/db/crud.py
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from db import models
from db.database import connect


def _to_int(val) -> Optional[int]:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


# ---------------------------
# Auth & Registration
# ---------------------------


async def email_available(email: str) -> bool:
    """True if no customer already registered with the given email."""
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT 1 FROM customers WHERE email = ? LIMIT 1;", (email,)
        )
        row = await cur.fetchone()
        await cur.close()
        return row is None


async def _generate_uid_unique() -> int:
    """Generate a uid/cid that isn't already in use."""
    async with connect() as conn:
        while True:
            uid = random.randint(1000, 999999)
            cur = await conn.execute("SELECT 1 FROM users WHERE uid = ?;", (uid,))
            exists = await cur.fetchone()
            await cur.close()
            if not exists:
                return uid


async def generate_uid(name: str, email: str) -> int:
    """Generate a unique uid for users table (e.g., based on name/email + disambiguation).

    Mirrors the original API but without a connection argument.
    """
    # Keep range similar to original (1000..9999) but ensure uniqueness if possible.
    async with connect() as conn:
        for _ in range(10000):
            cand = random.randint(1000, 9999)
            cur = await conn.execute("SELECT 1 FROM users WHERE uid = ?;", (cand,))
            exists = await cur.fetchone()
            await cur.close()
            if not exists:
                return cand
    # Fallback to broader range if small range exhausted
    return await _generate_uid_unique()


async def register_customer(name: str, email: str, pwd: str) -> Tuple[int, int]:
    """
    Create a new customer account and return (uid, cid) as integers.
    """
    uid = await _generate_uid_unique()
    cid = uid
    async with connect() as conn:
        await conn.execute(
            "INSERT INTO users(uid, pwd, role) VALUES (?, ?, 'customer');",
            (uid, pwd),
        )
        await conn.execute(
            "INSERT INTO customers(cid, name, email) VALUES (?, ?, ?);",
            (cid, name, email),
        )
        await conn.commit()
    return uid, cid


async def login(uid: int, pwd: str) -> Optional[models.User]:
    """Return User if uid/pwd match; otherwise None.

    Application-level uid is treated as int.
    """
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT uid, pwd, role FROM users WHERE uid = ? AND pwd = ?;",
            (uid, pwd),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            return None
        return models.User(uid=int(row[0]), pwd=row[1], role=row[2])


async def get_user_role(uid: int) -> Optional[str]:
    """Return 'customer' or 'sales' if user exists; otherwise None."""
    async with connect() as conn:
        cur = await conn.execute("SELECT role FROM users WHERE uid = ?;", (uid,))
        row = await cur.fetchone()
        await cur.close()
        return row[0] if row else None


async def get_user(uid: int) -> Optional[models.User]:
    """Return a User object for the given uid, or None if not found."""
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT uid, pwd, role FROM users WHERE uid = ?;",
            (uid,),
        )
        row = await cur.fetchone()
        await cur.close()
    if not row:
        return None
    return models.User(uid=int(row[0]), pwd=row[1], role=row[2])


async def get_customer(uid: int) -> Optional[models.Customer]:
    """Return the Customer row for a given uid, or None."""
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT c.cid, c.name, c.email FROM customers c JOIN users u ON c.cid=u.uid WHERE u.uid = ?;",
            (uid,),
        )
        row = await cur.fetchone()
        await cur.close()
    if not row:
        return None
    return models.Customer(cid=row[0], name=row[1], email=row[2])


# ---------------------------
# Sessions
# ---------------------------


async def start_session(cid: int, start_time: datetime) -> int:
    """
    Start a session for a customer; creates sessions(cid, sessionNo, start_time).
    Returns the new sessionNo for (cid).
    """
    # generate unique session number per customer
    async with connect() as conn:
        while True:
            session_no = random.randint(1000, 999999)
            cur = await conn.execute(
                "SELECT 1 FROM sessions WHERE cid=? AND sessionNo=?;",
                (cid, session_no),
            )
            exists = await cur.fetchone()
            await cur.close()
            if not exists:
                break
        await conn.execute(
            "INSERT INTO sessions(cid, sessionNo, start_time, end_time) VALUES(?, ?, ?, NULL);",
            (cid, session_no, start_time),
        )
        await conn.commit()
    return session_no


async def end_session(cid: int, sessionNo: int, end_time: datetime) -> None:
    """Set sessions.end_time for the given (cid, sessionNo)."""
    async with connect() as conn:
        await conn.execute(
            "UPDATE sessions SET end_time = ? WHERE cid = ? AND sessionNo = ?;",
            (end_time, cid, sessionNo),
        )
        await conn.commit()


# ---------------------------
# Products (Search, View, Read/Update)
# ---------------------------


async def mixed_product_search_sales(query: str) -> List[models.Product]:
    """
    Case-insensitive mixed search used by sales; DOES NOT record queries.
    Rules:
    - Empty string: return all products ordered by pid.
    - Numeric only: try PID exact match first, then fall back to keyword search
      over name/descr with the numeric string; concatenate in that order.
    - Multiple words: search exact phrase (name OR descr LIKE "%phrase%") first,
      then fall back to searching each word individually; exact results come first.
    - Single non-numeric word: standard keyword search over name/descr.
    Strips leading/trailing spaces and is case-insensitive.
    """
    phrase = (query or "").strip().lower()

    async def rows_to_products(rows: List[tuple]) -> List[models.Product]:
        return [
            models.Product(
                pid=row[0],
                name=row[1],
                category=row[2],
                price=row[3],
                stock_count=row[4],
                descr=row[5],
            )
            for row in rows
        ]

    async with connect() as conn:
        # Empty -> all products ordered by pid
        if not phrase:
            cur = await conn.execute(
                """
                SELECT pid, name, category, price, stock_count, descr
                FROM products
                ORDER BY pid;
                """
            )
            rows = await cur.fetchall()
            await cur.close()
            return await rows_to_products(rows)

        results: list[models.Product] = []
        seen: set[int] = set()

        def add_rows(rows: List[tuple]):
            nonlocal results, seen
            for row in rows:
                pid = row[0]
                if pid in seen:
                    continue
                seen.add(pid)
                results.append(
                    models.Product(
                        pid=row[0],
                        name=row[1],
                        category=row[2],
                        price=row[3],
                        stock_count=row[4],
                        descr=row[5],
                    )
                )

        # Numeric only -> PID exact first, then keyword
        if phrase.isdigit():
            pid_val = int(phrase)
            # PID exact
            cur = await conn.execute(
                """
                SELECT pid, name, category, price, stock_count, descr
                FROM products
                WHERE pid = ?
                ORDER BY pid;
                """,
                (pid_val,),
            )
            rows = await cur.fetchall()
            await cur.close()
            add_rows(rows)

            # Fall back to keyword on name/descr ONLY if no PID match
            if not rows:
                like = f"%{phrase}%"
                cur = await conn.execute(
                    """
                    SELECT pid, name, category, price, stock_count, descr
                    FROM products
                    WHERE LOWER(name) LIKE ? OR LOWER(descr) LIKE ?
                    ORDER BY pid;
                    """,
                    (like, like),
                )
                rows = await cur.fetchall()
                await cur.close()
                add_rows(rows)

            return results

        # Multiple words -> exact phrase first, then each word
        words = [w for w in phrase.split() if w]
        if len(words) > 1:
            like_phrase = f"%{phrase}%"
            # Exact phrase in name or descr
            cur = await conn.execute(
                """
                SELECT pid, name, category, price, stock_count, descr
                FROM products
                WHERE LOWER(name) LIKE ? OR LOWER(descr) LIKE ?
                ORDER BY pid;
                """,
                (like_phrase, like_phrase),
            )
            rows = await cur.fetchall()
            await cur.close()
            add_rows(rows)

            # Then each word in order, de-duplicated across words too
            seen_words: set[str] = set()
            for w in words:
                if w in seen_words:
                    continue
                seen_words.add(w)
                like_w = f"%{w}%"
                cur = await conn.execute(
                    """
                    SELECT pid, name, category, price, stock_count, descr
                    FROM products
                    WHERE LOWER(name) LIKE ? OR LOWER(descr) LIKE ?
                    ORDER BY pid;
                    """,
                    (like_w, like_w),
                )
                wrows = await cur.fetchall()
                await cur.close()
                add_rows(wrows)

            return results

        # Single non-numeric word -> standard keyword search
        like = f"%{phrase}%"
        cur = await conn.execute(
            """
            SELECT pid, name, category, price, stock_count, descr
            FROM products
            WHERE LOWER(name) LIKE ? OR LOWER(descr) LIKE ?
            ORDER BY pid;
            """,
            (like, like),
        )
        rows = await cur.fetchall()
        await cur.close()
        return await rows_to_products(rows)


async def search_products(
    keyword: str,
    cid: int,
    sessionNo: int,
    when: datetime,
    page: int,
    page_size: int = 5,
) -> Tuple[List[models.Product], int]:
    """
    Case-insensitive search over name/descr; records the search query.
    If the user input contains spaces, treat it as both:
      1) a single phrase (with spaces) and
      2) multiple keywords separated by spaces
    Return the union of matches without duplicates. Also records the query.
    Returns (products for page, total_count).
    """
    # Normalize input
    phrase = (keyword or "").strip().lower()
    words = [w for w in phrase.split() if w]

    # Build search terms per requirements
    terms: List[str] = []
    if not phrase:
        terms = []
    elif len(words) > 1:
        # include the whole phrase and each individual word
        terms.append(phrase)
        # add unique tokens while preserving order
        seen = set([phrase])
        for w in words:
            if w not in seen:
                terms.append(w)
                seen.add(w)
    else:
        # single word behaves as before
        terms = [phrase]

    # Construct dynamic WHERE clause: OR across all terms for name/descr
    if terms:
        cond_parts = ["(LOWER(name) LIKE ? OR LOWER(descr) LIKE ?)"] * len(terms)
        where_clause = " OR ".join(cond_parts)
        params: List[str | int] = []
        for t in terms:
            like = f"%{t}%"
            params.extend([like, like])
    else:
        # No terms -> match nothing
        where_clause = "1 = 0"
        params = []

    async with connect() as conn:
        # total count (distinct pids just in case)
        cur = await conn.execute(
            f"""
            SELECT COUNT(*)
            FROM products
            WHERE {where_clause};
            """,
            tuple(params),
        )
        total = (await cur.fetchone())[0]
        await cur.close()

        # page rows
        offset = max(page - 1, 0) * page_size
        cur = await conn.execute(
            f"""
            SELECT pid, name, category, price, stock_count, descr
            FROM products
            WHERE {where_clause}
            ORDER BY pid
            LIMIT ? OFFSET ?;
            """,
            tuple(params + [page_size, offset]),
        )
        rows = await cur.fetchall()
        await cur.close()

        # record the search
        await conn.execute(
            "INSERT INTO search(cid, sessionNo, ts, query) VALUES(?, ?, ?, ?);",
            (cid, sessionNo, when, keyword),
        )
        await conn.commit()

    products = [
        models.Product(
            pid=row[0],
            name=row[1],
            category=row[2],
            price=row[3],
            stock_count=row[4],
            descr=row[5],
        )
        for row in rows
    ]
    return products, total


async def record_view(cid: int, sessionNo: int, pid: int, ts: datetime) -> None:
    """Insert viewedProduct(cid, sessionNo, ts, pid) when a product detail is shown."""
    async with connect() as conn:
        await conn.execute(
            "INSERT INTO viewedProduct(cid, sessionNo, ts, pid) VALUES(?, ?, ?, ?);",
            (cid, sessionNo, ts, pid),
        )
        await conn.commit()


async def get_product(pid: int) -> Optional[models.Product]:
    """Fetch a product by pid."""
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT pid, name, category, price, stock_count, descr FROM products WHERE pid = ?;",
            (pid,),
        )
        row = await cur.fetchone()
        await cur.close()
    if not row:
        return None
    return models.Product(
        pid=row[0],
        name=row[1],
        category=row[2],
        price=row[3],
        stock_count=row[4],
        descr=row[5],
    )


# ---------------------------
# Cart Management
# ---------------------------


async def list_cart(cid: int, sessionNo: int) -> List[models.CartItem]:
    """Return aggregated cart items for the customer across all sessions.
    The returned CartItem.sessionNo will be set to the provided sessionNo for compatibility.
    """
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT cid, pid, SUM(qty) FROM cart WHERE cid = ? GROUP BY cid, pid;",
            (cid,),
        )
        rows = await cur.fetchall()
        await cur.close()
    return [
        models.CartItem(cid=row[0], sessionNo=sessionNo, pid=row[1], qty=row[2])
        for row in rows
    ]


async def add_to_cart(cid: int, sessionNo: int, pid: int, qty: int) -> None:
    """
    Add product to the customer's persistent cart (across sessions) with given qty;
    if already present in any session, increment total quantity. Ensures quantity
    does not exceed stock_count. Consolidates into the current session row.
    """
    async with connect() as conn:
        # current stock
        cur = await conn.execute(
            "SELECT stock_count FROM products WHERE pid = ?;", (pid,)
        )
        row = await cur.fetchone()
        await cur.close()
        stock = int(row[0]) if row else 0
        if stock <= 0 or qty <= 0:
            return

        # total existing quantity across sessions
        cur = await conn.execute(
            "SELECT COALESCE(SUM(qty), 0) FROM cart WHERE cid=? AND pid=?;",
            (cid, pid),
        )
        row = await cur.fetchone()
        await cur.close()
        cur_total = int(row[0]) if row and row[0] is not None else 0
        new_total = min(cur_total + qty, stock)

        # consolidate: remove any previous rows for this (cid, pid), then insert one for current session
        await conn.execute("DELETE FROM cart WHERE cid=? AND pid=?;", (cid, pid))
        await conn.execute(
            "INSERT INTO cart(cid, sessionNo, pid, qty) VALUES(?, ?, ?, ?);",
            (cid, sessionNo, pid, new_total),
        )
        await conn.commit()


async def update_cart_qty(cid: int, sessionNo: int, pid: int, qty: int) -> None:
    """Set the total quantity for the customer's cart item across sessions.
    If qty == 0, remove the item entirely. Respects stock limits and consolidates
    into a single row under the current session.
    """
    if qty < 0:
        raise ValueError("Quantity cannot be negative.")
    async with connect() as conn:
        if qty == 0:
            await conn.execute(
                "DELETE FROM cart WHERE cid=? AND pid=?;",
                (cid, pid),
            )
            await conn.commit()
            return
        # cap at stock
        cur = await conn.execute(
            "SELECT stock_count FROM products WHERE pid=?;", (pid,)
        )
        row = await cur.fetchone()
        await cur.close()
        stock = int(row[0]) if row else 0
        qty = min(qty, stock)
        # consolidate into current session
        await conn.execute("DELETE FROM cart WHERE cid=? AND pid=?;", (cid, pid))
        await conn.execute(
            "INSERT INTO cart(cid, sessionNo, pid, qty) VALUES(?, ?, ?, ?);",
            (cid, sessionNo, pid, qty),
        )
        await conn.commit()


async def remove_from_cart(cid: int, sessionNo: int, pid: int) -> None:
    """Remove a single product from the customer's cart across sessions."""
    async with connect() as conn:
        await conn.execute(
            "DELETE FROM cart WHERE cid = ? AND pid = ?;",
            (cid, pid),
        )
        await conn.commit()


async def clear_cart(cid: int, sessionNo: int) -> None:
    """Remove all items from the user's cart across all sessions."""
    async with connect() as conn:
        await conn.execute(
            "DELETE FROM cart WHERE cid = ?;",
            (cid,),
        )
        await conn.commit()


# ---------------------------
# Checkout & Orders
# ---------------------------


async def checkout(
    cid: int, sessionNo: int, shipping_address: str, odate: datetime
) -> int:
    """
    Create an order from the customer's persistent cart (across sessions) and return the created order number (ono).
    The order will still record the current sessionNo.
    """
    async with connect() as conn:
        # build order lines from aggregated cart across all sessions for this customer
        cur = await conn.execute(
            "SELECT pid, SUM(qty) as total_qty FROM cart WHERE cid=? GROUP BY pid;",
            (cid,),
        )
        cart_rows = await cur.fetchall()
        await cur.close()
        if not cart_rows:
            cart_rows = []

        # pick unique order number
        while True:
            ono = random.randint(100000, 999999)
            cur = await conn.execute("SELECT 1 FROM orders WHERE ono=?;", (ono,))
            exists = await cur.fetchone()
            await cur.close()
            if not exists:
                break

        await conn.execute(
            "INSERT INTO orders(ono, cid, sessionNo, odate, shipping_address) VALUES (?, ?, ?, ?, ?);",
            (ono, cid, sessionNo, odate, shipping_address),
        )

        # insert lines and decrement stock
        line_no = 1
        for pid, qty in cart_rows:
            cur = await conn.execute(
                "SELECT price, stock_count FROM products WHERE pid=?;", (pid,)
            )
            row = await cur.fetchone()
            await cur.close()
            if not row:
                continue
            price, stock = float(row[0]), int(row[1])
            use_qty = min(int(qty), stock)
            if use_qty <= 0:
                continue
            await conn.execute(
                "INSERT INTO orderlines(ono, lineNo, pid, qty, uprice) VALUES (?, ?, ?, ?, ?);",
                (ono, line_no, pid, use_qty, price),
            )
            await conn.execute(
                "UPDATE products SET stock_count = stock_count - ? WHERE pid = ?;",
                (use_qty, pid),
            )
            line_no += 1

        # empty the customer's cart across all sessions after checkout
        await conn.execute("DELETE FROM cart WHERE cid=?;", (cid,))
        await conn.commit()

    return ono


async def list_orders(
    cid: int, page: int, page_size: int = 5
) -> Tuple[List[models.Order], int]:
    """
    List a customer's past orders in reverse chronological order, paginated.
    Return (orders_for_page, total_count).
    """
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM orders WHERE cid = ?;",
            (cid,),
        )
        total = (await cur.fetchone())[0]
        await cur.close()
        offset = max(page - 1, 0) * page_size
        cur = await conn.execute(
            """
            SELECT ono, cid, sessionNo, odate, shipping_address
            FROM orders
            WHERE cid = ?
            ORDER BY odate DESC
            LIMIT ? OFFSET ?;
            """,
            (cid, page_size, offset),
        )
        rows = await cur.fetchall()
        await cur.close()
    orders = [
        models.Order(
            ono=row[0],
            cid=row[1],
            sessionNo=row[2],
            odate=row[3],
            shipping_address=row[4],
        )
        for row in rows
    ]
    return orders, total


async def get_order_detail(ono: int) -> Tuple[models.Order, List[models.OrderLine]]:
    """
    Return (order, lines) for a specific order.
    """
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT ono, cid, sessionNo, odate, shipping_address FROM orders WHERE ono = ?;",
            (ono,),
        )
        order_row = await cur.fetchone()
        await cur.close()
        if not order_row:
            return None, []  # type: ignore
        cur = await conn.execute(
            "SELECT ono, lineNo, pid, qty, uprice FROM orderlines WHERE ono = ? ORDER BY lineNo;",
            (ono,),
        )
        line_rows = await cur.fetchall()
        await cur.close()
    order = models.Order(
        ono=order_row[0],
        cid=order_row[1],
        sessionNo=order_row[2],
        odate=order_row[3],
        shipping_address=order_row[4],
    )
    lines = [
        models.OrderLine(
            ono=row[0], lineNo=row[1], pid=row[2], qty=row[3], uprice=row[4]
        )
        for row in line_rows
    ]
    return order, lines


async def compute_order_total(ono: int) -> float:
    """Return the grand total for a given order number."""
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT COALESCE(SUM(qty * uprice), 0.0) FROM orderlines WHERE ono = ?;",
            (ono,),
        )
        row = await cur.fetchone()
        await cur.close()
    return float(row[0]) if row and row[0] is not None else 0.0


# ---------------------------
# Sales Reports (Salesperson)
# ---------------------------


async def weekly_sales_summary(as_of: date) -> Dict[str, float]:
    """
    Summarize the previous 7 days (as_of - 7d .. as_of).
    Returns a dict with numeric values.
    """
    start_date = as_of - timedelta(days=7)
    async with connect() as conn:
        cur = await conn.execute(
            """
            SELECT 
                COUNT(DISTINCT o.ono) AS distinct_orders,
                COUNT(DISTINCT ol.pid) AS distinct_products_sold,
                COUNT(DISTINCT o.cid) AS distinct_customers,
                COALESCE(SUM(ol.qty * ol.uprice), 0.0) AS total_sales_amount
            FROM orders o
            JOIN orderlines ol ON ol.ono = o.ono
            WHERE date(?) <= date(o.odate) AND date(o.odate) <= date(?);
            """,
            (start_date, as_of),
        )
        row = await cur.fetchone()
        await cur.close()
    distinct_orders = int(row[0] or 0)
    distinct_products_sold = int(row[1] or 0)
    distinct_customers = int(row[2] or 0)
    total_sales_amount = float(row[3] or 0.0)
    avg_amount_per_customer = (
        total_sales_amount / distinct_customers if distinct_customers > 0 else 0.0
    )
    return {
        "distinct_orders": distinct_orders,
        "distinct_products_sold": distinct_products_sold,
        "distinct_customers": distinct_customers,
        "avg_amount_per_customer": avg_amount_per_customer,
        "total_sales_amount": total_sales_amount,
    }


async def top_products_by_orders(
    k: int = 3,
    include_ties_at_k: bool = True,
    as_of: Optional[datetime] = None,
) -> List[Tuple[int, int]]:
    """
    Return top products by count of distinct orders they appear in: [(pid, order_count), ...]
    If include_ties_at_k is True, include all products tied at the kth position.
    """
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT pid, COUNT(DISTINCT ono) AS order_count FROM orderlines GROUP BY pid ORDER BY order_count DESC, pid;"
        )
        rows = await cur.fetchall()
        await cur.close()
    if not rows:
        return []
    if not include_ties_at_k:
        rows = rows[:k]
    else:
        if k < 1:
            return []
        threshold = rows[min(k, len(rows)) - 1][1]
        rows = [r for r in rows if r[1] >= threshold]
    return [(int(r[0]), int(r[1])) for r in rows]


async def top_products_by_views(
    k: int = 3,
    include_ties_at_k: bool = True,
    as_of: Optional[datetime] = None,
) -> List[Tuple[int, int]]:
    """
    Return top products by total views (viewedProduct): [(pid, view_count), ...]
    If include_ties_at_k is True, include all products tied at the kth position.
    """
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT pid, COUNT(*) AS view_count FROM viewedProduct GROUP BY pid ORDER BY view_count DESC, pid;"
        )
        rows = await cur.fetchall()
        await cur.close()
    if not rows:
        return []
    if not include_ties_at_k:
        rows = rows[:k]
    else:
        if k < 1:
            return []
        threshold = rows[min(k, len(rows)) - 1][1]
        rows = [r for r in rows if r[1] >= threshold]
    return [(int(r[0]), int(r[1])) for r in rows]


# ---------------------------
# Convenience Helpers
# ---------------------------


async def update_product_price_stock(
    pid: int,
    new_price: Optional[float],
    new_stock_count: Optional[int],
) -> bool:
    """
    Update price and/or stock_count (only provided fields). Return True if a row was updated.
    """
    if new_price is None and new_stock_count is None:
        return False
    async with connect() as conn:
        # fetch current to compute updates if necessary
        cur = await conn.execute(
            "SELECT price, stock_count FROM products WHERE pid = ?;",
            (pid,),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            return False
        price = float(row[0]) if row[0] is not None else None
        stock = int(row[1]) if row[1] is not None else None
        upd_price = new_price if new_price is not None else price
        upd_stock = new_stock_count if new_stock_count is not None else stock
        res = await conn.execute(
            "UPDATE products SET price = ?, stock_count = ? WHERE pid = ?;",
            (upd_price, upd_stock, pid),
        )
        await conn.commit()
        return res.rowcount > 0


async def product_exists(pid: int) -> bool:
    async with connect() as conn:
        cur = await conn.execute("SELECT 1 FROM products WHERE pid = ?;", (pid,))
        row = await cur.fetchone()
        await cur.close()
        return row is not None


async def product_stock(pid: int) -> Optional[int]:
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT stock_count FROM products WHERE pid = ?;", (pid,)
        )
        row = await cur.fetchone()
        await cur.close()
        return int(row[0]) if row else None


async def set_cart_qty_if_in_stock(
    cid: int, sessionNo: int, pid: int, qty: int
) -> bool:
    """
    Set the customer's total cart quantity for a product across sessions, if within stock.
    Consolidates into a single row under the current session. Returns True if set; False if qty exceeds stock or qty < 0.
    """
    if qty < 0:
        return False
    async with connect() as conn:
        cur = await conn.execute(
            "SELECT stock_count FROM products WHERE pid=?;", (pid,)
        )
        row = await cur.fetchone()
        await cur.close()
        stock = int(row[0]) if row else 0
        if qty > stock:
            return False
        # consolidate into current session
        await conn.execute("DELETE FROM cart WHERE cid=? AND pid=?;", (cid, pid))
        await conn.execute(
            "INSERT INTO cart(cid, sessionNo, pid, qty) VALUES(?, ?, ?, ?);",
            (cid, sessionNo, pid, qty),
        )
        await conn.commit()
        return True
