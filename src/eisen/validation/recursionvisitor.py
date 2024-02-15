from __future__ import annotations

from alpaca.utils import Visitor
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.recursionvisitorstate import RecursionVisitorState
import eisen.adapters as adapters

from eisen.common.eiseninstance import FunctionInstance

State = RecursionVisitorState
class RecursionVisitor(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.find_recursive_closure = FindRecursiveClosure()

    def run(self, state: State_PostInstanceVisitor):
        self.apply(RecursionVisitorState.create_from_basestate(state))
        return state

    def apply(self, state: State):
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("start")
    def _start(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("struct")
    def _struct(fn, state: State):
        adapters.Struct(state).apply_fn_to_create_ast(fn)

    @Visitor.for_ast_types("trait_def")
    def _trait_def(fn, state: State):
        adapters.TraitDef(state).apply_fn_to_all_defined_functions(fn)

    @Visitor.for_ast_types("interface", "trait")
    def _noop(fn, _: State):
        return

    # (def ...) (create ...)
    @Visitor.for_ast_types(*adapters.CommonFunction.ast_types)
    def _def(fn, state: State):
        function = state.get_instances()[0]
        closure: set[FunctionInstance] = set()
        is_recursive = fn.find_recursive_closure.run(state.but_with(
            checked_functions=closure,
            original_function=function))
        function.is_recursive_function = is_recursive

class FindRecursiveClosure(Visitor):
    def run(self, state: State) -> bool:
        return self.apply(state)

    def apply(self, state: State) -> bool:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("call")
    def _call(fn, state: State):
        node = adapters.Call(state)
        if node.is_print() or node.is_append():
            return False

        # TODO: need to detect recursion for functions as arguments and for structs which could
        # have functions on them.
        if state.first_child().type == "ref" or state.first_child().type == ".":
            return False

        for instance in state.get_instances():
            if state.is_function_checked(instance):
                return state.is_this_the_original_instance(instance)

            state.mark_function_as_checked(instance)
            fn.apply(state.but_with(ast=instance.ast))
        return False

    # (def ...) (create ...)
    @Visitor.for_ast_types(*adapters.CommonFunction.ast_types)
    def _def(fn, state: State):
        node = adapters.CommonFunction(state)
        return fn.apply(state.but_with(ast=node.get_seq_ast()))

    @Visitor.for_default
    def _default(fn, state: State):
        found_original_instance = False
        for child in state.get_child_asts():
            found_original_instance = found_original_instance or fn.apply(state.but_with(ast=child))
        return found_original_instance

    @Visitor.for_tokens
    def _tokens(fn, _: State):
        return False
