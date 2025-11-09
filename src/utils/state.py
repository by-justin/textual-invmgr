from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

import db.crud as crud


@dataclass
class GlobalState:
    """
    Centralized application state shared by screens.

    Fields:
      - uid: current logged-in user id (users.uid)
      - role: "customer" | "sales" | None if not determined yet
      - cid: customers.cid for the logged-in customer (if role==customer)
      - session_no: active session number for the customer session
    """

    uid: Optional[int] = None
    role: Optional[Literal["customer", "sales"]] = None

    session_no: Optional[int] = None

    async def start_session(self, when: Optional[datetime] = None) -> Optional[int]:
        """Start a session for the current customer if possible.
        Returns the session number if started, otherwise None.
        """
        if self.role != "customer" or self.uid is None:
            return None
        when = when or datetime.now()
        self.session_no = await crud.start_session(self.uid, when)
        return self.session_no

    async def end_session(self, when: Optional[datetime] = None) -> None:
        """
        End the current session if one exists.
        This is only called upon logging out
        """

        if self.role != "customer" or self.uid is None or self.session_no is None:
            return
        when = when or datetime.now()
        await crud.end_session(self.uid, self.session_no, when)
        self.session_no = None
        self.uid = None
        self.role = None
