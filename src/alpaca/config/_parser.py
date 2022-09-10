from __future__ import annotations
import re
from typing import Any, Callable

from alpaca.config._config import Config
from alpaca.config._tokenrule import TokenRule

from alpaca.grammar import CFGRule, Action

class parser():
    @classmethod
    def run(cls, filename: str) -> Config:
        with open(filename, 'r') as f:
            txt = f.read()
        config1 = StateMachine().run(txt) 
        return config1

# a symbolics mask encapsulates line headers of the following sort:
#       <type>              ->  <regex>
# this can be applied to to each following line (provided a second mask is not 
# defined to override this) to parse the line into a TokenRule. effectively, all
# space separated characters on the left of the '->' get split and stripped, and 
# turned into the token type. The regex on the right side of the '->' gets stripped
# and turned into the regex identifying rule.
class SymbolicMask():
    def __init__(self, line: str):
        if not StateMachine.symbolics_mask_regex.match(line):
            raise Exception(f"Line '{line}' is not of the form '<type> -> <regex>'")
        
        pos = line.find("->")
        self.type_end = pos
        self.regex_start = pos + len("->")

    def apply(self, line : str) -> TokenRule:
        types = line[0: self.type_end].strip().split(" ")
        regex = line[self.regex_start: ].strip()

        return TokenRule(regex, types)

class Params:
    def __init__(self, txt: str):
        self.state = "start"
        self.lines = [l for l in txt.split("\n") if l]
        self.current_line = None
        self.symbolics_mask: SymbolicMask = None
        self.current_production_symbol = None
        self.current_action: Action

        self.tokenrules = []
        self.production_rules = []

    def add_token_rule(self, rule: TokenRule) -> None:
        self.tokenrules.append(rule)

    def transition_to_next_line(self):
        if self.lines:
            self.current_line = self.lines[0]
            self.lines = self.lines[1: ]
        else:
            self.current_line = None

class Transition:
    def __init__(self, state: str, f) -> None:
        self.f = f
        self.for_state = state

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.f(*args, **kwds)

# annotation used to denotate state
def state(name: str):
    return name

class StateMachine:
    symbolics_section_regex = re.compile(r"SYMBOLICS")
    structure_section_regex = re.compile(r"STRUCTURE")

    empty_line_regex = re.compile(r"[ \t]*$")
    symbolics_mask_regex = re.compile(r"( *<type> *)->( *<regex>)")
    action_flag_regex = re.compile(r"[ \t]*@action")
    production_symbol_declaration_regex = re.compile(r" *(\w+) *-> *$")
    production_pattern_definition_regex = re.compile(r" *\| *(.+)")
    full_rule_definition_regex = re.compile(r" *(\w+) *-> *((?:[^\s]+ *)+)")
    comment_regex = re.compile(r"[ |\t]*#.*?$")

    def __init__(self):
        attrs = dir(self)
        transitions: list[Transition] = [getattr(self, k) for k in attrs
            if isinstance(getattr(self, k), Transition)]
        self.states = dict({ t.for_state: t for t in transitions})

    def run(self, txt: str):
        p = Params(txt)
        while p.state != state("end"):
            self._run_step(p)
        return Config(p.tokenrules, p.production_rules)

    def _run_step(self, p: Params):
        state_function = self.states.get(p.state, None)
        if state_function is None:
            raise Exception(f"No transition matches state '{p.state}'")

        # update the state in the parameters with the value obtained from the 
        # state function 
        p.state = state_function(p)
        if p.state is None:
            raise Exception(
                f"No state transition for state={p.state}, given line={p.current_line}")

    def transition(f: Callable[[Any], Any]):
        return Transition(f.__name__, f)

    @transition
    def start(p: Params) -> str:
        if p.current_line is None:
            p.transition_to_next_line()
            return state("start")
        if StateMachine.symbolics_section_regex.match(p.current_line):
            p.transition_to_next_line()
            return state("symbolics_section")
        if StateMachine.empty_line_regex.match(p.current_line):
            p.transition_to_next_line()
            return state("start")
        if StateMachine.comment_regex.match(p.current_line):
            p.transition_to_next_line()
            return state("start")
        return None 

    @transition 
    def symbolics_section(p: Params) -> str:
        should_pass_line = (StateMachine.empty_line_regex.match(p.current_line)
            or StateMachine.comment_regex.match(p.current_line))
        
        if should_pass_line:
            p.transition_to_next_line()
            return state("symbolics_section")
        if StateMachine.symbolics_mask_regex.match(p.current_line):
            # no transition as the symbolics_mask state needs to use this line
            return state("symbolics_mask")
        if StateMachine.structure_section_regex.match(p.current_line):
            p.transition_to_next_line()
            return state("structure_section")
        
        rule = p.symbolics_mask.apply(p.current_line)
        p.tokenrules.append(rule)
        p.transition_to_next_line()
        return state("symbolics_section")

    @transition
    def symbolics_mask(p: Params) -> str:
        p.symbolics_mask = SymbolicMask(p.current_line)
        p.transition_to_next_line()
        return state("symbolics_section")

    @transition
    def structure_section(p: Params) -> str:
        if p.current_line is None:
            return state("end")

        should_pass_line = (StateMachine.empty_line_regex.match(p.current_line)
            or StateMachine.comment_regex.match(p.current_line))
        
        if should_pass_line:
            p.transition_to_next_line()
            return state("structure_section")
        if StateMachine.action_flag_regex.match(p.current_line):
            # no transition to next line
            return state("structure_annotation_action")
        if StateMachine.full_rule_definition_regex.match(p.current_line):
            # no transition to next line
            return state("structure_rule_full")
        if StateMachine.production_symbol_declaration_regex.match(p.current_line):
            # no transition to next line
            return state("structure_rule_header")
        if StateMachine.production_pattern_definition_regex.match(p.current_line):
            # no transition to next line
            return state("structure_rule_definition")
        
    @transition
    def structure_annotation_action(p: Params) -> str:
        parts = p.current_line.strip().split(' ')
        p.current_action = Action(
            type=parts[1], 
            value=parts[2] if len(parts) == 3 else "")

        p.transition_to_next_line()
        return state("structure_section")

    @transition
    def structure_rule_full(p: Params) -> str:
        match = StateMachine.full_rule_definition_regex.match(p.current_line)
        p.production_rules.append(
            CFGRule(match.group(1), match.group(2), p.current_action))

        p.transition_to_next_line()
        return state("structure_section")

    @transition
    def structure_rule_header(p: Params) -> str:
        match = StateMachine.production_symbol_declaration_regex.match(p.current_line)
        p.current_production_symbol = match.group(1)
        p.transition_to_next_line()
        return state("structure_section")

    @transition
    def structure_rule_definition(p: Params) -> str:
        match = StateMachine.production_pattern_definition_regex.match(p.current_line)
        p.production_rules.append(
            CFGRule(p.current_production_symbol, match.group(1), p.current_action))
        
        p.transition_to_next_line()
        return state("structure_section")
