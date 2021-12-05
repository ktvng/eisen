from __future__ import annotations
from error import Raise
from astnode import AstNode
import itertools

def is_op(txt : str) -> bool:
    return txt[0 : 3] == "op_"

OpCodes = {
    "=": "op_assign",
    ":=": "op_assign",
    "<-": "op_assign",
    "+=": "op_assign",
    "-=": "op_assign",
    "*=": "op_assign",
    "/=": "op_assign",
    "?": "op_unary_post",
    "==": "op_bin",
    "!=": "op_bin",
    "->": "->",
    ":": ":",
    "+": "op_bin",
    "-": "op_bin",
    "/": "op_bin",
    "*": "op_bin",
    "&": "&",
    "&&": "op_bin",
    "||": "op_bin",
    "!": "op_unary_pref",
    "%": "op_bin",
    "++": "op_unary_post",
    "--": "op_unary_post", 
    "<<": "op_bin",
    ">>": "op_bin",
    "|": "op_bin",
    "<": "op_bin",
    ">": "op_bin",
    "<=": "op_bin",
    ">=": "op_bin",
    ".": "op_bin",
    ",": ",",
    "//": "none",
    "::": "op_bin",
    "{": "{", 
    "}": "}", 
    "(": "(", 
    ")": ")", 
    "[": "[", 
    "]": "]", 
}

####################################################################################################
##
## Grammar architecture
##
####################################################################################################
class GrammarRule():
    """
    Encapsulates the information of a CFG production rule, including a string/list of strings which
    encodes how the rule should be reversed
    """
    def __init__(self, production_symbol : str, pattern_str : str, reverse_with : str | list[str]):
        """
        Create a new GrammarRule.

        Args:
            production_symbol (str): symbol which produces the pattern
            pattern_str (str): pattern which can be produced from the production_symbol
            reverse_with (str | list[str]): string(s) which define which methods to use to reverse
                                            the rule
        """
        self.production_symbol = production_symbol.strip()
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]

        if isinstance(reverse_with, str):
            self.reverse_with = [reverse_with]
        elif isinstance(reverse_with, list):
            self.reverse_with = reverse_with

    @classmethod
    def is_production_symbol(cls, token : str):
        return token.isupper() and all(map(lambda x : x.isalnum() or x == '_', token))

    def __str__(self):
        return self.production_symbol + " -> " + self.pattern_str

class CFG():
    """
    Encapsulates a list of CFG GrammarRules and a designated starting symbol
    """
    def __init__(self, rules : list[GrammarRule]):
        self.rules = rules
        self.start = "START"

    def set_start(self, start : str):
        self.start = start

####################################################################################################
##
## Grammar construction
##
####################################################################################################
class Grammar():
    expressional_keywords = [
        "this",
        "return",
    ]

    implementation : CFG = None

    @classmethod
    def load(cls):
        Grammar.implementation = GrammarParser.load()
        normer = CFGNormalizer()
        Grammar.implementation = normer.run(Grammar.implementation)
        return cls

class GrammarParser():
    """
    Stateless class which parses a seer grammar file into a CFG.
    """
    reverse_action_prefix_flag = "@action "
    grammar_file = "grammar.txt"

    @classmethod
    def _loadRule(cls, line : str, reverse_with : str) -> GrammarRule:
        parts = line.split('->', 1)
        if len(parts) != 2:
            Raise.error("invalid grammar line; must contain symbol -> once and only once")
        
        pattern, pattern_str = parts
        return GrammarRule(pattern, pattern_str, reverse_with)

    @classmethod
    def _defines_reverse_method_decl(cls, line : str) -> bool:
        return cls.reverse_action_prefix_flag == line[0 : len(cls.reverse_action_prefix_flag)]

    @classmethod
    def _get_reverse_method(cls, line : str) -> str:
        return line[len(cls.reverse_action_prefix_flag) : ]

    @classmethod
    def load(cls) -> CFG:
        cached_reverse_with_method = "pass"
        raw_rules = []
        with open(cls.grammar_file, 'r') as f:
            # remove empty lines
            raw_rules = [l.strip() for l in f.readlines() if l.strip() != ""]

            # remove comments
            raw_rules = [l for l in raw_rules if l[0] != "#"]

        rules = []
        for line in raw_rules:
            if cls._defines_reverse_method_decl(line):
                cached_reverse_with_method = cls._get_reverse_method(line)
                continue

            rules.append(cls._loadRule(line, cached_reverse_with_method))

        return CFG(rules)

