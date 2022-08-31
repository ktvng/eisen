import alpaca

class SeerCallback(alpaca.lexer.AbstractCallback):
    @classmethod
    def string(cls, string : str) -> str:
        return string.replace('\\n', '\n')[1 : -1]