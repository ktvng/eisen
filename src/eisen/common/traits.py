from __future__ import annotations
from typing import TYPE_CHECKING
from dataclasses import dataclass

from alpaca.pattern import Pattern
from alpaca.clr import AST
from alpaca.concepts import Type

from eisen.state.basestate import BaseState as State
from eisen.common.typefactory import TypeFactory
from eisen.common.eiseninstance import Instance

if TYPE_CHECKING:
    from eisen.typecheck.typechecker import TypeChecker


@dataclass
class TraitImplDetailsForFunctionVisitor:
    """
    Contains the un-enriched (only string) trait implementation details when inside a (trait_def ...)
    AST, which include the name of the trait being implemented, and the name of the struct which
    is implementing it.
    """

    trait_name: str
    implementing_struct_name: str

@dataclass
class TraitImplementation():
    """
    Contains the enriched (type-based) trait implementation details for general Visitors, including
    a list of function instances representing the functions defined for the trait implementation.
    """
    trait: Type
    struct: Type
    implementations: list[Instance]

    def get_key_for_this(self) -> str:
        """
        Return the key for this instance
        """
        return TraitImplementation.get_key(self.trait, self.struct)

    @staticmethod
    def get_key(trait: Type, struct: Type) -> str:
        """
        Return a key for the given [trait] and implementing [struct]
        """
        return trait.get_uuid_str() + " for " + struct.get_uuid_str()

    def __hash__(self) -> int:
        return hash(self.get_key_for_this())

