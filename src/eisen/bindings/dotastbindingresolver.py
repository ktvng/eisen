from __future__ import annotations

from alpaca.utils import Visitor

import eisen.adapters as adapters
from eisen.bindings.bindingcheckerstate import BindingCheckerState
from eisen.common.binding import Binding, Condition, BindingCondition
from eisen.validation.validate import Validate

State = BindingCheckerState
class DotAstBindingResolver(Visitor):
    def run(self, state: State):
        return self.apply(state)

    def apply(self, state: State) -> BindingCondition:
        return self._route(state.get_ast(), state)

    @Visitor.for_ast_types("index")
    def _index(fn, state: State):
        # TODO: fix this
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types("ref")
    def _ref(fn, state: State):
        return state.get_binding_condition(adapters.Ref(state).get_name())

    @Visitor.for_ast_types(".")
    def _dot(fn, state: State):
        parent_condition = fn.apply(state.but_with_first_child())
        child_binding = state.get_returned_bindings()[0]
        child_name = adapters.Scope(state).get_full_name()

        # Possible bindings of the child (one of these will be picked):
        fixed_child = BindingCondition.create_for_attribute(child_name, Binding.fixed)
        true_child = BindingCondition.create_for_attribute(child_name, child_binding)

        # Special case handled first, if the parent is under construction, then we are inside the
        # constructor, and initializing the child attributes.
        if parent_condition.condition == Condition.under_construction:
            attr_name = adapters.Scope(state).get_attribute_name()
            if parent_condition.get_attribute_initialization(attr_name) == Condition.initialized:
                return true_child

            # If the child is not already initialized, then we create a new BindingCondition with
            # a callback to mark the parent as initialized when the child is initialized.
            return BindingCondition.create_for_attribute_being_constructed(child_name, child_binding,
                callback_to_initialize_parent=lambda: parent_condition.but_with_attribute_initialized(attr_name))

        Validate.Bindings.is_initialized(state, parent_condition)

        match parent_condition, child_binding:
            # If we are in a constructor, and the constructed object is fully constructed, then
            # ignore parent restrictions.
            case BindingCondition(condition=Condition.constructed), _: return true_child

            # Immutability from the parent carries over.
            case BindingCondition(binding=Binding.fixed), _: return fixed_child
            case BindingCondition(binding=Binding.new), _: return fixed_child
            case BindingCondition(binding=Binding.var), _: return fixed_child

            # Immutability from the child takes effect
            case _, Binding.fixed: return fixed_child
            case _, Binding.new: return fixed_child

            # Otherwise take the child's binding, as the parent must be some type of mut
            case _, _: return true_child
