from __future__ import annotations
from typing import Any, Self
from alpaca.utils import Visitor
from alpaca.clr import AST
from alpaca.concepts import (Type, TypeFactory2, Type2, TypeManifest,
                             AbstractParams, Corpus, Module)
import eisen.adapters as adapters
from eisen.validation.validate import Validate
from eisen.state.basestate import BaseState
from eisen.common.typefactory import TypeFactory
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
        modifier = str(self.modifier)
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

    def get_defined_type(self, name: str, specified_namespace: str = None) -> Type2:
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

    def produce_void_type(self) -> TypeManifest:
        return self.get_type_factory().produce_void_type(modifier=Binding.void,
                                                         nilable=False)


class TypeParser2(Visitor):
    def run(self, state: BaseState):
        return self.apply(TypeParserState.create_from_basestate(state))

    def apply(self, state: TypeParserState) -> TypeManifest:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _type_binding_(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (mut (type int))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state).get_binding())
        return fn.apply(state.but_with(ast=state.first_child(),
                                       modifier=binding))

    @Visitor.for_ast_types(*adapters.TypeLike.ast_types)
    def _type(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (type int)
        """
        node = adapters.TypeLike(state)
        return state.get_type_factory().produce_type(
            type_=state.get_defined_type(node.get_name()),
            **state.get_options())

    @Visitor.for_ast_types(":")
    def _colon(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (: (binding name) (type int))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state.but_with_first_child()).get_binding())
        return fn.apply(state.but_with(ast=state.second_child(), modifier=binding))

    @Visitor.for_ast_types("prod_type", "types")
    def _types(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (prod_type (: name1 (type int)) (: name2 (type str)))
        (types (type int) (type str))
        """
        components= [fn.apply(state.but_with(ast=component)) for component in state.get_ast()]
        return state.get_type_factory().produce_tuple_type(components, **state.get_options())

    @Visitor.for_ast_types("fn_type")
    def _fn_type(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        return state.get_type_factory().produce_function_type(
            args=fn.apply(state.but_with(ast=state.first_child())),
            rets=fn.apply(state.but_with(ast=state.second_child())),
            **state.get_options())

    @Visitor.for_ast_types("fn_type_in", "fn_type_out")
    def _fn_type_io(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if state.get_ast().has_no_children():
            return state.produce_void_type()

        return fn.apply(state.but_with(ast=state.first_child()))


    @Visitor.for_ast_types("args", "rets")
    def _args(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (args (type ...))
        (rets (type ...))
        """
        if state.get_ast().has_no_children():
            return state.produce_void_type()
        return fn.apply(state.but_with(
            ast=state.first_child(),
            is_return_value=state.get_ast().type == "rets"))

    @Visitor.for_ast_types("def", "create")
    def _def(fn: TypeParser2, state: TypeParserState) -> TypeManifest:
        """
        (def name (args ...) (rets ...) (seq ...))
        (create name (args ...) (rets ...) (seq ...)) # after normalization
        """
        node = adapters.CommonFunction(state)
        return state.get_type_factory().produce_function_type(
            args=fn.apply(state.but_with(ast=node.get_args_ast())),
            rets=fn.apply(state.but_with(ast=node.get_rets_ast())),
            **state.get_options())



State = BaseState
class ProtoTypeParser(Visitor):
    """this parses the ast into a type. certain asts define types. these are:
        type, interface_type, prod_type, types,
        fn_type_in, fn_type_out, fn_type, args, rets
        def, create, struct, interface
    """
    def apply(self, state: State) -> Type:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _type_binding_(fn, state: State) -> Type:
        """
        Note: this is a special binding AST which binds a type, not a name.
        (void (fn_type ...))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state).get_binding())
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types(*adapters.TypeLike.ast_types)
    def type_(fn, state: State) -> Type:
        """
        (type int)
        (var_type int)
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        node = adapters.TypeLike(state)
        name = node.get_name()
        type = state.get_defined_type(name)
        if Validate.type_exists(state, name, type).failed():
            return state.get_abort_signal()
        return type

    @Visitor.for_ast_types(":")
    def colon_(fn, state: State) -> Type:
        """
        (: (binding name) (type int))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state.but_with_first_child()).get_binding())
        return fn.apply(state.but_with(ast=state.second_child()))

    @Visitor.for_ast_types("prod_type", "types")
    def prod_type_(fn, state: State) -> Type:
        """
        (prod_type (: name1 (type int)) (: name2 (type str)))
        (types (type int) (type str))
        """
        component_types = [fn.apply(state.but_with(ast=component)) for component in state.get_ast()]
        return TypeFactory.produce_tuple_type(components=component_types)

    @Visitor.for_ast_types("fn_type_in")
    def fn_type_in(fn, state: State) -> Type:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if len(state.get_ast()) == 0:
            return state.get_void_type()
        return fn.apply(state.but_with(ast=state.first_child()))

    @Visitor.for_ast_types("fn_type_out")
    def fn_type_out(fn, state: State) -> Type:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if len(state.get_ast()) == 0:
            return state.get_void_type()

        return fn.apply(state.but_with(ast=state.first_child()))

    @Visitor.for_ast_types("fn_type")
    def fn_type_(fn, state: State) -> Type:
        """
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        return TypeFactory.produce_function_type(
            arg=fn.apply(state.but_with(ast=state.first_child())),
            ret=fn.apply(state.but_with(ast=state.second_child())),
            mod=None)

    @Visitor.for_ast_types("args")
    def args_(fn, state: State) -> Type:
        """
        (args (type ...))
        """
        if state.get_ast():
            return fn.apply(state.but_with(ast=state.first_child()))
        return state.get_void_type()

    @Visitor.for_ast_types("rets")
    def rets_(fn, state: State) -> Type:
        """
        (rets (type ...))
        """
        if state.get_ast():
            return fn.apply(state.but_with(ast=state.first_child()))
        return state.get_void_type()

    @Visitor.for_ast_types("def", "create", ":=", "is_fn")
    def def_(fn, state: State) -> Type:
        """
        (def name (args ...) (rets ...) (seq ...))
        (create name (args ...) (rets ...) (seq ...)) # after normalization
        """
        node = adapters.CommonFunction(state)
        return TypeFactory.produce_function_type(
            arg=fn.apply(state.but_with(ast=node.get_args_ast())),
            ret=fn.apply(state.but_with(ast=node.get_rets_ast())),
            mod=None)

    @Visitor.for_ast_types("para_type")
    def para_type(fn, state: State) -> Type:
        """
        (para_type name (tags type1 type2))
        (para_type name type1)
        """
        return TypeFactory.produce_parametric_type(
            name=state.first_child().value,
            parametrics=[fn.apply(state.but_with(ast=child))
                for child in state.get_child_asts()])


class TypeParser(Visitor):
    """this parses the ast into a type. certain asts define types. these are:
        type, interface_type, prod_type, types,
        fn_type_in, fn_type_out, fn_type, args, rets
        def, create, struct, interface
    """
    def apply(self, state: State) -> Type:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _type_binding_(fn, state: State) -> Type:
        """
        Note: this is a special binding AST which binds a type, not a name.
        (void (fn_type ...))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state).get_binding())
        type = fn.apply(state.but_with_first_child())
        if type == state.get_void_type(): return type
        return type.with_modifier(binding)

    @Visitor.for_ast_types(*adapters.TypeLike.ast_types)
    def type_(fn, state: State) -> Type:
        """
        (type int)
        """
        node = adapters.TypeLike(state)
        name = node.get_name()
        if state.get_defined_type(name) == state.get_void_type():
            return state.get_void_type()
        type = state.get_defined_type(name).with_modifier(Binding.void)
        if Validate.type_exists(state, name, type).failed():
            return state.get_abort_signal()
        return type

    @Visitor.for_ast_types(":")
    def colon_(fn, state: State) -> Type:
        """
        (: (binding name) (type int))
        """
        binding = BindingMechanics.infer_fixed_binding(adapters.BindingAST(state.but_with_first_child()).get_binding())
        return fn.apply(state.but_with(ast=state.second_child())).with_modifier(binding)

    @Visitor.for_ast_types("prod_type", "types")
    def prod_type_(fn, state: State) -> Type:
        """
        (prod_type (: name1 (type int)) (: name2 (type str)))
        (types (type int) (type str))
        """
        component_types = [fn.apply(state.but_with(ast=component)) for component in state.get_ast()]
        return TypeFactory.produce_tuple_type(components=component_types)

    @Visitor.for_ast_types("fn_type_in")
    def fn_type_in(fn, state: State) -> Type:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if len(state.get_ast()) == 0:
            return state.get_void_type()
        return fn.apply(state.but_with(ast=state.first_child()))

    @Visitor.for_ast_types("fn_type_out")
    def fn_type_out(fn, state: State) -> Type:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if len(state.get_ast()) == 0:
            return state.get_void_type()

        return fn.apply(state.but_with(ast=state.first_child()))

    @Visitor.for_ast_types("fn_type")
    def fn_type_(fn, state: State) -> Type:
        """
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        return TypeFactory.produce_function_type(
            arg=fn.apply(state.but_with(ast=state.first_child())),
            ret=fn.apply(state.but_with(ast=state.second_child())),
            mod=None)

    @Visitor.for_ast_types("args")
    def args_(fn, state: State) -> Type:
        """
        (args (type ...))
        """
        if state.get_ast():
            return fn.apply(state.but_with(ast=state.first_child()))
        return state.get_void_type()

    @Visitor.for_ast_types("rets")
    def rets_(fn, state: State) -> Type:
        """
        (rets (type ...))
        """
        if state.get_ast():
            type = fn.apply(state.but_with(ast=state.first_child()))
            if type.is_tuple():
                components = [t.with_modifier(Binding.ret_new) if t.modifier == Binding.new else t for t in type.components]
                return TypeFactory.produce_tuple_type(components)
            else:
                return type.with_modifier(Binding.ret_new) if type.modifier == Binding.new else type
        return state.get_void_type()

    @Visitor.for_ast_types("def", "create", ":=", "is_fn")
    def def_(fn, state: State) -> Type:
        """
        (def name (args ...) (rets ...) (seq ...))
        (create name (args ...) (rets ...) (seq ...)) # after normalization
        """
        node = adapters.CommonFunction(state)
        return TypeFactory.produce_function_type(
            arg=fn.apply(state.but_with(ast=node.get_args_ast())),
            ret=fn.apply(state.but_with(ast=node.get_rets_ast())),
            mod=None).with_modifier(Binding.void)

    @Visitor.for_ast_types("para_type")
    def para_type(fn, state: State) -> Type:
        """
        (para_type name (tags type1 type2))
        (para_type name type1)
        """
        return TypeFactory.produce_parametric_type(
            name=state.first_child().value,
            parametrics=[fn.apply(state.but_with(ast=child))
                for child in state.get_child_asts()])
