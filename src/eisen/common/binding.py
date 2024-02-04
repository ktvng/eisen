from __future__ import annotations

from typing import Any
from enum import Enum
from dataclasses import dataclass, field

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

@dataclass
class CompositeBinding:
    components: dict[str, Binding] = None
    args: list[Binding] = None
    rets: list[Binding] = None

    def get_binding_of_attribute(self, name: str) -> Binding:
        return self.components[name]

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
    associated_composite_binding: CompositeBinding = None

    def but_initialized(self) -> BindingCondition:
        if self.callback_to_mark_as_initialized is not None:
            return self.callback_to_mark_as_initialized()
        return BindingCondition(self.name, self.binding, Condition.initialized,
                                attribute_initializations=self.attribute_initializations,
                                number_of_attributes=self.number_of_attributes,
                                callback_to_mark_as_initialized=self.callback_to_mark_as_initialized,
                                associated_composite_binding=self.associated_composite_binding)

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
            associated_composite_binding=self.associated_composite_binding,
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

            case _, _: return Binding.error

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
