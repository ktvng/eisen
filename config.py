from __future__ import annotations
import re

from error import Raise
from functools import reduce

class RegexTokenRule():
    def __init__(self, regex : str, type : str, value : str=None):
        self.regex_str = regex
        self.regex = re.compile(regex)
        self.type = type
        self.value = value

    def __str__(self):
        return f"[{self.regex_str}] -> {self.type} {self.value}"

    def match(self, text : str):
        match_obj = self.regex.match(text)
        if match_obj:
            match_str = match_obj.group(0)
            return match_str, len(match_str), self

        return "", 0, self

class Action():
    def __init__(self, type : str, value : str = ""):
        self.type = type
        self.value = value

class CFGRule2():
    def __init__(self, production_symbol : str, pattern_str : str, action : Action):
        self.production_symbol = production_symbol
        self.pattern_str = pattern_str
        self.pattern = [s.strip() for s in pattern_str.split(' ') if s != ""]
        self.actions = [action]

        # TODO: replace with above; here for back-compat
        self.reverse_with = [action]

    def __str__(self):
        return f"{self.production_symbol} -> {self.pattern_str}"

class Config():
    def __init__(self, regex_rules : list[RegexTokenRule], cfg_rules : list[CFGRule2]):
        self.regex_rules = regex_rules
        self.cfg_rules = cfg_rules

class ConfigParser():
    class SymbolicMask():
        def __init__(self, regex_part_len):
            self.regex_start = 0
            self.regex_end = regex_part_len
            self.token_start = regex_part_len + 2

        def apply(self, line : str) -> tuple[str, str, str|None]:
            regex = line[self.regex_start : self.regex_end].strip()
            token_line = line[self.token_start : len(line)].strip()
            token_parts = token_line.split(' ')

            if len(token_parts) == 1:
                return regex, token_parts[0], None
            elif len(token_parts) == 2:
                return regex, token_parts[0], token_parts[1]
            else:
                Raise.code_error("Error: malformed config")

    symbolics_section = "SYMBOLICS" 
    structure_section = "STRUCTURE"

    top_level_regex_str = f"{symbolics_section}|{structure_section}"
    top_level_regex = re.compile(top_level_regex_str)

    symbolics_headings_regex_str = "( *<regex> *)->( *<type> *<value>)"
    symbolics_headings_regex = re.compile(symbolics_headings_regex_str)

    action_flag_regex_str = " *@action"
    action_flag_regex = re.compile(action_flag_regex_str)

    production_symbol_declaration_regex_str = " *(\w+) *-> *\n"
    production_symbol_declaration_regex = re.compile(production_symbol_declaration_regex_str)
    
    production_pattern_definition_regex_str = " *\| *(.+)"
    production_pattern_definition_regex = re.compile(production_pattern_definition_regex_str)

    full_rule_definition_regex_str = " *(\w+) *-> *(.+)"
    full_rule_definition_regex = re.compile(full_rule_definition_regex_str)

    comment_regex_str = "[ |\t]*#.*?\n"
    comment_regex = re.compile(comment_regex_str)

    @classmethod
    def run(cls, filename):
        with open(filename, 'r') as f:
            lines = f.readlines()

        current_section = "ignore"
        current_symbolics_mask = None
        current_action = None
        current_production_symbol = None
        regex_tokens = []
        cfg_rules = []
        for line in lines:
            if not line.strip():
                continue

            if cls.comment_regex.match(line):
                continue

            was_section_change, current_section = cls._try_section_change(current_section, line)
            if was_section_change:
                continue

            if current_section == "ignore":
                continue

            if current_section == cls.symbolics_section:
                was_heading, current_symbolics_mask = \
                    cls._try_parse_symbolics_heading(current_symbolics_mask, line)

                if was_heading:
                    continue
                
                if current_symbolics_mask is None:
                    Raise.code_error("Error: symbolics header not yet defined.")

                regex, type, value = current_symbolics_mask.apply(line)
                regex_tokens.append(RegexTokenRule(regex, type, value))

            elif current_section == cls.structure_section:
                was_action, current_action = cls._try_change_action(current_action, line)
                if was_action:
                    continue

                was_production_symbol_declaration, current_production_symbol =\
                    cls._try_change_production_symbol(current_production_symbol, line)

                if was_production_symbol_declaration:
                    continue

                was_production_pattern_definition, cfg_rule = \
                    cls._try_parse_production_pattern(
                        current_production_symbol, 
                        current_action, 
                        line)

                if was_production_pattern_definition:
                    cfg_rules.append(cfg_rule)
                    continue

                was_full_rule_definition, cfg_rule = \
                    cls._try_parse_full_rule_definition(line, current_action)

                if was_full_rule_definition:
                    current_production_symbol = None
                    cfg_rules.append(cfg_rule)
        
        return Config(regex_tokens, cfg_rules)
                

    @classmethod
    def _try_section_change(cls, current_section : str, line : str):
        match = cls.top_level_regex.match(line)
        if match:
            return True, match.group(0)
            
        return False, current_section
                  
    @classmethod
    def _try_parse_symbolics_heading(cls, current_symbolic_mask : ConfigParser.SymbolicsMask, line : str):
        match = cls.symbolics_headings_regex.match(line)
        if match:
            return True, ConfigParser.SymbolicMask(len(match.group(1)))

        return False, current_symbolic_mask

    @classmethod
    def _try_change_action(cls, current_action : Action, line : str):
        match = cls.action_flag_regex.match(line)
        if match:
            parts = line.strip().split(' ')
            type = parts[1]
            value = parts[2] if len(parts) == 3 else ""
            return True, Action(type, value)

        return False, current_action

    @classmethod
    def _try_change_production_symbol(cls, current_production_symbol : str, line : str):
        match = cls.production_symbol_declaration_regex.match(line)
        if match:
            return True, match.group(1)
        
        return False, current_production_symbol

    @classmethod
    def _try_parse_production_pattern(cls, 
            current_production_symbol : str, 
            current_action : Action, 
            line : str):

        match = cls.production_pattern_definition_regex.match(line)
        if match:
            return True, CFGRule2(current_production_symbol, match.group(1), current_action)
        
        return False, None

    @classmethod
    def _try_parse_full_rule_definition(cls, line : str, current_action : Action):
        match = cls.full_rule_definition_regex.match(line)
        if match:
            return True, CFGRule2(match.group(1), match.group(2), current_action)

        return False, None

