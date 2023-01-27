from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type, TypeFactory
import eisen.nodes as nodes
from eisen.validation.validate import Validate
from eisen.common.restriction import FunctionalRestriction
from eisen.state.basestate import BaseState as State

class TypeParser(Visitor):
    """this parses the asl into a type. certain asls define types. these are:
        type, interface_type, prod_type, types,
        fn_type_in, fn_type_out, fn_type, args, rets
        def, create, struct, interface
    """
    def apply(self, state: State) -> Type:
        return self._route(state.get_asl(), state)

    @Visitor.for_asls("type", "var_type", "var_type?")
    def type_(fn, state: State) -> Type:
        """
        (type int)
        (var_type int)
        """
        node = nodes.TypeLike(state)
        name = node.get_name()
        type = state.get_defined_type(name)
        if Validate.type_exists(state, name, type).failed():
            return state.get_abort_signal()
        return type.with_restriction(node.get_restriction(type))

    @Visitor.for_asls(":")
    def colon_(fn, state: State) -> Type:
        """
        (: name (type int))
        """
        return fn.apply(state.but_with(asl=state.second_child()))

    @Visitor.for_asls("prod_type", "types")
    def prod_type_(fn, state: State) -> Type:
        """
        (prod_type (: name1 (type int)) (: name2 (type str)))
        (types (type int) (type str))
        """
        component_types = [fn.apply(state.but_with(asl=component)) for component in state.get_asl()]
        return TypeFactory.produce_tuple_type(components=component_types)

    @Visitor.for_asls("fn_type_in", "fn_type_out")
    def fn_type_out(fn, state: State) -> Type:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if len(state.get_asl()) == 0:
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.for_asls("fn_type")
    def fn_type_(fn, state: State) -> Type:
        """
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        return TypeFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.first_child())),
            ret=fn.apply(state.but_with(asl=state.second_child())),
            mod=None).with_restriction(FunctionalRestriction())

    @Visitor.for_asls("args")
    def args_(fn, state: State) -> Type:
        """
        (args (type ...))
        """
        if state.get_asl():
            node = nodes.ArgsRets(state)
            type = fn.apply(state.but_with(asl=state.first_child()))
            node.convert_let_args_to_var(type)
            return type
        return state.get_void_type()

    @Visitor.for_asls("rets")
    def rets_(fn ,state: State) -> Type:
        """
        (rets (type ...))
        """
        if state.get_asl():
            return fn.apply(state.but_with(asl=state.first_child()))
        return state.get_void_type()

    @Visitor.for_asls("def", "create", ":=", "is_fn")
    def def_(fn, state: State) -> Type:
        """
        (def name (args ...) (rets ...) (seq ...))
        (create name (args ...) (rets ...) (seq ...)) # after normalization
        """
        node = nodes.CommonFunction(state)
        return TypeFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=node.get_args_asl())),
            ret=fn.apply(state.but_with(asl=node.get_rets_asl())),
            mod=None).with_restriction(FunctionalRestriction())
