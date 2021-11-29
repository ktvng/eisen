from __future__ import annotations
import ast
from typing import Any
from error import Raise
from grammar import Grammar

class Token():
    """
    Encapsulates strings of text and associated metadata.

    Attributes
        type (str):           string contained in Token.types, determines type of token
        value (str):          string for the actual text of the token
        line_number (int):    (starting at 1) line number where to token originates
    """

    types = [
        "symbol",       # used to organize information (e.g. brackets/parens) 
        "string",       # enclosed in double quotes (TODO: allow single quotes)
        "var",          # name of variable
        "operator",     # symbol with associated operation (see examples in Parser.operators)
        "keyword",      # text with associated operation (see examples in Parser.keywords)
        "flag",         # text flags used during parsing only, removed before compilation
        "int",          # integer numbers
        "bool",         # booleans
    ] 

    def __init__(self, type : str, value : str = ""):
        if type not in Token.types:
            Raise.code_error(f"unknown token type: {type}")
            
        self.type = type
        self.value = value
        self.line_number = None

    def change_type_to(self, type : str) -> None:
        if type not in Token.types:
            Raise.code_error(f"unknown token type: {type}")
        
        self.type = type

# TODO: allow parsing of floats

# implementation
#   applies a sequence of functions to a mixed list containing raw strings and/or Tokens.
#   each function will return a new, more processed, mixed list that is used as the input 
#   of the subsequent function, and the list returned by the final function should be a list
#   consisting of Token objects.
#
#   functions inherit from the Parser.Passover class.
class Parser():
    """
    Stateless class which converts a string of text into a list of Tokens.
    """

    class Definitions():
        @classmethod
        def is_int(cls, txt : str) -> bool:
            return txt.isnumeric()
    
    operators = [
        "=", ":=", "<-",            # assignment 
        "+=", "-=", "*=", "/=",     # shorthand arithmetic+assignment       
        "?",                        # nullable
        "==", "!=",                 # equality
        "+", "-", "/", "*",         # arithmetic
        "&",                        # reference
        "&&", "||", "!",            # logical
        "%",                        # modulus
        "++", "--",                 # increment
        "<<", ">>",                 # bitshift
        "|",                        # pipe
        "<", ">", "<=", ">=",       # comparison
        ".",                        # attribution
        "::",                       # scope
        "->", ":",                  # typing
    ]

    symbols = [
        ",",
        "//",
        "{", "}", "(", ")", "[", "]",
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
        """
        Abstract class inherited and implemented by functions that process a mixed list
        of strings/Tokens and return a new, more processed mixed list. An implementing function
        should be defined as a stateless map from each string/Token of the input mixed list to a
        single or multiple string(s)/Token(s) to be added in-order to the output mixed list.

        Stateful functions are allowed, but discouraged. The function can be called by the
        'run' method.
        """
        def __init__(self, tokens : list[str | Token] = []):
            self.tokens = tokens;

        def __str__(self):
            return f"{self.__doc__}\n"

        def _run(self, pretokens : list[str | Token]) -> list[str | Token]:
            if not pretokens:
                Raise.error("no tokens parsed by", str(self))

            self.tokens = []
            for tok in pretokens:
                if isinstance(tok, Token):
                    self.tokens += self._if_tok(tok)
                elif isinstance(tok, str):
                    self.tokens += self._if_str(tok)
                else:
                    Raise.code_error("pretoken must be str or Token")

            return self.tokens
        
        def _if_str(self, tok : str) -> list[str | Token]:
            """
            Called in the case that an object in the input mixed-list is a string. Should map this
            string to one or more string(s)/Tokens(s) which should be returned inside a list. This list 
            will be automatically appended to the output mixed-list.

            Args:
                tok (str): string object from the input-mixed list.

            Returns:
                list: string(s)/Token(s) to be appended to the output mixed-list.
            """
            pass
        
        def _if_tok(self, tok : Token) -> list[str | Token]:
            """
            Called in the case that an object in the input mixed-list is a Token. Should map this 
            Token to one or Token(s) which should be returned inside a list. This list will automatically 
            be appended to the output mixed-list.

            By default it returns the input token unchanged.

            Args:
                tok (Token): Token object from the input-mixed list.

            Returns:
                list: Token objects to be appended in-order to the output mixed-list.
            """
            return [tok]

        def __call__(self, *args: Any, **kwds: Any) -> list[str | Token]:
            """
            Evaluates the passover function on a mixed list of string(s)/Token(s) and 
            returns the resulting, more processed mixed-list

            Returns:
                [type]: [description]
            """
            return self._run(*args)



    ################################################################################################
    ##
    ## Passover functions
    ##
    ################################################################################################
    @classmethod
    def _greedy_match_symbol_set(cls, symbol_set : list, txt : str, loc : int) -> int:
        """
        Matches the longest symbol in [symbol_set] with the substring of [txt] starting at 
        index [loc]. 

        Args:
            symbol_set (list[str]): a list of single/multi character symbols to be matched
            txt (str): text to match a substring of to some symbol in the [symbol_set]
            loc (int): index of [txt] from where the symbol is matched such that the first char
                       of the symbol is (txt[loc])

        Returns:
            int: Returns the end index of the longest matching symbol such that txt[loc : end] 
                 would yield the symbol. End will be (loc+1) if no matching symbol exists.
        """
        start = loc
        end = loc
        while end <= len(txt):
            if txt[start : end + 1] not in symbol_set:
                return end

            end += 1

        return end

    @classmethod
    def _split_out_symbol_set(cls, 
        token_type : str, 
        symbol_set : list[str], 
        txt : str
        ) -> list [str : Token]:
        """
        Assumes that [txt] does not contain '\\n' or '"' characters. Splits all symbols
        in the [symbol_set] out of [txt] as Tokens of [token_type].

        Args:
            token_type (str): type of token to be created for matching symbols
            symbol_set (list[str]): set of symbols to match
            txt (str): text to process and match symbols over

        Returns:
            list[str | Token]: Returns a new mixed list of string(s)/Token(s) which preserves order.
        """
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

                tokens.append(Token(token_type, txt[i : end]))
                i = end
            else:
                residual += txt[i]
                i += 1

        # flush 
        if residual != "":
            tokens.append(residual)

        return tokens

    class _split_lines(Passover):
        """
        Break apart any strings in the input mixed-list by '\\n' character. Adds codeline flag
        Tokens in place of the '\\n' character, and adds endl symbol Tokens for where a non-empty
        line of code terminates.

        Returns:
            list[str | Token]: New mixed-list with string/Token elements not containing '\\n'
        """
        order = 1

        def _if_str(self, tok : str):
            lines = tok.split('\n')
            out_toks = []
            for line in lines:
                line = line.strip()
                if len(line) == 0:
                    out_toks.append(Token("flag", "codeline"))
                    continue

                out_toks.append(line)
                out_toks.append(Token("symbol", "endl"));
                out_toks.append(Token("flag", "codeline"))
            
            return out_toks
    
    class _remove_comments(Passover):
        """
        Removes full-line and partial comments from string type objects in the input mixed-list.

        Returns:
            list[str | Token]: New mixed-list, preserving order, without comments
        """
        order = 1.5

        def _if_str(self, tok: str) -> list[str | Token]:
            if tok[0:2] == "//":
                return []

            if "//" in tok:
                # make sure the "//" character is not enclosed inside a string
                in_str = False
                for i, c in enumerate(tok):
                    if c == '"':
                        in_str = not in_str
                    
                    if not in_str and i+1 < len(tok):
                        if tok[i : i+2] == "//":
                            return [tok[0 : i].strip()]
        
            return [tok]
    
    class _split_strings(Passover):
        """
        Break apart string type objects in the input mixed-list if they contain strings. Strings
        are stored as string type Tokens without the enclosing double quotes.

        Returns:
            list[str | Token]: New mixed-list without any string objects containing double quotes.
        """
        order = 2

        @classmethod
        def stringify(cls, chunk : str):
            return chunk.replace("\\n", "\n")

        def _if_str(self, tok: str) -> list[str | Token]:
            # line should not start with '"'
            if tok[0] == '"':
                Raise.error("line cannot start with string")

            out_toks = []
            chunks = tok.split('"')
            # split out strings. as a line cannot begin with a string, the result of the code below
            # will have even indices as 'code' and odd indices as strings.
            for i, chunk in enumerate(chunks):
                if i % 2 == 0:
                    out_toks.append(chunk)
                else:
                    out_toks.append(Token("string", self.stringify(chunk)))
            
            return out_toks

    class _split_spaces(Passover):
        """
        Break apart string type objects in the input mixed-list by (' ') space characters.

        Returns:
            list[str | Token]: New mixed-list not containing any space characters.
        """
        order = 3

        def _if_str(self, tok: str) -> list[str | Token]:
            return tok.split(' ')

    class _split_operators(Passover):
        """
        Break apart any string type objects in the input mixed list if they contain substrings 
        matching any of the defined Parser.operators. Creates a new "operator" type Token for these
        values and adds them and any surrounding string fragments in order to a new mixed list.

        Returns:
            list[str | Token]: New-mixed list where all operators have been converted to Tokens.
        """
        order = 4

        def _if_str(self, tok: str) -> list[str | Token]:
            return Parser._split_out_symbol_set("operator", Parser.operators, tok)

    class _split_symbols(Passover):
        """
        Break apart any string type objects in the input mixed list if they contain substrings
        matching any of the defined Parser.symbols. Create a new "symbol" type TOken for these
        values and adds them to and any surround string fragments in order to a new mixed list.

        Returns:
            list[str | Token]: New-mixed list where all symbols have been converted to Tokens.
        """
        order = 5

        def _if_str(self, tok: str) -> list[str | Token]:
            return Parser._split_out_symbol_set("symbol", Parser.symbols, tok)

    class _split_keywords_and_vars(Passover):
        """
        Convert any string type objects in the input mixed-list that match keywords to "keyword"
        Type tokens, and any remaining tokens to "var" type Tokens.

        Returns:
            list[Token]: New list which should contain only Token type objects.
        """
        order = 6
        description = "split keywords and variables into tokens"

        def _if_str(self, tok: str) -> list[str | Token]:
            tok = tok.strip()

            if tok in Parser.keywords:
                return [Token("keyword", tok)]
            else:
                return [Token("var", tok)]   
    
    class _validate_list_contains_only_tokens(Passover):
        """
        Validates that the input list contains only Token type objects.

        Returns:
            list[Token]: The original list is returned.
        """
        order = 6.5

        def _if_str(self, tok: str) -> list[str | Token]:
            Raise.error("list should not contain str type objects at this point")

    class _label_ints(Passover):
        """
        Convert var Tokens to int types.

        Returns:
            list[Token]: The original list with some tokens relabeled.
        """
        order = 7

        def _if_tok(self, tok : Token) -> list[Token]:
            if Parser.Definitions.is_int(tok.value):
                tok.change_type_to("int")

            return [tok]

    class _label_bools(Passover):
        """
        Convert var Tokens to bool types.

        Returns:
            list[Token]: The original list with some tokens relabeled.
        """
        order = 8

        def _if_tok(self, tok : Token) -> list[Token]:
            if tok.value == "true" or tok.value == "false":
                tok.change_type_to("bool")

            return [tok]
    
    class _assign_line_numbers(Passover):
        """
        Assign line numbers to Tokens in the input list, and remove the codeline flags which
        define where newlines in the original code are located. 

        Requires state to store information about the current line number.

        Returns:
            list[Token]: The input list with all tokens assigned to line numbers.
        """
        order = 9
        
        def __init__(self):
            self.line_number = 1

        def _if_tok(self, tok : Token) -> list[Token]:
            if tok.type == "flag" and tok.value == "codeline":
                self.line_number += 1
                return []
            
            tok.line_number = self.line_number
            return [tok]
    
    class _remove_unnecessary_newlines(Passover):
        @classmethod
        def _isbrace(cls, tok : Token) -> bool:
            val = tok.value
            return val == "{" or val == "}"

        @classmethod
        def _islbrace(cls, tok : Token) -> bool:
            return tok.value == "{"

        def _run(cls, pretokens : list) -> list:
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

    ################################################################################################
    ##
    ## Workflow and main logic
    ##
    ################################################################################################
    workflow = [
        _split_lines,
        _remove_comments,
        _split_strings,
        _split_spaces,
        _split_operators,
        _split_symbols,
        _split_keywords_and_vars,
        _validate_list_contains_only_tokens,
        _label_ints,
        _label_bools,
        _assign_line_numbers,
        _remove_unnecessary_newlines,
    ]

    @classmethod
    def tokenize(cls, txt : str) -> list:
        passovers = [e() for e in Parser.workflow]
        tokens = [txt]

        for passover in passovers:
            tokens = passover(tokens)

        return tokens
