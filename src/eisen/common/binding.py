from __future__ import annotations

from typing import Any
from enum import Enum
from dataclasses import dataclass, field

from alpaca.concepts import Type

class Binding(Enum):
    ret_new = 1
    new = 2
    mut_new = 3

    fixed = 4
    mut = 5

    var = 6
    mut_var = 7

    mut_star = 8

    move = 9
    void = 10
    data = 11
    error = 12

class Condition(Enum):
    not_initialized = 1
    initialized = 2
    under_construction = 3
    constructed = 4

@dataclass
class BindingCondition:
    name: str
    binding: Binding
    condition: Condition
    attribute_initializations: dict[str, Condition] = field(default_factory=dict)
    number_of_attributes: int = 0
    callback_to_mark_as_initialized: Any = None

    @staticmethod
    def create_anonymous(binding: Binding = Binding.fixed) ->  BindingCondition:
        return BindingCondition("", binding, Condition.initialized)

    @staticmethod
    def create_for_reference(reference_name: str, binding: Binding, condition: Condition) -> BindingCondition:
        return BindingCondition(reference_name, binding, condition)

    @staticmethod
    def create_for_attribute(full_name: str, binding: Binding):
        return BindingCondition(full_name, binding, Condition.initialized)

    @staticmethod
    def create_for_attribute_being_constructed(full_name: str, binding: Binding, callback_to_initialize_parent: Any):
        return BindingCondition(full_name, binding, Condition.not_initialized,
            callback_to_mark_as_initialized=callback_to_initialize_parent)

    @staticmethod
    def create_for_arguments_or_return_values(reference_name: str, condition: Condition, reference_type: Type) -> BindingCondition:
        # Number of attributes only applies for BindingConditions which are under construction
        n_attributes = (len(reference_type.get_all_component_names())
                        if condition == Condition.under_construction
                        else 0)

        return BindingCondition(
            name=reference_name,
            binding=reference_type.modifier,
            condition=condition,
            number_of_attributes=n_attributes)

    def but_initialized(self) -> BindingCondition:
        if self.callback_to_mark_as_initialized is not None:
            return self.callback_to_mark_as_initialized()
        return BindingCondition(self.name, self.binding, Condition.initialized,
                                attribute_initializations=self.attribute_initializations,
                                number_of_attributes=self.number_of_attributes,
                                callback_to_mark_as_initialized=self.callback_to_mark_as_initialized)

    def get_attribute_initialization(self, attribute_name: str) -> Condition:
        return self.attribute_initializations.get(attribute_name, Condition.not_initialized)

    def but_with_attribute_initialized(self, attribute_name: str) -> BindingCondition:
        attribute_initializations = self.attribute_initializations.copy()
        attribute_initializations[attribute_name] = Condition.initialized
        condition = self.condition
        if len(attribute_initializations) == self.number_of_attributes:
            condition = Condition.constructed
        return BindingCondition(self.name, self.binding,
            condition=condition,
            attribute_initializations=attribute_initializations,
            callback_to_mark_as_initialized=self.callback_to_mark_as_initialized,
            number_of_attributes=self.number_of_attributes)

