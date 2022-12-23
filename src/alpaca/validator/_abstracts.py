from __future__ import annotations

class AbstractParams:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            self.__setattr__(key, val)

    def _but_with(self, **kwargs) -> AbstractParams:
        filtered_kwargs = {}
        for k, v in kwargs.items():
            if v is not None:
                filtered_kwargs[k] = v
        # filtered_kwargs = dict({(k, v) for k, v in kwargs.items() if v is not None})
        updated_attrs = { **self.__dict__, **filtered_kwargs}
        return type(self)(**updated_attrs)

class AbstractException():
    size_bound = 56
    delineator = "="*74+"\n"
    type = None
    description = None

    def __init__(self, msg : str, line_number : int):
        self.msg = msg
        self.line_number = line_number
        self._stub = None

    def cut_to_size(self, s: str) -> list[str]:
        bits = s.split(" ")
        lines = []
        line = ""
        for bit in bits:
            if len(line) + len(bit) > AbstractException.size_bound:
                lines.append(line + "\n")
                line = bit + " "
                continue
            else:
                line += bit + " "

        # flush the remainder
        lines.append(line + "\n")
        return lines


    def __str__(self):
        prefix = f"    Line {self.line_number}: "
        full_indent = " "*len(prefix)

        padding = " "*len(str(self.line_number))
        return (AbstractException.delineator
            + f"{self.type}Exception\n"
            + prefix + full_indent.join(self.cut_to_size(self.description))
            + f"{padding}     INFO: " + full_indent.join(self.cut_to_size(self.msg))
            + f"\n")

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