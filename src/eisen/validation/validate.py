from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from alpaca.concepts import Type, AbstractException, Type
from eisen.common.eiseninstance import Instance
from eisen.common.exceptions import Exceptions
from eisen.common.traits import TraitsLogic
from eisen.state.basestate import BaseState as State
from eisen.validation.nilablestatus import NilableStatus
from eisen.common.binding import Binding, Condition, BindingCondition, BindingMechanics, BindingConditionForObjectUnderConstruction

if TYPE_CHECKING:
    from eisen.trace.entity import Trait
    from eisen.trace.shadow import Shadow
    from eisen.trace.memory import Memory, Impression
    from eisen.state.memoryvisitorstate import MemoryVisitorState

@dataclass
class ValidationResult:
    result: bool

    def failed(self) -> bool:
        return not self.result

    def succeeded(self) -> bool:
        return self.result

    @staticmethod
    def failure() -> ValidationResult:
        return ValidationResult(result=False)

    @staticmethod
    def success() -> ValidationResult:
        return ValidationResult(result=True)

@dataclass
class TypePair:
    left: Type
    right: Type


class TypeCheck:
    @staticmethod
    def encountered_prior_failure(state: State, *args: list[Type]) -> bool:
        return any(arg.equals(state.get_abort_signal(), Type.structural_equivalency) for arg in args)

    @staticmethod
    def flatten_to_type_pairs(left: Type, right: Type) -> list[TypePair]:
        if left.is_tuple():
            return [TypePair(left=l, right=r) for l, r in zip(left.components, right.components)]
        return [TypePair(left=left, right=right)]

    @staticmethod
    def type_pair_is_nil_compatible(state: State, type_pair: TypePair) -> bool:
        # TODO: restore after refactor of nil concept
        # if not type_pair.left.restriction.is_nilable() and type_pair.right.is_nil():
        #     add_exception_to(state,
        #         ex=Exceptions.NilAssignment,
        #         msg=f"cannot assign nil to non-nilable type '{type_pair.left}'")
        #     return False
        return True

    @staticmethod
    def equivalent_types(state: State, type_pair: TypePair) -> bool:
        # TODO: restore after refactor of nil concept
        # 'nil' is considered equivalent to all nilable types
        # if type_pair.left.restriction.is_nilable() and type_pair.right.is_nil():
        #     return True
        if not type_pair.left.equals(type_pair.right, Type.structural_equivalency):
            add_exception_to(state,
                ex=Exceptions.TypeMismatch,
                msg=f"'{type_pair.left}' != '{type_pair.right}'")
            return False
        return True

    @staticmethod
    def compatible_types(state: State, type_pair: TypePair) -> bool:
        if type_pair.left.equals(type_pair.right, Type.structural_equivalency): return True
        if len(type_pair.left.unpack()) != len(type_pair.right.unpack()): return False
        for left_type, right_type in zip(type_pair.left.unpack(), type_pair.right.unpack()):
            if left_type.equals(state.get_self_type(), Type.structural_equivalency):
                if right_type.is_trait(): continue
                return False
            if not left_type.equals(right_type, Type.structural_equivalency):
                return False
        return True


    @staticmethod
    def type_is_expected(state: State, expected: Type, gotten: Type) -> bool:
        # TODO: restore after refactor of nil concept
        # if expected.restriction.is_nilable() and gotten.is_nil():
        #     return True

        if not expected.equals(gotten, Type.structural_equivalency):
            add_exception_to(state,
                ex=Exceptions.TypeMismatch,
                msg=f"expected '{expected}' but got '{gotten}'")
            return False
        return True

class ImplementationCheck:
    @staticmethod
    def _has_attribute(state: State, type: Type, attribute_name: str, inherited_type: Type) -> bool:
        if not type.has_member_attribute_with_name(attribute_name):
            add_exception_to(state,
                ex=Exceptions.AttributeMismatch,
                msg=f"'{type}' is missing attribute '{attribute_name}' required to inherit '{inherited_type}'")
            return False
        return True

    @staticmethod
    def _attribute_matches_type(state: State,
                                type: Type,
                                attribute_name: str,
                                required_attribute_type: Type,
                                inherited_type: Type):
        if not type.get_member_attribute_by_name(attribute_name) == required_attribute_type:
            add_exception_to(state,
                ex=Exceptions.MissingAttribute,
                msg=f"'{type}' is missing attribute '{attribute_name}' required to inherit '{inherited_type}'")
            return False
        return True

    @staticmethod
    def has_required_attributes(state: State, type: Type, inherited_type: Type) -> bool:
        return all([ImplementationCheck._has_attribute(state, type, required_attribute_name, inherited_type)
                    and ImplementationCheck._attribute_matches_type(state,
                                                                    type,
                                                                    required_attribute_name,
                                                                    required_attribute_type,
                                                                    inherited_type)
                        for required_attribute_name, required_attribute_type in inherited_type.get_all_attribute_name_type_pairs()])


