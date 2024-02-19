from __future__ import annotations

from alpaca.utils import Visitor
from eisen.common.restriction import MutableRestriction, NewLetRestriction, ImmutableRestriction
from eisen.common.eiseninstance import Instance
from eisen.state.basestate import BaseState as State

import eisen.adapters as adapters

class VectorVisitor(Visitor):
    def run(self, state: State):
        self.apply(state)
        return state

    def apply(self, state: State) -> None:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("new_vec")
    def new_vec_(fn, state: State) -> None:
        # TODO: broken with new types
        vec_type = adapters.NewVec(state).get_type()
        element_type = vec_type.get_first_parameter_type()
        if not element_type.restriction.is_primitive():
            element_type = TypeFactory.produce_function_type(
                arg=state.get_void_type(),
                ret=element_type.with_restriction(NewLetRestriction()),
                mod=None).with_restriction(ImmutableRestriction())

        append_fn_type = TypeFactory.produce_function_type(
            arg=TypeFactory.produce_tuple_type(
                components=[vec_type.with_restriction(MutableRestriction()),
                            element_type]),
            ret=vec_type.with_restriction(MutableRestriction()),
            mod=None)

        if state.get_builtin_function("append", append_fn_type) is None:
            instance = Instance(
                name="append",
                type=append_fn_type,
                context=state.get_global_module(),
                ast=None,
                no_mangle=True,
                no_lambda=True)
            state.add_builtin_function(instance)
            state.get_global_module().add_function_instance(instance)



    @Visitor.for_default
    def default_(fn, state: State) -> None:
        for child in state.get_child_asts():
            fn.apply(state.but_with(ast=child))
