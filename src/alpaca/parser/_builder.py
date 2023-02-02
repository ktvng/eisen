from __future__ import annotations
from typing import Any
from alpaca.clr import CLRList

class TaggedTransform():
    def __init__(self, types: list[str], f):
        self.f = f
        self.handles_types = types

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.f(*args, **kwds)

class DefaultTaggedTransform(TaggedTransform):
    def __init__(self, f) -> None:
        self.f = f
        self.handles_types = None

class Builder():
    def __init__(self) -> None:
        self.index = {}
        self.new_default_transform = None

        attrs = dir(self)
        transforms: list[TaggedTransform] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), TaggedTransform)]
        for t in transforms:
            if isinstance(t, DefaultTaggedTransform):
                self.new_default_transform = t
            else:
                for type_name in t.handles_types:
                    if type_name in self.index:
                        raise Exception(f"{self._get_loggable_name()} already has definition for {type_name}")
                    self.index[type_name] = t

    @classmethod
    def for_procedure(cls, *args: list[str]):
        def decorator(f):
            return TaggedTransform(args, f)
        return decorator

    def apply(self, type_name: str, config, components: list[CLRList | list[CLRList]], *args):
        transform = self.index.get(type_name, self.new_default_transform)
        if transform is None:
            raise Exception(f"{self._get_loggable_name()} has no transform for {type_name}")
        result = transform(self, config, components, *args)
        return result

    def _get_loggable_name(self) -> str:
        return type(self).__name__
