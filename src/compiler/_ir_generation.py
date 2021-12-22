from __future__ import annotations

from ._context import Context
from ._options import Options
from ._object import Object
from astnode import AstNode

class RecursiveDescentIntermediateState():
    def __init__(self):
        self._child_paths : list[tuple[Context, AstNode]] = []
        self.args = {}

    def add_child(self, cx : Context, node : AstNode):
        self._child_paths.append((cx, node))

    def add_arg(self, name : str, val):
        self.args[name] = val

    def get_paths(self) -> list[tuple[Context, AstNode]]:
        return self._child_paths

class IRGenerationProcedure():
    matches = []

    @classmethod
    def precompile(cls, 
            node : AstNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:
        """
        Return a list of child nodes and contexts to use when compiling each child node, as 
        well as a dict of args which will be passed to the compile method.

        Args:
            node (AstNode): Node to precompile
            cx (Context): Context to precompile node over.

        Returns:
            [type]: [description]
        """
        rdstate = RecursiveDescentIntermediateState()
        for child in node.vals:
            rdstate.add_child(cx, child)

        return rdstate

    @classmethod
    def validate_precompile(cls,
            node : AstNode,
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:
        
        # start
        rdstate = RecursiveDescentIntermediateState()
        for child in node.vals:
            rdstate.add_child(cx, child)
        
        return rdstate
        
    @classmethod
    def validate_compile(cls,
            node : AstNode,
            cx : Context,
            args : dict,
            options : Options=None) -> list[Object]:

        # start 
        return []

    @classmethod
    def compile(cls, 
            node : AstNode, 
            cx : Context, 
            args : dict, 
            options : Options=None) -> list[Object]:
        # start
        return []
    