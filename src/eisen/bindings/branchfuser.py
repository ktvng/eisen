from __future__ import annotations

from alpaca.clr import AST
from alpaca.utils import Visitor
from eisen.bindings.bindingcheckerstate import BindingCheckerState
from eisen.common.binding import Condition, BindingCondition

from eisen.validation.validate import Validate

State = BindingCheckerState
class BranchFuser:
    @staticmethod
    def apply_fn_in_branch_and_return_branch_state(
            parent_state: State,
            fn: Visitor,
            child: AST) -> State:

        branch_state = parent_state.but_with(
            ast=child,
            context=parent_state.create_block_context())
        fn.apply(branch_state)
        return branch_state

    @staticmethod
    def check_conditional_initialization(root_state: State, branch_states: list[State]):
        branched_binding_conditions = [branch.get_all_local_binding_conditions() for branch in branch_states]
        names_of_modified_objs = BranchFuser.get_unique_names(branched_binding_conditions)
        relevant_names = BranchFuser.get_relevant_names(names_of_modified_objs, root_state)

        for name in relevant_names:
            branched_bcs = BranchFuser.select_from_branch(root_state, name, branched_binding_conditions)

            if Validate.Bindings.no_split_initialization_after_conditional(root_state, branched_bcs).failed():
                # The error is already recorded here. Treat this as an initialization and continue.
                root_state.add_binding_condition(root_state.get_binding_condition(name).but_initialized())
            elif any(bc.condition == Condition.initialized for bc in branched_bcs):
                root_state.add_binding_condition(root_state.get_binding_condition(name).but_initialized())

    @staticmethod
    def select_from_branch(root_state: State, name: str, branched_binding_conditions: list[list[BindingCondition]]) -> list[BindingCondition]:
        """
        Return a list of BindingConditions which match name, taken across all branches.
        """
        bcs = []
        for binding_conditions in branched_binding_conditions:
            found_in_branch = False
            for bc in binding_conditions:
                if bc.name == name:
                    found_in_branch = True
                    bcs.append(bc)
            if not found_in_branch: bcs.append(root_state.get_binding_condition(name))
        return bcs

    @staticmethod
    def get_unique_names(branched_binding_conditions: list[list[BindingCondition]]) -> set[str]:
        """
        Return a set of unique names with modified BindingConditions across all branched states.
        """
        return set(bc.name for branch_conditions in branched_binding_conditions for bc in branch_conditions)

    @staticmethod
    def get_relevant_names(unique_names: list[str], root_state: State) -> list[str]:
        """
        Names are only relevant if they exist in the root state in an uninitialized condition. Return
        a list of relevant names.
        """
        return [name for name in unique_names if (
            root_state.get_binding_condition(name) is not None
            and root_state.get_binding_condition(name).condition != Condition.initialized
            )]
