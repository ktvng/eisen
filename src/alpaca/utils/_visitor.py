from __future__ import annotations
from typing import Any
import sys

from alpaca.clr import AST, ASTToken
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

    @staticmethod
    def for_ast_types(*args: list[str]):
        def decorator(f):
            return TaggedTransform(args, f)
        return decorator

    @staticmethod
    def for_tokens(f):
        return TokenTaggedTransform(f)

    @staticmethod
    def for_default(f):
        return DefaultTaggedTransform(f)


    def __init__(self, debug: bool = False):
        # true if we should add debug logging and tracking to this wrangler
        self.debug = debug

        # depth of recusion, used during debug functionality
        self._depth = 0

        # logger for use with debugging
        self.logger = Logger(
            file="wrangler",
            tag=type(self).__name__,
            log_level="debug" if self.debug else "info")

        self.logger.log_debug("#" * 20 + " Init " + "#" * 20)

        self.transform_index: dict[str, TaggedTransform] = {}
        self.default_transform: DefaultTaggedTransform = None
        self.token_transform: TokenTaggedTransform = None
        self._build_transform_index()


    def _add_tagged_transform_to_index(self, transform: TaggedTransform):
        for type_name in transform.handles_types:
            if type_name in self.transform_index:
                raise Exception(f"{self._get_loggable_name()} already has definition for {type_name}")
            self.transform_index[type_name] = transform


    def _build_transform_index(self):
        transforms: list[TaggedTransform] = [getattr(self, k) for k in dir(self)
            if isinstance(getattr(self, k), TaggedTransform)]
        for t in transforms:
            match t:
                case DefaultTaggedTransform(): self.default_transform = t
                case TokenTaggedTransform(): self.token_transform = t
                case TaggedTransform(): self._add_tagged_transform_to_index(t)


    def _apply_transform_on_ast(self, ast: AST, state: Any) -> Any:
        transform = self.transform_index.get(ast.type, self.default_transform)
        if transform is None:
            raise Exception(f"{self._get_loggable_name()} has no tranform for {ast.type}")
        return transform(self, state)


    def _apply_transform_on_token(self, state: Any) -> Any:
        if self.token_transform is None:
            raise Exception(f"{self._get_loggable_name()} has no transform for CLRTokens")
        return self.token_transform(self, state)


    def _perform_debug_safety_checks(self, ast: AST):
        self.logger.log_debug(f"Depth: {self._depth}, routing for {ast.type}")
        self._depth += 1
        if self.debug and self._depth > self.max_depth:
            raise Exception(f"{self._get_loggable_name()} may be stuck in infinite recursion.")


    def _route(self, ast: AST, state: Any):
        self._perform_debug_safety_checks(ast)
        try:
            match ast:
                case AST(): result = self._apply_transform_on_ast(ast, state)
                case ASTToken(): result = self._apply_transform_on_token(state)
                case _: raise Exception(f"{self._get_loggable_name()} received unexpected ast {ast}")

            self._depth -= 1
            return result

        except VisitorException as ve:
            raise ve
        except Exception as e:
            raise VisitorException(f"\n{self._get_loggable_name()} thrown from ast:\n{ast}") from e

    def _get_loggable_name(self) -> str:
        return type(self).__name__
