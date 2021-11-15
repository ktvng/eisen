import ast
from error import Raise
from grammar import Grammar

class Token():
    def __init__(self, type, value = ""):
        self.type = type
        self.value = value

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
        "public"
    ]

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
    # split out newlines
    @classmethod
    def _pass1(cls, pretokens : list) -> list:
        tokens = []
        for tok in pretokens:
            lines = tok.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) == 0:
                    continue
        
                # TODO: remove and refactor
                if line[0:2] == "//":
                    continue

                tokens.append(line)
                tokens.append(Token("symbol", "endl"));

        return tokens

   # split out strings
    @classmethod
    def _pass2(cls, pretokens : list) -> list:
        tokens = []
        for tok in pretokens:
            if isinstance(tok, Token):
                tokens.append(tok)
                continue

            # line should not start with '"'
            if tok[0] == '"':
                Raise.error("line cannot start with string")

            chunks = tok.split('"')
            # split out strings. as a line cannot begin with a string, the result of the code below
            # will have even indices as 'code' and odd indices as strings.
            for i, chunk in enumerate(chunks):
                if i % 2 == 0:
                    tokens.append(chunk)
                else:
                    tokens.append(Token("string", chunk))
        
        return tokens
        
    # split out spaces
    @classmethod
    def _pass3(cls, pretokens : list) -> list:
        tokens = []
        for tok in pretokens:
            if isinstance(tok, Token):
                tokens.append(tok)
                continue
            
            tokens += tok.split(' ')
        
        return tokens

    # split out operators
    @classmethod
    def _pass4(cls, pretokens : list) -> list:
        tokens = []
        for tok in pretokens:
            if isinstance(tok, Token):
                tokens.append(tok)
                continue
        
            tokens += cls._split_out_symbol_set("operator", Parser.operators, tok)

        return tokens

    # split out symbols 
    @classmethod
    def _pass5(cls, pretokens : list) -> list:
        tokens = []
        for tok in pretokens:
            if isinstance(tok, Token):
                tokens.append(tok)
                continue
                
            tokens += cls._split_out_symbol_set("symbol", Parser.symbols, tok)

        return tokens

    # label keywords
    @classmethod
    def _pass6(cls, pretokens : list) -> list:
        tokens = []
        for tok in pretokens:
            if isinstance(tok, Token):
                tokens.append(tok)
                continue

            tok = tok.strip()

            if tok in Parser.keywords:
                tokens.append(Token(tok))
            else:
                tokens.append(Token("var", tok))

        return tokens

    @classmethod
    def _isbrace(cls, tok : Token) -> bool:
        val = tok.value
        return val == "{" or val == "}"

    @classmethod
    def _islbrace(cls, tok : Token) -> bool:
        return tok.value == "{"

    # remove uneccessary newlines
    @classmethod
    def _pass7(cls, pretokens : list) -> list:
        if not pretokens:
            Raise.error("tokens are empty")

        tokens = [pretokens[0]]
        last_token = pretokens[0]
        for tok in pretokens[1:]:
            if tok.type == "symbol" and tok.value == "endl" and cls._isbrace(last_token):
                continue
            if tok.type == "symbol" and tok.value == "endl" and last_token.type == "endl":
                continue

            if cls._islbrace(tok) and last_token.type == "endl":
                tokens.pop()
            
            tokens.append(tok)
            last_token = tok
        
        return tokens

    @classmethod
    def tokenize(cls, txt : str) -> list:
        tokens = [txt]
        tokens = cls._pass1(tokens)
        tokens = cls._pass2(tokens)
        tokens = cls._pass3(tokens)
        tokens = cls._pass4(tokens)
        tokens = cls._pass5(tokens)
        tokens = cls._pass6(tokens)
        tokens = cls._pass7(tokens)

        return tokens

    @classmethod
    def lex(cls, tokens : list):
        Grammar.load()
        ast_queue = Grammar.tokens_to_ast_queue(tokens)
        backlog_queue = []

        working_queue = cls.try_match(backlog_queue, ast_queue)
        print(working_queue)

    @classmethod
    def try_match(cls, backlog_queue : list, ast_queue : list) -> list:
        working_queue = cls._greedy_match(ast_queue)
        if not working_queue:
            backlog_queue.append(ast_queue.pop(0))
        else:
            exists_match = cls._filter_for_complete_matches(working_queue, ast_queue)
            if exists_match:
                matches = Grammar.matches(working_queue)
                for match in matches:
                    print(match.parent + " -> " + " ".join(match.pattern))
                if len(matches) > 1:
                    Raise.error("more than 1 match!")

                return working_queue

        return []
    
    @classmethod
    def _filter_for_complete_matches(cls, working_queue : list, ast_queue : list) -> bool:
        if not working_queue:
            return False

        if not Grammar.matches(working_queue):
            return False

        while len(working_queue) > 1 and Grammar.matches(working_queue[:-1]):
            ast_queue.insert(0, working_queue.pop())
        
        return True
            
    @classmethod
    def _greedy_match(cls, ast_queue : list) -> list:
        if not ast_queue:
            return []

        partial_queue = []
        lookahead = ast_queue[0]
        prefix_matches = Grammar.prefix_matches(partial_queue + [lookahead])

        while prefix_matches:
            ast_queue.pop(0)
            partial_queue.append(lookahead)

            if not ast_queue:
                break

            lookahead = ast_queue[0]
            prefix_matches = Grammar.prefix_matches(partial_queue + [lookahead])

        return partial_queue
        