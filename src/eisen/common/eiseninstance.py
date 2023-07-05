from alpaca.concepts import Type, Instance, Context
from alpaca.clr import AST

class EisenInstance(Instance):
    def __init__(self, name: str, type: Type, context: Context, ast: AST,
                 is_ptr=False,
                 is_constructor=False,
                 is_function=False,
                 no_mangle=False,
                 no_lambda=False):
        super().__init__(name, type, context, ast)
        self.is_ptr = is_ptr
        self.is_constructor = is_constructor
        self.is_var = False
        self.is_function = is_function
        self.no_mangle = no_mangle
        self.no_lambda = no_lambda
        self.type: Type = type

    def get_full_name(self):
        if self.no_mangle:
            return self.name

        return (self.context.get_full_name()
            + self.name
            + "___"
            + EisenInstance.get_signature_string(self.type))

    @staticmethod
    def get_signature_string(type: Type):
        if type.classification == Type.classifications.novel:
            return type.name
        elif type.classification == Type.classifications.tuple:
            return "d_" + "_".join([EisenInstance.get_signature_string(t)
                for t in type.components]) + "_b"
        elif type.classification == Type.classifications.function:
            return ("Fd_" + EisenInstance.get_signature_string(type.get_argument_type())
                + "_I_" + EisenInstance.get_signature_string(type.get_return_type())
                + "_b")
        elif type.classification == Type.classifications.struct:
            return type.name
        elif type.classification == Type.classifications.interface:
            return type.name
        elif type.classification == Type.classifications.variant:
            return type.name
        elif type.classification == Type.classifications.parametric:
            return type.name + "q_" + "_".join([EisenInstance.get_signature_string(t)
                for t in type.parametrics]) + "_p"
        else:
            raise Exception(f"signature not implemented for type: {type}")

class EisenFunctionInstance(EisenInstance):
    pass
