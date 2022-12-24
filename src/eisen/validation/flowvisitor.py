from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import TypeClass, TypeClassFactory
from eisen.common import EisenInstance, binary_ops, boolean_return_ops
from eisen.common.state import State
from eisen.common.restriction import (GeneralRestriction, LetRestriction, VarRestriction)
from eisen.validation.nodetypes import Nodes
from eisen.validation.typeclassparser import TypeclassParser
from eisen.validation.validate import Validate
from eisen.validation.callunwrapper import CallUnwrapper

from eisen.validation.builtin_print import BuiltinPrint

implemented_primitive_types = ["str", "int", "bool", "flt"]

class FlowVisitor(Visitor):
    """this evaluates the flow of typeclasses throughout the asl, and records which 
    typeclass flows up through each asl.
    """

    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, state: State) -> TypeClass:
        if self.debug and isinstance(state.get_asl(), CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()

        # this guards the function such that if there is a critical exception thrown
        # downstream, the method will skip execution.
        if state.critical_exception:
            return state.get_void_type()

        result = self._route(state.get_asl(), state)
        if state.is_asl():
            state.assign_returned_typeclass(result)
        return result

    def apply_to_first_child_of(self, state: State) -> TypeClass:
        return self.apply(state.but_with_first_child())

    def apply_to_second_child_of(self, state: State) -> TypeClass:
        return self.apply(state.but_with_second_child())

    def returns_void_type(f):
        """this signifies that the void type should be returned. abstracted so if 
        the void_type is changed, we can easily configure it here.
        """
        def decorator(fn, state: State):
            f(fn, state)
            return state.get_void_type()
        return decorator

    @classmethod
    def add_instance_to_context(cls, name: str, typeclass: TypeClass, state: State):
        """add a new instance to the current context and return it."""
        instance = EisenInstance(
            name=name,
            type=typeclass,
            context=state.get_context(),
            asl=state.get_asl(),
            is_ptr=state.is_ptr)
        state.context.add_instance(instance)
        return instance

    @Visitor.for_tokens
    def token_(fn, state: State) -> TypeClass:
        if state.get_asl().type in implemented_primitive_types:
            return TypeClassFactory.produce_novel_type(name=state.get_asl().type)
        raise Exception(f"unexpected token type of {state.get_asl().type}")

    @Visitor.for_asls("fn_type")
    def fn_type_(fn, state: State) -> TypeClass:
        return TypeclassParser().apply(state)

    @Visitor.for_asls("start", "return", "cond", "seq")
    @returns_void_type
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    @returns_void_type
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_asls("!")
    def not_(fn, state: State) -> TypeClass:
        return fn.apply_to_first_child_of(state)

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> TypeClass:
        node = Nodes.Scope(state)
        parent_typeclass = fn.apply(state.but_with(asl=node.get_object_asl()))
        name = node.get_attribute_name()
        result = Validate.has_member_attribute(state, parent_typeclass, name)
        if result.failed():
            return result.get_failure_type()
        return parent_typeclass.get_member_attribute_by_name(name)

    @Visitor.for_asls("::")
    def scope_(fn, state: State) -> TypeClass:
        node = Nodes.ModuleScope(state)
        entering_into_mod = state.get_enclosing_module().get_child_by_name(node.get_module_name())
        return fn.apply(state.but_with(
            asl=state.second_child(),
            mod=entering_into_mod))

    @Visitor.for_asls("tuple", "params", "prod_type")
    def tuple_(fn, state: State) -> TypeClass:
        if len(state.get_asl()) == 0:
            return state.get_void_type()
        elif len(state.get_asl()) == 1:
            # if there is only one child, then we simply pass the type back, not as a tuple
            return fn.apply_to_first_child_of(state)
        return TypeClassFactory.produce_tuple_type(
            components=[fn.apply(state.but_with(asl=child)) for child in state.get_asl()])

    @Visitor.for_asls("if")
    @returns_void_type
    def if_(fn, state: State) -> TypeClass:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                context=state.create_block_context("if")))

    @Visitor.for_asls("while")
    @returns_void_type
    def while_(fn, state: State) -> TypeClass:
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=state.create_block_context("while")))

    @Visitor.for_asls(":")
    def colon_(fn, state: State) -> TypeClass:
        node = Nodes.Colon(state)
        names = node.get_names()
        typeclass = fn.apply(state.but_with(asl=node.get_type_asl()))

        check = Validate.all_names_are_unbound(state, names)
        if check.failed():
            return state.abort_signal

        instances = [FlowVisitor.add_instance_to_context(name, typeclass, state) for name in names]
        state.assign_instances(instances)
        return typeclass

    @Visitor.for_asls("fn")
    def fn_(fn, state: State) -> TypeClass:
        node = Nodes.Fn(state)
        if node.is_print():
            return BuiltinPrint.get_typeclass_of_function(state)

        if node.is_simple():
            result = Validate.function_instance_exists_in_local_context(state)
            if result.failed():
                return result.get_failure_type()

            instance = result.get_found_instance()
            state.assign_instances(instance)
            return instance.type
        else:
            return fn.apply_to_first_child_of(state)

    @Visitor.for_asls("disjoint_fn")
    def disjoint_ref_(fn, state: State) -> TypeClass:
        result = Validate.function_instance_exists_in_module(state)
        if result.failed():
            return result.get_failure_type()

        instance = result.get_found_instance()
        state.assign_instances(instance)
        return instance.type

    @Visitor.for_asls("call")
    def call_(fn, state: State) -> TypeClass:
        fn_type = fn.apply_to_first_child_of(state)
        if fn_type == state.abort_signal:
            return state.abort_signal

        # still need to type flow through the params passed to the function
        params_type = fn.apply_to_second_child_of(state)

        fn_node = Nodes.Fn(state.but_with_first_child())
        if not fn_node.is_print():
            fn_in_type = fn_type.get_argument_type()
            result = Validate.correct_argument_types(state, fn_node.get_function_name(), fn_in_type, params_type)
            if result.failed():
                return result.get_failure_type()

        return fn_type.get_return_type()

    @Visitor.for_asls("raw_call")
    def raw_call(fn, state: State) -> TypeClass:
        # e.g. (raw_call (expr ...) (fn name) (state ...))
        # because the first element can be a list itself, we need to apply the 
        # fn over it to get the flowed out type.
        fn.apply_to_first_child_of(state)

        # this will actually change the asl inplace, converting (raw_call ...) into (call ...)
        CallUnwrapper.process(state)
        # print(state.get_asl())

        # now we have converted the (raw_call ...) into a normal (call ...) asl 
        # so we can apply fn to the state again with the new asl.
        return fn.apply(state)

    @Visitor.for_asls("struct")
    @returns_void_type
    def struct(fn, state: State) -> TypeClass:
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("interface", "impls")
    @returns_void_type
    def interface_(fn, state: State) -> TypeClass:
        # no action required
        return

    @Visitor.for_asls("cast")
    def cast(fn, state: State) -> TypeClass:
        # (cast (ref name) (type into))
        left_typeclass = fn.apply_to_first_child_of(state)
        right_typeclass = fn.apply_to_second_child_of(state)

        result = Validate.castable_types(
            state=state, 
            type=left_typeclass, 
            cast_into_type=right_typeclass)
        if result.failed():
            return result.get_failure_type()
        return right_typeclass

    @Visitor.for_asls("def", "create", ":=")
    @returns_void_type
    def fn(fn, state: State) -> TypeClass:
        Nodes.CommonFunction(state).enter_context_and_apply_fn(fn)

    @Visitor.for_asls("ilet", "ivar")
    @returns_void_type
    def idecls_(fn, state: State):
        node = Nodes.Ilet(state)
        names = node.get_names()
        typeclass = fn.apply_to_second_child_of(state)

        if node.assigns_a_tuple():
            typeclasses = typeclass.components
        else:
            typeclasses = [typeclass]

        if (any(typeclass is state.abort_signal for typeclass in typeclasses)
                or Validate.all_names_are_unbound(state, names).failed()):
            state.critical_exception.set(True)
            return

        instances = [FlowVisitor.add_instance_to_context(name, typeclass, state)
            for name, typeclass in zip(names, typeclasses)]
        state.assign_instances(instances)

    @Visitor.for_asls("var")
    @returns_void_type
    def var_(fn, state: State):
        # validations occur inside the (: ...) asl 
        fn.apply_to_first_child_of(state)
        instances = state.but_with_first_child().get_instances()
        for instance in instances:
            instance.is_var = True
        state.assign_instances(instances) 

    @Visitor.for_asls("val", "mut_val", "mut_var", "let")
    @returns_void_type
    def decls_(fn, state: State):
        # validations occur inside the (: ...) asl 
        fn.apply_to_first_child_of(state)
        instances = state.but_with_first_child().get_instances()
        state.assign_instances(instances)

    @Visitor.for_asls("type", "type?", "var_type")
    def _type1(fn, state: State) -> TypeClass:
        typeclass = state.get_enclosing_module().get_typeclass(name=state.first_child().value)
        if state.get_asl().type == "type":
            return typeclass.with_restriction(LetRestriction())
        elif state.get_asl().type == "var_type":
            return typeclass.with_restriction(VarRestriction())

    @Visitor.for_asls("=", "<-", *binary_ops)
    def binary_ops(fn, state: State) -> TypeClass:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
    
    @Visitor.for_asls(*boolean_return_ops)
    def boolean_return_ops_(fn, state: State) -> TypeClass:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return state.get_bool_type()

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> TypeClass:
        result = Validate.instance_exists(state)
        if result.failed():
            return result.get_failure_type()

        instance = result.get_found_instance()
        state.assign_instances(instance)
        return instance.type

    @Visitor.for_asls("args")
    def args_(fn, state: State) -> TypeClass:
        if not state.get_asl():
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=False))

    @Visitor.for_asls("rets")
    def rets_(fn, state: State) -> TypeClass:
        if not state.get_asl():
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=True))
