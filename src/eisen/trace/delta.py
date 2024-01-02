from __future__ import annotations
import uuid
from dataclasses import dataclass

from alpaca.utils import Visitor
import eisen.adapters as  adapters
from eisen.trace.shadow import Shadow
from eisen.trace.entity import Angel
from eisen.trace.memory import Memory
from eisen.trace.functionargs import FunctionsAsArgumentsLogic

from eisen.state.memoryvisitorstate import MemoryVisitorState

State = MemoryVisitorState

@dataclass
class FunctionDelta():
    """
    A FunctionDelta represents how calling a function on a generic set of parameters
    may permute the dependencies of the parameters. Any changes that the function would make
    to the parameters, as well as any return value dependencies are recorded by the FunctionDelta
    and can be replayed wherever the function is called to impart these changes.
    """
    function_name: str
    arg_shadows: list[Shadow]
    ret_shadows: list[Shadow]
    angels: list[Angel]
    angel_shadows: dict[uuid.UUID, Shadow]
    ret_memories: list[Memory]

    @staticmethod
    def compute_for(node: adapters.Def, fn: Visitor) -> FunctionDelta:
        state = node.state
        if fn.function_db.get_function_delta(node.get_function_instance().get_full_name()) is not None:
            return []

        # we can't process a function that takes
        if FunctionsAsArgumentsLogic.cannot_process_method_yet(node, state): return

        # print("starting def of", node.get_function_name())

        # angels will be updated as the (seq ...) list of the function is processed.
        angels: list[Angel] = []
        fn_context = state.create_isolated_context()
        fn_state = state.but_with(context=fn_context, function_base_context=fn_context, depth=0,
                                  angels=angels)

        fn.apply(fn_state.but_with(ast=node.get_args_ast()))
        fn.apply(fn_state.but_with(ast=node.get_rets_ast()))

        # remove functions before we process the body of the function, so that they don't
        # interfere with other processing.
        # TODO: this might not be necessary?
        fn_state = fn_state.but_with(function_parameters=None)

        fn_state = fn_state.but_with(
            depth=1,
            rets=[fn_state.get_entity(name) for name in node.get_ret_names()],
            args=[fn_state.get_entity(name) for name in node.get_arg_names()],
            angels=angels)
        fn.apply(fn_state.but_with(ast=node.get_seq_ast()))

        delta = FunctionDelta(
                    function_name=node.get_function_name(),
                    arg_shadows=[fn_state.get_shadow(entity) for entity in fn_state.get_arg_entities()],
                    ret_shadows=[fn_state.get_shadow(entity) for entity in fn_state.get_ret_entities()],
                    angels=angels,
                    angel_shadows={ angel.uid: fn_state.get_shadow(angel) for angel in angels },
                    ret_memories=[fn_state.get_memory(entity.name) for entity in fn_state.get_ret_entities()])

        # if the node has a function as an argument, we can't add this to the database yet.
        if not node.has_function_as_argument():
            # add a new function_delta for this function
            fn.function_db.add_function_delta(
                name=node.get_function_instance().get_full_name(),
                fc=delta)

        return delta


class FunctionDB():
    """
    A wrapper around a dictionary mapping the FQDN of a function (str) to its computed
    FunctionDelta.
    """

    def __init__(self) -> None:
        self._function_deltas: dict[str, FunctionDelta] = {}

    def add_function_delta(self, name: str, fc: FunctionDelta):
        self._function_deltas[name] = fc

    def get_function_delta(self, name: str) -> FunctionDelta:
        return self._function_deltas.get(name, None)
