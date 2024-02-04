from __future__ import annotations

from typing import Self

from alpaca.concepts import Module, Context, Type, AbstractException
from alpaca.utils import Visitor
from alpaca.config import Config
from alpaca.clr import AST

from eisen.common.eiseninstance import FunctionInstance
from eisen.common.nodedata import NodeData
from eisen.validation.lookupmanager import LookupManager
from eisen.common.typefactory import TypeFactory

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
        return self.ast.type

    def inspect(self) -> str:
        if isinstance(self.ast, AST):
            instances = None
            try:
                instances = self.get_instances()
            except:
                pass

            instance_strs = ("N/A" if instances is None
                else ", ".join([str(i) for i in instances]))

            children_strs = []
            for child in self.ast:
                if isinstance(child, AST):
                    children_strs.append(f"({child.type} )")
                else:
                    children_strs.append(str(child))
            ast_info_str = f"({self.ast.type} {' '.join(children_strs)})"
            if len(ast_info_str) > 64:
                ast_info_str = ast_info_str[:64] + "..."

            type = "N/A"
            try:
                type = self.get_node_data().returned_type
            except:
                pass

            return f"""
    INSPECT ==================================================
    ----------------------------------------------------------
    ast: {ast_info_str}
    {self.ast}

    ----------------------------------------------------------
    Module: {self.mod.name} {self.mod.type}
    {self.mod}

    Type: {type}
    Instances: {instance_strs}
    """
        else:
            return f"""
    INSPECT ==================================================
    Token: {self.ast}
    """


    def get_config(self) -> Config:
        """
        Get the language configuration.

        :return: The config which defines the language specifications.
        :rtype: Config
        """
        return self.config


    def get_ast(self) -> AST:
        """
        Get the abstract syntax list (ast) which is currently being evaluated.

        :return: The current CLRList.
        :rtype: CLRList
        """
        return self.ast


    def get_ast_type(self) -> str:
        return self.ast.type


    def get_txt(self) -> str:
        """
        Get the full text supplied to be compiled.

        :return: The full text as a string.
        :rtype: CLRList
        """
        return self.txt


    def get_context(self) -> Context | Module:
        """
        Get the context which encloses the current ast. Note that context may be both the module
        itself, or the function/local context (i.e. if/while context).

        :return: The context or module which is a subclass of NestedContainer
        :rtype: Context | Module
        """
        return self.context


    def get_enclosing_module(self) -> Module:
        """
        Get the module which encloses the current ast.

        :return: The enclosing module.
        :rtype: Module
        """

        return self.mod


    def get_line_number(self) -> int:
        """
        Get the line number within the source code for the ast currently being evaluated

        :return: The integer line number.
        :rtype: int
        """
        return self.ast.line_number


    def get_bool_type(self) -> Type:
        """
        Get the type used for boolean values in Eisen.

        :return: The boolean type.
        :rtype: Type
        """
        return TypeFactory.produce_novel_type("bool")


    def get_void_type(self) -> Type:
        """
        Get the type used to represent void values.

        :return: The void type.
        :rtype: Type
        """
        return TypeFactory.produce_void_type()

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


    def first_child(self) -> AST:
        """
        Get the first child of the current ast.

        :return: The first child.
        :rtype: CLRList
        """
        return self.ast.first()


    def second_child(self) -> AST:
        """
        Get the second child of the current ast.

        :return: The second child.
        :rtype: CLRList
        """
        return self.ast.second()


    def third_child(self) -> AST:
        """
        Get the third child of the current ast.

        :return: The third child.
        :rtype: CLRList
        """
        return self.ast.third()


    def get_child_asts(self) -> list[AST]:
        """
        Get a list of the children of this ast, in the order of that they appear, filtering out any
        children which are not asts themselves. No child tokens will appear.

        :return: The list of children asts.
        :rtype: list[CLRList]
        """
        return [child for child in self.ast if isinstance(child, AST)]


    def get_all_children(self) -> list[AST]:
        """
        Get a list of all children of this ast in the order that they appear, including any token
        children

        :return: The list of children.
        :rtype: list[CLRList]
        """
        return self.ast._list


    def but_with_first_child(self) -> Self:
        """
        Return a new State object with the same properties as this current State, except that the
        ast is changed to be the first child of this State's ast.

        :return: A new State object with the ast changed.
        :rtype: Self
        """
        return self.but_with(ast=self.first_child())


    def but_with_second_child(self) -> Self:
        """
        Return a new State object with the same properties as this current State, except that the
        ast is change to be the second child of this State's ast.

        :return: A new State object with the ast changed.
        :rtype: Self
        """
        return self.but_with(ast=self.second_child())


    def apply_fn_to_all_children(self, fn: Visitor):
        """
        Apply the given Visitor function to all children of the ast at State. Returns nothing

        :param fn: The Visitor function to apply
        :type fn: Visitor
        """
        for child in self.ast:
            fn.apply(self.but_with(ast=child))

    def apply_fn_to_all_child_asts(self, fn: Visitor):
        """
        Apply the given Visitor function to all children which are not ASTTokens of the ast at State.
        Returns nothing

        :param fn: The Visitor function to apply
        :type fn: Visitor
        """
        for child in self.ast:
            if isinstance(child, AST):
                fn.apply(self.but_with(ast=child))

    def get_node_data(self) -> NodeData:
        """
        Get the NodeData object which contains enriched information about a given ast that is
        progressively filled during the compilation.

        :return: The NodeData object stored at this ast.
        :rtype: NodeData
        """
        return self.ast.data


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
        return Context(name="isolated", parent=self.get_enclosing_module())


    def is_ast(self) -> bool:
        """
        Returns whether or not the current State is at an ast (vs a terminal, CLRToken)

        :return: True if this state is visiting an ast.
        :rtype: bool
        """
        return isinstance(self.ast, AST)


    def get_exceptions(self) -> list[AbstractException]:
        """
        Return a list of exceptions which ave been thrown over the course of compilation.

        :return: The list of exceptions.
        :rtype: list[AbstractException]
        """
        return self.exceptions

    def add_builtin_function(self, instance: FunctionInstance) -> None:
        self.builtin_functions[instance.name + instance.type.get_uuid_str()] = instance

    def get_builtin_function(self, name: str, type: Type) -> FunctionInstance | None:
        self.builtin_functions.get(name + type.get_uuid_str(), None)

    def get_global_module(self) -> Module:
        return self.global_module

    def get_all_builtins(self) -> list[FunctionInstance]:
        return list(self.builtin_functions.values())
