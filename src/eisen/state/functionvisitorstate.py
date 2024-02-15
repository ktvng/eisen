from __future__ import annotations
from dataclasses import dataclass

from alpaca.concepts import Module, Context
from alpaca.clr import AST

from eisen.common.eiseninstance import Instance
from eisen.common.traits import TraitImplementation, TraitImplDetailsForFunctionVisitor
from eisen.state.basestate import BaseState
from eisen.typecheck.typeparser import TypeParser

class FunctionVisitorState(BaseState):
    """
    This is state that is used by the FunctionVisitor when parsing an ast from the head. It extends
    BaseState to include the 'struct_name' attribute which may be recursively passed down during
    compilation.
    """
    def __init__(self, **kwargs):
        self._init(**kwargs)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            struct_name: str = None,
            trait_impl_details: TraitImplDetailsForFunctionVisitor = None
            ) -> FunctionVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            struct_name=struct_name,
            trait_impl_details=trait_impl_details)


    @staticmethod
    def create_from_basestate(state: BaseState):
        return FunctionVisitorState(**state._get(),
                                    type_parser=TypeParser(),
                                    struct_name="",
                                    trait_impl_details=None)

    def get_trait_impl_details(self) -> TraitImplDetailsForFunctionVisitor | None:
        """
        Get the details about the trait/implementing struct, which is not None for any context
        that occurs inside a (trait_def ...) AST
        """
        return self.trait_impl_details

    def get_struct_name(self) -> str:
        """
        Gets the name of a struct if the current State exists inside a struct definition within the
        Eisen source code being compiled.

        :return: The name of the struct.
        :rtype: str
        """
        return self.struct_name

    def add_function_instance_to_module(self, instance: Instance):
        """
        A defined function must be parsed into a FunctionInstance and added to the module where it
        was defined.

        :param instance: The EisenInstance created for some Eisen source code defined function.
        :type instance: EisenInstance
        """
        self.get_enclosing_module().add_function_instance(instance)

    def get_type_parser(self) -> TypeParser:
        return self.type_parser

    def add_trait_implementation(self, impl: TraitImplementation):
        self.get_enclosing_module().add_obj("trait_implementations", impl.get_key_for_this(), impl)

    def this_is_trait_implementation(self) -> bool:
        return self.trait_impl_details is not None
