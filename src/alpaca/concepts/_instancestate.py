from __future__ import annotations
from typing import Any

from alpaca.concepts._initialization import Initialization
class InstanceState:
    def __init__(
            self, name: str,
            restriction: Any,
            initialization: Initialization) -> None:
        self.name = name
        self.restriction = restriction
        self.initialization = initialization
