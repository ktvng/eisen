from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field

from alpaca.concepts import Type

class Binding(Enum):
    """
    A binding is a modifier on a type in eisen which adds additional constraints on usage and
    modification. For references, bindings be used to change mutability or variability.

    A reference is mutable if it (1) refers to a struct or composite type and (2) allows that struct
    to be modified, i.e. its attribute changed.

    A reference is variable if it can be reassigned to another reference.

    Mutability and variability together create four different base bindings for a reference.

    A binding may also be used to differentiate between names that refer to references and names
    which refer to allocations. References are equivalent to pointers, and refer to existing
    allocations. Allocations are actual memory allocations on the stack.

    An allocation is denoted by the 'new' component of a binding. Allocations cannot be reassigned,
    as they refer to a specific and immobile memory allocation.
    """

    # Memory Allocations
    # ==============================================================================================

    # This binding is only available to return values of functions which construct new memory
    # allocations. In general, allocations cannot be reassigned, so new <- new is not permitted.
    # However, for 'new' bindings which are not initialized, new <- ret new is allowed, to represent
    # the memory allocation bound by 'new' being initialized by a function which returns a new
    # memory allocation for the first time.
    ret_new = 1

    # This binding refers to a new memory allocation which is neither mutable nor variable (as
    # allocations are always invariable).
    new = 2

    # This binding refers to a new memory allocation which is mutable but not variable.
    mut_new = 3


    # Basic References
    # ==============================================================================================
    #
    #                          Variability
    #                       Yes         No
    #
    #               Yes   mut_var       mut
    # Mutability
    #               No      var        fixed
    #
    fixed = 4
    mut = 5
    var = 6
    mut_var = 7

    # Memory Management Bindings
    # ==============================================================================================

    # This binding refers to a mutable reference which is memory-unsafe
    mut_star = 8

    # This binding refers to an allocation which is moved into a helper method.
    move = 9


    # Defaults
    # ==============================================================================================

    # Initially, any binding which is not explicitly specified is marked as void. After binding
    # and type inference, void bindings are replaced.
    void = 10

    # Any literal (integer, double, string) is given the data binding.
    data = 11

    # The error binding is returned if binding inference fails.
    error = 12

class Condition(Enum):
    not_initialized = 1
    initialized = 2
    under_construction = 3
    constructed = 4


@dataclass(kw_only=True)
class BindingCondition:
    """
    The BindingCondition should be created for a name (anything defined by the 'let' keyword) to join
    information about the binding and the condition of that name. Whether or not a name can be used,
    mutated, changed, or (re)assigned is dependent on both the binding of the name as well as its
    condition.
    """
    name: str
    binding: Binding
    condition: Condition

    @staticmethod
    def create_anonymous(binding: Binding = Binding.fixed) ->  BindingCondition:
        """
        Create a new anonymous (no-name) instance for an intermediate step. e.g: the result of (+ x 4)
        will return an anonymous BindingCondition
        """
        return BindingCondition(name="", binding=binding, condition=Condition.initialized)

    @staticmethod
    def create_for_declaration(name: str, binding: Binding, condition: Condition) -> BindingCondition:
        """
        Create a new instance for a [name] declared with the 'let' keyword with the specified
        [binding] and [condition].
        """
        return BindingCondition(name=name, binding=binding, condition=condition)

    @staticmethod
    def create_for_attribute(full_name: str, binding: Binding):
        """
        Create a new instance for a attribute with [full_name] (e.g. "obj.attr") with the specified
        [binding].
        """
        return BindingCondition(name=full_name, binding=binding, condition=Condition.initialized)

    @staticmethod
    def create_for_arguments_or_return_values(name: str, condition: Condition, reference_type: Type) -> BindingCondition:
        """
        Create a new instance for an argument or return value called [name] with the defined
        [condition] and of the specified [type].
        """
        return BindingCondition(
            name=name,
            binding=reference_type.modifier,
            condition=condition)

    def but_initialized(self) -> BindingCondition:
        """
        Return a new BindingCondition which represents this same name/binding, but is initialized.
        """
        return BindingCondition(name=self.name,
                                binding=self.binding,
                                condition=Condition.initialized)


@dataclass(kw_only=True)
class BindingConditionForAttributeUnderConstruction(BindingCondition):
    """
    An extension of BindingCondition specific to attributes of an object which is being constructed
    instead a create() constructor of a struct declaration. The initialization of the object is
    actually recorded by the BindingConditionForObjectUnderConstruction of its parent, which means
    when its 'but_initialized' method is called, it must update the parent.
    """

    # The name of the attribute
    attribute_name: str

    # A reference to the parent object which is being constructed (which this is an attribute
    # of)
    parent: BindingConditionForObjectUnderConstruction

    @staticmethod
    def create(full_name: str, binding: Binding, parent: BindingConditionForObjectUnderConstruction,
               attribute_name: str):
        return BindingConditionForAttributeUnderConstruction(
            name=full_name,
            binding=binding,
            condition=Condition.not_initialized,
            parent=parent,
            attribute_name=attribute_name)

    def but_initialized(self) -> BindingCondition:
        return self.parent.but_with_attribute_initialized(self.attribute_name)


