from __future__ import annotations
from typing import Any, Callable

class PartialTransform():
    def __init__(self, predicate: Callable[[Any], bool], f: Callable[[Any], Any]):
        self.f = f
        self.predicate = predicate

    def invoke(self, *args):
        if args:
            return self.f(*args)
        else:
            return self.f()

    def covers(self, *args):
        if args:
            return self.predicate(*args)
        else:
            return self.predicate()

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)

class TransformFunction():
    def __init__(self):
        attrs = dir(self)
        self.partial_transforms: list[PartialTransform] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), PartialTransform)]

    def _apply(self, match_args: list, fn_args: list):
        matching_transforms = [f for f in self.partial_transforms if f.covers(*match_args)]
        if not matching_transforms:
            args = [str(arg) for arg in match_args]
            raise Exception(f"{type(self)}: No transforms matching for {args}")
        if len(matching_transforms) > 1:
            raise Exception(f"Multiple transforms matching for {match_args}")

        return matching_transforms[0].invoke(*[self, *fn_args])

    @classmethod
    def covers(cls, predicate: Callable[[Any], bool]):
        def decorator(f):
            return PartialTransform(predicate, f)
        return decorator 


