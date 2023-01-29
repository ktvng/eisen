from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList
from alpaca.concepts import Type, TypeFactory
from eisen.common import binary_ops, boolean_return_ops, implemented_primitive_types
from eisen.state.basestate import BaseState
from eisen.state.statea import StateA
from eisen.state.typecheckerstate import TypeCheckerState
from eisen.common.restriction import PrimitiveRestriction, FunctionalRestriction
import eisen.nodes as nodes
from eisen.validation.validate import Validate
from eisen.validation.callunwrapper import CallUnwrapper
from eisen.validation.restructure_is_statement import RestructureIsStatement
from eisen.validation.typeparser import TypeParser

from eisen.validation.builtin_print import BuiltinPrint

State = TypeCheckerState

class TypeChecker(Visitor):
    """this evaluates the flow of types throughout the asl, and records which
    type flows up through each asl.
    """

    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        self.typeparser = TypeParser()

    def run(self, state: BaseState):
        self.apply(TypeCheckerState.create_from_basestate(state))
        return StateA.create_from_basestate(state)

    def apply(self, state: State) -> Type:
        # this guards the function such that if there is a critical exception thrown
        # downstream, the method will skip execution.
        if state.critical_exception:
            return state.get_void_type()

        result = self._route(state.get_asl(), state)
        if state.is_asl():
            TypeChecker.set_returned_type(state, result)
        return result

    @classmethod
    def get_curried_type(cls, state: State, fn_type: Type, n_curried_args: int) -> Type:
        argument_type = fn_type.get_argument_type()
        if not argument_type.is_tuple():
            if n_curried_args == 1:
                return TypeFactory.produce_function_type(
                    arg=state.get_void_type(),
                    ret=fn_type.get_return_type(),
                    mod=fn_type.mod).with_restriction(FunctionalRestriction())
            raise Exception(f"tried to curry more arguments than function allows: {n_curried_args} {fn_type}")

        if len(argument_type.components) - n_curried_args == 1:
            # unpack tuple to just a single type
            curried_fn_args = argument_type.components[-1]
        elif len(argument_type.components) - n_curried_args == 0:
            curried_fn_args = state.get_void_type()
        else:
            curried_fn_args = TypeFactory.produce_tuple_type(argument_type.components[n_curried_args:])

        return TypeFactory.produce_function_type(
            arg=curried_fn_args,
            ret=fn_type.get_return_type(),
            mod=fn_type.mod).with_restriction(FunctionalRestriction())


    @classmethod
    def set_returned_type(cls, state: State, type: Type):
        state.get_node_data().returned_type = type

    @classmethod
    def add_reference_type(cls, state: State, name: str, type: Type):
        state.get_context().add_reference_type(name, type)

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

    @classmethod
    def update_to_primitive_restriction_if_needed(cls, type: Type):
        """for novel types with let restrictions, we must change the restriction to
        primitive."""
        if type.is_novel() and type.restriction.is_let():
            return type.with_restriction(PrimitiveRestriction())
        if type.is_tuple() and all([c.is_novel() and c.restriction.is_let() for c in type.components]):
            return type.with_restriction(PrimitiveRestriction())
        if type.is_function():
            return type.with_restriction(FunctionalRestriction())
        return type

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

    @Visitor.for_asls("start", "return", "cond", "seq")
    @returns_void_type
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_asls("mod")
    @returns_void_type
    def mod_(fn, state: State):
        nodes.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_asls("!")
    def not_(fn, state: State) -> Type:
        return fn.apply_to_first_child_of(state)

    @Visitor.for_asls(".")
    def dot_(fn, state: State) -> Type:
        node = nodes.Scope(state)
        parent_type = fn.apply(state.but_with(asl=node.get_object_asl()))
        attr_name = node.get_attribute_name()
        if Validate.has_member_attribute(state, parent_type, attr_name).failed():
            return state.get_abort_signal()
        return parent_type.get_member_attribute_by_name(attr_name)

    @Visitor.for_asls("::")
    def scope_(fn, state: State) -> Type:
        node = nodes.ModuleScope(state)
        instance = node.get_end_instance()
        return instance.type

    @Visitor.for_asls("tuple", "params", "prod_type", "lvals", "curried")
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
        nodes.If(state).enter_context_and_apply(fn)

    @Visitor.for_asls("while")
    @returns_void_type
    def while_(fn, state: State) -> Type:
        nodes.While(state).enter_context_and_apply(fn)

    @classmethod
    def _shared_call_checks(cls, state: State, params_type: Type):
        node = nodes.RefLike(state.but_with_first_child())
        fn_type = node.resolve_reference_type(params_type)
        if Validate.instance_exists(state, node.get_name(), fn_type).failed():
            return state.get_abort_signal()

        if Validate.correct_argument_types(state,
            name=node.get_name(),
            arg_type=fn_type.get_argument_type(),
            given_type=params_type).failed():
                return state.get_abort_signal()

        return fn_type.get_return_type()

    @Visitor.for_asls("raw_call")
    def raw_call(fn, state: State) -> Type:
        # this will actually change the asl inplace, converting (raw_call ...)
        # into (call (ref ...) (params ...))
        params_type = CallUnwrapper.process(
            state=state,
            guessed_params_type=fn.apply_to_second_child_of(state),
            fn=fn)

        fn.apply(state.but_with(asl=state.first_child(), arg_type=params_type))
        node = nodes.RefLike(state.but_with_first_child())
        if node.is_print():
            return BuiltinPrint.get_type_of_function(state).get_return_type()
        return TypeChecker._shared_call_checks(state, params_type)

    @Visitor.for_asls("is")
    def is_(fn, state: State) -> Type:
        node = nodes.Is(state)
        # if the check is not against nil, treat this as a call to
        # some "is" function of a variant
        if node.get_type_name() != "nil":
            params_type = node.get_considered_type().parent_type
            RestructureIsStatement.run(state)
            fn.apply(state.but_with(asl=state.first_child(), arg_type=params_type))
            fn.apply(state.but_with_second_child())
            return TypeChecker._shared_call_checks(state, params_type)
        return state.get_bool_type()

    @Visitor.for_asls("curry_call")
    def curry_call_(fn, state: State) -> Type:
        fn_type = fn.apply_to_first_child_of(state)
        curried_args_type = fn.apply_to_second_child_of(state)
        n_curried_args = 1
        if curried_args_type.is_tuple():
            n_curried_args = len(curried_args_type.components)

        return TypeChecker.get_curried_type(state, fn_type, n_curried_args)

    @Visitor.for_asls("struct")
    @returns_void_type
    def struct(fn, state: State) -> Type:
        node = nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))

    @Visitor.for_asls("variant")
    @returns_void_type
    def variant_(fn, state: State) -> Type:
        fn.apply(state.but_with(asl=nodes.Variant(state).get_is_asl()))

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

        if Validate.castable_types(
            state=state,
            type=left_type,
            cast_into_type=right_type).failed(): return state.get_abort_signal()
        return right_type

    @Visitor.for_asls("def", "create", ":=", "is_fn")
    @returns_void_type
    def fn(fn, state: State) -> Type:
        nodes.CommonFunction(state).enter_context_and_apply(fn)

    @classmethod
    def _create_references(cls, state: State, names: list[str], type: Type):
        types = type.components if type.is_tuple() else [type] * len(names)
        if any(type is state.get_abort_signal() for type in types):
            state.critical_exception.set(True)
            return
        if Validate.all_names_are_unbound(state, names).failed():
            return state.get_abort_signal()
        for name, t in zip(names, types):
            TypeChecker.add_reference_type(state, name, t)
        return type

    @Visitor.for_asls("ilet", "ivar")
    def idecls_(fn, state: State):
        node = nodes.IletIvar(state)
        names = node.get_names()
        type = fn.apply_to_second_child_of(state).with_restriction(node.get_restriction())
        type = TypeChecker.update_to_primitive_restriction_if_needed(type)
        return TypeChecker._create_references(state, names, type)

    @Visitor.for_asls(":", "val", "var", "var?", "let")
    def decls_(fn, state: State):
        node = nodes.Decl(state)
        names = node.get_names()
        type = fn.apply(state.but_with(asl=node.get_type_asl())).with_restriction(node.get_restriction())
        type = TypeChecker.update_to_primitive_restriction_if_needed(type)
        return TypeChecker._create_references(state, names, type)

    @Visitor.for_asls("fn_type", "type", "var_type", "var_type?")
    def _type1(fn, state: State) -> Type:
        return fn.typeparser.apply(state)

    @Visitor.for_asls("=", "<-", *binary_ops)
    def binary_ops(fn, state: State) -> Type:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        if Validate.can_assign(state, left_type, right_type).failed():
            return state.get_abort_signal()
        return left_type

    @Visitor.for_asls(*boolean_return_ops)
    def boolean_return_ops_(fn, state: State) -> Type:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        if Validate.equivalent_types(state, left_type, right_type).failed():
            return state.get_abort_signal()
        return state.get_bool_type()

    @Visitor.for_asls("fn")
    def fn_(fn, state: State) -> Type:
        node = nodes.Fn(state)
        instance = node.resolve_function_instance(state.get_arg_type())
        if Validate.instance_exists(state, node.get_name(), instance).failed():
            return state.get_abort_signal()
        return instance.type

    @Visitor.for_asls("ref")
    def ref_(fn, state: State) -> Type:
        node = nodes.Ref(state)
        if node.is_print():
            return BuiltinPrint.get_type_of_function(state)

        type = node.resolve_reference_type()
        if Validate.instance_exists(state, node.get_name(), type).failed():
            return state.get_abort_signal()
        return type

    @Visitor.for_asls("args", "rets")
    def args_(fn, state: State) -> Type:
        node = nodes.ArgsRets(state)
        if not state.get_asl():
            return state.get_void_type()
        type = fn.apply(state.but_with(asl=state.first_child()))
        node.convert_let_args_to_var(type)
        return type
