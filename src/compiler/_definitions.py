class Definitions():
    @classmethod
    def type_equality(cls, typeA : str, typeB : str):
        # TODO: formalize this hack
        if typeB[0] == "#":
            return typeA == typeB[1:]
        return typeA == typeB

    reference_type = "#reference"

    @classmethod
    def type_is_reference(cls, type : str):
        return type == Definitions.reference_type

    literal_tag = "#"
    def type_is_literal(cls, type : str):
        return (not Definitions.type_is_reference(type) 
            and type[0] == Definitions.literal_tag)

    print_function_type = "(...) -> (void)"
    print_function_name = "print"

    @classmethod
    def is_primitive(cls, type : str):
        return (Definitions.type_equality(type, "int") #Seer.Types.Primitives.Int) 
            or Definitions.type_equality(type, "float") #Seer.Types.Primitives.Float)
            or Definitions.type_equality(type, "bool")) #Seer.Types.Primitives.Bool))
