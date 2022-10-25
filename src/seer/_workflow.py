from seer._working import (ModuleWrangler2, TypeDeclarationWrangler, FinalizeProtoInterfaceWrangler, 
    FinalizeProtoStructWrangler, TypeClassFlowWrangler, FunctionWrangler, InitializeNodeData)

from seer._ast_interpreter import AstInterpreter
from seer._exceptionshandler import ExceptionsHandler

# Notes:
# A module is a collection of structs/functions
# A context, properly, is a block with instances defined
# A context may have a parent as a module (as module level functions are available
# for use as instances)
# They are implemented the same.

class Workflow():   
    steps = [
        # initialize the .data attribute for all asls with empty NodeData instances
        InitializeNodeData,

        # create the module structure of the program.
        #   - the module of a node can be accessed by params.asl_get_mod()
        ModuleWrangler2, 

        # add proto types for struct/interfaces, which are the representation 
        # of struct declaration without definition.
        TypeDeclarationWrangler,

        # finalizes the proto types (which moves from declaration to definition)
        # TODO: for now, interfaces can only be implemented from the same module 
        # in which they are defined.
        #
        # we must finalize interfaces first because structs depend on interfaces
        # as they implement interfaces
        FinalizeProtoInterfaceWrangler,
        FinalizeProtoStructWrangler,

        # adds types for and constructs the functions. this also normalizes the
        # (def ...) and (create ...) asls so they have the same child structure,
        # which allows us to process them identically later in the 
        # TypeClassFlowWrangler.
        FunctionWrangler,
        
        # evaluate the flow of types through the program. 
        #   - the typeclass which is flowed through a node can be accessed by
        #     params.get_returned_typeclass()
        TypeClassFlowWrangler,

        ExceptionsHandler,

        # execute the augmented AST via the interpreter.
        AstInterpreter  
    ]