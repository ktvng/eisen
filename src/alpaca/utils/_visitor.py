from __future__ import annotations
from typing import Any
import sys

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


class VisitorException(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        self.msg = msg
        super().__init__(*args)

    def __str__(self) -> str:
        return self.msg


orignal_hook = sys.excepthook
def exceptions_hook(e_type, e_value: Exception, tb):
    if e_type == VisitorException:
        orignal_hook(e_type, e_value.with_traceback(None), None)
    else:
        orignal_hook(e_type, e_value, tb)

sys.excepthook = exceptions_hook

class Visitor():
    max_depth = 100

    def __init__(self, debug: bool = False):
        # true if we should add debug logging and tracking to this wrangler
        self.debug = debug

        # logger for use with debugging
        self.logger = Logger(
            file="wrangler",
            tag=type(self).__name__)

        self.logger.log_debug("#" * 20 + " Init " + "#" * 20)

        # depth of recusion, used during debug functionality
        self._depth = 0

        attrs = dir(self)
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

    def _route(self, asl: CLRList, state: Any):
        try:
            if isinstance(asl, CLRList):
                transform = self.index.get(asl.type, self.new_default_transform)
                if transform is None:
                    raise Exception(f"{self._get_loggable_name()} has no tranform for {asl.type}")
                result = transform(self, state)
            else:
                if self.token_transform is None:
                    raise Exception(f"{self._get_loggable_name()} has no transform for CLRTokens")
                result = self.token_transform(self, state)

            return result
        except VisitorException as ve:
            raise ve
        except Exception as e:
            raise VisitorException(f"\n{self._get_loggable_name()} thrown from asl:\n{asl}") from e

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
