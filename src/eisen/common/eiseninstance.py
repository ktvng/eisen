from alpaca.concepts import Type, Instance, Context
from alpaca.clr import CLRList

class EisenInstance(Instance):
    def __init__(self, name: str, type: Type, context: Context, asl: CLRList,
                 is_ptr=False,
                 is_constructor=False,
                 is_function=False):
        super().__init__(name, type, context, asl)
        self.is_ptr = is_ptr
        self.is_constructor = is_constructor
        self.is_var = False
        self.is_function = is_function
        self.type: Type = type

    def get_full_name(self):
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
        else:
            raise Exception(f"signature not implemented for type: {type}")

class EisenFunctionInstance(EisenInstance):
    pass
