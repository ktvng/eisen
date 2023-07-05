from __future__ import annotations
from typing import List
import itertools
import random
from alpaca.grammar import CFGRule, CFG, CFGNormalizer
from alpaca.lexer import Token
from alpaca.clr import ASTToken

class DpTableEntry():
    def __init__(self,
            rule : CFGRule,
            x : int,
            y : int,
            delta : int=None,
            lname : str=None,
            rname : str=None) -> None:

        self.rule = rule
        self.name = rule.production_symbol
        self.x = x
        self.y = y
        self.diagonal = x - y

        if self.diagonal == 0:
            self.is_main_diagonal = True
        else:
            self.is_main_diagonal = False

        self.delta = delta
        self.lname = lname
        self.rname = rname

    def __str__(self) -> str:
        return f"({self.x}, {self.y}: {self.rule} <{self.lname}, {self.rname}>)"

    def _get_unique_rules(self, entries: list[DpTableEntry]):
        unique_entries = []
        for entry in entries:
            if entry.rule not in [e.rule for e in unique_entries]:
                unique_entries.append(entry)

        return unique_entries

    def get_left_child(self, dp_table : DpTable):
        # left_child_x, left_child_y
        lcx, lcy = CYKAlgo.get_left_child_point(self.x, self.y, self.delta)
        entries = dp_table[lcx][lcy]
        matching_entries = [e for e in entries if e.name == self.lname]
        unique_entries = self._get_unique_rules(matching_entries)

        if not unique_entries:
            raise Exception("reached point in gramatical tree with no children??")
        if len(unique_entries) > 1:
            print("non-uniqueness, multiple production pathways (picked first)")
            random.shuffle(unique_entries)
            for entry in unique_entries:
                print(entry)

        return unique_entries[0]

    def get_right_child(self, dp_table : DpTable):
        # right_child_x, right_child_y
        rcx, rcy = CYKAlgo.get_right_child_point(self.x, self.y, self.delta)
        entries = dp_table[rcx][rcy]
        matching_entries = [e for e in entries if e.name == self.rname]
        unique_entries = self._get_unique_rules(matching_entries)

        if not unique_entries:
            raise Exception("reached point in gramatical tree with no children??")
        if len(unique_entries) > 1:
            print("non-uniqueness, multiple production pathways (picked first)")
            random.shuffle(unique_entries)
            print(self.rname)
            print(self.name)

        return unique_entries[0]

DpTable = List[List[List[DpTableEntry]]]

class RuleQuery():
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        self._production_lookup_table = {}
        self._token_lookup_table = {}
        self._init_lookup_tables()

    def _init_lookup_tables(self):
        for rule in self.cfg.rules:
            if len(rule.pattern) == 1:
                key = rule.pattern[0]
                if key in self._token_lookup_table:
                    self._token_lookup_table[key].append(rule)
                else:
                    self._token_lookup_table[key] = [rule]
            else:
                key = (rule.pattern[0], rule.pattern[1])
                if key in self._production_lookup_table:
                    self._production_lookup_table[key].append(rule)
                else:
                    self._production_lookup_table[key] = [rule]
        pass

    def get_rules_for_token(self, tok: ASTToken) -> list[CFGRule]:
        return self._token_lookup_table.get(tok.type, [])

    def get_rules(self, lname: str, rname: str) -> list[CFGRule]:
        return self._production_lookup_table.get((lname, rname), [])

class CYKAlgo:
    def __init__(self, cfg : CFG):
        for rule in cfg.rules:
            if not CFGNormalizer.is_cnf_rule(cfg, rule):
                raise Exception("grammar is not normalized")

        self.cfg = cfg
        self.query = RuleQuery(cfg)

    @classmethod
    def tokens_to_clrtoken(cls, tokens : list[Token]) -> list[ASTToken]:
        return [ASTToken(t.rule.type_chain, t.value, t.line_number) for t in tokens]

    def _fill_first_diagonal_special(self):
        points = self._get_points_on_diagonal(0)
        for point in points:
            x, y = point
            rules = [rule for rule in self.cfg.rules if rule.production_symbol == "CONTEXT"]
            bootstrap_rule = rules[0]
            self.dp_table[x][y] = [DpTableEntry(bootstrap_rule, x, y)]



    def parse_clrtokens(self, tokens: list[ASTToken]):
        self.n = len(tokens)
        self.tokens = tokens
        self.dp_table = [[[] for y in range(self.n)] for x in range(self.n)]

        self._fill_first_diagonal_special()
        for i in range (1, self.n):
            self._fill_diagonal(i)
        # can't call do_parse b/c filling first row is different
        # self._do_parse()

    def parse(self, tokens : list[Token]):
        self.n = len(tokens)
        self.tokens = CYKAlgo.tokens_to_clrtoken(tokens)
        self.dp_table = [[[] for y in range(self.n)] for x in range(self.n)]
        self._do_parse()

    def _do_parse(self):
        self._fill_first_diagonal()
        for i in range (1, self.n):
            self._fill_diagonal(i)

    def _get_points_on_diagonal(self, starting_x : int) -> list[tuple[int, int]]:
        return [(starting_x + delta, delta) for delta in range(self.n - starting_x)]

    def _get_producing_rules_for_clrtoken(self, tok : ASTToken) -> list[CFGRule]:
        return self.query.get_rules_for_token(tok)
        return [rule for rule in self.cfg.rules
            if len(rule.pattern) == 1 and tok.type == rule.pattern[0]]

    def _get_producing_rules_for(self, lname : str, rname : str) -> list[CFGRule]:
        return self.query.get_rules(lname, rname)
        return [rule for rule in self.cfg.rules
            if len(rule.pattern) == 2
                and rule.pattern[0] == lname
                and rule.pattern[1] == rname]

    def _fill_first_diagonal(self):
        points = self._get_points_on_diagonal(0)
        for point in points:
            x, y = point
            clrtoken = self.tokens[x]
            producing_rules = self._get_producing_rules_for_clrtoken(clrtoken)
            self.dp_table[x][y] = [DpTableEntry(rule, x, y) for rule in producing_rules]

    def _fill_diagonal(self, diagonal_number : int):
        points = self._get_points_on_diagonal(diagonal_number)
        for point in points:
            x, y = point
            for delta in range(diagonal_number):
                lchild_x, lchild_y = CYKAlgo.get_left_child_point(*point, delta)
                lrule_names = list(map(lambda x: x.name, self.dp_table[lchild_x][lchild_y]))

                rchild_x, rchild_y = CYKAlgo.get_right_child_point(*point, delta)
                rrule_names = list(map(lambda x: x.name, self.dp_table[rchild_x][rchild_y]))

                for l_and_r_names in itertools.product(lrule_names, rrule_names):
                    producing_rules = self._get_producing_rules_for(*l_and_r_names)
                    self.dp_table[x][y] += \
                        [DpTableEntry(rule, *point, delta, *l_and_r_names)
                            for rule in producing_rules]

    @classmethod
    def get_left_child_point(cls, x : int, y : int, delta : int) -> tuple[int, int]:
        diagonal_number = x - y
        return (x - diagonal_number + delta, y)

    @classmethod
    def get_right_child_point(cls, x : int, y : int, delta : int) -> tuple[int, int]:
        return (x, y + 1 + delta)

    @classmethod
    def is_main_diagonal(cls, x : int, y : int) -> bool:
        return x == y
