class Exceptions():
    delineator = "="*80+"\n"

    class AbstractException():
        type = None
        description = None

        def __init__(self, msg : str, line_number : int):
            self.msg = msg
            self.line_number = line_number
            self._stub = None

        def __str__(self):
            padding = " "*len(str(self.line_number))
            return (Exceptions.delineator
                + f"{self.type}Exception\n    Line {self.line_number}: {self.description}\n"
                + f"{padding}     INFO: {self.msg}\n\n")

        def to_str_with_context(self, txt : str):
            str_rep = str(self)

            lines = txt.split('\n')
            index_of_line_number = self.line_number - 1

            start = index_of_line_number - 2
            start = 0 if start < 0 else start

            end = index_of_line_number + 3
            end = len(lines) if end > len(lines) else end

            for i in range(start, end):
                c = ">>" if i == index_of_line_number else "  "
                line = f"       {c} {i+1} \t| {lines[i]}\n" 
                str_rep += line
                
            return str_rep

        def set_compiler_stub(self, stub):
            self._stub = stub

        def get_stub(self):
            return self._stub

        def has_stub(self) -> bool:
            return self._stub is not None


    class UseBeforeInitialize(AbstractException):
        type = "UseBeforeInitialize"
        description = "variable cannot be used before it is initialized"

        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)
    
    class UndefinedVariable(AbstractException):
        type = "UndefinedVariable"
        description = "variable is not defined"
    
        def __init__(self, msg: str, line_number: int):
            super().__init__(msg, line_number)

    class TypeMismatch(AbstractException):
        type = "TypeMismatch"
        description = "type different from expected"

        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)

    class TupleSizeMismatch(AbstractException):
        type = "TupleSizeMismatch"
        description = "tuple unpack requires equal sizes"

        def __init__(self, msg : str, line_number : int):
            super().__init__(msg, line_number)
