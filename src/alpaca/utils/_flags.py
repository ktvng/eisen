from __future__ import annotations

class AbstractFlags:
    def __init__(self, flags: list[str] = []):
        self._flags = flags

    def __getitem__(self, x) -> str:
        return self._flags.__getitem__(x)

    def __setitem__(self, x, y: str) -> str:
        return self._flags.__setitem__(x, y)

    def __len__(self) -> int:
        return len(self._flags)

    def but_with(self, *args) -> AbstractFlags:
        return AbstractFlags(list(set(list(args) + self._flags)))

    def but_without(self, *args) -> AbstractFlags:
        return AbstractFlags([f for f in self._flags if f not in args])
