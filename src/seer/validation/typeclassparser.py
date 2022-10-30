from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRToken
from alpaca.concepts import TypeClass, TypeClassFactory, Restriction2
from seer.common import asls_of_type
from seer.common.params import Params
from seer.validation.nodetypes import Nodes

################################################################################
# this parses the asl into a typeclass. certain asls define types. these are:
#   type, interface_type, prod_type, types, fn_type_in, fn_type_out, fn_type, args, rets
#   def, create, struct, interface
class TypeclassParser(Visitor):
    def apply(self, state: Params) -> TypeClass:
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("type", "var_type"))
    def type_(fn, state: Params) -> TypeClass:
        # eg. (type int)
        #     (var_type int)
        token: CLRToken = state.first_child()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        if state.asl.type == "var_type":
            restriction = Restriction2.for_var()
        elif state.asl.type == "type":
            restriction = Restriction2.for_let()

        found_type = state.get_module().get_typeclass_by_name(token.value)
        if found_type:
            return found_type.with_restriction(restriction)
        raise Exception(f"unknown type! {token.value}")

    @Visitor.covers(asls_of_type("interface_type"))
    def interface_type_(fn, state: Params) -> TypeClass:
        # eg. (interface_type name)
        token: CLRToken = state.first_child()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = state.get_module().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Visitor.covers(asls_of_type(":"))
    def colon_(fn, state: Params) -> TypeClass:
        # eg. (: name (type int))
        return fn.apply(state.but_with(asl=state.second_child()))

    @Visitor.covers(asls_of_type("prod_type", "types"))
    def prod_type_(fn, state: Params) -> TypeClass:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        # eg. (types (type int) (type str))
        component_types = [fn.apply(state.but_with(asl=component)) for component in state.asl]
        return TypeClassFactory.produce_tuple_type(components=component_types, global_mod=state.global_mod)

    @Visitor.covers(asls_of_type("fn_type_in", "fn_type_out"))
    def fn_type_out(fn, state: Params) -> TypeClass:
        # eg. (fn_type_in/out (type(s) ...))
        if len(state.asl) == 0:
            return state.get_module().resolve_type(TypeClassFactory.produce_novel_type("void"))
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.covers(asls_of_type("fn_type")) 
    def fn_type_(fn, state: Params) -> TypeClass:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.first_child())),
            ret=fn.apply(state.but_with(asl=state.second_child())),
            mod=state.global_mod)

    @Visitor.covers(asls_of_type("args", "rets"))
    def args_(fn, state: Params) -> TypeClass:
        # eg. (args (type ...))
        if state.asl:
            return fn.apply(state.but_with(asl=state.first_child()))
        return TypeClassFactory.produce_novel_type("void", state.global_mod).with_restriction(Restriction2.for_let())

    @Visitor.covers(asls_of_type("def", "create", ":="))
    def def_(fn, state: Params) -> TypeClass:
        node = Nodes.CommonFunction(state)
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=node.get_args_asl())),
            ret=fn.apply(state.but_with(asl=node.get_rets_asl())),
            mod=state.global_mod)
    
    @Visitor.covers(asls_of_type("struct", "interface"))
    def struct_(fn, state: Params) -> TypeClass:
        # this method should not be reached. Instead, struct/interface typeclasses
        # should be created as a proto_struct/proto_interface by the
        # TypeDeclarationWrangler
        raise Exception("this should not be used to produce struct types")