class CFGNormalizer():
    """
    Converts a generic CFG grammar into a CNF CFG.
    """

    def __init__(self):
        # maps from literals : str to rules : GrammarRule
        self.rules_for_literals = {}
        self.n_rules_for_literals = 0
        self.n_connector_rules = 0

        # maps from ruleA:ruleB 
        self.connectors = {} 
        self.rules = []

        self.starting_rule_name = "START"

    def run(self, cfg : CFG) -> CFG:
        self.original_cfg = cfg
        for rule in cfg.rules:
            self._expand_rule(rule)

        new_cfg = CFG(self.rules)
        new_cfg.set_start(self.starting_rule_name)

        return new_cfg

    @classmethod 
    def is_connector(cls, name : str) -> bool:
        return "_CONNECTOR" in name and name[-1] == "_"

    @classmethod
    def is_cnf_rule(cls, rule : GrammarRule) -> bool:
        if len(rule.pattern) == 2:
            return all(map(GrammarRule.is_production_symbol, rule.pattern))
        elif len(rule.pattern) == 1:
            return not GrammarRule.is_production_symbol(rule.pattern[0])
        else:
            return False

    def _add_new_rule_for_literal(self, literal : str) -> GrammarRule:
        new_rule = GrammarRule(f"_TOKENS{self.n_rules_for_literals}_", literal, "none")
        self.n_rules_for_literals += 1
        self.rules_for_literals[literal] = new_rule
        self.rules.append(new_rule)

        return new_rule

    def _get_rule_for_literal(self, literal : str) -> GrammarRule:
        existing_rule = self.rules_for_literals.get(literal, None)
        if existing_rule is None:
            return self._add_new_rule_for_literal(literal)

        return existing_rule

    def get_rule_for_connector(self, ruleA : str, ruleB : str, name=None):
        existing_rule = None

        key = f"{ruleA}:{ruleB}"

        # use [name] in key as well if it exists
        if name is not None:
            key = f"{name}:" + key

        existing_rule = self.connectors.get(key, None)

        if existing_rule is None:
            pattern = f"{ruleA} {ruleB}"
            if name is None:
                name = f"_CONNECTOR{self.n_connector_rules}_"

            new_connector = GrammarRule(name, pattern, "pool")

            self.n_connector_rules += 1
            self.connectors[key] = new_connector
            self.rules.append(new_connector)

            return new_connector

        return existing_rule

    # in the case that [rule] produces a pattern consiting of a single production_symbol, substitute 
    # the pattern of that production_symbol in for it and expand the resulting temporary rule
    def _handle_single_prod_rule_case(self, rule : GrammarRule) -> None:
        substitute_production_symbol = rule.pattern[0]
        substitutions = [r for r in self.original_cfg.rules 
            if r.production_symbol == substitute_production_symbol]

        for rule_to_sub in substitutions:
            pattern_to_sub = rule_to_sub.pattern_str
            
            # rule_to_sub.reverse with should be executed before the original rule
            steps_to_reverse_both_rules = [*rule_to_sub.reverse_with, *rule.reverse_with]
            
            temp_rule = GrammarRule(
                rule.production_symbol, 
                pattern_to_sub, 
                steps_to_reverse_both_rules)

            self._expand_rule(temp_rule)

    def _expand_rule(self, rule : GrammarRule):
        if CFGNormalizer.is_cnf_rule(rule):
            self.rules.append(GrammarRule(
                rule.production_symbol, 
                rule.pattern_str, 
                rule.reverse_with))

            return
        
        if len(rule.pattern) == 1:
            self._handle_single_prod_rule_case(rule)
            return

        # working pattern is a list of CFG production_symbols
        working_pattern = [part if GrammarRule.is_production_symbol(part) 
            else self._get_rule_for_literal(part).production_symbol
            for part in rule.pattern]

        # merges the last two production_symbols into a connector, and proceeds forward 
        # until the list has only 2 production symbols
        while len(working_pattern) > 2:
            # order because popping occurs as stack
            ruleB = working_pattern.pop()
            ruleA = working_pattern.pop()

            connector = self.get_rule_for_connector(ruleA, ruleB)
            working_pattern.append(connector.production_symbol)

        # merge the last two production_symbols in the working_pattern into a named rule
        ruleB = working_pattern.pop()
        ruleA = working_pattern.pop()

        # final connector should inherit the name of the original rule as effectively inherits the
        # production pattern of the rule
        connector = self.get_rule_for_connector(ruleA, ruleB, name=rule.production_symbol)

        # final connector should inherit the reverse_with method of the original rule as it inherits
        # the pattern
        connector.reverse_with.extend(rule.reverse_with)



