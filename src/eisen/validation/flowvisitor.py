from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import TypeClass, TypeClassFactory, Restriction2
from eisen.common import EisenInstance, binary_ops, boolean_return_ops
from eisen.common.params import State
from eisen.validation.nodetypes import Nodes
from eisen.validation.typeclassparser import TypeclassParser
from eisen.validation.validate import Validate
from eisen.validation.callunwrapper import CallUnwrapper

################################################################################
# this evaluates the flow of typeclasses throughout the asl, and records which 
# typeclass flows up through each asl.
class FlowVisitor(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, state: State) -> TypeClass:
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()

        # this guards the function such that if there is a critical exception thrown
        # downstream, the method will skip execution.
        if state.critical_exception:
            return state.get_void_type()

        result = self._route(state.asl, state)
        if state.is_asl():
            state.assign_returned_typeclass(result)
        return result

    # this signifies that the void type should be returned. abstract this so if 
    # the void_type is changed, we can easily configure it here.
    def returns_void_type(f):
        def decorator(fn, state: State):
            f(fn, state)
            return state.get_void_type()
        return decorator

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
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> TypeClass:
        parent_typeclass = fn.apply(state.but_with(asl=state.first_child()))
        name = state.second_child().value
        result = Validate.has_member_attribute(state, parent_typeclass, name)
        if result.failed():
            return result.get_failure_type()
        return parent_typeclass.get_member_attribute_by_name(name)

    @Visitor.for_asls("::")
    def scope_(fn, state: State) -> TypeClass:
        entering_into_mod = state.get_enclosing_module().get_child_by_name(state.first_child().value)
        return fn.apply(state.but_with(
            asl=state.second_child(),
            mod=entering_into_mod))

    @Visitor.for_asls("tuple", "params", "prod_type")
    def tuple_(fn, state: State) -> TypeClass:
        if len(state.asl) == 0:
            return state.get_void_type()
        if len(state.asl) == 1:
            # if there is only one child, then we simply pass the type back, not as a tuple
            return fn.apply(state.but_with(asl=state.first_child()))
        if len(state.asl) > 1:
            return TypeClassFactory.produce_tuple_type(
                components=[fn.apply(state.but_with(asl=child)) for child in state.asl],
                global_mod=state.global_mod)

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

        instances = []
        for name in names:
            result = Validate.name_is_unbound(state, name)
            if not result.failed():
                instances.append(state.context.add_instance(EisenInstance(
                    name=name, 
                    type=typeclass, 
                    context=state.get_context(), 
                    asl=state.asl, 
                    is_ptr=state.is_ptr)))
        state.assign_instances(instances)
        return typeclass

    @Visitor.for_asls("fn")
    def fn_(fn, state: State) -> TypeClass:
        node = Nodes.Fn(state)
        if node.is_print():
            # TODO: handle this better
            return TypeClassFactory.produce_function_type(
                    arg=state.get_void_type(),
                    ret=state.get_void_type(),
                    mod=state.global_mod)
        if node.is_simple():
            result = Validate.function_instance_exists_in_local_context(state)
            if result.failed():
                return result.get_failure_type()

            instance = result.get_found_instance()
            state.assign_instances(instance)
            return instance.type
        else:
            return fn.apply(state.but_with(asl=state.first_child()))

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
        fn_type = fn.apply(state.but_with(asl=state.first_child()))
        if fn_type == state.abort_signal:
            return state.abort_signal

        # still need to type flow through the params passed to the function
        params_type = fn.apply(state.but_with(asl=state.second_child()))

        fn_node = Nodes.Fn(state.but_with(asl=state.first_child()))
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
        fn.apply(state.but_with(asl=state.first_child()))

        # this will actually change state.asl, converting (raw_call ...) into (call ...)
        CallUnwrapper.process(state)
        # print(state.asl)

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
        return

    @Visitor.for_asls("cast")
    def cast(fn, state: State) -> TypeClass:
        # (cast (ref name) (type into))
        left_typeclass = fn.apply(state.but_with(asl=state.first_child()))
        right_typeclass = fn.apply(state.but_with(asl=state.second_child()))

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
        # inside the FunctionWrangler, (def ...) and (create ...) asls have been
        # normalized to have the same signature. therefore we can treat them identically
        # here
        fn_context = state.create_block_context("func")
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                context=fn_context))

    # we don't need to add/record typeclasses because this is a CLRToken
    @Visitor.for_tokens
    def token_(fn, state: State) -> TypeClass:
        # TODO: make this nicer
        if state.asl.type in ["str", "int", "bool"]:
            return TypeClassFactory.produce_novel_type(name=state.asl.type, global_mod=state.global_mod)
        else:
            print(state.asl)
            raise Exception(f"unexpected token type of {state.asl.type}")

    @Visitor.for_asls("ilet", "ivar")
    @returns_void_type
    def idecls_(fn, state: State):
        node = Nodes.Ilet(state)
        names = node.get_names()
        typeclass = fn.apply(state.but_with(asl=state.second_child()))

        if node.assigns_a_tuple():
            typeclasses = typeclass.components
        else:
            typeclasses = [typeclass]

        result = Validate.tuple_sizes_match(state, names, typeclasses)
        if result.failed():
            state.critical_exception.set(True)
            return 

        instances = []
        for name, typeclass in zip(names, typeclasses):
            result = Validate.name_is_unbound(state, name)
            if result.failed():
                return 

            if typeclass is state.abort_signal:
                state.critical_exception.set(True)
                return

            instance = EisenInstance(
                name, 
                typeclass, 
                state.get_context(), 
                state.asl)

            instances.append(instance)
            state.context.add_instance(instance)
        state.assign_instances(instances)

    @Visitor.for_asls("var")
    @returns_void_type
    def var_(fn, state: State):
        # validations occur inside the (: ...) asl 
        fn.apply(state.but_with(asl=state.first_child()))
        instances = state.but_with(asl=state.first_child()).get_instances()
        for instance in instances:
            instance.is_var = True
        state.assign_instances(instances) 

    @Visitor.for_asls("val", "mut_val", "mut_var", "let")
    @returns_void_type
    def decls_(fn, state: State):
        # validations occur inside the (: ...) asl 
        fn.apply(state.but_with(asl=state.first_child()))
        instances = state.but_with(asl=state.first_child()).get_instances()
        state.assign_instances(instances)

    @Visitor.for_asls("type", "type?", "var_type")
    def _type1(fn, state: State) -> TypeClass:
        typeclass = state.get_enclosing_module().get_typeclass_by_name(name=state.first_child().value)
        if state.asl.type == "type":
            return typeclass.with_restriction(Restriction2.for_let())
        elif state.asl.type == "var_type":
            return typeclass.with_restriction(Restriction2.for_var())

    @Visitor.for_asls(*binary_ops)
    def binary_ops(fn, state: State) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
    
    @Visitor.for_asls(*boolean_return_ops)
    def boolean_return_ops_(fn, state: State) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return state.get_bool_type()

    @Visitor.for_asls("=")
    def assigns(fn, state: State) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type

    @Visitor.for_asls("<-")
    def larrow_(fn, state: State) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type

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
        if not state.asl:
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=False))

    @Visitor.for_asls("rets")
    def rets_(fn, state: State) -> TypeClass:
        if not state.asl:
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=True))
