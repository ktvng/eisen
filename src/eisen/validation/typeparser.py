from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type
import eisen.adapters as adapters
from eisen.validation.validate import Validate
from eisen.state.basestate import BaseState as State
from eisen.common.typefactory import TypeFactory

class TypeParser(Visitor):
    """this parses the ast into a type. certain asts define types. these are:
        type, interface_type, prod_type, types,
        fn_type_in, fn_type_out, fn_type, args, rets
        def, create, struct, interface
    """
    def apply(self, state: State) -> Type:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def binding_(fn, state: State) -> Type:
        """
        (void (fn_type ...))
        """
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
        (: name (type int))
        """
        return fn.apply(state.but_with(ast=state.second_child()))

    @Visitor.for_ast_types("let")
    def let_(fn, state: State) -> Type:
        """
        (let name (type int))
        """
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

    @Visitor.for_ast_types(*adapters.ArgsRets.ast_types)
    def args_(fn, state: State) -> Type:
        """
        (args (type ...))
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
