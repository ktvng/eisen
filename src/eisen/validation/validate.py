from __future__ import annotations

from alpaca.concepts import TypeClass, Context
from eisen.common import EisenInstance, Module
from eisen.common.state import State
from eisen.common.exceptions import Exceptions
from eisen.common.restriction import Restriction


class ValidationResult():
    def __init__(self, result: bool, return_obj: TypeClass | EisenInstance):
        self.result = result
        self.return_obj = return_obj

    def failed(self) -> bool:
        return not self.result

    def get_failure_type(self) -> TypeClass:
        return self.return_obj

    def get_found_instance(self) -> EisenInstance:
        return self.return_obj


################################################################################
# performs the actual validations
class Validate:
    @classmethod
    def _abort_signal(cls, state: State) -> ValidationResult:
        return ValidationResult(result=False, return_obj=state.abort_signal)

    @classmethod
    def _success(cls, return_obj=None) -> ValidationResult:
        return ValidationResult(result=True, return_obj=return_obj)

    @classmethod
    def equivalent_types(cls, state: State, type1: TypeClass, type2: TypeClass) -> ValidationResult:
        if any([state.abort_signal in (type1, type2)]):
            return Validate._abort_signal(state) 

        if type1 != type2:
            state.report_exception(Exceptions.TypeMismatch(
                msg=f"'{type1}' != '{type2}'",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state) 
        return Validate._success(type1)


    @classmethod
    def tuple_sizes_match(cls, state: State, lst1: list, lst2: list):
        if len(lst1) != len(lst2):
            state.report_exception(Exceptions.TupleSizeMismatch(
                msg=f"expected tuple of size {len(lst1)} but got {len(lst2)}",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state)
        return Validate._success()


    @classmethod
    def correct_argument_types(cls, state: State, name: str, fn_type: TypeClass, given_type: TypeClass) -> ValidationResult:
        if any([state.abort_signal in (fn_type, given_type)]):
            return Validate._abort_signal(state) 

        if fn_type != given_type:
            # if the given_type is a struct, we have another change to succeed if 
            # the struct embeds the expected fn_type
            if given_type.classification == TypeClass.classifications.struct:
                if fn_type not in given_type.embeds:
                    state.report_exception(Exceptions.TypeMismatch(
                        msg=f"function '{name}' takes '{fn_type}' but was given '{given_type}'",
                        line_number=state.get_line_number()))
                    return Validate._abort_signal(state)  
                return Validate._success(fn_type)
            
            state.report_exception(Exceptions.TypeMismatch(
                msg=f"function '{name}' takes '{fn_type}' but was given '{given_type}'",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state) 
        return Validate._success(fn_type)


    @classmethod
    def instance_exists(cls, state: State) -> ValidationResult:
        name = state.first_child().value
        instance = state.context.get_instance_by_name(name)
        if instance is None:
            state.report_exception(Exceptions.UndefinedVariable(
                msg=f"'{name}' is not defined",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state) 
        return Validate._success(return_obj=instance)


    @classmethod
    def function_instance_exists_in_local_context(cls, state: State) -> ValidationResult:
        return cls._instance_exists_in_container(
            state.first_child().value,
            state.context,
            state)


    @classmethod
    def function_instance_exists_in_module(cls, state: State) -> ValidationResult:
        return cls._instance_exists_in_container(
            state.first_child().value,
            state.get_enclosing_module(),
            state)

    @classmethod
    def _instance_exists_in_container(cls, name: str, container: Context | Module, state: State) -> ValidationResult:
        instance = container.get_instance_by_name(name)
        if instance is None:
            state.report_exception(Exceptions.UndefinedFunction(
                msg=f"'{name}' is not defined",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state) 
        return Validate._success(return_obj=instance)
    
    @classmethod
    def name_is_unbound(cls, state: State, name: str) -> ValidationResult:
        if state.context.find_instance(name) is not None:
            state.report_exception(Exceptions.RedefinedIdentifier(
                msg=f"'{name}' is in use",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)

    @classmethod
    def all_names_are_unbound(cls, state: State, names: list[str]) -> ValidationResult:
        results = [Validate.name_is_unbound(state, name) for name in names]
        if any(result.failed() for result in results):
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)

    @classmethod
    def has_member_attribute(cls, state: State, typeclass: TypeClass, attribute_name: str) -> ValidationResult:
        if not typeclass.has_member_attribute_with_name(attribute_name):
            state.report_exception(Exceptions.MissingAttribute(
                f"'{typeclass}' does not have member attribute '{attribute_name}'",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)

    
    @classmethod
    def castable_types(cls, state: State, type: TypeClass, cast_into_type: TypeClass) -> ValidationResult:
        if any([state.abort_signal in (type, cast_into_type)]):
            return Validate._abort_signal(state) 

        if cast_into_type not in type.inherits:
            state.report_exception(Exceptions.CastIncompatibleTypes(
                msg=f"'{type}' cannot be cast into '{cast_into_type}'",
                line_number=state.get_line_number()))
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)

    @classmethod
    def all_implementations_are_complete(cls, state: State, type: TypeClass):
        for interface in type.inherits:
            cls.implementation_is_complete(state, type, interface)

    @classmethod
    def implementation_is_complete(cls, state: State, type: TypeClass, inherited_type: TypeClass) -> ValidationResult:
        encountered_exception = False
        for name, required_attribute_type in zip(inherited_type.component_names, inherited_type.components):
            if type.has_member_attribute_with_name(name):
                attribute_type = type.get_member_attribute_by_name(name)
                if attribute_type != required_attribute_type:
                    encountered_exception = True
                    state.report_exception(Exceptions.AttributeMismatch(
                        msg=f"'{type}' has attribute '{name}' of '{attribute_type}', but '{required_attribute_type}' is required to inherit '{inherited_type}'",
                        line_number=state.get_line_number()))
            else:
                encountered_exception = True
                state.report_exception(Exceptions.MissingAttribute(
                    msg=f"'{type}' is missing attribute '{name}' required to inherit '{inherited_type}'",
                    line_number=state.get_line_number()))

        if encountered_exception:
            return Validate._abort_signal(state)
        return Validate._success()

    
    @classmethod
    def embeddings_dont_conflict(cls, state: State, typeclass: TypeClass):
        conflicts = False
        conflict_map: dict[tuple[str, TypeClass], bool] = {}
        
        for attribute_pair in typeclass.get_direct_attribute_name_type_pairs():
            conflict_map[attribute_pair] = typeclass

        for embedded_type in typeclass.embeds:
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
            return Validate._abort_signal(state)
        return Validate._success()


    @classmethod
    def assignment_restrictions_met(cls, state: State, left_restriction: Restriction, right_restriction: Restriction):
        # print(state.asl)
        is_assignable, error_msg = left_restriction.assignable_to(right_restriction)
        if not is_assignable:
            state.report_exception(Exceptions.MemoryAssignment(
                # TODO, figure out how to pass the name of the variable here
                msg=error_msg,
                line_number=state.get_line_number()))
            return Validate._abort_signal(state)
        return Validate._success()

    @classmethod
    def parameter_assignment_restrictions_met(cls, state: State, left_restriction: Restriction, right_restriction: Restriction):
        # print(state.asl)
        is_assignable, error_msg = left_restriction.assignable_to(right_restriction)
        if not is_assignable:
            state.report_exception(Exceptions.MemoryAssignment(
                # TODO, figure out how to pass the name of the variable here
                msg=error_msg,
                line_number=state.get_line_number()))
            return Validate._abort_signal(state)
        return Validate._success()

         