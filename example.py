# This is the example is explained in more detail in README.md

from symbols import Terminal as T, NonTerminal as NT
from earley_parser import ParseRule, ParseRuleSet

grammar = ParseRuleSet()
grammar.add(ParseRule("sentence", [NT("noun"), NT("verb"), NT("noun")]))
grammar.add(ParseRule("noun", [T("man")]))
grammar.add(ParseRule("noun", [T("dog")]))
grammar.add(ParseRule("verb", [T("bites")]))

###

from earley_parser import parse
parse_forest = parse(grammar, "sentence", "man bites dog".split())
print(parse_forest.single())

###

grammar.add(ParseRule("relative", [T("step", optional=True), T("sister")]))
grammar.add(ParseRule("relative", [T("great", star=True), T("grandfather")]))

print(parse(grammar, "relative", "sister".split()).single())
print(parse(grammar, "relative", "step sister".split()).single())
print(parse(grammar, "relative", "grandfather".split()).single())
print(parse(grammar, "relative", "great great grandfather".split()).single())

###

grammar.add(ParseRule("described relative", [NT("adjective", star=True), NT("relative")]))
grammar.add(ParseRule("adjective", [T("awesome")]))
grammar.add(ParseRule("adjective", [T("great")]))

#print(parse(grammar, "described relative", "great grandfather".split()).single())
# -- raise AmbiguousParseError

grammar.add(ParseRule("described relative 2", [NT("adjective", star=True, greedy=True), NT("relative")]))
print(parse(grammar, "described relative 2", "great grandfather".split()).single())

###

grammar.add(ParseRule("dinner order", [T("I"), T("want"), NT("item", prefer_early=True)]))
grammar.add(ParseRule("item", [T("ham")]))
grammar.add(ParseRule("item", [T("eggs")]))
grammar.add(ParseRule("item", [T("ham"), T("and"), T("eggs")]))
grammar.add(ParseRule("item", [NT("item", prefer_early=True), T("and"), NT("item", prefer_early=True)]))

print(parse(grammar, "dinner order", "I want eggs and ham".split()).single())

print(parse(grammar, "dinner order", "I want ham and eggs".split()).single())

###
grammar.add(ParseRule("sentence", [NT("noun"), T("like"), T("a"), NT("noun")]))
grammar.add(ParseRule("sentence", [NT("noun"), T("flies"), T("like"), T("a"), NT("noun")]))
grammar.add(ParseRule("noun", [T("fruit"), T("flies")], penalty=1))
grammar.add(ParseRule("noun", [T("fruit")]))
grammar.add(ParseRule("noun", [T("banana")]))

print(parse(grammar, "sentence", "fruit flies like a banana".split()).single())
