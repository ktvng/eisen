from eisen.validation.modulevisitor import ModuleVisitor
from eisen.validation.flowvisitor import FlowVisitor
from eisen.validation.functionvisitor import FunctionVisitor
from eisen.validation.permissionsvisitor import PermissionsVisitor
from eisen.validation.declarationvisitor import DeclarationVisitor
from eisen.validation.finalizationvisitor import InterfaceFinalizationVisitor, StructFinalizationVisitor
from eisen.validation.initalizer import Initializer
from eisen.common.exceptionshandler import ExceptionsHandler

# Notes:
# A module is a collection of structs/functions
# A context, properly, is a block with instances defined
# A context may have a parent as a module (as module level functions are available
# for use as instances)
# They are implemented the same.

class Workflow():   
    steps = [
        # initialize the .data attribute for all asls with empty NodeData instances
        Initializer,

        # create the module structure of the program.
        #   - the module of a node can be accessed by params.asl_get_mod()
        ModuleVisitor, 

        # add proto types for struct/interfaces, which are the representation 
        # of struct declaration without definition.
        DeclarationVisitor,

        # finalizes the proto types (which moves from declaration to definition)
        # TODO: for now, interfaces can only be implemented from the same module 
        # in which they are defined.
        #
        # we must finalize interfaces first because structs depend on interfaces
        # as they implement interfaces
        InterfaceFinalizationVisitor,
        StructFinalizationVisitor,

        # handle execptions thrown due to interfaces/embeddings
        ExceptionsHandler,

        # adds types for and constructs the functions. this also normalizes the
        # (def ...) and (create ...) asls so they have the same child structure,
        # which allows us to process them identically later in the 
        # TypeClassFlowWrangler.
        FunctionVisitor,
        
        # evaluate the flow of types through the program. 
        #   - the type which is flowed through a node can be accessed by
        #     params.get_returned_type()
        FlowVisitor,
        ExceptionsHandler,

        # this handles restrictions based on let/var/val differences
        PermissionsVisitor,
        ExceptionsHandler,

        # note: def, create, fn, ref, ilet need instances!!
    ]