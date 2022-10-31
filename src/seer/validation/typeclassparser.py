from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import TypeClass, TypeClassFactory, Restriction2
from seer.common.params import Params
from seer.validation.nodetypes import Nodes

################################################################################
# this parses the asl into a typeclass. certain asls define types. these are:
#   type, interface_type, prod_type, types, fn_type_in, fn_type_out, fn_type, args, rets
#   def, create, struct, interface
class TypeclassParser(Visitor):
    def apply(self, state: Params) -> TypeClass:
        return self._route(state.asl, state)

    @Visitor.for_asls("type", "var_type")
    def type_(fn, state: Params) -> TypeClass:
        """
        (type int)
        (var_type int)
        """
        node = Nodes.TypeLike(state)
        restriction = node.get_restriction()
        found_type = state.get_enclosing_module().get_typeclass_by_name(node.get_name())
        if found_type:
            return found_type.with_restriction(restriction)
        raise Exception(f"unknown type! {node.get_name()}")

    @Visitor.for_asls(":")
    def colon_(fn, state: Params) -> TypeClass:
        """
        (: name (type int))
        """
        return fn.apply(state.but_with(asl=state.second_child()))

    @Visitor.for_asls("prod_type", "types")
    def prod_type_(fn, state: Params) -> TypeClass:
        """
        (prod_type (: name1 (type int)) (: name2 (type str)))
        (types (type int) (type str))
        """
        component_types = [fn.apply(state.but_with(asl=component)) for component in state.asl]
        return TypeClassFactory.produce_tuple_type(components=component_types, global_mod=state.global_mod)

    @Visitor.for_asls("fn_type_in", "fn_type_out")
    def fn_type_out(fn, state: Params) -> TypeClass:
        """
        (fn_type_in (type/s ...)
        (fn_type_out (type/s ...))
        """
        if len(state.asl) == 0:
            return state.get_void_type() 
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.for_asls("fn_type")
    def fn_type_(fn, state: Params) -> TypeClass:
        """
        (fn_type (fn_type_in ...) (fn_type_out ...))
        """
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.first_child())),
            ret=fn.apply(state.but_with(asl=state.second_child())),
            mod=state.global_mod)

    @Visitor.for_asls("args", "rets")
    def args_(fn, state: Params) -> TypeClass:
        """ 
        (args (type ...))
        """
        if state.asl:
            return fn.apply(state.but_with(asl=state.first_child()))
        return state.get_void_type().with_restriction(Restriction2.for_let())

    @Visitor.for_asls("def", "create", ":=")
    def def_(fn, state: Params) -> TypeClass:
        """
        (def name (args ...) (rets ...) (seq ...))
        (create name (args ...) (rets ...) (seq ...)) # after normalization
        """
        node = Nodes.CommonFunction(state)
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=node.get_args_asl())),
            ret=fn.apply(state.but_with(asl=node.get_rets_asl())),
            mod=state.global_mod)
