from __future__ import annotations

import uuid
from alpaca.utils import Visitor
from alpaca.concepts import Type
from alpaca.clr import AST

import eisen.adapters as adapters
from eisen.common import no_assign_binary_ops, boolean_return_ops
from eisen.validation.validate import Validate
from eisen.trace.entity import Angel, Trait
from eisen.trace.memory import Memory, ImpressionSet, Function
from eisen.trace.shadow import Shadow
from eisen.trace.lvalmemoryvisitor import LValMemoryVisitor
from eisen.trace.attributevisitor import AttributeVisitor
from eisen.trace.conditionalrealities import RealityFuser
from eisen.trace.callhandler import CallHander

from eisen.trace.delta import FunctionDB, FunctionDelta
from eisen.state.memoryvisitorstate import MemoryVisitorState

State = MemoryVisitorState
class MemoryVisitor(Visitor):
    def __init__(self, debug: bool = False):
        self.function_db = FunctionDB()
        super().__init__(debug)

    def apply(self, state: State) -> list[Memory]:
        return self._route(state.get_ast(), state)

    def run(self, state: State) -> State:
        self.apply(MemoryVisitorState.create_from_basestate(state))
        return state

    @Visitor.for_ast_types("interface", "return")
    def _noop(fn, state: State):
        return

    @Visitor.for_ast_types("params", "tuple")
    def _params(fn, state: State):
        memories = []
        for child in state.get_all_children():
            memories += fn.apply(state.but_with(ast=child))
        return memories

    @Visitor.for_ast_types("struct")
    def _struct(fn, state: State):
        if adapters.Struct(state).has_create_ast():
            fn.apply(state.but_with(ast=adapters.Struct(state).get_create_ast()))

    @Visitor.for_ast_types("start", "prod_type", "seq")
    def _start(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("mod")
    def _mod(fn, state: State):
        adapters.Mod(state).enter_module_and_apply(fn)

    @Visitor.for_ast_types("rets", "args")
    def _rets(fn, state: State):
        for name in adapters.ArgsRets(state).get_names():
            state.create_new_entity(name)

    @Visitor.for_ast_types("def", "create")
    def _def(fn, state: State):
        node = adapters.Def(state)
        # print(node.get_function_name())

        fn_context = state.create_isolated_context()
        fn_state = state.but_with(context=fn_context, function_base_context=fn_context, depth=0)

        fn.apply(fn_state.but_with(ast=node.get_args_ast()))
        fn.apply(fn_state.but_with(ast=node.get_rets_ast()))

        # angels will be updated as the (seq ...) list of the function is processed.
        angels: list[Angel] = []
        fn_state = fn_state.but_with(
            depth=1,
            rets=[fn_state.get_entity(name) for name in node.get_ret_names()],
            args=[fn_state.get_entity(name) for name in node.get_arg_names()],
            angels=[])
        fn.apply(fn_state.but_with(ast=node.get_seq_ast()))

        # add a new function_delta for this function
        fn.function_db.add_function_delta(
            name=node.get_function_instance().get_full_name(),
            fc=FunctionDelta(
                arg_shadows=[fn_state.get_shadow(entity) for entity in fn_state.get_arg_entities()],
                ret_shadows=[fn_state.get_shadow(entity) for entity in fn_state.get_ret_entities()],
                angels=angels,
                angel_shadows={ angel.uid: fn_state.get_shadow(angel) for angel in angels },
                ret_memories=[fn_state.get_memory(entity.name) for entity in fn_state.get_ret_entities()]))

        # print("finished for ", node.get_function_name())
        return []

    @Visitor.for_ast_types(*no_assign_binary_ops)
    def _no_assign_binary_ops(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())
        # TODO: formalize
        return [Memory(rewrites=False, impressions=ImpressionSet(), depth=state.get_depth())]

    @Visitor.for_ast_types(*boolean_return_ops)
    def _boolean_return_ops(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())
        # TODO: formalize
        return [Memory(rewrites=False, impressions=ImpressionSet(), depth=state.get_depth())]

    @Visitor.for_ast_types("+=", "*=", "/=", "-=")
    def _assign_binary_ops(fn, state: State):
        fn.apply(state.but_with_first_child())
        fn.apply(state.but_with_second_child())
        # TODO: if these operations are ever defined for non-primitive types, then
        # there is an additional assignment step required here.

    @Visitor.for_ast_types("!")
    def _not(fn, state: State):
        fn.apply(state.but_with_first_child())
        return [Memory(rewrites=False, impressions=ImpressionSet(), depth=state.get_depth())]

    @Visitor.for_ast_types("fn")
    def _fn(fn, state: State):
        return [Memory(
            rewrites=True,
            impressions=ImpressionSet(),
            depth=state.get_depth(),
            functions=set([Function(state.get_instances()[0])]))]

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        node = adapters.Ref(state)
        memory = state.get_memory(node.get_name())
        Validate.memory_dependencies_havent_moved_away(state, memory)
        return [memory]

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        return AttributeVisitor.get_memories(state)

    @Visitor.for_ast_types("cast")
    def _cast(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types("let")
    def _let(fn, state: State):
        node = adapters.Decl(state)
        for name in node.get_names():
            state.create_new_entity(name)

    @Visitor.for_ast_types("mut", "val", "nil?")
    def _vars(fn, state: State):
        node = adapters.Decl(state)
        for name in node.get_names():
            state.add_memory(name, Memory(
                name=name,
                rewrites=True,
                impressions=ImpressionSet(),
                depth=state.get_depth()))

    @Visitor.for_ast_types("ilet")
    def _ilet(fn, state: State):
        node = adapters.InferenceAssign(state)
        for name in node.get_names():
            state.create_new_entity(name)
        state.update_lvals(
            lvals=LValMemoryVisitor().apply(state.but_with_first_child()),
            rvals=fn.apply(state.but_with_second_child()))

    @Visitor.for_ast_types("ival", "imut", "inil?")
    def _ival(fn, state: State):
        node = adapters.InferenceAssign(state)
        for name in node.get_names():
            state.add_memory(name, Memory(
                name=name,
                rewrites=True,
                impressions=ImpressionSet(),
                depth=state.get_depth()))
        state.update_lvals(
            lvals=LValMemoryVisitor().apply(state.but_with_first_child()),
            rvals=fn.apply(state.but_with_second_child()))

    @Visitor.for_ast_types("=")
    def _eq(fn, state: State):
        state.update_lvals(
            lvals=LValMemoryVisitor().apply(state.but_with_first_child()),
            rvals=fn.apply(state.but_with_second_child()))

    # TODO: should this sometimes return a list of shadows/memories?
    @Visitor.for_ast_types("call")
    def _call(fn, state: State):
        node = adapters.Call(state)
        if node.is_print():
            fn.apply(state.but_with_second_child())
            return []

        param_memories = fn.apply(state.but_with_second_child())
        realities = [CallHander(node=node, delta=delta, param_memories=param_memories).start()
            for delta in CallHander.aquire_function_deltas(node, fn)]
        outcomes: list[list[Shadow | Memory]] = [reality.resolve_outcome() for reality in realities]
        return RealityFuser.fuse_outcomes_together(outcomes)

    @Visitor.for_ast_types("cond")
    def _cond(fn, state: State):
        state.apply_fn_to_all_children(fn)

    @Visitor.for_ast_types("while")
    def _while(fn, state: State):
        # There is one shared context for the conditional of the while loop
        # as well as the body
        cond_state = state.but_with(
            ast=state.first_child(),
            context=state.create_block_context())

        encountered_memory_states: list[set[Memory]] = []
        exceptions = []

        # Each time the while loop iterates is considered a "conditional branch" and
        # is associated with a branch state
        branch_states: list[State] = []
        times_run = 0
        while True:
            times_run += 1

            fn.apply(cond_state.but_with(exceptions=exceptions))
            # need to use the same context to keep updating it iteration by iteration
            seq_state = cond_state.but_with(
                ast=state.first_child().second(),
                depth=state.get_depth() + 1,
                exceptions=exceptions)

            fn.apply(seq_state)

            # Preserve the state of the branch by forking its context. Add this
            # as the state in the "conditional" branch for the while loop.
            preserved_state_for_branch = seq_state.but_with(context=seq_state.get_context().fork())
            branch_states.append(preserved_state_for_branch)

            # We use the RealityFuser with the only branch being the seq_state of
            # this run of the while loop (as an optimization). This returns the final
            # state of each updated memory.
            final_memory_states = RealityFuser(state, [seq_state]).all_updated_memories()

            # If we've seen the final state of each Memory, then the while loop has
            # stabilized and we are done.
            if final_memory_states in encountered_memory_states:
                break

            # Otherwise, mark the state of each Memory as seen.
            encountered_memory_states.append(final_memory_states)

        fn.logger.log(f"Runs over while loop {times_run} times.")
        RealityFuser(origin_state=state, branch_states=branch_states).fuse_realities_after_conditional()

        # Report any unique exceptions encountered through the while loop process.
        for e in set(exceptions):
            state.report_exception(e)


    @Visitor.for_ast_types("if")
    def _if(fn, state: State) -> Type:
        branch_states = [MemoryVisitor.apply_fn_in_branch_and_return_branch_state(state, fn, child)
                         for child in state.get_child_asts()]
        RealityFuser(origin_state=state, branch_states=branch_states).fuse_realities_after_conditional()

    @staticmethod
    def apply_fn_in_branch_and_return_branch_state(parent_state: State, fn: Visitor, child: AST) -> State:
        branch_state = parent_state.but_with(
            ast=child,
            context=parent_state.create_block_context(),
            depth=parent_state.get_depth() + 1)
        fn.apply(branch_state)
        return branch_state

    @Visitor.for_tokens
    def _tokens(fn, state: State):
        return [Memory(rewrites=True, impressions=ImpressionSet(), depth=0)]

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, state: State):
        node = adapters.Annotation(state)
        match node.get_annotation_type():
            case "compiler_assert":
                Annotations.handle_compiler_assert(state)
        return

class Annotations:
    @staticmethod
    def parse_dependency_dict(strs: list[str]):
        key_val_pairs = [s.split(':') for s in strs]
        key_val_pairs = [(p[0].strip(), p[1].split()) for p in key_val_pairs]
        key_val_pairs = [(p[0], set([v.strip() for v in p[1]])) for p in key_val_pairs]
        return { Trait(p[0]): p[1] for p in key_val_pairs}

    @staticmethod
    def handle_compiler_assert(state: State):
        node = adapters.CompilerAssertAnnotation(state)
        function = node.get_functionality()
        args = node.get_annotation_arguments()
        match function:
            case "reference_has_dependencies":
                Validate.var_has_expected_dependencies(state, args[0], args[1: ])
            case "object_has_dependencies":
                Validate.object_has_expected_dependencies(state, args[0],
                    Annotations.parse_dependency_dict(args[1: ]))
