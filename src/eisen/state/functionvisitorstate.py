from __future__ import annotations

from alpaca.concepts import Module, Context
from alpaca.clr import CLRList

from eisen.common.eiseninstance import EisenInstance
from eisen.state.basestate import BaseState


class FunctionVisitorState(BaseState):
    """
    This is state that is used by the FunctionVisitor when parsing an ASL from the head. It extends
    BaseState to include the 'struct_name' attribute which may be recursively passed down during
    compilation.
    """
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            struct_name: str = None
            ) -> FunctionVisitorState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            struct_name=struct_name,)


    @staticmethod
    def create_from_basestate(state: BaseState):
        return FunctionVisitorState(**state._get(), struct_name="")


    def get_struct_name(self) -> str:
        """
        Gets the name of a struct if the current State exists inside a struct definition within the
        Eisen source code being compiled.

        :return: The name of the struct.
        :rtype: str
        """
        return self.struct_name


    def get_variant_name(self) -> str:
        """
        Gets the name of the variant if the current State exists inside a variant definition within
        the Eisen source code being compiled.

        :return: The name of the variant.
        :rtype: str
        """
        return self.struct_name


    def add_function_instance_to_module(self, instance: EisenInstance):
        """
        A defined function must be parsed into a FunctionInstance and added to the module where it
        was defined.

        :param instance: The EisenInstance created for some Eisen source code defined function.
        :type instance: EisenInstance
        """
        self.get_enclosing_module().add_function_instance(instance)
