from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.concepts import Type, TypeFactory
from eisen.common import binary_ops, boolean_return_ops, implemented_primitive_types
from eisen.common.binding import Binding, BindingMechanics
from eisen.state.basestate import BaseState
from eisen.state.state_posttypecheck import State_PostTypeCheck
from eisen.state.typecheckerstate import TypeCheckerState
import eisen.adapters as adapters
from eisen.validation.validate import Validate
from eisen.validation.callunwrapper import CallUnwrapper
from eisen.common.typefactory import TypeFactory

from eisen.validation.builtin_print import Builtins

State = TypeCheckerState
class TypeChecker(Visitor):
    """this evaluates the flow of types throughout the ast, and records which
    type flows up through each ast.
    """

    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)

    def run(self, state: BaseState):
        self.apply(TypeCheckerState.create_from_basestate(state))
        return State_PostTypeCheck.create_from_basestate(state)

    def apply(self, state: State) -> Type:
        # this guards the function such that if there is a critical exception thrown
        # downstream, the method will skip execution.
        if state.critical_exception:
            return state.get_void_type()

        result = self._route(state.get_ast(), state)
        if result is None: result = state.get_void_type()

        # Set the returned type of each AST node.
        state.get_node_data().returned_type = result
        return result

    def apply_to_first_child_of(self, state: State) -> Type:
        return self.apply(state.but_with_first_child())

    def apply_to_second_child_of(self, state: State) -> Type:
        return self.apply(state.but_with_second_child())

    @Visitor.for_tokens
    def token_(fn, state: State) -> Type:
        if state.get_ast().type in implemented_primitive_types:
            return TypeFactory.produce_novel_type(name=state.get_ast().type)
        elif state.get_ast().type == "nil":
            return TypeFactory.produce_nil_type()

        # debug only
        raise Exception(f"unexpected token type of {state.get_ast().type}, {state.get_ast().value}")

    @Visitor.for_ast_types("start", "return", "cond", "seq")
    def start_(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("!")
    def not_(fn, state: State) -> Type:
        return fn.apply_to_first_child_of(state)

    @Visitor.for_ast_types(".")
    def dot_(fn, state: State) -> Type:
        node = adapters.Scope(state)
        parent_type = fn.apply(state.but_with(ast=node.get_object_ast()))
        attr_name = node.get_attribute_name()
        if Validate.has_member_attribute(state, parent_type, attr_name).failed():
            return state.get_abort_signal()
        return parent_type.get_member_attribute_by_name(attr_name)

    @Visitor.for_ast_types("::")
    def scope_(fn, state: State) -> Type:
        node = adapters.ModuleScope(state)
        instance = node.get_end_instance()
        return instance.type

    @Visitor.for_ast_types("tuple", "params", "prod_type", "lvals", "curried")
    def tuple_(fn, state: State) -> Type:
        if len(state.get_ast()) == 0:
            return state.get_void_type()
        elif len(state.get_ast()) == 1:
            # if there is only one child, then we simply pass the type back, not as a tuple
            return fn.apply_to_first_child_of(state)
        return TypeFactory.produce_tuple_type(
            components=[fn.apply(state.but_with(ast=child)) for child in state.get_ast()])

    @Visitor.for_ast_types("if")
    def if_(fn, state: State) -> Type:
        adapters.If(state).enter_context_and_apply(fn)

    @Visitor.for_ast_types("while")
    def while_(fn, state: State) -> Type:
        adapters.While(state).enter_context_and_apply(fn)

    @classmethod
    def _shared_call_checks(cls, state: State, params_type: Type):
        node = adapters.RefLike(state.but_with_first_child())
        fn_type = node.resolve_reference_type(params_type)
        if Validate.instance_exists(state, node.get_name(), fn_type).failed():
            return state.get_abort_signal()

        if Validate.correct_argument_types(state,
            name=node.get_name(),
            arg_type=fn_type.get_argument_type(),
            given_type=params_type).failed():
                return state.get_abort_signal()
        return fn_type.get_return_type()

    @Visitor.for_ast_types("raw_call")
    def raw_call(fn, state: State) -> Type:
        guessed_params_type = fn.apply_to_second_child_of(state)

        # this will actually change the ast inplace, converting (raw_call ...)
        # into (call (ref ...) (params ...))
        if guessed_params_type == state.get_abort_signal():
            return state.get_abort_signal()
        params_type = CallUnwrapper.process(
            state=state,
            guessed_params_type=guessed_params_type,
            fn=fn)

        if params_type == state.get_abort_signal():
            return params_type

        fn.apply(state.but_with(ast=state.first_child(), arg_type=params_type))
        if adapters.Call(state).is_print():
            return Builtins.get_type_of_print(state).get_return_type()
        return TypeChecker._shared_call_checks(state, params_type)

    @Visitor.for_ast_types("curry_call")
    def curry_call_(fn, state: State) -> Type:
        fn_type = fn.apply_to_first_child_of(state)
        curried_args_type = fn.apply_to_second_child_of(state)

        argument_type = fn_type.get_argument_type()
        if Validate.function_has_enough_arguments_to_curry(state, argument_type, curried_args_type).failed():
            return state.get_abort_signal()

        if Validate.curried_arguments_are_of_the_correct_type(state, argument_type, curried_args_type).failed():
            return state.get_abort_signal()
        return TypeFactory.produce_curried_function_type(fn_type, curried_args_type)

    @Visitor.for_ast_types("struct")
    def struct(fn, state: State) -> Type:
        adapters.Struct(state).apply_fn_to_create_ast(fn)

    @Visitor.for_ast_types("variant")
    def variant_(fn, state: State) -> Type:
        fn.apply(state.but_with(ast=adapters.Variant(state).get_is_ast()))

    @Visitor.for_ast_types("interface", "impls")
    def interface_(fn, state: State) -> Type:
        # no action required
        return

    @Visitor.for_ast_types("cast")
    def cast(fn, state: State) -> Type:
        # (cast (ref name) (type into))
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        if Validate.castable_types(
            state=state,
            type=left_type,
            cast_into_type=right_type).failed(): return state.get_abort_signal()
        return right_type

    @Visitor.for_ast_types("def", "create", ":=", "is_fn")
    def fn(fn, state: State) -> Type:
        adapters.CommonFunction(state.but_with(in_constructor=state.get_ast_type() == "create"))\
            .enter_context_and_apply(fn)

    @staticmethod
    def _create_references(node: adapters.InferenceAssign | adapters.Decl, types: list[Type]):
        """
        This creates the references for each entity defined with the 'let' keyword, performing
        both type checking but also binding inference.
        """
        state = node.state
        if any(type is state.get_abort_signal() for type in types):
            state.critical_exception.set(True)
            return

        names = node.get_names()
        bindings = node.get_bindings()

        # First validate that any inference on bindings is acceptable.
        for name, t, b in zip(names, types, bindings):
            Validate.Bindings.can_be_inferred(state, name, b, t.modifier)

        # Infer bindings. However, if we are inside a constructor, and the reference we are creating
        # is for the new returned object, then the binding of that object must be mut_new as it's
        # mutable inside of the constructor.
        types = [t.with_modifier(BindingMechanics.infer_binding(b, t.modifier)) for t, b in zip(types, bindings)]
        types = [t.with_modifier(Binding.mut_new) if state.is_inside_create() and state.is_inside_rets() else t for t in types]

        if Validate.all_names_are_unbound(state, node.get_names()).failed():
            return state.get_abort_signal()

        for name, t in zip(names, types):
            state.get_context().add_type_of_reference(name, t)

        # Produce a new type with the contents of [types] to ensure the bindings get updated.
        match len(types):
            case 0: return state.get_void_type()
            case 1: return types[0]
            case _: return TypeFactory.produce_tuple_type(types)


    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def idecls_(fn, state: State):
        return TypeChecker._create_references(
            node=adapters.InferenceAssign(state),
            types=fn.apply_to_second_child_of(state).unpack_into_parts())

    @Visitor.for_ast_types(*adapters.Typing.ast_types)
    def decls_(fn, state: State):
        node = adapters.Typing(state)

        # as multiple variable could all be defined of a single type, if we see that only one
        # type is specified, we duplicate this type for each variable that gets defined.
        right_type = fn.apply(state.but_with(ast=node.get_type_ast()))
        n_variables = len(node.get_names())
        types = right_type.unpack_into_parts() if right_type.is_tuple() else [right_type]*n_variables
        return TypeChecker._create_references(
            node=node,
            types=types)

    @Visitor.for_ast_types("fn_type", "para_type", *adapters.TypeLike.ast_types)
    def _type(fn, state: State) -> Type:
        return state.parse_type_represented_here()

    @Visitor.for_ast_types("=", "<-", *binary_ops)
    def binary_ops(fn, state: State) -> Type:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        if Validate.can_assign(state, left_type, right_type).failed():
            return state.get_abort_signal()
        return left_type

    @Visitor.for_ast_types(*boolean_return_ops)
    def boolean_return_ops_(fn, state: State) -> Type:
        left_type = fn.apply_to_first_child_of(state)
        right_type = fn.apply_to_second_child_of(state)

        if Validate.equivalent_types(state, left_type, right_type).failed():
            return state.get_abort_signal()
        return state.get_bool_type()

    @Visitor.for_ast_types("fn")
    def fn_(fn, state: State) -> Type:
        node = adapters.Fn(state)
        instance = node.resolve_function_instance(state.get_arg_type())
        if Validate.instance_exists(state, node.get_name(), instance).failed():
            return state.get_abort_signal()
        return instance.type

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State) -> Type:
        node = adapters.Ref(state)
        if node.is_print():
            return Builtins.get_type_of_print(state)

        type_ = node.resolve_reference_type()
        if Validate.instance_exists(state, node.get_name(), type_).failed():
            return state.get_abort_signal()
        return type_

    @Visitor.for_ast_types("args", "rets")
    def argsrets_(fn, state: State) -> Type:
        if state.get_ast().has_no_children(): return state.get_void_type()
        return fn.apply(state.but_with(
            ast=state.first_child(),
            in_rets=state.get_ast_type()=="rets"))

    @Visitor.for_ast_types("new_vec")
    def new_vec_(fn, state: State) -> Type:
        node = adapters.NewVec(state)
        return node.get_type()

    @Visitor.for_ast_types("index")
    def index_(fn, state: State) -> Type:
        return fn.apply_to_first_child_of(state).parametrics[0]

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, state: State) -> Type:
        # Not implemented
        return
