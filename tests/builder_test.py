# This is the example comes from builders.rst

from axaxaxas import ParseRule, Terminal as T, NonTerminal as NT, ParseRuleSet, parse, Builder
import unittest


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

    def compare(self, output, test_case=None):
        i = 0
        for oline in output.split("\n"):
            if "#" in oline: oline = oline[:oline.index("#")]
            oline = oline.strip()
            if not oline: continue
            if oline != self.lines[i]:
                if test_case is not None:
                    test_case.assertEqual(oline, self.lines[i])
                print(repr(oline))
                print(repr(self.lines[i]))
                assert oline == self.lines[i], "Failed at line {}".format(i+1)
            i += 1

    def start_rule(self, context):
        return self.log("start_rule", context)

    def end_rule(self, context, prev_value):
        return self.log("end_rule", context, prev_value)

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


class Builder(unittest.TestCase):
    def parse(self, lcls, head, tokens, output):
        grammar = ParseRuleSet()
        for rule_name, rule in sorted(lcls.items(), reverse=True):
            if isinstance(rule, ParseRule):
                grammar.add(rule)
        logging_builder = LoggingBuilder(lcls)
        parse(grammar, head, tokens).apply(logging_builder)
        print(logging_builder.get_text())
        logging_builder.compare(output, self)


    def test_ex1(self):
        rule1 = ParseRule("rule 1", [T("a"), NT("rule 2"), T("c")])
        rule2 = ParseRule("rule 2", [T("b")])

        self.parse(locals(), "rule 1", ["a", "b", "c"], """
    v1 = builder.start_rule({rule2, 0})
    v2 = builder.terminal({rule2, 0}, 'b')
    v3 = builder.extend({rule2, 0}, v1, v2)
    v4 = builder.end_rule({rule2, 1}, v3)
    v5 = builder.start_rule({rule1, 0})
    v6 = builder.terminal({rule1, 0}, 'a')
    v7 = builder.extend({rule1, 0}, v5, v6)
    v8 = builder.extend({rule1, 1}, v7, v4)
    v9 = builder.terminal({rule1, 1}, 'c')
    v10 = builder.extend({rule1, 2}, v8, v9)
    v11 = builder.end_rule({rule1, 3}, v10)
        """)


    def test_ex2(self):
        rule1 = ParseRule("sentence", [T("hello")])
        rule2 = ParseRule("sentence", [T("hello")])
        self.parse(locals(), "sentence", ["hello"], """
    v1 = builder.start_rule({rule1, 0})
    v2 = builder.terminal({rule1, 0}, 'hello')
    v3 = builder.extend({rule1, 0}, v1, v2)
    v4 = builder.end_rule({rule1, 1}, v3)
    v5 = builder.start_rule({rule2, 0})
    v6 = builder.terminal({rule2, 0}, 'hello')
    v7 = builder.extend({rule2, 0}, v5, v6)
    v8 = builder.end_rule({rule2, 1}, v7)
    v9 = builder.merge_vertical({None, 0}, [v8, v4])
        """)


    def test_ex3(self):
        sentence = ParseRule("sentence", [NT("X"), NT("Y")])
        X = ParseRule("X", [T("a", optional=True)])
        Y = ParseRule("Y", [T("a", optional=True)])

        self.parse(locals(), "sentence", ["a"], """
    v1 = builder.start_rule({Y, 0})             # After token 0
    v2 = builder.skip_optional({Y, 0}, v1)
    v3 = builder.end_rule({Y, 1}, v2)
    v4 = builder.start_rule({X, 0})
    v5 = builder.terminal({X, 0}, 'a')
    v6 = builder.extend({X, 0}, v4, v5)
    v7 = builder.end_rule({X, 1}, v6)
    v8 = builder.start_rule({sentence, 0})
    v9 = builder.extend({sentence, 0}, v8, v7)
    v10 = builder.start_rule({Y, 0})             # Before token 0
    v11 = builder.terminal({Y, 0}, 'a')
    v12 = builder.extend({Y, 0}, v10, v11)
    v13 = builder.end_rule({Y, 1}, v12)
    v14 = builder.skip_optional({X, 0}, v4)
    v15 = builder.end_rule({X, 1}, v14)
    v16 = builder.extend({sentence, 0}, v8, v15)
    v17 = builder.extend({sentence, 1}, v9, v3)
    v18 = builder.extend({sentence, 1}, v16, v13)
    v19 = builder.merge_horizontal({sentence, 2}, [v17, v18])
    v20 = builder.end_rule({sentence, 2}, v19)
        """)

if __name__ == '__main__':
    unittest.main()