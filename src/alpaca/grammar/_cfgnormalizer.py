from alpaca.grammar import CFG, CFGRule, Action

class CFGNormalizer():
    """
    Converts a generic CFG grammar into a CNF CFG.
    """

    def __init__(self):
        self.rules_for_literals: dict[str, CFGRule] = {}
        self.n_rules_for_literals: int = 0
        self.n_connector_rules: int = 0

        self.connectors: dict[str: CFGRule] = {}
        self.normalized_rules: list[CFGRule] = []
        self.original_cfg: CFG = None

    def run(self, cfg: CFG) -> CFG:
        # reset state
        self.rules_for_literals = {}
        self.n_rules_for_literals = 0
        self.n_connector_rules = 0
        self.connectors = {}
        self.normalized_rules = []

        self.original_cfg = cfg
        for rule in cfg.rules:
            self._expand_rule(rule)

        new_cfg = CFG(self.normalized_rules, self.original_cfg.terminals)
        return new_cfg

    @staticmethod
    def is_connector(name: str) -> bool:
        return "_CONNECTOR" in name and name[-1] == "_"

    @staticmethod
    def name_for_connector(id: int) -> str:
        return f"_CONNECTOR{id}_"

    def generate_name_for_connector(self) -> str:
        self.n_connector_rules += 1
        return CFGNormalizer.name_for_connector(self.n_connector_rules)

    @staticmethod
    def is_cnf_rule(cfg: CFG, rule: CFGRule) -> bool:
        match len(rule.pattern):
            case 2: return all(map(cfg.is_production_symbol, rule.pattern))
            case 1: return not cfg.is_production_symbol(rule.pattern[0])
            case _: return False

    @staticmethod
    def rule_for_literal(id: int, literal_text: str) -> CFGRule:
        return CFGRule(f"__{id}({literal_text})", literal_text, Action("pass"))

    def _add_new_rule_for_literal(self, literal: str) -> CFGRule:
        self.n_rules_for_literals += 1
        new_rule = CFGNormalizer.rule_for_literal(self.n_rules_for_literals, literal)
        self.rules_for_literals[literal] = new_rule
        self.normalized_rules.append(new_rule)
        return new_rule

    def _get_rule_for_literal(self, literal : str) -> CFGRule:
        existing_rule = self.rules_for_literals.get(literal, None)
        if existing_rule is None:
            return self._add_new_rule_for_literal(literal)
        return existing_rule

    @staticmethod
    def get_key_for_connector(name, left_rule: str, right_rule: str) -> str:
        prefix = name + ":"  if name is not None else ""
        return f"{prefix}{left_rule}:{right_rule}"

    def _add_new_connector(self, name: str | None, left_rule: str, right_rule: str,
                           original_entry: str = None) -> CFGRule:

        pattern = f"{left_rule} {right_rule}"
        if name is None: name = self.generate_name_for_connector()
        new_connector = CFGRule(name, pattern, Action("pool"), original_entry=original_entry)

        self.connectors[CFGNormalizer.get_key_for_connector(name, left_rule, right_rule)] = new_connector
        self.normalized_rules.append(new_connector)
        return new_connector

    def get_rule_for_connector(
            self,
            left_rule: str,
            right_rule: str,
            name: str = None,
            original_entry: str = None):

        key = CFGNormalizer.get_key_for_connector(name, left_rule, right_rule)
        existing_rule = self.connectors.get(key, None)
        if existing_rule is None:
            return self._add_new_connector(name, left_rule, right_rule, original_entry=original_entry)
        return existing_rule

    # in the case that [rule] produces a pattern consisting of a single production_symbol, substitute
    # the pattern of that production_symbol in for it and expand the resulting temporary rule
    def _handle_single_prod_rule_case(self, rule: CFGRule) -> None:
        substitute_production_symbol = rule.pattern[0]
        substitutions = [r for r in self.original_cfg.rules
            if r.production_symbol == substitute_production_symbol]

        for rule_to_sub in substitutions:
            pattern_to_sub = rule_to_sub.pattern_str

            # rule_to_sub.reverse with should be executed before the original rule
            steps_to_reverse_both_rules = [*rule_to_sub.actions, *rule.actions]

            temp_rule = CFGRule(
                rule.production_symbol,
                pattern_to_sub,
                steps_to_reverse_both_rules,
                original_entry=rule.original_entry)

            self._expand_rule(temp_rule)

    def _expand_rule(self, rule: CFGRule):
        if CFGNormalizer.is_cnf_rule(self.original_cfg, rule):
            self.normalized_rules.append(rule.copy())
            return

        if len(rule.pattern) == 1:
            self._handle_single_prod_rule_case(rule)
            return

        # working pattern is a list of CFG production_symbols
        working_pattern = [part if self.original_cfg.is_production_symbol(part)
            else self._get_rule_for_literal(part).production_symbol
            for part in rule.pattern]

        # merges the last two production_symbols into a connector, and proceeds forward
        # until the list has only 2 production symbols
        while len(working_pattern) > 2:
            # order because popping occurs as stack
            right_symbol = working_pattern.pop()
            left_symbol = working_pattern.pop()

            connector = self.get_rule_for_connector(
                left_symbol,
                right_symbol,
                original_entry=rule.original_entry)
            working_pattern.append(connector.production_symbol)

        # merge the last two production_symbols in the working_pattern into a named rule
        right_symbol = working_pattern.pop()
        left_symbol = working_pattern.pop()

        # final connector should inherit the name of the original rule as effectively inherits the
        # production pattern of the rule
        connector = self.get_rule_for_connector(
            left_symbol,
            right_symbol,
            name=rule.production_symbol,
            original_entry=rule.original_entry)

        # final connector should inherit the reverse_with method of the original rule as it inherits
        # the pattern
        connector.actions.extend(rule.actions)
