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

class TransformFunction2():
    def __init__(self):
        attrs = dir(self)
        self.partial_transforms: list[PartialTransform] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), PartialTransform)]

    def _apply(self, match_args: list, fn_args: list):
        matching_transforms = [f for f in self.partial_transforms if f.covers(*match_args)]
        if not matching_transforms:
            raise Exception(f"No transforms matching for {match_args}")
        if len(matching_transforms) > 1:
            raise Exception(f"Multiple transforms matching for {match_args}")

        return matching_transforms[0].invoke(*[self, *fn_args])

class _TransformFunction():
    def __init__(self, type: str, over_class: Any):
        attrs = dir(over_class)
        self.type = type
        self.over_class = over_class

        # obtain list of partial transforms from the containing over_class
        self.partial_transforms: list[PartialTransform] = [getattr(over_class, k) for k in attrs 
            if isinstance(getattr(over_class, k), PartialTransform)]

    def apply(self, match_args: list, fn_args: list):
        matching_transforms = [f for f in self.partial_transforms if f.covers(*match_args)]
        if not matching_transforms:
            raise Exception(f"No transforms matching for {match_args}")
        if len(matching_transforms) > 1:
            raise Exception(f"Multiple transforms matching for {match_args}")
        
        return matching_transforms[0].invoke(*fn_args)

def TransformFunction(cls):
    return _TransformFunction(cls.__name__, cls)