def add_exception_to(state: State, ex: AbstractException, msg: str, line_number: int=0):
    if line_number == 0:
        line_number = state.get_line_number()
    state.report_exception(ex(
        msg=msg,
        line_number=line_number))

def failure_with_exception_added_to(state: State, ex: AbstractException, msg: str, line_number: int=0):
    add_exception_to(state, ex, msg, line_number)
    return ValidationResult.failure()

################################################################################
# performs the actual validations
class Validate:
    class Traits:
        def implementation_is_complete(state: State, trait: Type, implementing_struct: Type, implemented_fns: list[Instance]):
            for name, type_ in zip(trait.component_names, trait.components):
                # The type to look for must substitute Self for the implementation_type
                type_to_look_for = TraitsLogic.get_type_of_trait_function_where_implemented(type_, implementing_struct)

                # Validate the definition can be found
                definitions = [i for i in implemented_fns
                               if i.name_of_trait_attribute == name
                               and i.type.equals(type_to_look_for, Type.structural_equivalency)]
                if len(definitions) == 0:
                    return failure_with_exception_added_to(state,
                        ex=Exceptions.IncompleteTraitDefinition,
                        msg=f"implementation of {trait} for {implementing_struct} is missing a definition of '{name}' {type_to_look_for}")

                # Validate bindings are correct
                definition = definitions[0]
                if not BindingMechanics.types_are_binding_equivalent(type_to_look_for, definition.type):
                    add_exception_to(state,
                        ex=Exceptions.IncompatibleBinding,
                        msg=f"bindings in the definition of '{name}' for '{implementing_struct}' are different that defined in the trait '{trait}'",
                        line_number=definition.ast.line_number)

            return ValidationResult.success()

        def _trait_component_is_correct(state: State, component_name: str, component_type: Type):
            if not component_type.is_function():
                return failure_with_exception_added_to(state,
                    ex=Exceptions.MalformedTraitDeclaration,
                    msg=f"traits only permit function attributes but '{component_name}' is not a function")
            if not TraitsLogic.is_well_formed_trait_function_declaration(state.get_defined_type("Self"), component_type):
                return failure_with_exception_added_to(state,
                    ex=Exceptions.MalformedTraitDeclaration,
                    msg=f"'{component_name}' misuses the Self type. Self should must be used only as the first parameter")
            return ValidationResult.success()

        def correctly_declared(state: State, trait: Type):
            for name, type_ in zip(trait.component_names, trait.components):
                Validate.Traits._trait_component_is_correct(state, name, type_)
            return ValidationResult.success()

    @staticmethod
    def can_assign(state: State, type1: Type, type2: Type) -> ValidationResult:
        if TypeCheck.encountered_prior_failure(state, type1, type2):
            return ValidationResult.failure()

        if (Validate.types_are_nil_compatible(state, type1, type2).failed()
                or Validate.equivalent_types(state, type1, type2).failed()):
            return ValidationResult.failure()
        return ValidationResult.success()

    @staticmethod
    def types_are_nil_compatible(state: State, type1: Type, type2: Type) -> ValidationResult:
        if TypeCheck.encountered_prior_failure(state, type1, type2):
            return ValidationResult.failure()

        if all([TypeCheck.type_pair_is_nil_compatible(state, type_pair) for
                type_pair in TypeCheck.flatten_to_type_pairs(type1, type2)]):
            return ValidationResult.success()
        return ValidationResult.failure()

    @staticmethod
    def equivalent_types(state: State, type1: Type, type2: Type) -> ValidationResult:
        if TypeCheck.encountered_prior_failure(state, type1, type2):
            return ValidationResult.failure()

        if all([TypeCheck.equivalent_types(state, type_pair)
                for type_pair in TypeCheck.flatten_to_type_pairs(type1, type2)]):
            return ValidationResult.success()
        return ValidationResult.failure()

    @staticmethod
    def tuple_sizes_match(state: State, lst1: list, lst2: list):
        if len(lst1) != len(lst2):
            return failure_with_exception_added_to(state,
                ex=Exceptions.TupleSizeMismatch,
                msg=f"expected tuple of size {len(lst1)} but got {len(lst2)}")
        return ValidationResult.success()

    @staticmethod
    def correct_argument_types(state: State, name: str, arg_type: Type, given_type: Type) -> ValidationResult:
        if TypeCheck.encountered_prior_failure(state, arg_type, given_type):
            return ValidationResult.failure()

        if not arg_type.equals(given_type, Type.structural_equivalency):
            if TypeCheck.compatible_types(state, TypePair(arg_type, given_type)):
                return ValidationResult.success()
            return failure_with_exception_added_to(state,
                ex=Exceptions.TypeMismatch,
                msg=f"function '{name}' takes '{arg_type}' but was given '{given_type}'")
        return ValidationResult.success()


    @staticmethod
    def instance_exists(state: State, name: str, instance: Instance | Type) -> ValidationResult:
        if instance is None:
            return failure_with_exception_added_to(state,
                ex=Exceptions.UndefinedVariable,
                msg=f"'{name}' is not defined")
        return ValidationResult.success()

    @staticmethod
    def function_exists(state: State, name: str, type: Type, instance: Instance) -> ValidationResult:
        if instance is None:
            return failure_with_exception_added_to(state,
                ex=Exceptions.UndefinedFunction,
                msg=f"'{name}' is not defined for the given argument type '{type}'")
        return ValidationResult.success()

    @staticmethod
    def type_exists(state: State, name: str, type: Type) -> ValidationResult:
        if type is None:
            return failure_with_exception_added_to(state,
                ex=Exceptions.UndefinedType,
                msg=f"'{name}' is not defined")
        return ValidationResult.success()

    @staticmethod
    def name_is_unbound(state: State, name: str) -> ValidationResult:
        if state.get_context().get_type_of_reference(name) is not None:
            return failure_with_exception_added_to(state,
                ex=Exceptions.RedefinedIdentifier,
                msg=f"'{name}' is in use")
        return ValidationResult.success()

    @staticmethod
    def all_names_are_unbound(state: State, names: list[str]) -> ValidationResult:
        results = [Validate.name_is_unbound(state, name) for name in names]
        if any(result.failed() for result in results):
            return ValidationResult.failure()
        return ValidationResult.success()

    @staticmethod
    def has_member_attribute(state: State, type: Type, attribute_name: str) -> ValidationResult:
        if TypeCheck.encountered_prior_failure(state, type):
            return ValidationResult.failure()

        if not type.has_member_attribute_with_name(attribute_name):
            return failure_with_exception_added_to(state,
                ex=Exceptions.MissingAttribute,
                msg=f"'{type}' does not have member attribute '{attribute_name}'")
        return ValidationResult.success()

    @staticmethod
    def castable_types(state: State, type: Type, cast_into_type: Type) -> ValidationResult:
        if TypeCheck.encountered_prior_failure(state, type, cast_into_type):
            return ValidationResult.failure()

        if (type == cast_into_type
                or type.parent_type == cast_into_type
                or cast_into_type.parent_type == type
                or cast_into_type in type.inherits):
            return ValidationResult.success()

        return failure_with_exception_added_to(state,
            ex=Exceptions.CastIncompatibleTypes,
            msg=f"'{type}' cannot be cast into '{cast_into_type}'")

    @staticmethod
    def all_implementations_are_complete(state: State, type: Type):
        for interface in type.inherits:
            Validate.implementation_is_complete(state, type, interface)

    @staticmethod
    def implementation_is_complete(state: State, type: Type, inherited_type: Type) -> ValidationResult:
        if ImplementationCheck.has_required_attributes(state, type, inherited_type):
            return ValidationResult.success()
        return ValidationResult.failure()

    @staticmethod
    def embeddings_dont_conflict(state: State, type: Type):
        conflicts = False
        conflict_map: dict[tuple[str, Type], bool] = {}

        for attribute_pair in type.get_direct_attribute_name_type_pairs():
            conflict_map[attribute_pair] = type

        for embedded_type in type.embeds:
            embedded_type_attribute_pairs = embedded_type.get_all_attribute_name_type_pairs()
            for pair in embedded_type_attribute_pairs:
                conflicting_type = conflict_map.get(pair, None)
                if conflicting_type is not None:
                    conflicts = True
                    state.report_exception(Exceptions.EmbeddedStructCollision(
                        msg=f"attribute '{pair[0]}' received from {embedded_type} conflicts with the same "
                            + f"attribute received from '{conflicting_type}'",
                        line_number=state.get_line_number()))
                else:
                    conflict_map[pair] = embedded_type
        if conflicts:
            return ValidationResult.failure()
        return ValidationResult.success()

    @staticmethod
    def function_has_enough_arguments_to_curry(state: State, argument_type: Type, curried_args_type: Type):
        n_args = len(argument_type.unpack())
        n_curried_args = len(curried_args_type.unpack())
        if n_args < n_curried_args:
            return failure_with_exception_added_to(state,
                ex=Exceptions.TooManyCurriedArguments,
                msg= f"Trying to curry '{n_curried_args}' arguments, but function has argument type '{argument_type}' with '{n_args}' arguments")

        return ValidationResult.success()

    @staticmethod
    def curried_arguments_are_of_the_correct_type(state: State, argument_type: Type, curried_args_type: Type):
        for expected_type, curried_type in zip(argument_type.unpack(), curried_args_type.unpack()):
            if not TypeCheck.type_is_expected(state, expected_type, gotten=curried_type):
                return ValidationResult.failure()

        return ValidationResult.success()

    @staticmethod
    def cannot_be_nil(state: State, nilstate: NilableStatus | list[NilableStatus]) -> ValidationResult:
        if not isinstance(nilstate, list):
            nilstate = [nilstate]

        for ns in nilstate:
            if ns.could_be_nil:
                return failure_with_exception_added_to(state,
                    ex=Exceptions.NilUsage,
                    msg=f"'{ns.name}' is being used but could be nil")
        return ValidationResult.success()

    @staticmethod
    def cast_into_non_nil_valid(state: State, parent: NilableStatus, child: NilableStatus) -> ValidationResult:
        if parent.is_nilable and parent.could_be_nil and not child.is_nilable:
            return failure_with_exception_added_to(state,
                ex=Exceptions.NilCast,
                msg=f"'{parent.name}' could be nil")
        return ValidationResult.success()

    @staticmethod
    def _generate_nil_exception_msg(status: NilableStatus) -> str:
        if status.name:
            return f"'{status.name}' is nilable, and may be nil."
        else:
            return f"something may be nilable in this expession"

    @staticmethod
    def both_operands_are_not_nilable(state: State, left: NilableStatus, right: NilableStatus) -> ValidationResult:
        if any([state.get_abort_signal() in (left, right)]):
            return ValidationResult.failure()

        if left.is_nilable:
            state.report_exception(Exceptions.NilUsage(
                msg=Validate._generate_nil_exception_msg(left),
                line_number=state.get_line_number()))
        if right.is_nilable:
            state.report_exception(Exceptions.NilUsage(
                msg=Validate._generate_nil_exception_msg(right),
                line_number=state.get_line_number()))

        return ValidationResult.success()

    @staticmethod
    def dependency_outlives_self(state: State, memory_name: str, self_shadow: Shadow, dependency_impression: Impression) -> ValidationResult:
        if self_shadow.entity.depth < dependency_impression.shadow.entity.depth:
            return failure_with_exception_added_to(state,
                ex=Exceptions.ObjectLifetime,
                msg=f"'{self_shadow.entity.name}.{memory_name}' may depend on '{dependency_impression.shadow.entity.name}'")

        return ValidationResult.success()

    @staticmethod
    def dependency_outlives_memory(state: State, memory: Memory):
        failed = False
        for impression in memory.impressions:
            if memory.depth < impression.shadow.entity.depth:
                failed = True
                add_exception_to(state,
                    ex=Exceptions.ObjectLifetime,
                    msg=f"'{memory.name}' may depend on '{impression.shadow.entity.name}'")

        if failed:
            return ValidationResult.failure()
        return ValidationResult.success()

    @staticmethod
    def memory_dependencies_havent_moved_away(state: State, memory: Memory, override_name: str = ""):
        failed = False
        for impression in memory.impressions:
            if impression.shadow.entity.moved:
                failed = True
                name = override_name if override_name else memory.name
                add_exception_to(state,
                    ex=Exceptions.ReferenceInvalidation,
                    msg=f"'{name}' may depend on '{impression.shadow.entity.name}' which is moved away.")

        if failed:
            return ValidationResult.failure()
        return ValidationResult.success()

    @staticmethod
    def var_has_expected_dependencies(state: MemoryVisitorState, var_name: str, dependency_names: list[str]) -> ValidationResult:
        var = state.get_memory(var_name)
        var_dependencies = set([i.shadow.entity for i in var.impressions])
        expected_entities = set([state.get_entity(name) for name in dependency_names])
        if var_dependencies != expected_entities:
            var_dependency_names = [entity.name for entity in list(var_dependencies)]
            return failure_with_exception_added_to(state,
                ex=Exceptions.CompilerAssertion,
                msg=f"assertion 'var_has_dependencies' failed: expected [{', '.join(dependency_names)}] but got [{', '.join(var_dependency_names)}]")

        return ValidationResult.success()

    @staticmethod
    def object_has_expected_dependencies(state: MemoryVisitorState, obj_name: str, dependency_dict: dict[Trait, set[str]]) -> ValidationResult:
        obj_shadow = state.get_shadow(state.get_entity(obj_name).uid)
        for key in obj_shadow.personality.memories:
            if key not in dependency_dict:
                return failure_with_exception_added_to(state,
                    ex=Exceptions.CompilerAssertion,
                    msg=f"'{obj_name}' has extra dependency '{key}'")
        for key, expected_names in dependency_dict.items():
            memory = obj_shadow.personality.get_memory(key)
            dependency_names = set([i.shadow.entity.name for i in memory.impressions])
            if dependency_names != expected_names:
                return failure_with_exception_added_to(state,
                    ex=Exceptions.CompilerAssertion,
                    msg=f"assertion 'object_has_expected_dependencies' failed: expected '{obj_name}.{key}' to be [{', '.join(expected_names)}], but got [{', '.join(dependency_names)}]")

        return ValidationResult.success()

    class Bindings:
        @staticmethod
        def are_compatible_for_assignment(state: State, left: BindingCondition, right: BindingCondition) -> ValidationResult:
            result = BindingMechanics.can_be_assigned(left, right)
            if result == True:
                return ValidationResult.success()
            return failure_with_exception_added_to(state,
                ex=Exceptions.IncompatibleBinding,
                msg=result)

        @staticmethod
        def no_split_initialization_after_conditional(state: State, bcs: list[BindingCondition]) -> ValidationResult:
            """
            Split initialization occurs after a conditional if some branches initialize the bindings
            but some don't. It's okay for all branches to initialize (or not to initialize) the binding.
            """

            are_initialized = [bc.condition == Condition.initialized for bc in bcs]
            if all(val == True for val in are_initialized) or all(val == False for val in are_initialized):
                return ValidationResult.success()

            return failure_with_exception_added_to(state,
                ex=Exceptions.PartialConditionalInitialization,
                msg=f"'{bcs[0].name}' may not be initialized in some branches")

        @staticmethod
        def are_all_initialized(state: State, conditions: list[BindingCondition]) -> ValidationResult:
            results = [Validate.Bindings.is_initialized(state, condition) for condition in conditions]
            if all([r.succeeded() for r in results]):
                return ValidationResult.success()
            return ValidationResult.failure()


        @staticmethod
        def is_initialized(state: State, binding_condition: BindingCondition) -> ValidationResult:
            if binding_condition.condition == Condition.under_construction:
                return failure_with_exception_added_to(state,
                    ex=Exceptions.IncompleteInitialization,
                    msg=f"'{binding_condition.name}' is being constructed and cannot be used.")

            if binding_condition.condition == Condition.initialized or binding_condition.condition == Condition.constructed:
                return ValidationResult.success()
            return failure_with_exception_added_to(state,
                ex=Exceptions.UseBeforeInitialize,
                msg=f"{binding_condition.name} is not initialized")

        @staticmethod
        def of_types_is_compatible(state: State, expected: Type, received: Type) -> ValidationResult:
            if BindingMechanics.types_are_binding_compatible(expected, received):
                return ValidationResult.success()
            return failure_with_exception_added_to(state,
                ex=Exceptions.IncompatibleBinding,
                msg=f"Parameter incompatibility expected {expected} received {received}")

        @staticmethod
        def can_be_inferred(state: State, name: str, declared: Binding, received: Binding) -> ValidationResult:
            if BindingMechanics.infer_binding(declared, received) != Binding.error:
                return ValidationResult.success()
            return failure_with_exception_added_to(state,
                ex=Exceptions.IncompatibleBinding,
                msg=BindingMechanics.why_binding_cant_be_inferred(name, declared, received))

        @staticmethod
        def all_struct_members_initialized_after_constructor(state: State, struct_type: Type, binding_condition: BindingConditionForObjectUnderConstruction):
            for attr in struct_type.get_all_component_names():
                if not binding_condition.attribute_is_initialized(attr):
                    add_exception_to(state,
                        ex=Exceptions.IncompleteInitialization,
                        msg=f"'{attr}' is not initialized")
