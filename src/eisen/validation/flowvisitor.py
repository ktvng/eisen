from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Type, TypeFactory
from eisen.common import binary_ops, boolean_return_ops, implemented_primitive_types
from eisen.common.nodedata import NodeData
from eisen.common.state import State
from eisen.common.restriction import LetRestriction, VarRestriction, PrimitiveRestriction, NullableVarRestriction
from eisen.validation.nodetypes import Nodes
from eisen.validation.typeparser import TypeParser
from eisen.validation.validate import Validate
from eisen.validation.callunwrapper import CallUnwrapper

from eisen.validation.builtin_print import BuiltinPrint


class FlowVisitor(Visitor):
    """this evaluates the flow of types throughout the asl, and records which
    type flows up through each asl.
    """

    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, state: State) -> Type:
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
            state.assign_returned_type(result)
        return result

    def apply_to_first_child_of(self, state: State) -> Type:
        return self.apply(state.but_with_first_child())

    def apply_to_second_child_of(self, state: State) -> Type:
        return self.apply(state.but_with_second_child())

    def returns_void_type(f):
        """this signifies that the void type should be returned. abstracted so if
        the void_type is changed, we can easily configure it here.
        """
        def decorator(fn, state: State):
            f(fn, state)
            return state.get_void_type()
        return decorator

    @Visitor.for_tokens
    def token_(fn, state: State) -> Type:
        if state.get_asl().type in implemented_primitive_types:
            return (TypeFactory
                .produce_novel_type(name=state.get_asl().type)
                .with_restriction(PrimitiveRestriction()))
        elif state.get_asl().type == "nil":
            return TypeFactory.produce_nil_type()

        # debug only
        raise Exception(f"unexpected token type of {state.get_asl().type}")

    @Visitor.for_asls("fn_type")
    def fn_type_(fn, state: State) -> Type:
        return TypeParser().apply(state)

    @Visitor.for_asls("start", "return", "cond", "seq")
    @returns_void_type
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    @returns_void_type
    def mod_(fn, state: State):
        Nodes.Mod(state).enter_module_and_apply_fn_to_child_asls(fn)

    @Visitor.for_asls("!")
    def not_(fn, state: State) -> Type:
        return fn.apply_to_first_child_of(state)

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> Type:
        node = Nodes.Scope(state)
        parent_type = fn.apply(state.but_with(asl=node.get_object_asl()))
        attr_name = node.get_attribute_name()
        result = Validate.has_member_attribute(state, parent_type, attr_name)
        if result.failed():
            return result.get_failure_type()
        return parent_type.get_member_attribute_by_name(attr_name)

    @Visitor.for_asls("::")
    def scope_(fn, state: State) -> Type:
        node = Nodes.ModuleScope(state)
        instance = node.get_end_instance()
        return instance.type

    @Visitor.for_asls("tuple", "params", "prod_type")
    def tuple_(fn, state: State) -> Type:
        if len(state.get_asl()) == 0:
            return state.get_void_type()
        elif len(state.get_asl()) == 1:
            # if there is only one child, then we simply pass the type back, not as a tuple
            return fn.apply_to_first_child_of(state)
        return TypeFactory.produce_tuple_type(
            components=[fn.apply(state.but_with(asl=child)) for child in state.get_asl()])

    @Visitor.for_asls("if")
    @returns_void_type
    def if_(fn, state: State) -> Type:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=state.create_block_context("if")))

    @Visitor.for_asls("while")
    @returns_void_type
    def while_(fn, state: State) -> Type:
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=state.create_block_context("while")))

    @Visitor.for_asls("raw_call")
    def raw_call(fn, state: State) -> Type:
        # this will actually change the asl inplace, converting (raw_call ...)
        # into (call (ref ...) (params ...))
        guessed_params_type = fn.apply_to_second_child_of(state)
        params_type = CallUnwrapper.process(state, guessed_params_type, fn)

        # need to change the params type to the correct one
        state.but_with_second_child().get_node_data().returned_type = params_type
        fn.apply(state.but_with(asl=state.first_child(), arg_type=params_type))
        node = Nodes.RefLike(state.but_with_first_child())
        if node.is_print():
            return BuiltinPrint.get_type_of_function(state).get_return_type()

        # TODO: move this logic to the instance visitor
        fn_instance = node.resolve_function_instance(params_type)
        result = Validate.instance_exists(state, node.get_name(), fn_instance)
        if result.failed():
            return result.get_failure_type()

        node.assign_instance(fn_instance)
        result = Validate.correct_argument_types(state,
            name=node.get_name(),
            arg_type=fn_instance.type.get_argument_type(),
            given_type=params_type)
        if result.failed():
            return result.get_failure_type()

        return fn_instance.type.get_return_type()

    @Visitor.for_asls("struct")
    @returns_void_type
    def struct(fn, state: State) -> Type:
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("variant")
    @returns_void_type
    def variant_(fn, state: State) -> Type:
        node = Nodes.Variant(state)
        fn.apply(state.but_with(asl=node.get_is_asl()))

    @Visitor.for_asls("interface", "impls")
    @returns_void_type
    def interface_(fn, state: State) -> Type:
        # no action required
        return

    @Visitor.for_asls("cast")
    def cast(fn, state: State) -> Type:
        # (cast (ref name) (type into))
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        result = Validate.castable_types(
            state=state,
            type=left_type,
            cast_into_type=right_type)
        if result.failed():
            return result.get_failure_type()
        return right_type

    @Visitor.for_asls("is")
    def is_(fn, state: State) -> Type:
        node = Nodes.Is(state)

        if node.get_type_name() != "nil":
            params_type = node.get_considered_type().parent_type
            RestructureIsStatement.run(state)
            # TODO: merge this logic with raw_call
            fn.apply(state.but_with(asl=state.first_child(), arg_type=params_type))
            fn.apply(state.but_with_second_child())
            node = Nodes.RefLike(state.but_with_first_child())

            # TODO: move this logic to the instance visitor
            fn_instance = node.resolve_function_instance(params_type)
            node.assign_instance(fn_instance)
            result = Validate.correct_argument_types(state,
                name=node.get_name(),
                arg_type=fn_instance.type.get_argument_type(),
                given_type=params_type)
            if result.failed():
                return result.get_failure_type()

        return state.get_bool_type()

    @Visitor.for_asls("def", "create", ":=", "is_fn")
    @returns_void_type
    def fn(fn, state: State) -> Type:
        Nodes.CommonFunction(state).enter_context_and_apply_fn(fn)

    @Visitor.for_asls("ilet", "ivar")
    def idecls_(fn, state: State):
        node = Nodes.IletIvar(state)
        names = node.get_names()
        type_to_be_assigned = fn.apply_to_second_child_of(state)
        componentwise_types = node.unpack_assigned_types(type_to_be_assigned)

        if (any(type is state.get_abort_signal() for type in componentwise_types)
                or Validate.all_names_are_unbound(state, names).failed()):
            state.critical_exception.set(True)
            return

        for name, type in zip(names, componentwise_types):
            state.add_reference_type(name, type)
        return type_to_be_assigned

    @classmethod
    def _create_references(cls, state: State, names: list[str], type: Type):
        check = Validate.all_names_are_unbound(state, names)
        if check.failed():
            return state.get_abort_signal()
        for name in names:
            state.add_reference_type(name, type)
        return type

    @Visitor.for_asls(":", "val", "var", "var?", "let")
    def decls_(fn, state: State):
        node = Nodes.Decl(state)
        names = node.get_names()
        type = fn.apply(state.but_with(asl=node.get_type_asl())).with_restriction(node.get_restriction())
        return FlowVisitor._create_references(state, names, type)

    @Visitor.for_asls("type", "var_type", "var_type?")
    def _type1(fn, state: State) -> Type:
        name = state.first_child().value
        type = state.get_defined_type(name)
        result = Validate.type_exists(state, name, type)
        if result.failed():
            return result.get_failure_type()

        if state.get_asl().type == "type":
            if state.first_child().value in implemented_primitive_types:
                return type.with_restriction(PrimitiveRestriction())
            return type.with_restriction(LetRestriction())
        elif state.get_asl().type == "var_type":
            return type.with_restriction(VarRestriction())
        elif state.get_asl().type == "var_type?":
            return type.with_restriction(NullableVarRestriction())

    @Visitor.for_asls("=", "<-", *binary_ops)
    def binary_ops(fn, state: State) -> Type:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        result = Validate.can_assign(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type

    @Visitor.for_asls(*boolean_return_ops)
    def boolean_return_ops_(fn, state: State) -> Type:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return state.get_bool_type()

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> Type:
        node = Nodes.Ref(state)
        if node.is_print():
            return BuiltinPrint.get_type_of_function(state)

        type = node.resolve_reference_type()
        # TODO: validate lookup succeeded
        # result = Validate.instance_exists(state, node.get_name(), type)
        # if result.failed():
        #     return result.get_failure_type()

        return type

    @Visitor.for_asls("args")
    def args_(fn, state: State) -> Type:
        if not state.get_asl():
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=False))

    @Visitor.for_asls("rets")
    def rets_(fn, state: State) -> Type:
        if not state.get_asl():
            return state.get_void_type()
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=True))


class RestructureIsStatement():
    @classmethod
    def run(cls, state: State):
        node = Nodes.Is(state)
        is_asl = state.get_asl()
        new_token = CLRToken(type_chain=["TAG"], value="is_" + node.get_type_name())
        new_ref = CLRList(type="ref", lst=[new_token], line_number=is_asl.line_number, data=NodeData())
        new_params = CLRList(type="params", lst=[is_asl.first()], line_number=is_asl.line_number, data=NodeData())
        is_asl.update(type="call", lst=[new_ref, new_params])
