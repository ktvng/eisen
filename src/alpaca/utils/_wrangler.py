from __future__ import annotations
from typing import Any, Callable

from alpaca.logging._logger import Logger

class PartialTransform():
    def __init__(self, predicate: Callable[[Any], bool], f: Callable[[Any], Any]):
        self.f = f
        self.predicate = predicate

    def invoke(self, *args):
        return self.f(*args)

    def covers(self, *args):
        return self.predicate(*args)

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)

class DefaultTransform():
    def __init__(self, f: Callable[[Any], Any]):
        self.f = f

    def invoke(self, *args):
        return self.f(*args)

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs) 

class Wrangler():
    max_depth = 100

    def __init__(self, debug: bool = False):
        # true if we should add debug logging and tracking to this wrangler
        self.debug = debug

        # logger for use with debugging
        self.logger = Logger(
            file="wrangler", 
            tag=type(self).__name__)

        self.logger.log("#" * 20 + " Init " + "#" * 20)

        # depth of recusion, used during debug functionality
        self._depth = 0

        attrs = dir(self)
        self.partial_transforms: list[PartialTransform] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), PartialTransform)]
        
        has_default_transform_attr = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), DefaultTransform)]

        self.default_transform = None
        if has_default_transform_attr:
            self.default_transform: DefaultTransform = has_default_transform_attr[0]

    def _apply(self, match_args: list, fn_args: list):
        args_str = str([str(arg) for arg in match_args])
        self.logger.log(f"Matching against {args_str}, depth={self._depth}")

        matching_transforms = [f for f in self.partial_transforms if f.covers(*match_args)]
        if not matching_transforms:
            if self.default_transform is not None:
                return self.default_transform.invoke(*[self, *fn_args])

            msg = f"No matching transforms for provided match_args: '{args_str}'"
            self.logger.raise_exception(msg)

        if len(matching_transforms) > 1:
            msg = f"Multiple matching transforms for provided match_args: '{args_str}'"
            transform_names = ", ".join([x.f.__name__ for x in matching_transforms])
            self.logger.log_error(f"Matched transform names: [{transform_names}]")
            self.logger.raise_exception(msg)

        if self.debug and self._depth > self.max_depth:
            self.logger.raise_exception(f"Max depth ({self.max_depth}) reached; forcing exit")

        self._depth += 1
        result = matching_transforms[0].invoke(*[self, *fn_args])
        self._depth -= 1
        return result

    @classmethod
    def covers(cls, predicate: Callable[[Any], bool]):
        def decorator(f):
            return PartialTransform(predicate, f)
        return decorator 

    @classmethod
    def default(cls, f):
        return DefaultTransform(f)
