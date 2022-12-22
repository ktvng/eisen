import alpaca

class EisenCallback(alpaca.lexer.AbstractCallback):
    @classmethod
    def string(cls, string : str) -> str:
        return string.replace('\\n', '\n')[1 : -1]

    @classmethod
    def str(cls, string : str) -> str:
        return string.replace('\\n', '\n')[1 : -1]