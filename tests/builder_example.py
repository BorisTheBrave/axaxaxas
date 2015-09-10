# This is the example comes from builders.rst

from axaxaxas import ParseRule, Terminal as T, NonTerminal as NT, ParseRuleSet, parse, Builder


class LoggingBuilder(Builder):
    """Builder implementation that simply records what methods were invoked"""
    def __init__(self, rule_by_name):
        self.rules_by_name = rule_by_name
        self.count = 0
        self.lines = []

    def format(self, v):
        if isinstance(v, int):
            return "v"+str(v)
        if isinstance(v, list):
            return "["+", ".join(map(self.format, v))+"]"
        else:
            return repr(v)

    def log(self, event, context, *args):
        self.count += 1
        for rule_name, rule in self.rules_by_name.items():
            if rule is context.rule:
                break
        else:
            rule_name = "None"
        line = "{0} = builder.{1}({{{2}, {3}}}{4})".format(
            self.format(self.count),
            event,
            rule_name,
            context.symbol_index,
            "".join(", "+self.format(v) for v in args))
        self.lines.append(line)
        return self.count

    def get_text(self):
        return "\n".join(self.lines)

    def compare(self, output):
        i = 0
        for oline in output.split("\n"):
            if "#" in oline: oline = oline[:oline.index("#")]
            oline = oline.strip()
            if not oline: continue
            if oline != self.lines[i]:
                print(repr(oline))
                print(repr(self.lines[i]))
                assert oline == self.lines[i], "Failed at line {}".format(i+1)
            i += 1

    def start_rule(self, context):
        return self.log("start_rule", context)

    def terminal(self, context, token):
        return self.log("terminal", context, token)

    def skip_optional(self, context, prev_value):
        return self.log("skip_optional", context, prev_value)

    def begin_multiple(self, context, prev_value):
        return self.log("begin_multiple", context, prev_value)

    def end_multiple(self, context, prev_value):
        return self.log("end_multiple", context, prev_value)

    def extend(self, context, prev_value, extension_value):
        return self.log("extend", context, prev_value, extension_value)

    def merge_horizontal(self, context, values):
        return self.log("merge_horizontal", context, values)

    def merge_vertical(self, context, values):
        return self.log("merge_vertical", context, values)


def run(lcls, head, tokens, output):
    grammar = ParseRuleSet()
    for rule_name, rule in sorted(lcls.items(), reverse=True):
        grammar.add(rule)
    logging_builder = LoggingBuilder(lcls)
    parse(grammar, head, tokens).apply(logging_builder)
    # print(logging_builder.get_text())
    logging_builder.compare(output)


def ex1():
    rule1 = ParseRule("rule 1", [T("a"), NT("rule 2"), T("c")])
    rule2 = ParseRule("rule 2", [T("b")])

    run(locals(), "rule 1", ["a", "b", "c"], """
    v1 = builder.start_rule({rule2, 0})
    v2 = builder.terminal({rule2, 0}, 'b')
    v3 = builder.extend({rule2, 0}, v1, v2)
    v4 = builder.start_rule({rule1, 0})
    v5 = builder.terminal({rule1, 0}, 'a')
    v6 = builder.extend({rule1, 0}, v4, v5)
    v7 = builder.extend({rule1, 1}, v6, v3)
    v8 = builder.terminal({rule1, 1}, 'c')
    v9 = builder.extend({rule1, 2}, v7, v8)
    """)
ex1()


def ex2():
    rule1 = ParseRule("sentence", [T("hello")])
    rule2 = ParseRule("sentence", [T("hello")])
    run(locals(), "sentence", ["hello"], """
    v1 = builder.start_rule({rule1, 0})
    v2 = builder.terminal({rule1, 0}, 'hello')
    v3 = builder.extend({rule1, 0}, v1, v2)
    v4 = builder.start_rule({rule2, 0})
    v5 = builder.terminal({rule2, 0}, 'hello')
    v6 = builder.extend({rule2, 0}, v4, v5)
    v7 = builder.merge_vertical({None, 0}, [v6, v3])
    """)
ex2()


def ex3():
    sentence = ParseRule("sentence", [NT("X"), NT("Y")])
    X = ParseRule("X", [T("a", optional=True)])
    Y = ParseRule("Y", [T("a", optional=True)])

    run(locals(), "sentence", ["a"], """
    v1 = builder.start_rule({Y, 0})             # After token 0
    v2 = builder.skip_optional({Y, 0}, v1)
    v3 = builder.start_rule({X, 0})
    v4 = builder.terminal({X, 0}, 'a')
    v5 = builder.extend({X, 0}, v3, v4)
    v6 = builder.start_rule({sentence, 0})
    v7 = builder.extend({sentence, 0}, v6, v5)
    v8 = builder.start_rule({Y, 0})             # Before token 0
    v9 = builder.terminal({Y, 0}, 'a')
    v10 = builder.extend({Y, 0}, v8, v9)
    v11 = builder.skip_optional({X, 0}, v3)
    v12 = builder.extend({sentence, 0}, v6, v11)
    v13 = builder.extend({sentence, 1}, v7, v2)
    v14 = builder.extend({sentence, 1}, v12, v10)
    v15 = builder.merge_horizontal({sentence, 2}, [v13, v14])
    """)
ex3()
