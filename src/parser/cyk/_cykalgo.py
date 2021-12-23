from __future__ import annotations

from grammar import CFGRule, CFG, CFGNormalizer
from ast import AstNode
from error import Raise

import itertools

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
        Entry in the dp_table which wraps a CFGRule that can produce a sub-order of the input
        token list.
        """
        
        def __init__(self, 
            rule : CFGRule, 
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
                rule (CFGRule): Rule stored inside the table as a possible production rule
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

    # TODO: this should be standardized based on type:value of each token
    @classmethod
    def tokens_to_ast_queue(cls, tokens : list) -> list[AstNode]:
        ast_queue = []
        for tok in tokens:
            astnode = AstNode()
            astnode.line_number = tok.line_number
            if tok.type == "var":
                ast_queue.append(astnode.leaf(tok.value))
            elif tok.type == "operator":
                ast_queue.append(astnode.operator(tok.value, match_with=tok.value))
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
                Raise.code_error(f"unimplemented token type: ({tok.type})")

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
