from __future__ import annotations

from compiler._context import Context
from compiler._options import Options
from compiler._object import Object
from compiler._intermediatestate import RecursiveDescentIntermediateState
from ast import AstNode

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
    