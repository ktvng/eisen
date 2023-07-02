from __future__ import annotations

from dataclasses import dataclass

from alpaca.concepts import Type, AbstractException
from eisen.common.eiseninstance import EisenInstance
from eisen.common.exceptions import Exceptions
from eisen.common.usagestatus import UsageStatus
from eisen.common.initialization import Initializations
from eisen.state.basestate import BaseState as State
from eisen.validation.nilablestatus import NilableStatus

@dataclass
class ValidationResult:
    result: bool

    def failed(self) -> bool:
        return not self.result

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
        return state.get_abort_signal() in args

    @staticmethod
    def flatten_to_type_pairs(left: Type, right: Type) -> list[TypePair]:
        if left.is_tuple():
            return [TypePair(left=l, right=r) for l, r in zip(left.components, right.components)]
        return [TypePair(left=left, right=right)]

    @staticmethod
    def type_pair_is_nil_compatible(state: State, type_pair: TypePair) -> bool:
        if not type_pair.left.restriction.is_nilable() and type_pair.right.is_nil():
            add_exception_to(state,
                ex=Exceptions.NilAssignment,
                msg=f"cannot assign nil to non-nilable type '{type_pair.left}'")
            return False
        return True

    @staticmethod
    def equivalent_types(state: State, type_pair: TypePair) -> bool:
        # 'nil' is considered equivalent to all nilable types
        if type_pair.left.restriction.is_nilable() and type_pair.right.is_nil():
            return True

        if type_pair.left != type_pair.right:
            add_exception_to(state,
                ex=Exceptions.TypeMismatch,
                msg=f"'{type_pair.left}' != '{type_pair.right}'")
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

        if arg_type != given_type:
            # if the given_type is a struct, we have another change to succeed if
            # the struct embeds the expected fn_type
            if given_type.classification == Type.classifications.struct:
                if arg_type not in given_type.embeds:
                    return failure_with_exception_added_to(state,
                        ex=Exceptions.TypeMismatch,
                        msg=f"function '{name}' takes '{arg_type}' but was given '{given_type}'")
                return ValidationResult.success()

            return failure_with_exception_added_to(state,
                ex=Exceptions.TypeMismatch,
                msg=f"function '{name}' takes '{arg_type}' but was given '{given_type}'")
        return ValidationResult.success()


    @staticmethod
    def instance_exists(state: State, name: str, instance: EisenInstance | Type) -> ValidationResult:
        if instance is None:
            return failure_with_exception_added_to(state,
                ex=Exceptions.UndefinedVariable,
                msg=f"'{name}' is not defined")
        return ValidationResult.success()

    @staticmethod
    def type_exists(state: State, name: str, type: Type) -> ValidationResult:
        if type is None:
            return failure_with_exception_added_to(state,
                ex=Exceptions.UnderfinedType,
                msg=f"'{name}' is not defined")
        return ValidationResult.success()

    @staticmethod
    def name_is_unbound(state: State, name: str) -> ValidationResult:
        if state.get_context().get_reference_type(name) is not None:
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
    def assignment_restrictions_met(state: State, left: UsageStatus, right: UsageStatus):
        if left.modifies_val_state():
            return failure_with_exception_added_to(state,
                ex=Exceptions.ImmutableVal,
                msg=f"cannot modify val state")

        result = left.assignable_to(right)
        if result.failed():
            return failure_with_exception_added_to(state,
                ex=result.ex_type,
                msg=result.msg)
        if right.is_under_construction():
            return failure_with_exception_added_to(state,
                ex=Exceptions.IncompleteInitialization,
                msg=f"'{right.name}' is being constructed, cannot be assigned")

        return ValidationResult.success()

    @staticmethod
    def parameter_assignment_restrictions_met(state: State, argument_requires: UsageStatus, given: UsageStatus):
        # print(state.asl)
        result = argument_requires.assignable_to(given)
        if result.failed():
            return failure_with_exception_added_to(state,
                ex=result.ex_type,
                msg=result.msg)
        return ValidationResult.success()

    @staticmethod
    def status_is_initialized(state: State, status: UsageStatus) -> ValidationResult:
        if status.is_aborted_status():
            return ValidationResult.failure()

        if status.is_under_construction():
            return failure_with_exception_added_to(state,
                ex=Exceptions.IncompleteInitialization,
                msg=f"'{status.name}' is being constructed and cannot be used.")

        if status.initialization != Initializations.Initialized:
            return failure_with_exception_added_to(state,
                ex=Exceptions.UseBeforeInitialize,
                msg=f"{status.name} is not initialized")
        return ValidationResult.success()

    @staticmethod
    def attribute_is_initialized(state: State, attr: str, status: UsageStatus) -> ValidationResult:
        if not status.get_initialization_of_attribute(attr) == Initializations.Initialized:
            return failure_with_exception_added_to(state,
                ex=Exceptions.IncompleteInitialization,
                msg=f"'{attr}' is not initialized")
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
