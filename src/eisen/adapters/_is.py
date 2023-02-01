from __future__ import annotations

from alpaca.concepts import Type
from alpaca.concepts import TypeFactory
from eisen.adapters.nodeinterface import AbstractNodeInterface
from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.validation.lookupmanager import LookupManager

class Is(AbstractNodeInterface):
    asl_type = "is"
    examples = """
    (is (expr ...) TAG)
    """

    def get_type_name(self) -> str:
        return self.second_child().value

    def get_considered_type(self) -> Type:
        return self.state.get_defined_type(self.get_type_name())

    def _get_name_of_is_function(self) -> str:
        return "is_" + self.get_type_name()

    def _get_type_of_is_function(self) -> Type:
        parent_type = self.get_considered_type().parent_type
        # TODO: function types should not need modules
        return TypeFactory.produce_function_type(parent_type, self.state.get_bool_type(), mod=None)

    def get_is_function_instance(self) -> EisenFunctionInstance:
        LookupManager.resolve_function_reference_type_by_signature(
            name=self._get_name_of_is_function(),
            type=self._get_type_of_is_function(),
            mod=self.state.get_enclosing_module())
