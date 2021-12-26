import alpaca

class Callback(alpaca.lexer.AbstractCallback):
    @classmethod
    def string(cls, string : str) -> str:
        return string.replace('\\n', '\n')[1 : -1]