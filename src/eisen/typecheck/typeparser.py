from __future__ import annotations
from typing import Any, Self
from alpaca.utils import Visitor
from alpaca.clr import AST
from alpaca.concepts import (Type, TypeFactory2, Type, TypeManifest,
                             AbstractParams, Corpus, Module)
import eisen.adapters as adapters
from eisen.state.basestate import BaseState
from eisen.common.binding import Binding, BindingMechanics


class TypeParserState(AbstractParams):
    def but_with(self,
            ast: AST = None,
            modifier: Binding = None,
            nilable: bool = None,
            is_return_value: bool = None
            ) -> BaseState:

        return self._but_with(
            ast=ast,
            modifier=modifier,
            nilable=nilable,
            is_return_value=is_return_value,
            )

    @classmethod
    def create_from_basestate(cls, state: BaseState):
        return TypeParserState(ast=state.get_ast(), corpus=state.get_corpus(), type_factory=state.get_type_factory(),
                               mod=state.get_enclosing_module(),
                               nilable=False,
                               modifier=Binding.void,
                               is_return_value=False)

    def get_options(self) -> dict[str, Any]:
        modifier = self.modifier
        if modifier == Binding.new and self.is_return_value: modifier = Binding.ret_new
        return { "modifier": modifier, "nilable": self.nilable }

    def get_type_factory(self) -> TypeFactory2:
        return self.type_factory

    def get_ast(self) -> AST:
        return self.ast

    def get_corpus(self) -> Corpus:
        return self.corpus

    def first_child(self) -> AST:
        return self.get_ast().first()

    def second_child(self) -> AST:
        return self.get_ast().second()

    def get_defined_type(self, name: str, specified_namespace: str = None) -> Type:
        return self.get_corpus().get_type(
            name=name,
            environmental_namespace=self.get_enclosing_module().get_namespace_str(),
            specified_namespace=specified_namespace)

    def get_enclosing_module(self) -> Module:
        return self.mod

    def but_with_first_child(self) -> Self:
        return self.but_with(ast=self.first_child())

    def but_with_second_child(self) -> Self:
        return self.but_with(ast=self.second_child())

    def get_void_type(self) -> TypeManifest:
        return self.get_type_factory().produce_void_type(modifier=Binding.void,
                                                         nilable=False)


class TypeParser(Visitor):
    def run(self, state: BaseState):
        return self.apply(TypeParserState.create_from_basestate(state))

    def apply(self, state: TypeParserState) -> TypeManifest:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _type_binding_(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (mut (type int))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state).get_binding())
        return fn.apply(state.but_with(ast=state.first_child(),
                                       modifier=binding))

    @Visitor.for_ast_types(*adapters.TypeLike.ast_types)
    def _type(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (type int)
        """
        node = adapters.TypeLike(state)
        return state.get_type_factory().produce_type(
            type_=state.get_defined_type(node.get_name()),
            **state.get_options())

    @Visitor.for_ast_types(":")
    def _colon(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (: (binding name) (type int))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state.but_with_first_child()).get_binding())
        return fn.apply(state.but_with(ast=state.second_child(), modifier=binding))

    @Visitor.for_ast_types("prod_type", "types")
    def _types(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (prod_type (: name1 (type int)) (: name2 (type str)))
        (types (type int) (type str))
        """
        components= [fn.apply(state.but_with(ast=component)) for component in state.get_ast()]
        return state.get_type_factory().produce_tuple_type(components, **state.get_options())

    @Visitor.for_ast_types("fn_type")
    def _fn_type(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        return state.get_type_factory().produce_function_type(
            args=fn.apply(state.but_with(ast=state.first_child())),
            rets=fn.apply(state.but_with(ast=state.second_child())),
            **state.get_options())

    @Visitor.for_ast_types("fn_type_in", "fn_type_out")
    def _fn_type_io(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if state.get_ast().has_no_children():
            return state.get_void_type()

        return fn.apply(state.but_with(ast=state.first_child()))


    @Visitor.for_ast_types("args", "rets")
    def _args(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (args (type ...))
        (rets (type ...))
        """
        if state.get_ast().has_no_children():
            return state.get_void_type()
        return fn.apply(state.but_with(
            ast=state.first_child(),
            is_return_value=state.get_ast().type == "rets"))

    @Visitor.for_ast_types("def", "create")
    def _def(fn: TypeParser, state: TypeParserState) -> TypeManifest:
        """
        (def name (args ...) (rets ...) (seq ...))
        (create name (args ...) (rets ...) (seq ...)) # after normalization
        """
        node = adapters.CommonFunction(state)
        return state.get_type_factory().produce_function_type(
            args=fn.apply(state.but_with(ast=node.get_args_ast())),
            rets=fn.apply(state.but_with(ast=node.get_rets_ast())),
            **state.get_options())