class TraitsLogic:
    """
    Logic which concerns parsing, compiling, and using traits; kept in one place for logical
    consistency.
    """

    @staticmethod
    def get_name_for_instance_implementing_trait_function(
            details: TraitImplDetailsForFunctionVisitor,
            name_of_implemented_function: str) -> str:
        """
        Return the name to use for an Instance representing a function definition that implements a trait
        function
        """
        return f"#{details.trait_name}_for_{details.implementing_struct_name}_" + name_of_implemented_function

    @staticmethod
    def get_python_writable_name_for_trait_class(
            struct_name: str,
            trait_name: str) -> str:
        """
        Return the name of the trait class to create when converting to Python. In Python, a trait is
        represented as a class decorator which wraps the struct, stores an internal reference to the
        struct, and contains the function definitions for all of the trait functions.

        Thus, when a (trait_def ...) is processed, a Python class must be produced with name following
        the form trait_for_struct, and when a instance_of_struct.as(trait) is processed, a new instance
        of that decorator class is created like so: trait_for_struct(instance_of_struct)
        """

        return f"{trait_name}_for_{struct_name}"

    @staticmethod
    def is_trait_function(state: State, function_type: Type):
        """
        The only functions where the first type is 'Self' are trait functions
        """
        return TraitsLogic.are_arguments_of_a_trait_function(state, function_type.get_argument_type())

    @staticmethod
    def are_arguments_of_a_trait_function(state: State, function_argument_type: Type):
        """
        The provided [function_argument_type] is indicative of a trait function if the
        first type is 'Self'
        """
        match arg_type := function_argument_type:
            case Type(classification=Type.classifications.tuple, components=[first, *_]):
                return first == state.get_defined_type("Self")
            case Type():
                return arg_type == state.get_defined_type("Self")
            case _:
                return False

    @staticmethod
    def get_type_of_trait_function_where_implemented(
            trait_function_declaration: Type,
            implementation_type: Type) -> Type:
        """
        A trait function will be declared with 'Self' as the first type.
            (Self, int, obj) -> obj

        If a struct MyStruct implements the trait, then its definition of the same function will
        substitute its type for Self:
            (MyStruct, int, obj) -> obj

        For a trait function declared with type [trait_function_declaration], this method returns
        the type of that function where it is implemented by [implementation_type]
        """
        return TypeFactory.produce_function_type(
            mod=None,
            arg=TraitsLogic._replace_Self_type_with_implementation_type(
                trait_function_declaration_type=trait_function_declaration.get_argument_type(),
                implementation_type=implementation_type),
            ret=trait_function_declaration.get_return_type())

    @staticmethod
    def _Self_type_is_first_parameter(Self_type: Type, parameter_type: Type) -> bool:
        """
        Returns true if [Self_type] is equal to [parameter_type] if it is a singular type, or the
        first element if [parameter_type] is a tuple
        """
        match parameter_type:
            case Type(classification=Type.classifications.tuple, components=[first, *_]):
                return first == Self_type
            case Type():
                return parameter_type == Self_type

    @staticmethod
    def _count_occurrences_of(type_to_count: Type, in_type: Type) -> int:
        """
        Returns the number of occurrences of [type_to_count] [in_type]
        """
        count = 0
        for t in in_type.unpack():
            match t.classification:
                case Type.classifications.tuple:
                    count += TraitsLogic._count_occurrences_of(type_to_count, t)
                case Type.classifications.function:
                    count += (TraitsLogic._count_occurrences_of(type_to_count, t.get_argument_type())
                            + TraitsLogic._count_occurrences_of(type_to_count, t.get_return_type()))
                case Type.classifications.parametric:
                    count += sum(TraitsLogic._count_occurrences_of(type_to_count, p)
                               for p in t.parametrics)
                case Type.classifications.novel:
                    count += 1 if t == type_to_count else 0
                case _:
                    count += 0
        return count

    @staticmethod
    def _Self_type_is_nowhere_else(Self_type: Type, function_type: Type) -> bool:
        """
        Assuming that 'Self' appears once as the first parameter, returns True if [Self_type]
        is nowhere else inside the [function_type]
        """
        return TraitsLogic._count_occurrences_of(Self_type, function_type) == 1

    @staticmethod
    def is_well_formed_trait_function_declaration(Self_type: Type, function_type: Type) -> bool:
        """
        A trait function declaration is well-formed if its type contains 'Self' ([Self_type]) as the first
        parameter of the [function_type], and the type 'Self' is nowhere else referenced in the
        [function_type]
        """
        return (TraitsLogic._Self_type_is_first_parameter(Self_type, function_type.get_argument_type())
            and TraitsLogic._Self_type_is_nowhere_else(Self_type, function_type))

    def _replace_Self_type_with_implementation_type(trait_function_declaration_type: Type, implementation_type: Type):
        """
        Assuming that [in_type] is a well-formed trait function declaration type, replace the first
        parameter (which must be 'Self') with the implementation type of the trait, [with_type]
        """
        match trait_function_declaration_type:
            case Type(classification=Type.classifications.tuple, components=[first, *others]):
                return TypeFactory.produce_tuple_type(
                    [implementation_type.with_modifier(first.modifier), *others])
            case Type():
                return implementation_type.with_modifier(trait_function_declaration_type.modifier)

    @staticmethod
    def restructure_call_of_trait_attribute_function_if_needed(
            fn: TypeChecker,
            state: State,
            function_type: Type,
            params_type: Type) -> Type:
        """
        In Eisen, a trait function will be expanded by the CallUnwrapper to be something like:

            (call (. (ref trait_instance) function_name) (params ...))

        But the definition of the trait function actually takes the object as the first parameter,
        so we need to insert the calling object to achieve:

            (call (. (ref trait_instance) function_name) (params (ref trait_instance)) ...)
        """

        # Only needed if we're looking at a trait function.
        if not TraitsLogic.is_trait_function(state, function_type): return params_type

        match = Pattern("('call ('. caller_obj _) params)").match(state.get_ast())
        caller_ast: AST = match.caller_obj
        params_ast: AST = match.params

        # Add the caller as the first parameter
        params_ast._list.insert(0, caller_ast)

        # Need to update the AST in place
        state.get_ast()._list[1] = params_ast

        return fn.apply(state.but_with(ast=params_ast))
