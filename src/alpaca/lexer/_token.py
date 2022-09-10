from alpaca.config import TokenRule

class Token():
    def __init__(self, type : str, value : str, line_number : int, rule : TokenRule):
        self.type = type
        self.value = value
        self.line_number = line_number
        self.rule = rule

    type_print_len = 12
    def __str__(self):
        padding = max(0, self.type_print_len - len(self.type))
        clean_value = self.value.replace('\n', '\\n')
        return f"{self.line_number}\t{self.type}{' ' * padding}{clean_value}"
        