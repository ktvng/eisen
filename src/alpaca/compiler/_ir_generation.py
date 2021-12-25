from __future__ import annotations

from alpaca.compiler._context import Context
from alpaca.compiler._options import Options
from alpaca.compiler._object import Object
from alpaca.compiler._intermediatestate import RecursiveDescentIntermediateState
from alpaca.asts import ASTNode

class IRGenerationProcedure():
    matches = []

    @classmethod
    def precompile(cls, 
            node : ASTNode, 
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:
        """
        Return a list of child nodes and contexts to use when compiling each child node, as 
        well as a dict of args which will be passed to the compile method.

        Args:
            node (ASTNode): Node to precompile
            cx (Context): Context to precompile node over.

        Returns:
            [type]: [description]
        """
        rdstate = RecursiveDescentIntermediateState()
        for child in node.children:
            rdstate.add_child(cx, child)

        return rdstate

    @classmethod
    def validate_precompile(cls,
            node : ASTNode,
            cx : Context,
            options : Options=None
            ) -> RecursiveDescentIntermediateState:
        
        # start
        rdstate = RecursiveDescentIntermediateState()
        for child in node.children:
            rdstate.add_child(cx, child)
        
        return rdstate
        
    @classmethod
    def validate_compile(cls,
            node : ASTNode,
            cx : Context,
            args : dict,
            options : Options=None) -> list[Object]:

        # start 
        return []

    @classmethod
    def compile(cls, 
            node : ASTNode, 
            cx : Context, 
            args : dict, 
            options : Options=None) -> list[Object]:
        # start
        return []
    