import unittest
from earley_parser import parse, unparse, ParseRuleSet, NoParseError, AmbiguousParseError, InfiniteParseError, ParseTree
import earley_parser
from symbols import NonTerminal, Terminal

# The simplest possible lexer, for testing
def lex(s):
    return s.split()


def unlex(tokens):
    return " ".join(tokens)

# Having names for the individual rules facilitates testing and debugging
class ParseRule(earley_parser.ParseRule):
    def __init__(self, name, *args, **kwargs):
        earley_parser.ParseRule.__init__(self, *args, **kwargs)
        self.name = name


def simplify_parse_tree(parse_tree):
    if isinstance(parse_tree, tuple):
        return "(" + " ".join(map(simplify_parse_tree, parse_tree)) + ")"
    if not isinstance(parse_tree, ParseTree):
        return parse_tree
    return "(" + parse_tree.rule.name + ": " + " ".join(map(simplify_parse_tree, parse_tree.children)) + ")"


class EarleyParserTestCase(unittest.TestCase):
    def parse(self, text, trees):
        result_trees = set(map(simplify_parse_tree, parse(self.p, "top", lex(text))))
        expected_trees = set(trees)
        extra_results = result_trees - expected_trees
        missing_results = expected_trees - result_trees
        t = []
        if extra_results:
            t.append("Parsed unexpected parse trees:\n" + "\n".join(extra_results))
        if missing_results:
            t.append("Expected parse trees:\n" + "\n".join(missing_results))
        if t:
            self.assertFalse(extra_results or missing_results, "\n".join(t))

    def roundtrip(self, text):
        round_trip = unlex(unparse(parse(self.p, "top", lex(text)).single()))
        self.assertEqual(text.strip(), round_trip.strip())

    def ambig(self, text):
        with self.assertRaises(AmbiguousParseError):
            parse(self.p, "top", lex(text)).single()

    def no_parse(self, text, at_index, encountered=None, expected_terminals=None, expected=None):
        with self.assertRaises(NoParseError) as cm:
            parse(self.p, "top", lex(text)).single()
        e = cm.exception
        self.assertEqual(e.start_index, at_index)
        self.assertEqual(e.end_index, at_index)
        if encountered is not None:
            self.assertEqual(e.encountered, encountered)
        if expected_terminals is not None:
            self.assertEqual(set(map(repr,e.expected_terminals)), set(map(repr,expected_terminals)))
        if expected is not None:
            self.assertEqual(set(map(repr,e.expected)), set(map(repr,expected)))

    def infinite(self, text):
        with self.assertRaises(InfiniteParseError):
            parse(self.p, "top", lex(text)).single()

    def setUp(self):
        self.p = ParseRuleSet()

    def test_single_word(self):
        # Can we match a single word?
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a")]))

        self.roundtrip("a")
        self.no_parse("b", 0)

    def test_alternatives(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a")]))
        p.add(ParseRule("top","top",[Terminal("b")]))

        self.roundtrip("a")
        self.roundtrip("b")

    def test_basic_ambig(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a")]))
        p.add(ParseRule("top","top",[Terminal("a")]))
    
        self.ambig("a")

    def test_classic_1(self):
        # From https://web.archive.org/web/20130508170633/http://thor.info.uaic.ro/~grigoras/diplome/5.pdf
        p = self.p
        p.add(ParseRule("1","top",[Terminal("a")]))
        p.add(ParseRule("2","top",[NonTerminal("top"), NonTerminal("top")]))
    
        self.parse("a a a", [
            "(2: (2: (1: a) (1: a)) (1: a))",
            "(2: (1: a) (2: (1: a) (1: a)))",
            ])
    def test_classic_2(self):
        # From https://web.archive.org/web/20130508170633/http://thor.info.uaic.ro/~grigoras/diplome/5.pdf
        p = self.p
        p.add(ParseRule("1","top",[Terminal("a")]))
        p.add(ParseRule("2","top",[NonTerminal("top"), NonTerminal("top")]))
        p.add(ParseRule("3","top",[NonTerminal("top"), NonTerminal("top"), NonTerminal("top")]))
    
        self.parse("a a a", [
            "(2: (2: (1: a) (1: a)) (1: a))",
            "(2: (1: a) (2: (1: a) (1: a)))",
            "(3: (1: a) (1: a) (1: a))",
            ])

    def test_diamond_1(self):
        # Diamond
        # Checks the parser deals with common subclauses
        p = self.p
        p.add(ParseRule("1","top",[NonTerminal("a")]))
        p.add(ParseRule("2","top",[NonTerminal("b")]))
        p.add(ParseRule("3","a",[NonTerminal("c")]))
        p.add(ParseRule("4","b",[NonTerminal("c")]))
        p.add(ParseRule("5","c",[Terminal("a")]))
    
        self.parse("a", [
            "(1: (3: (5: a)))",
            "(2: (4: (5: a)))",
            ])
    def test_diamond_2(self):
        # Diamond 2
        # Checks the parser deals with empty common subclauses
        p = self.p
        p.add(ParseRule("1","top",[NonTerminal("a"), Terminal("a")]))
        p.add(ParseRule("2","top",[NonTerminal("b"), Terminal("a")]))
        p.add(ParseRule("3","a",[NonTerminal("c")]))
        p.add(ParseRule("4","b",[NonTerminal("c")]))
        p.add(ParseRule("5","c",[]))
    
        self.parse("a", [
            "(1: (3: (5: )) a)",
            "(2: (4: (5: )) a)",
            ])

    def test_error_messages_1(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a"), Terminal("b")]))
    
        self.no_parse("a a", 1,
                      encountered="a",
                      expected_terminals=[Terminal("b")],
                      expected=[Terminal("b")],
                      )
    
    def test_error_messages_2(self):
        p = self.p
        p.add(ParseRule("1","top",[NonTerminal("a")]))
        p.add(ParseRule("2","a",[Terminal("a")]))
    
        self.no_parse("", 0,
                      expected_terminals=[Terminal("a")],
                      expected=[NonTerminal("a")],
                      )
    
    def test_error_messages_3(self):
        p = self.p
        p.add(ParseRule("1","top",[NonTerminal("a", optional=True), NonTerminal("b"), ]))
        p.add(ParseRule("2","a",[Terminal("a")]))
        p.add(ParseRule("2","b",[Terminal("b")]))
    
        self.no_parse("c", 0,
                      expected_terminals=[Terminal("a"), Terminal("b")],
                      expected=[NonTerminal("a"), NonTerminal("b")],
                      )
    
    def test_infinite_short_loop(self):
        # Looping grammar (points to self)
        p = self.p
        p.add(ParseRule("1","top", [Terminal("a")]))
        p.add(ParseRule("2","top", [NonTerminal("top")]))
    
        self.infinite("a")
    
    def test_infinite_longer_loop(self):
        # Looping grammar (larger cycle)
        p = self.p
        p.add(ParseRule("1","top", [Terminal("a")]))
        p.add(ParseRule("2","top", [NonTerminal("b")]))
        p.add(ParseRule("3","b", [NonTerminal("top")]))
    
        self.infinite("a")
    
    def test_infinite_symmetric(self):
        # This larger example demonstrates there is no natural
        # way to remove edges to eliminate loops
        p = self.p
        p.add(ParseRule("1","top", [NonTerminal("b")]))
        p.add(ParseRule("2","top", [NonTerminal("b")]))
        p.add(ParseRule("3","c", [NonTerminal("b")]))
        p.add(ParseRule("4","b", [NonTerminal("c")]))
        p.add(ParseRule("5","b", [Terminal("a")]))
        p.add(ParseRule("6","c", [Terminal("a")]))
    
        self.infinite("a")
    
    def test_infinite_star(self):
        # Star can introduce loops
        p = self.p
        p.add(ParseRule("1","top", [NonTerminal("a", star=True)]))
        p.add(ParseRule("2","a", [Terminal("a")]))
        p.add(ParseRule("3","a", []))
    
        self.infinite("a")
    
    def test_infinite_penalty(self):
        # Penalty can resolve infinite loops
        p = self.p
        p.add(ParseRule("1","top", [Terminal("a")]))
        p.add(ParseRule("2","top", [NonTerminal("b")], penalty=1))
        p.add(ParseRule("3","b", [NonTerminal("top")]))
    
        self.roundtrip("a")
    
    def test_infinite_penalty_2(self):
        # Only when prefering the non-loop
        p = self.p
        p.add(ParseRule("1","top", [Terminal("a")], penalty=1))
        p.add(ParseRule("2","top", [NonTerminal("b")]))
        p.add(ParseRule("3","b", [NonTerminal("top")]))
    
        self.infinite("a")
    
    def test_infinite_greedy(self):
        # So can greedy
        p = self.p
        p.add(ParseRule("1","top", [Terminal("a")]))
        p.add(ParseRule("2","top", [NonTerminal("b")]))
        p.add(ParseRule("3","b", [NonTerminal("top", prefer_early=True)]))
    
        self.parse("a", ["(1: a)", "(2: (3: (1: a)))"])
    
    def test_infinite_greedy_2(self):
        # But only if the greedy actually prefers the non-loop
        p = self.p
        p.add(ParseRule("1","top", [Terminal("a")]))
        p.add(ParseRule("2","top", [NonTerminal("b")]))
        p.add(ParseRule("3","b", [NonTerminal("top", prefer_late=True)]))
    
        self.infinite("a")

    def test_complexity(self):
        # Correctly written an Earley parse should be O(n) for several sorts of grammar
        # and O(n^3) worse case
        p = self.p
        p.add(ParseRule("1","top",[NonTerminal("a", star=True)]))
        p.add(ParseRule("2","a",[Terminal("a")]))
        p.add(ParseRule("3","a",[Terminal("a")]))
    
        # Assuming the EarleyParser is correct, this should only take linear time/space to compute, despite 2^n possible
        # parses. Note that you can set this value well beyond Python's recursion depth
        n = 1000
        forest = parse(self.p, "top", lex("a " * n))
        self.assertEqual(forest.count(), 2**n)
        self.assertEqual(forest.internal_node_count, 4 + 5 * n)
    
        # TODO: Need better complexity tests: Test LL, LR and worst case

    def test_complexity_ll(self):
        p = self.p
        p.add(ParseRule("1","top",[NonTerminal("top"), Terminal("a")]))
        p.add(ParseRule("2","top",[]))

        n = 1000
        forest = parse(self.p, "top", lex("a " * n))
        self.assertEqual(forest.count(), 1)
        self.assertEqual(forest.internal_node_count, 4 + 2 * n)


    def test_complexity_lr(self):
        p = self.p
        p.add(ParseRule("1","top",[Terminal("a"), NonTerminal("top")]))
        p.add(ParseRule("2","top",[]))

        n = 1000
        forest = parse(self.p, "top", lex("a " * n))
        self.assertEqual(forest.count(), 1)
        self.assertEqual(forest.internal_node_count, 3 + 3 * n)


    
    def test_greedy(self):
        # greedy/lazy is a feature of optional/star for cutting down amgiguity
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a", optional=True), Terminal("a", star=True)]))
    
        self.ambig("a a")
    
    def test_greedy2(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a", optional=True, lazy=True), Terminal("a", star=True)]))
    
        self.roundtrip("a a")
    
    def test_greedy3(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a", optional=True, greedy=True), Terminal("a", star=True)]))
    
        self.roundtrip("a a")
    
    def test_greedy4(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a", star=True), Terminal("a", optional=True)]))
    
        self.ambig("a a")
    
    def test_greedy5(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a", star=True, lazy=True), Terminal("a", optional=True)]))
    
        self.roundtrip("a a")
    
    def test_greedy6(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a", star=True, greedy=True), Terminal("a", optional=True)]))
    
        self.roundtrip("a a")
    
    def test_prefer_early(self):
        # prefer_early/lazy is a feature of optional/star for cutting down amgiguity
        # TODO
        pass
    
    def test_penalty(self):
        # Penalty is a feature for cutting down ambiguity
        p = self.p
        p.add(ParseRule("1","top",[Terminal("a")]))
        p.add(ParseRule("2","top",[Terminal("a")]))
    
        self.ambig("a")
    
    def test_penalty2(self):
        p = self.p
        p.add(ParseRule("top","top",[Terminal("a")], penalty=1))
        p.add(ParseRule("top","top",[Terminal("a")]))
    
        self.roundtrip("a")
