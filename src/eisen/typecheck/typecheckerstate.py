from __future__ import annotations

from alpaca.concepts import Module, Context, Type
from alpaca.clr import AST

from eisen.state.basestate import BaseState
from eisen.typecheck.typeparser import TypeParser, TypeParser2

class TypeCheckerState(BaseState):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            arg_type: Type = None,
            in_constructor: bool = None,
            in_rets: bool = None,
            ) -> BaseState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            arg_type=arg_type,
            in_constructor=in_constructor,
            in_rets=in_rets
            )

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return TypeCheckerState(**state._get(), arg_type=None, in_constructor=False, in_rets=False,
                                typeparser=TypeParser(), typeparser2=TypeParser2())

    def get_arg_type(self) -> Type | None:
        return self.arg_type

    def is_inside_create(self) -> bool:
        return self.in_constructor

    def is_inside_rets(self) -> bool:
        return self.in_rets

    def parse_type_represented_here(self) -> Type:
        # return self.typeparser2.run(self)
        return self.typeparser.apply(self)
