from seer._typedeclarationwrangler import ModuleWrangler2, TypeDeclarationWrangler, FinalizeProtoWrangler, TypeFlowWrangler2, FunctionWrangler
from seer._ast_interpreter import AstInterpreter
from seer._flattener import Flattener

class Workflow():   
    steps = [
        # create the module structure of the program
        #   - the module of a node can be accessed by params.asl_get_mod()
        ModuleWrangler2, 

        # add proto types for struct/interfaces
        TypeDeclarationWrangler,

        # finalizes the proto types
        # TODO: for now, interfaces can only be implemented from the same module 
        # in which they are defined
        FinalizeProtoWrangler,

        # adds types for and constructs the functions
        FunctionWrangler,
        
        # evaluate the flow of types through the program
        TypeFlowWrangler2,

        AstInterpreter
        ]