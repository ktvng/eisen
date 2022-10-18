from seer._typedeclarationwrangler import ModuleWrangler2, TypeDeclarationWrangler, FinalizeProtoWrangler, TypeClassFlowWrangler, FunctionWrangler
from seer._ast_interpreter import AstInterpreter

class Workflow():   
    steps = [
        # create the module structure of the program.
        #   - the module of a node can be accessed by params.asl_get_mod()
        ModuleWrangler2, 

        # add proto types for struct/interfaces, which are the representation 
        # of struct declaration without definition.
        TypeDeclarationWrangler,

        # finalizes the proto types (which moves from declaration to definition)
        # TODO: for now, interfaces can only be implemented from the same module 
        # in which they are defined
        FinalizeProtoWrangler,

        # adds types for and constructs the functions. this also normalizes the
        # (def ...) and (create ...) asls so they have the same child structure,
        # which allows us to process them identically later in the 
        # TypeClassFlowWrangler.
        FunctionWrangler,
        
        # evaluate the flow of types through the program. 
        #   - the typeclass which is flowed through a node can be accessed by
        #     params.asl_get_typeclass()
        TypeClassFlowWrangler,

        # execute the augmented AST via the interpreter.
        AstInterpreter  
    ]