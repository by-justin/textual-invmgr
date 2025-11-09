# provide dataclass models

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    uid: int
    pwd: str
    role: str  # "customer" or "sales"


@dataclass(frozen=True)
class Customer:
    cid: int
    name: str
    email: str


@dataclass(frozen=True)
class Product:
    pid: int
    name: str
    category: str
    price: float
    stock_count: int
    descr: str


@dataclass(frozen=True)
class Order:
    ono: int
    cid: int
    sessionNo: int
    odate: datetime
    shipping_address: str


@dataclass(frozen=True)
class OrderLine:
    ono: int
    lineNo: int
    pid: int
    qty: int
    uprice: float  # unit price at time of order


@dataclass(frozen=True)
class Session:
    cid: int
    sessionNo: int
    start_time: datetime
    end_time: datetime | None


@dataclass(frozen=True)
class ViewedProduct:
    cid: int
    sessionNo: int
    ts: datetime
    pid: int


@dataclass(frozen=True)
class Search:
    cid: int
    sessionNo: int
    ts: datetime
    query: str


@dataclass(frozen=True)
class CartItem:
    cid: int
    sessionNo: int
    pid: int
    qty: int
