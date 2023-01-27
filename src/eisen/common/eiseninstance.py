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

    def get_c_name(self):
        return self.context.get_full_name() + "_" + self.name

    def get_unique_function_name(self):
        return self.context.get_full_name() + "_" + self.name + "_" + str(self.type)


class EisenFunctionInstance(EisenInstance):
    pass