@dataclass(kw_only=True)
class BindingConditionForObjectUnderConstruction(BindingCondition):
    """
    An extension of BindingCondition specific to an object which is being constructed inside a
    create() constructor of a struct declaration. As the object is being constructed, it needs
    special semantics because:

        1. All its attributes must be initialized
        2. Some of its attributes may be initialized while others are not. This means its state
           may be non-homogenous
        3. It should not be marked as constructed until all its attributes are initialized
    """
    initialized_attributes: set[str] = field(default_factory=set)
    number_of_attributes: int = 0

    @staticmethod
    def create(object_name: str, object_type: Type) -> BindingConditionForObjectUnderConstruction:
        return BindingConditionForObjectUnderConstruction(
            name=object_name,
            binding=object_type.modifier,
            condition=Condition.under_construction,
            number_of_attributes=len(object_type.get_all_component_names()))

    def but_initialized(self) -> BindingCondition:
        """
        This method should not be called. Instead initialization should occur implicitly after the
        last attribute is initialized via 'but_with_attribute_initialized()'
        """
        raise Exception("Bad logic.")

    def attribute_is_initialized(self, attribute_name: str) -> bool:
        return attribute_name in self.initialized_attributes

    def but_with_attribute_initialized(self, attribute_name: str) -> BindingCondition:
        """
        This method marks the [attribute_name] of this object as initialized.

        An object being constructed inside a create method is considered initialized if all of its
        attributes have been initialized, at which point this method will also mark this object
        as constructed.
        """

        initialized_attributes = self.initialized_attributes.copy()
        initialized_attributes.add(attribute_name)
        condition = self.condition

        object_is_fully_constructed = len(initialized_attributes) == self.number_of_attributes
        condition = (Condition.constructed if object_is_fully_constructed
                     else Condition.under_construction)

        return BindingConditionForObjectUnderConstruction(
            name=self.name,
            binding=self.binding,
            condition=condition,
            initialized_attributes=initialized_attributes,
            number_of_attributes=self.number_of_attributes)


class BindingMechanics:
    @staticmethod
    def infer_fixed_binding(declared: Binding):
        """
        Inside type definitions (: (void x) type) or type_binding ASTS (void (type x)), if there is
        no supplied binding, it is inferred to be fixed.
        """
        match declared:
            case Binding.void: return Binding.fixed
            case _: return declared

    @staticmethod
    def infer_binding(declared: Binding, received: Binding) -> Binding:
        """
        Canonical semantics for inferring bindings for 'let' statements.
        """
        match declared, received:
            # No declared binding.
            case Binding.void, Binding.ret_new: return Binding.new
            case Binding.void, _: return Binding.fixed

            # Declared binding, and no received binding.
            case _, Binding.void: return declared

            # Declared as var
            case Binding.var, Binding.ret_new: return Binding.error
            case Binding.var, Binding.data: return Binding.var
            case Binding.var, _: return Binding.var

            # Declared as mut
            case Binding.mut, Binding.ret_new: return Binding.mut_new
            case Binding.mut, Binding.mut_new: return Binding.mut
            case Binding.mut, Binding.mut: return Binding.mut
            case Binding.mut, Binding.mut_var: return Binding.mut
            case Binding.mut, _: return Binding.error

            # Declared as mut_var reference:
            case Binding.mut_var, Binding.mut: return Binding.mut_var
            case Binding.mut_var, Binding.mut_var: return Binding.mut_var
            case Binding.mut_var, Binding.mut_new: return Binding.mut_var
            case Binding.mut_var, Binding.ret_new: return Binding.error
            case Binding.mut_var, _: return Binding.error

            # Declared as new allocation
            case Binding.mut_new, Binding.ret_new: return Binding.mut_new
            case Binding.mut_new, _: return Binding.error
            case Binding.new, Binding.ret_new: return Binding.new
            case Binding.new, _: return Binding.error

            case _, _:
                raise Exception(f"Unhandled case {declared} {received}")

    @staticmethod
    def why_binding_cant_be_inferred(name: str, declared: Binding, received: Binding) -> str:
        match declared, received:
            case Binding.mut, Binding.data:
                return f"cannot bind '{name}' to a primitive as primitives are immutable"
            case Binding.mut, _:
                return f"cannot bind '{name}' which is mutable to something which is immutable"

            case Binding.mut_var, Binding.data:
                return f"cannot bind '{name}' to a primitive as primitives are immutable"
            case Binding.mut_var, _:
                return f"cannot bind '{name}' which is mutable to something which is immutable"

            case _, Binding.ret_new:
                return f"cannot bind '{name}', a reference, to a new memory allocation"
            case Binding.new, _:
                return f"cannot bind '{name}', which must refer to a memory allocation, to a reference"
            case _, _:
                return f"unhandled message '{name}' {declared} {received}"

    @staticmethod
    def types_are_binding_compatible(left: Type, right: Type, is_param=False) -> bool:
        if left.is_function():
            return (BindingMechanics.types_are_binding_compatible(left.get_argument_type(), right.get_argument_type(), is_param=True)
                and BindingMechanics.types_are_binding_compatible(left.get_return_type(), right.get_return_type(), is_param))
        if left.is_tuple():
            return all(BindingMechanics.types_are_binding_compatible(l, r, is_param) for l, r, in zip(left.unpack_into_parts(), right.unpack_into_parts()))
        return BindingMechanics._types_are_binding_compatible(left, right, is_param)

    @staticmethod
    def _types_are_binding_compatible(left: Type, right: Type, is_param) -> bool:
        # If we're looking at a parameter of a function, then we need to swap the left and right
        # because the right is the actual binding required, and the left is what could be provided.
        if is_param:
            return BindingMechanics.type_bindings_are_compatible(right.modifier, left.modifier)
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