####################################################################################################
##
## Parsing with Grammar
##
####################################################################################################
class CYKAlgo():
    """Class which encapsulates the CYK algo to parse a stream of tokens.
    """

    implementation = """
    The CYK algorithm parses a list of Tokens, attempting to reverse the CFG production rules 
    which were used to produce the Tokens, ultimately arriving at the starting state of the grammar.
    An ordered list of Tokens is considered grammatical if it can be produced by applying CFG
    production rules from the starting state of the grammar.

    The CYK algorithm is implemented as a dynamic programming algorithm, which attempts to 
    fill a dynamic programing table (dp_table) from the main diagonal outwards, until the 
    top right square is filled. The Tokens of the list are numbered (0..n), and the dp_table is
    of size (n x n). 

    Each entry in the DP table is a list of DpTableEntry(s) which contain information about a CFG
    production rule that can produce a sub-order of of the token list. In particular, entries at
    position (x, y) in the table correspond to the production rules which can produce the sub-order
    list_of_tokens[y : x + 1].
    
    Example:
    
          0   1   2   3   4   ... 
      0   .
      1       A   B   C   x
      2           .       A'
      3               .   B'
      4                   C'
      .
      .
      . 
      
    Entry A at (1,1) stores a rule which can produce list_of_tokens[1 : 1 + 1] 
        (i.e. token #1)
    Entry B at (2,1) stores a rule which can produce list_of_tokens[1 : 2 + 1] 
        (i.e. tokens #1 and #2)

    Therefore x at (4,1) must store rules which can produce list_of_tokens[1 : 4 + 1] = [1 : 5]
        (i.e. tokens #1, #2, #3, and #4)

    Note that two slices [a:b] and [b:c] are equivalently to the slice [a:c]

    To compute this, we only need to consider the following pairs of dp_table positions
    - (1,1) and (4,2), producing [1:2] and [2:5] respectively
    - (2,1) and (4,3), producing [1:3] and [3:5] respectively
    - (3,1) and (4,4), producing [1:4] and [4:5] respectively

    Geometrically, we can compute both elements of the pair based on the diagonal number of
    the entry for x, and a delta number (0..3).
    """

    def __init__(self, cfg : CFG):
        for rule in cfg.rules:
            if not CFGNormalizer.is_cnf_rule(rule):
                Raise.error("grammar is not normalized")

        self.cfg = cfg

    class DpTableEntry():
        """
        Entry in the dp_table which wraps a GrammarRule that can produce a sub-order of the input
        token list.
        """
        
        def __init__(self, 
            rule : GrammarRule, 
            x : int, 
            y : int, 
            diagonal_number : int, 
            delta : int=None, 
            lname : str=None, 
            rname : str=None
            ) -> None:
            """
            Entry in the DP table used during the CYK algorithm to reverse production rules. 
            An entry consists of a rule which can produce a section of the table and the
            coordinates of the rule.

            Args:
                rule (GrammarRule): Rule stored inside the table as a possible production rule
                x (int): y coordinate of the entry in the dp_table
                y (int): x coordinate of the entry in the dp_table
                diagonal_number (int): Number of the diagonal, counting up from the main diagonal 
                                       which begins a zero
                delta (int, optional): An offset which can be use to compute the coordinates of 
                                       the left and right entries in the dp_table. These entries 
                                       store the pattern which rule rule produces. Should only be 
                                       None if (diagonal_number = 0). Defaults to None.
                lname (str, optional): Name of the left production_symbol produced by the [rule]. 
                                       Defaults to None.
                rname (str, optional): Name of the right production_symbol produced by the [rule].
                                       Defaults to None.
            """
            self.rule = rule
            self.name = rule.production_symbol
            self.x = x
            self.y = y
            self.diagonal_number = diagonal_number

            if self.diagonal_number == 0:
                self.is_main_diagonal = True
                return

            if delta is None:
                Raise.error("delta should only be None for the main diagonal (0)")

            self.is_main_diagonal = False 
            self.delta = delta
            self.lname = lname
            self.rname = rname

        def get_left_child(self, dp_table):
            # left_child_x, left_child_y
            lcx, lcy = CYKAlgo.get_left_child(self.x, self.y, self.diagonal_number, self.delta)
            table_entries = dp_table[lcx][lcy]
            matching_entries = [e for e in table_entries if e.name == self.lname]

            if len(matching_entries) == 0:
                Raise.code_error("reached point in grammatical tree with no children")

            if len(matching_entries) > 1:
                Raise.notice("non-uniqueness, multiple possible production pathways")

            return matching_entries[0]

        def get_right_child(self, dp_table):
            # right_child_x, right_child_y
            rcx, rcy = CYKAlgo.get_right_child(self.x, self.y, self.diagonal_number, self.delta)
            table_entries = dp_table[rcx][rcy]
            matching_entries = [e for e in table_entries if e.name == self.rname]

            if len(matching_entries) == 0:
                Raise.code_error("reached point in grammatical tree with no children")

            if len(matching_entries) > 1:
                Raise.notice("non-uniqueness, multiple possible production pathways")

            return matching_entries[0]

        # end class

    @classmethod
    def tokens_to_ast_queue(cls, tokens : list) -> list[AstNode]:
        ast_queue = []
        for tok in tokens:
            astnode = AstNode()
            astnode.line_number = tok.line_number
            if tok.type == "var":
                ast_queue.append(astnode.leaf(tok.value))
            elif tok.type == "operator":
                ast_queue.append(astnode.operator(tok.value, match_with=OpCodes[tok.value]))
            elif tok.type == "symbol":
                ast_queue.append(astnode.symbol(tok.value))
            elif tok.type == "keyword":
                ast_queue.append(astnode.keyword(tok.value))
            elif tok.type == "string":
                ast_queue.append(astnode.literal("string", tok.value))
            elif tok.type == "int":
                ast_queue.append(astnode.literal("int", tok.value))
            elif tok.type == "bool":
                ast_queue.append(astnode.literal("bool", tok.value))
            else:
                Raise.code_error("unimplemented token type")

        return ast_queue

    def parse(self, tokens : list):
        self.n = len(tokens)
        self.asts = CYKAlgo.tokens_to_ast_queue(tokens)
        self.dp_table = [[[] for y in range(self.n)] for x in range(self.n) ] 
        self._do_parse()

        return self.dp_table

    def _do_parse(self):
        self._fill_first_diagonal()

        for i in range(1, self.n):
            self._fill_diagonal(i)

    def _get_diagonal(self, starting_x : int) -> list:
        x , y = starting_x, 0
        diagonal_points = []
        while x < self.n:
            diagonal_points.append((x, y))
            x += 1
            y += 1
        
        return diagonal_points

    def _get_producing_rules_for_token(self, match_with : str):
        return [rule for rule in self.cfg.rules
            if len(rule.pattern) == 1 and rule.pattern[0] == match_with]

    def _get_producing_rules(self, lname : str, rname : str):
        return [rule for rule in self.cfg.rules
            if len(rule.pattern) == 2 
                and rule.pattern[0] == lname 
                and rule.pattern[1] == rname]

    def _fill_first_diagonal(self):
        diagonal_points = self._get_diagonal(0)
        for point in diagonal_points:
            # x == y for diagonal(0)
            x, y = point

            astnode = self.asts[x]
            producing_rules = self._get_producing_rules_for_token(astnode.match_with)
            entries = [CYKAlgo.DpTableEntry(rule, x, y, 0) for rule in producing_rules]
            self.dp_table[x][y] = entries

    def _fill_diagonal(self, diagonal_number : int):
        diagonal_points = self._get_diagonal(diagonal_number)
        for point in diagonal_points:
            x, y = point
            for delta in range(diagonal_number):
                left_child_x, left_child_y = CYKAlgo.get_left_child(x, y ,diagonal_number, delta)
                lrule_names = list(map(lambda x: x.name, self.dp_table[left_child_x][left_child_y]))

                right_child_x, right_child_y = CYKAlgo.get_right_child(x, y, diagonal_number, delta)
                rrule_names = list(map(lambda x: x.name, self.dp_table[right_child_x][right_child_y]))

                rule_pairs = itertools.product(lrule_names, rrule_names)
                for rule_pair in rule_pairs:
                    lname, rname = rule_pair
                    producing_rules = self._get_producing_rules(lname, rname)
                    entries = \
                        [CYKAlgo.DpTableEntry(rule, x, y, diagonal_number, delta, lname, rname) 
                         for rule in producing_rules]
                            
                    self.dp_table[x][y] += entries

    @classmethod
    def get_left_child(cls, x : int, y : int, diagonal_number : int, delta : int) -> tuple[int, int]:
        """
        For a root entry at (x,y) the pertinent children would be: 
            left: (x-diagonal_number + delta, y)
            right (bottom/vertical): (x, y + 1 + delta)
        
        Respectively, these produce
            [y,x-diagonal_number+delta+1]
            [y+1+delta, x+1]
        
        And these slices are correct if 
            x-diagonal_number+delta+1 = y + 1 + delta
            x-y = diagonal_number
            true
        
        Args:
            x (int): x coordinate of the original entry
            y (int): y coordinate of the original entry
            diagonal_number (int): number of the diagonal of the original entry
            delta (int): specifies an offset for the table

        Returns:
            tuple[int, int]: coordinates of the left child in the dp_table
        """
        return x-diagonal_number+delta, y

    @classmethod
    def get_right_child(cls, x, y, diagnonal_number, delta):
        """
        See documentation for get_left_child.

        Returns:
            tuple[int, int]: coordinates of the right child in the dp_table
        """
        return x, y + 1 + delta

    @classmethod
    def is_main_diagonal(cls, x, y):
        return x == y

