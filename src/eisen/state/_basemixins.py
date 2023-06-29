from __future__ import annotations

from typing import Self

from alpaca.concepts import Module, Context, TypeFactory, Type, AbstractException
from alpaca.utils import Visitor
from alpaca.config import Config
from alpaca.clr import CLRList

from eisen.common.eiseninstance import EisenFunctionInstance
from eisen.common.nodedata import NodeData
from eisen.common.restriction import PrimitiveRestriction, NoRestriction
from eisen.validation.lookupmanager import LookupManager

class BaseMixins():
    def report_exception(self, e: AbstractException):
        """
        Add a new compile time exception to be displayed. Unless the critical exception flag is set,
        reporting an exception will not stop the compiler process.

        :param e: An instance any child class of AbstractException to be reported.
        :type e: AbstractException
        """
        self.exceptions.append(e)


    def __str__(self) -> str:
        return self.asl.type

    def inspect(self) -> str:
        if isinstance(self.asl, CLRList):
            instances = None
            try:
                instances = self.get_instances()
            except:
                pass

            instance_strs = ("N/A" if instances is None
                else ", ".join([str(i) for i in instances]))

            children_strs = []
            for child in self.asl:
                if isinstance(child, CLRList):
                    children_strs.append(f"({child.type} )")
                else:
                    children_strs.append(str(child))
            asl_info_str = f"({self.asl.type} {' '.join(children_strs)})"
            if len(asl_info_str) > 64:
                asl_info_str = asl_info_str[:64] + "..."

            type = "N/A"
            try:
                type = self.get_node_data().returned_type
            except:
                pass

            return f"""
    INSPECT ==================================================
    ----------------------------------------------------------
    ASL: {asl_info_str}
    {self.asl}

    ----------------------------------------------------------
    Module: {self.mod.name} {self.mod.type}
    {self.mod}

    Type: {type}
    Instances: {instance_strs}
    """
        else:
            return f"""
    INSPECT ==================================================
    Token: {self.asl}
    """


    def get_config(self) -> Config:
        """
        Get the language configuration.

        :return: The config which defines the language specifications.
        :rtype: Config
        """
        return self.config


    def get_asl(self) -> CLRList:
        """
        Get the abstract syntax list (ASL) which is currently being evaluated.

        :return: The current CLRList.
        :rtype: CLRList
        """
        return self.asl


    def get_txt(self) -> str:
        """
        Get the full text supplied to be compiled.

        :return: The full text as a string.
        :rtype: CLRList
        """
        return self.txt


    def get_context(self) -> Context | Module:
        """
        Get the context which encloses the current ASL. Note that context may be both the module
        itself, or the function/local context (i.e. if/while context).

        :return: The context or module which is a subclass of NestedContainer
        :rtype: Context | Module
        """
        return self.context


    def get_enclosing_module(self) -> Module:
        """
        Get the module which encloses the current ASL.

        :return: The enclosing module.
        :rtype: Module
        """

        return self.mod


    def get_line_number(self) -> int:
        """
        Get the line number within the source code for the ASL currently being evaluated

        :return: The integer line number.
        :rtype: int
        """
        return self.asl.line_number


    def get_bool_type(self) -> Type:
        """
        Get the type used for boolean values in Eisen.

        :return: The boolean type.
        :rtype: Type
        """
        return TypeFactory.produce_novel_type("bool").with_restriction(PrimitiveRestriction())


    def get_void_type(self) -> Type:
        """
        Get the type used to represent void values.

        :return: The void type.
        :rtype: Type
        """
        return TypeFactory.produce_novel_type("void").with_restriction(NoRestriction())

    def get_abort_signal(self) -> Type:
        """
        Get the type used to represent an abort signal. If the type checker fails a given step,
        the abort type can be returned. This will allow the type checker to continue to evaluate
        the remaining program logic for components that do not depend on the type returned by the
        failed step.

        :return: The abort type.
        :rtype: Type
        """
        return TypeFactory.produce_novel_type("_abort_")


    def first_child(self) -> CLRList:
        """
        Get the first child of the current ASL.

        :return: The first child.
        :rtype: CLRList
        """
        return self.asl.first()


    def second_child(self) -> CLRList:
        """
        Get the second child of the current ASL.

        :return: The second child.
        :rtype: CLRList
        """
        return self.asl.second()


    def third_child(self) -> CLRList:
        """
        Get the third child of the current ASL.

        :return: The third child.
        :rtype: CLRList
        """
        return self.asl.third()


    def get_child_asls(self) -> list[CLRList]:
        """
        Get a list of the children of this ASL, in the order of that they appear, filtering out any
        children which are not ASLs themselves. No child tokens will appear.

        :return: The list of children ASLs.
        :rtype: list[CLRList]
        """
        return [child for child in self.asl if isinstance(child, CLRList)]


    def get_all_children(self) -> list[CLRList]:
        """
        Get a list of all children of this ASL in the order that they appear, including any token
        children

        :return: The list of children.
        :rtype: list[CLRList]
        """
        return self.asl._list


    def but_with_first_child(self) -> Self:
        """
        Return a new State object with the same properties as this current State, except that the
        ASL is changed to be the first child of this State's ASL.

        :return: A new State object with the ASL changed.
        :rtype: Self
        """
        return self.but_with(asl=self.first_child())


    def but_with_second_child(self) -> Self:
        """
        Return a new State object with the same properties as this current State, except that the
        ASL is change to be the second child of this State's ASL.

        :return: A new State object with the ASL changed.
        :rtype: Self
        """
        return self.but_with(asl=self.second_child())


    def apply_fn_to_all_children(self, fn: Visitor):
        """
        Apply the given Visitor function to all children of the ASL at State. Returns nothing

        :param fn: The Visitor function to apply
        :type fn: Visitor
        """
        for child in self.asl:
            fn.apply(self.but_with(asl=child))


    def get_node_data(self) -> NodeData:
        """
        Get the NodeData object which contains enriched information about a given ASL that is
        progressively filled during the compilation.

        :return: The NodeData object stored at this ASL.
        :rtype: NodeData
        """
        return self.asl.data


    def get_defined_type(self, name: str) -> Type:
        """
        Lookup a Type object by it's given name. This uses the current context/module to resolve
        the Type. Non-existance of a the type does not mean the type has not been defined, but
        only that the type is not defined in the current context/module and it's associated lookup
        context/module(s).

        :param name: The name given to the Type.
        :type name: str
        :return: The object representing the Type.
        :rtype: Type
        """
        return LookupManager.resolve_defined_type(name, self.get_enclosing_module())


    def create_block_context(self) -> Context:
        """
        Create a new Context for a block of code, and initialize the parent context structure
        properly so that the new Context is a child of the current Context.

        :return: A new Context instance.
        :rtype: Context
        """
        return Context(
            name="block",
            parent=self.get_context())


    def create_isolated_context(self) -> Context:
        """
        Create a new Context without a parent context.

        :return: A new Context instance.
        :rtype: Context
        """
        return Context(name="isolated", parent=None)


    def is_asl(self) -> bool:
        """
        Returns whether or not the current State is at an ASL (vs a terminal, CLRToken)

        :return: True if this state is visiting an ASL.
        :rtype: bool
        """
        return isinstance(self.asl, CLRList)


    def get_exceptions(self) -> list[AbstractException]:
        """
        Return a list of exceptions which ave been thrown over the course of compilation.

        :return: The list of exceptions.
        :rtype: list[AbstractException]
        """
        return self.exceptions

    def add_builtin_function(self, instance: EisenFunctionInstance) -> None:
        self.builtin_functions[instance.name + instance.type.get_uuid_str()] = instance

    def get_builtin_function(self, name: str, type: Type) -> EisenFunctionInstance | None:
        self.builtin_functions.get(name + type.get_uuid_str(), None)

    def get_global_module(self) -> Module:
        return self.global_module

    def get_all_builtins(self) -> list[EisenFunctionInstance]:
        return list(self.builtin_functions.values())
