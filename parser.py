import ast
from typing import Any
from error import Raise
from grammar import Grammar

class Token():
    types = [
        "symbol",
        "string",
        "var",
        "operator",
        "keyword",
        "flag",
    ]

    def __init__(self, type, value = ""):
        if type not in Token.types:
            Raise.code_error(f"unknown token type: {type}")
            
        self.type = type
        self.value = value
        self.line_number = None

# TODO: fix for floats
class Parser():
    operators = [
        "=", ":=", "<-",
        "+=", "-=", "*=", "/="
        "?",
        "==", "!=",
        "+", "-", "/", "*",
        "&",
        "&&", "||", "!"
        "%",
        "++", "--", 
        "<<", ">>",
        "|",
        "<", ">", "<=", ">=",
        ".",        
        "::",
        "->", ":"
    ]

    symbols = [
        ",",
        "//",
        "{", "}", "(", ")", "[", "]"
    ]

    keywords = [
        "class",
        "return",
        "this",
        "fun",
        "if",
        "else",
        "for",
        "while",
        "private",
        "public",
        "let",
    ]

    class Passover():
        description = None

        def __init__(self):
            self.tokens = [];

        def __str__(self):
            return f"{self.description}\n"

        def run(self, pretokens : list):
            if not pretokens:
                Raise.error("no tokens parsed by", str(self))

            self.tokens = []
            for tok in pretokens:
                if isinstance(tok, Token):
                    self.if_tok(tok)
                elif isinstance(tok, str):
                    self.if_str(tok)
                else:
                    Raise.code_error("pretoken must be str or Token")

            return self.tokens
            
        def if_str(self, tok : str) -> None:
            pass

        def if_tok(self, tok : Token) -> None:
            self.tokens.append(tok)

        def __call__(self, *args: Any, **kwds: Any) -> Any:
            return self.run(*args)

            
            


    # returns end of longest matching operator
    @classmethod
    def _greedy_match_symbol_set(cls, symbol_set : list, txt : str, loc : int) -> int:
        start = loc
        end = loc + 1
        while end <= len(txt):
            if txt[start : end] not in symbol_set:
                return end - 1

            end += 1

        return end

    # assumes txt has already been split by '\n' and '"'
    @classmethod
    def _split_out_symbol_set(cls, symbol_name, symbol_set, txt : str) -> list:
        tokens = []
        residual = ""
        size = len(txt)
        i = 0
        while i < size:
            end = cls._greedy_match_symbol_set(symbol_set, txt, i)

            # true if operator was matched
            if end != i:
                if residual != "":
                    tokens.append(residual)
                    residual = ""

                tokens.append(Token(symbol_name, txt[i : end]))
                i = end
            else:
                residual += txt[i]
                i += 1

        # flush 
        if residual != "":
            tokens.append(residual)

        return tokens

    # TODO: this currently also splits out comments; should be refactored; also only supports 
    # comments that take up the whole line
    class _split_lines(Passover):
        order = 1
        description = "split by newlines; also remove comments."

        def if_str(self, tok : str):
            lines = tok.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) == 0:
                    self.tokens.append(Token("flag", "codeline"))
                    continue
        
                # TODO: remove and refactor
                if line[0:2] == "//":
                    self.tokens.append(Token("flag", "codeline"))
                    continue

                self.tokens.append(line)
                self.tokens.append(Token("symbol", "endl"));

    class _split_strings(Passover):
        order = 2
        description = "split strings into tokens"

        @classmethod
        def stringify(cls, chunk : str):
            return chunk.replace("\\n", "\n")

        def if_str(self, tok : str):
            # line should not start with '"'
            if tok[0] == '"':
                Raise.error("line cannot start with string")

            chunks = tok.split('"')
            # split out strings. as a line cannot begin with a string, the result of the code below
            # will have even indices as 'code' and odd indices as strings.
            for i, chunk in enumerate(chunks):
                if i % 2 == 0:
                    self.tokens.append(chunk)
                else:
                    self.tokens.append(Token("string", self.stringify(chunk)))

    class _split_spaces(Passover):
        order = 3
        description = "split by spaces"

        def if_str(self, tok: str) -> None:
            self.tokens += tok.split(' ')

    class _split_operators(Passover):
        order = 4
        description = "split operators into tokens"

        def if_str(self, tok: str) -> None:
            self.tokens += Parser._split_out_symbol_set("operator", Parser.operators, tok)

    class _split_symbols(Passover):
        order = 5
        description = "split symbols into tokens"

        def if_str(self, tok: str) -> None:
            self.tokens += Parser._split_out_symbol_set("symbol", Parser.symbols, tok)

    class _split_keywords_and_vars(Passover):
        order = 6
        description = "split keywords and variables into tokens"

        def if_str(self, tok: str) -> None:
            tok = tok.strip()

            if tok in Parser.keywords:
                self.tokens.append(Token("keyword", tok))
            else:
                self.tokens.append(Token("var", tok))

    class _label_ints(Passover):
        order = 7
        description = "convert var tokens to int if needed"

        def if_str(self, tok: str) -> None:
            Raise.error("should not have str tokens at this point")

        def if_tok(self, tok: Token) -> None:
            if Parser.is_int(tok.value):
                tok.type = "int"

            self.tokens.append(tok)

    class _label_bools(Passover):
        order = 8
        description = "convert var tokens to bool if needed"

        def if_str(self, tok: str) -> None:
            Raise.error("should not have str tokens at this point")

        def if_tok(self, tok: Token) -> None:
            if tok.value == "true" or tok.value == "false":
                tok.type = "bool"

            self.tokens.append(tok) 
    
    class _assign_line_numbers(Passover):
        order = 9
        description = "assign line numbers to tokens and remove codeline flags"
        
        def __init__(self):
            self.line_number = 1

        def if_str(self, tok: str) -> None:
            Raise.error("should not have str tokens at this point")
        
        def if_tok(self, tok : Token) -> None:
            if tok.type == "flag" and tok.value == "codeline":
                self.line_number += 1
                return
            
            tok.line_number = self.line_number
            self.tokens.append(tok)
            

            


    @classmethod
    def _isbrace(cls, tok : Token) -> bool:
        val = tok.value
        return val == "{" or val == "}"

    @classmethod
    def _islbrace(cls, tok : Token) -> bool:
        return tok.value == "{"

    @classmethod
    def is_int(cls, txt : str) -> bool:
        return txt.isnumeric()


    @classmethod
    def _remove_unnecessary_newlines(cls, pretokens : list) -> list:
        if not pretokens:
            Raise.error("tokens are empty")

        tokens = [pretokens[0]]
        last_token = pretokens[0]
        for tok in pretokens[1:]:
            if tok.type == "symbol" and tok.value == "endl" and cls._isbrace(last_token):
                continue
            if tok.type == "symbol" and tok.value == "endl" and last_token.type == "endl":
                continue

            if cls._islbrace(tok) and last_token.type == "symbol" and last_token.value == "endl":
                tokens.pop()
            
            tokens.append(tok)
            last_token = tok
        
        return tokens

    workflow = [
        _split_lines,
        _split_strings,
        _split_spaces,
        _split_operators,
        _split_symbols,
        _split_keywords_and_vars,
        _label_ints,
        _label_bools,
        _assign_line_numbers,
    ]

    @classmethod
    def tokenize(cls, txt : str) -> list:
        passovers = [e() for e in Parser.workflow]

        tokens = [txt]
        for passover in passovers:
            tokens = passover(tokens)

        tokens = cls._remove_unnecessary_newlines(tokens)

        return tokens
