from __future__ import annotations
from typing import Any, Callable

from alpaca.clr import CLRList
from alpaca.logging._logger import Logger

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

class TokenTaggedTransform(TaggedTransform):
    def __init__(self, f) -> None:
        self.f = f 
        self.handles_types = None



# TODO: remove some of this deprecated code
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

class Visitor():
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

        # TODO: remove some of this deprecated code
        attrs = dir(self)
        self.partial_transforms: list[PartialTransform] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), PartialTransform)]
        
        has_default_transform_attr = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), DefaultTransform)]

        self.default_transform = None
        if has_default_transform_attr:
            self.default_transform: DefaultTransform = has_default_transform_attr[0]

        # start of new implementation
        self.index = {}
        self.new_default_transform = None
        self.token_transform = None

        transforms: list[TaggedTransform] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), TaggedTransform)]
        for t in transforms:
            if isinstance(t, DefaultTaggedTransform):
                self.new_default_transform = t
            elif isinstance(t, TokenTaggedTransform):
                self.token_transform = t
            else:
                for type_name in t.handles_types:
                    if type_name in self.index:
                        raise Exception(f"{self._get_loggable_name()} already has definition for {type_name}")
                    self.index[type_name] = t


    # TODO: remove some of this deprecated code
    def _apply(self, match_args: list, fn_args: list):
        args_str = str([str(arg) for arg in match_args])
        self.logger.log(f"Matching against {args_str}, depth={self._depth}")

        matching_transforms = [f for f in self.partial_transforms if f.covers(*match_args)]
        if not matching_transforms:
            if self.default_transform is not None:
                return self.default_transform.invoke(*[self, *fn_args])

            msg = f"{type(self).__name__} has no matching transforms for provided match_args: '{args_str}'"
            self.logger.raise_exception(msg)

        if len(matching_transforms) > 1:
            msg = f"{type(self).__name__} has multiple matching transforms for provided match_args: '{args_str}'"
            transform_names = ", ".join([x.f.__name__ for x in matching_transforms])
            self.logger.log_error(f"Matched transform names: [{transform_names}]")
            self.logger.raise_exception(msg)

        if self.debug and self._depth > self.max_depth:
            self.logger.raise_exception(f"{type(self).__name__} has reached max depth ({self.max_depth}); forcing exit")

        self._depth += 1
        result = matching_transforms[0].invoke(*[self, *fn_args])
        self._depth -= 1
        return result

    def _route(self, asl: CLRList, state: Any):
        if isinstance(asl, CLRList):
            transform = self.index.get(asl.type, self.new_default_transform)
            if transform is None:
                raise Exception(f"{self._get_loggable_name()} has no matching transforms for asl of type '{asl.type}'")
            result = transform(self, state)
        else:
            if self.token_transform is None:
                raise Exception(f"{self._get_loggable_name()} has no transform for CLRTokens")
            result = self.token_transform(self, state)
            
        return result

    def _get_loggable_name(self) -> str:
        return type(self).__name__

    @classmethod
    def for_asls(cls, *args: list[str]):
        def decorator(f):
            return TaggedTransform(args, f)
        return decorator

    @classmethod
    def for_tokens(cls, f):
        return TokenTaggedTransform(f)

    @classmethod
    def for_default(cls, f):
        return DefaultTaggedTransform(f)