class BindingMechanics:
    @staticmethod
    def convert_binding(declared: Binding):
        match declared:
            case Binding.void: return Binding.fixed
            case _: return declared

    @staticmethod
    def infer_binding(declared: Binding, received: Binding) -> Binding:
        match declared, received:
            case Binding.void, Binding.data: return Binding.fixed
            case Binding.var, Binding.data: return Binding.var

            case Binding.void, Binding.ret_new: return Binding.new
            case Binding.new, Binding.ret_new: return Binding.new
            case Binding.mut, Binding.ret_new: return Binding.mut_new
            case Binding.mut_new, Binding.ret_new: return Binding.mut_new

            case Binding.var, Binding.ret_new: return Binding.error
            case Binding.mut_var, Binding.ret_new: return Binding.error

            case Binding.void, _: return Binding.fixed
            case Binding.mut, Binding.mut: return Binding.mut
            case Binding.mut, Binding.mut_var: return Binding.mut
            case Binding.mut, Binding.mut_new: return Binding.mut

            case Binding.var, _: return Binding.var

            case Binding.mut_var, Binding.mut: return Binding.mut_var
            case Binding.mut_var, Binding.mut_var: return Binding.mut_var
            case Binding.mut_var, Binding.mut_new: return Binding.mut_var

            case _, Binding.void: return declared
            case _, _:
                return Binding.error

    @staticmethod
    def why_binding_cant_be_inferred(name: str, declared: Binding, received: Binding) -> str:
        match declared, received:
            case Binding.mut, Binding.data:
                return f"cannot bind '{name}' to a primitive as primitives are immutable"
            case Binding.mut, _:
                return f"cannot bind '{name}' which is mutable to something which is immutable"

            case Binding.mut, Binding.data:
                return f"cannot bind '{name}' to a primitive as primitives are immutable"
            case Binding.mut_var, _:
                return f"cannot bind '{name}' which is mutable to something which is immutable"
            case _, Binding.ret_new:
                return f"cannot bind '{name}', a reference, to a new object"

    @staticmethod
    def types_are_binding_compatible(left: Type, right: Type) -> bool:
        if left.is_function():
            # TODO: document why we do the switcheroo
            return (BindingMechanics.types_are_binding_compatible(right.get_argument_type(), left.get_argument_type())
                and BindingMechanics.types_are_binding_compatible(left.get_return_type(), right.get_return_type()))
        if left.is_tuple():
            return all(BindingMechanics.types_are_binding_compatible(l, r) for l, r, in zip(left.unpack_into_parts(), right.unpack_into_parts()))
        return BindingMechanics._types_are_binding_compatible(left, right)

    @staticmethod
    def _types_are_binding_compatible(left: Type, right: Type) -> bool:
        return BindingMechanics.type_bindings_are_compatible(left.modifier, right.modifier)

    @staticmethod
    def type_bindings_are_compatible(left: Binding, right: Binding) -> bool:
        match left, right:
            case Binding.mut, Binding.mut: return True
            case Binding.mut, Binding.mut_new: return True
            case Binding.mut, Binding.mut_var: return True
            case Binding.mut, _: return False

            case Binding.mut_var, Binding.mut: return True
            case Binding.mut_var, Binding.mut_new: return True
            case Binding.mut_var, Binding.mut_var: return True
            case Binding.mut_var, _: return False

            case Binding.var, _: return True
            case Binding.fixed, _: return True

            case Binding.move, Binding.new: return True
            case Binding.move, Binding.mut_new: return True
            case Binding.move, _: return False

            case Binding.new, Binding.ret_new: return True
            case Binding.new, _: return False

            case Binding.data, Binding.data: return True
            case Binding.data, _: return False
            case _, _:
                raise Exception(f"not handled binding {left}, {right}")



    @staticmethod
    def can_be_assigned_to_parameter(expected_for_parameter: Binding, received: BindingCondition):
        match expected_for_parameter, received:
            case Binding.fixed, _: return True
            case Binding.var, _: return True

            case Binding.mut, BindingCondition(binding=Binding.mut): return True
            case Binding.mut, BindingCondition(binding=Binding.mut_var): return True
            case Binding.mut, BindingCondition(binding=Binding.mut_new): return True
            case Binding.mut, BindingCondition(binding=Binding.new, condition=Condition.constructed): return True
            case Binding.mut, BindingCondition(binding=Binding.new, condition=Condition.under_construction): return True

            case Binding.mut_var, BindingCondition(binding=Binding.mut): return True
            case Binding.mut_var, BindingCondition(binding=Binding.mut_var): return True
            case Binding.mut_var, BindingCondition(binding=Binding.mut_new): return True
            case Binding.mut_var, BindingCondition(binding=Binding.new, condition=Condition.constructed): return True
            case Binding.mut_var, BindingCondition(binding=Binding.new, condition=Condition.under_construction): return True

            case Binding.move, BindingCondition(binding=Binding.new): return True
            case Binding.move, BindingCondition(binding=Binding.ret_new): return True
            case _, _: return False

    @staticmethod
    def why_binding_cant_be_assigned_to_parameter(
            function_name: str,
            parameter_name: str,
            expected_for_parameter: Binding,
            received: Binding) -> str:

        match expected_for_parameter, received:
            case Binding.mut, _:
                return f"'{parameter_name}' of '{function_name}' is mutable and cannot be set to something which is immutable"
            case Binding.mut_var, _:
                return f"'{parameter_name}' of '{function_name}' is mutable and cannot be set to something which is immutable"
            case Binding.move, _:
                return f"'{parameter_name}' of '{function_name}' will move the underlying memory and must be given a memory allocation"
            case _, _:
                raise Exception(f"not handled for {expected_for_parameter}, {received}")


    @staticmethod
    def can_be_assigned(left: BindingCondition, right: BindingCondition):
        match left, right:
            case _, BindingCondition(condition=Condition.under_construction):
                return f"'{right.name}' is not fully constructed and cannot be used."

            # ======================================================================================
            # Exhaustive failures for when assignmet of ret_new fails
            # TODO: fill in the rest
            case BindingCondition(binding=Binding.fixed, condition=Condition.not_initialized), BindingCondition(binding=Binding.ret_new):
                return f"cannot assign a memory allocation to a variable '{left.name}'"

            # ======================================================================================
            # Exhaustive cases for when assignment of a mut binding succeeds
            case BindingCondition(binding=Binding.mut, condition=Condition.not_initialized), BindingCondition(binding=Binding.mut): return True
            case BindingCondition(binding=Binding.mut, condition=Condition.not_initialized), BindingCondition(binding=Binding.mut_new): return True
            case BindingCondition(binding=Binding.mut, condition=Condition.not_initialized), BindingCondition(binding=Binding.mut_var): return True
            # Failures
            case BindingCondition(binding=Binding.mut, condition=Condition.not_initialized), _:
                return f"cannot assign something which is immutable to '{left.name}' which is mutable"
            case BindingCondition(binding=Binding.mut), _:
                return f"cannot reassign '{left.name}' as it is non-variable "

            # Exhaustive cases for when assignemnt of a fixed binding succeeds
            case BindingCondition(binding=Binding.fixed, condition=Condition.not_initialized), _: return True
            # Failures
            case BindingCondition(binding=Binding.fixed), _:
                return f"cannot reassign '{left.name}' as it is non-variable "

            # Exhaustive cases for when assignment of a variable binding succeeds
            case BindingCondition(binding=Binding.var), _: return True

            # Exhaustive cases for when assignment of a mutable and variable binding succeeds
            case BindingCondition(binding=Binding.mut_var), BindingCondition(binding=Binding.mut): return True
            case BindingCondition(binding=Binding.mut_var), BindingCondition(binding=Binding.mut_new): return True
            case BindingCondition(binding=Binding.mut_var), BindingCondition(binding=Binding.mut_var): return True
            # Failures
            case BindingCondition(binding=Binding.mut_var, condition=Condition.not_initialized), _:
                return f"cannot initialize '{left.name}' which is mutable with something that is immutable"
            case BindingCondition(binding=Binding.mut_var), _:
                return f"cannot reassign '{left.name}' which is mutable to something which is immutable"

            # Exhaustive cases for when assignment of a data binding succeeds
            case BindingCondition(binding=Binding.data), BindingCondition(binding=Binding.data): return True

            # Exhaustive cases for when assignment of a new binding succeeds
            case BindingCondition(binding=Binding.new, condition=Condition.not_initialized), BindingCondition(binding=Binding.ret_new): return True
            case BindingCondition(binding=Binding.mut_new, condition=Condition.not_initialized), BindingCondition(binding=Binding.ret_new): return True
            # This is initialization
            case BindingCondition(binding=Binding.new, condition=Condition.under_construction), _: return True
            # Failures
            case BindingCondition(binding=Binding.new, condition=Condition.not_initialized), _:
                return f"as '{left.name}' is a new memory allocation, it must be created by a function which returns a new object"
            case BindingCondition(binding=Binding.new), _:
                return f"cannot reassign '{left.name}' as this is a memory allocation"

            case _, _: return f"can't do left={left}, right={right}"
