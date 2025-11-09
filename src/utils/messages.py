from textual.message import Message


class QuitRequestedMessage(Message):
    """
    broadcasted when the app is about to quit
    """

    bubble = True


class UserLogoutMessage(Message):
    """
    broadcasted when the user logs out
    """

    bubble = True


class UserLoginMessage(Message):
    """
    Fired when user logged, so the scren can refresh
    """

    bubble = True


class CartChangedMessage(Message):
    """
    Fire by OrderEntry if any item changed in the cart, or new items being added in prod search
    Will trigger a refresh of cart screen

    If posted from outside CartScreen, make sure to post at App level
    """

    bubble = True


class NewOrderMessage(Message):
    """
    Fired when a new oder is created.
    Listened to by past oders, and sales functionality
    """

    bubble = True


class ModeSwitchedMessage(Message):
    """
    fired whenever switch_mode is called
    must be fired from app level
    """

    bubble = True

    def __init__(self, old_mode: str, new_mode: str) -> None:
        super().__init__()
        self.old_mode = old_mode
        self.new_mode = new_mode
