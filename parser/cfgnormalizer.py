from parser.action import Action
from parser.cfgrule import CFGRule

class CFG:
    def __init__(self, rules):
        self.rules = rules

class CFGNormalizer():
    """
    Converts a generic CFG grammar into a CNF CFG.
    """

    def __init__(self):
        # maps from literals : str to rules : CFGRule
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
        # new_cfg.set_start(self.starting_rule_name)

        return new_cfg

    @classmethod 
    def is_connector(cls, name : str) -> bool:
        return "_CONNECTOR" in name and name[-1] == "_"

    @classmethod
    def is_cnf_rule(cls, rule : CFGRule) -> bool:
        if len(rule.pattern) == 2:
            return all(map(CFGRule.is_production_symbol, rule.pattern))
        elif len(rule.pattern) == 1:
            return not CFGRule.is_production_symbol(rule.pattern[0])
        else:
            return False

    def _add_new_rule_for_literal(self, literal : str) -> CFGRule:
        new_rule = CFGRule(f"_TOKENS{self.n_rules_for_literals}_", literal, Action("pass"))
        self.n_rules_for_literals += 1
        self.rules_for_literals[literal] = new_rule
        self.rules.append(new_rule)

        return new_rule

    def _get_rule_for_literal(self, literal : str) -> CFGRule:
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

            new_connector = CFGRule(name, pattern, Action("pool"))

            self.n_connector_rules += 1
            self.connectors[key] = new_connector
            self.rules.append(new_connector)

            return new_connector

        return existing_rule

    # in the case that [rule] produces a pattern consiting of a single production_symbol, substitute 
    # the pattern of that production_symbol in for it and expand the resulting temporary rule
    def _handle_single_prod_rule_case(self, rule : CFGRule) -> None:
        substitute_production_symbol = rule.pattern[0]
        substitutions = [r for r in self.original_cfg.rules 
            if r.production_symbol == substitute_production_symbol]

        for rule_to_sub in substitutions:
            pattern_to_sub = rule_to_sub.pattern_str
            
            # rule_to_sub.reverse with should be executed before the original rule
            steps_to_reverse_both_rules = [*rule_to_sub.reverse_with, *rule.reverse_with]
            
            temp_rule = CFGRule(
                rule.production_symbol, 
                pattern_to_sub, 
                steps_to_reverse_both_rules)

            self._expand_rule(temp_rule)

    def _expand_rule(self, rule : CFGRule):
        if CFGNormalizer.is_cnf_rule(rule):
            self.rules.append(CFGRule(
                rule.production_symbol, 
                rule.pattern_str, 
                rule.reverse_with))

            return
        
        if len(rule.pattern) == 1:
            self._handle_single_prod_rule_case(rule)
            return

        # working pattern is a list of CFG production_symbols
        working_pattern = [part if CFGRule.is_production_symbol(part) 
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