class Token2():
    def __init__(self, type : str, value : str, line_number : int):
        self.type = type
        self.value = value
        self.line_number = line_number

    type_print_len = 16
    def __str__(self):
        padding = max(0, self.type_print_len - len(self.type))
        return f"{self.line_number}\t{self.type}{' ' * padding}{self.value}"

class Lexer():
    _newline_regex = re.compile("\n+")

    @classmethod
    def _try_increment_line_number(cls, text : str):
        match = cls._newline_regex.match(text)
        if match:
            return len(match.group(0))
        
        return 0

    @classmethod
    def run(cls, text : str, config : Config):
        tokens = []
        line_number = 1
        while text:
            match_tuples = [rule.match(text) for rule in config.regex_rules]
            longest_match = reduce(
                lambda a, b: a if a[1] >= b[1] else b, 
                match_tuples)

            line_number += cls._try_increment_line_number(text)
            match_str, match_len, rule = longest_match
            token_value = rule.value if rule.value is not None else match_str
            if rule.type != "none":
                tokens.append(Token2(rule.type, token_value, line_number))

            text = text[match_len :]
            if match_len == 0:
                Raise.code_error(f"Error: no regex matches, head of input: {text[0:10]}")

        return tokens



cf = ConfigParser.run("./grammar.gm")
# for rule in cf.cfg_rules:
#     print(rule)

# for rule in cf.regex_rules:
#     print(rule)

with open("./test.rs", 'r') as f:
    text = f.read()

tokens = Lexer.run(text, cf)
# [print(x) for x in tokens]

from grammar import CFGNormalizer

class CFG2():
    def __init__(self, rules):
        self.rules = rules

cfg = CFG2(cf.cfg_rules)

normer = CFGNormalizer()
cfg = normer.run(cfg)

# for rule in cfg.rules:
#     print(rule)

from grammar import CYKAlgo

cyk = CYKAlgo(cfg)
cyk.parse(tokens)

for entry in cyk.dp_table[-1][0]:
    print(entry.name)


from grammar import AstBuilder

ab = AstBuilder(cyk.asts, cyk.dp_table)
ast = ab.run()

print("########")
ast.print()