class AstBuilder():
    def __init__(self, astnodes, dp_table):
        self.astnodes = astnodes
        self.dp_table = dp_table

    def run(self):
        if "START" not in map(lambda x: x.name, self.dp_table[-1][0]):
            Raise.error("input is ungramatical")

        starting_entry = [x for x in self.dp_table[-1][0] if x.name == "START"][0]
        ast_list = self._recursive_descent(starting_entry)
        if len(ast_list) != 1:
            Raise.code_error("ast heads not parsed to single state")
        
        asthead = ast_list[0]
        self._postprocess(asthead)

        return asthead

    @classmethod
    def _postprocess(cls, node : AstNode):
        if node.op == "let" and node.vals[0].op == ":":
            # remove the ':' node underneath let
            node.vals = node.vals[0].vals
            node.left = node.vals[0]
            node.right = node.vals[1]

        if node.op == ":" or node.op == "let":
            if node.left.op == "var_name_tuple":
                for child in node.left.vals:
                    child.convert_var_to_tag()
            else:
                node.left.convert_var_to_tag()
            node.right.convert_var_to_tag()
            return

        if node.op == "function":
            node.vals[0].convert_var_to_tag()

        for child in node.vals:
            AstBuilder._postprocess(child)

    @classmethod
    def reverse_with_pool(cls, components : list) -> list:
        pass_up_list = []
        for component in components:
            if isinstance(component, list):
                pass_up_list += component
            elif isinstance(component, AstNode):
                pass_up_list.append(component)
            else:
                Raise.code_error("reverse engineering with pooling must be either list or AstNode")

        return pass_up_list

    @classmethod
    def reverse_with_merge(cls, components : list) -> list:
        flattened_comps = []
        for comp in components:
            if isinstance(comp, list):
                flattened_comps += comp
            else:
                flattened_comps.append(comp)

        newnode = AstNode()
        if len(flattened_comps) == 2:
            Raise.code_error("unimplemented unary ops")
        elif len(flattened_comps) == 3:
            newnode.line_number = flattened_comps[1].line_number
            newnode.binary(flattened_comps[1].op, flattened_comps[0], flattened_comps[2])
        else:
            Raise.code_error("should not merge with more than 3 nodes")
        
        return [newnode]

    @classmethod
    def reverse_with_build(cls, build_name : str, components : list):
        newnode = AstNode()
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        line_number = 0 if not flattened_components else flattened_components[0].line_number
        newnode.line_number = line_number
        
        return [newnode.plural(build_name, flattened_components)]

    @classmethod
    def reverse_with_pass(cls, components : list) -> list:
        return components

    def _recursive_descent(self, entry : CYKAlgo.DpTableEntry) -> list:
        if entry.is_main_diagonal:
            astnode = self.astnodes[entry.x]
            if astnode.type == "symbol":
                return []
            elif astnode.type == "keyword" and astnode.op not in Grammar.expressional_keywords:
                return []
            else:
                return [astnode]

        left = self._recursive_descent(entry.get_left_child(self.dp_table))
        right = self._recursive_descent(entry.get_right_child(self.dp_table)) 


        flag = "build="
        components = [left, right]
        for reversal_step in entry.rule.reverse_with:
            if reversal_step == "pass":
                components = AstBuilder.reverse_with_pool(components)
            elif reversal_step == "merge":
                components = AstBuilder.reverse_with_merge(components)
            elif reversal_step == "pool":
                components = AstBuilder.reverse_with_pool(components)
            elif reversal_step[0 : len(flag)] == flag:
                components = AstBuilder.reverse_with_build(reversal_step[len(flag): ], components)

        return components
