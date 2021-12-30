from __future__ import annotations
import re

from alpaca.config._config import Config
from alpaca.config._regextokenrule import RegexTokenRule

from alpaca.grammar import CFGRule, Action
from error import Raise

class ConfigParser():
    class SymbolicMask():
        def __init__(self, token_part_len):
            self.token_start = 0
            self.token_end = token_part_len
            self.regex_start = token_part_len + 2

        def apply(self, line : str) -> tuple[str, str, str|None]:
            regex = line[self.regex_start : ].strip()
            token_line = line[self.token_start : self.token_end].strip()
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

    symbolics_headings_regex_str = "( *<type> *<value> *)->( *<regex>)"
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
            return True, CFGRule(current_production_symbol, match.group(1), current_action)
        
        return False, None

    @classmethod
    def _try_parse_full_rule_definition(cls, line : str, current_action : Action):
        match = cls.full_rule_definition_regex.match(line)
        if match:
            return True, CFGRule(match.group(1), match.group(2), current_action)

        return False, None
