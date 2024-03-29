from dataclasses import dataclass
from alpaca.concepts import Type, Context
from alpaca.clr import AST

@dataclass
class Instance():
    name: str
    type: Type
    context: Context
    ast: AST

    is_ptr: bool = False
    is_constructor: bool = False
    is_function: bool = False
    is_recursive_function: bool = False
    no_mangle: bool = False
    no_lambda: bool = False

    def __hash__(self) -> int:
        return hash(self.get_full_name())

    def get_full_name(self):
        if self.no_mangle:
            return self.name

        return (self.context.get_full_name()
            + self.name
            + "___"
            + Instance.get_signature_string(self.type))

    def __str__(self) -> str:
        return self.get_full_name()

    @staticmethod
    def get_signature_string(type: Type):
        match type:
            case (Type(classification=Type.classifications.novel)
                | Type(classification=Type.classifications.struct)
                | Type(classification=Type.classifications.interface)
                | Type(classification=Type.classifications.variant)):
                return type.name
            case Type(classification=Type.classifications.tuple):
                return "d_" + "_".join([Instance.get_signature_string(t)
                    for t in type.components]) + "_b"
            case Type(classification=Type.classifications.function):
                return ("Fd_" + Instance.get_signature_string(type.get_argument_type())
                    + "_I_" + Instance.get_signature_string(type.get_return_type())
                    + "_b")
            case Type(classification=Type.classifications.parametric):
                return type.name + "q_" + "_".join([Instance.get_signature_string(t)
                    for t in type.parametrics]) + "_p"
            case _:
                raise Exception(f"signature not implemented for type: {type}")

@dataclass
class FunctionInstance(Instance):
    pass
