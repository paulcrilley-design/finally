"""Errors raised by the data layer."""


class InsufficientCash(Exception):  # noqa: N818 (name fixed by contract)
    """A buy costs more than the available cash."""


class InsufficientShares(Exception):  # noqa: N818 (name fixed by contract)
    """A sell asks for more shares than are held."""
