Usage
=====

This section assumes you are familiar with the basic terminology involved in parsing Context Free grammars.

Defining a Grammar
------------------

A grammar is stored as a collection of `ParseRule` objects inside a `ParseRuleSet`. Each `ParseRule` is a single
production from a "head" (symbol named by string), to a list of `Symbol` objects. Multiple `ParseRule` objects with
the same head define alternative productions.

For example, the following `Backus-Naur <https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_Form>`_ notated grammar::

    <sentence> ::= <noun> <verb> <noun>
    <noun> ::= "man" | "dog"
    <verb> ::= "bites"

Would be expressed::

    from symbols import Terminal as T, NonTerminal as NT
    from earley_parser import ParseRule, ParseRuleSet

    grammar = ParseRuleSet()
    grammar.add(ParseRule("sentence", [NT("noun"), NT("verb"), NT("noun")]))
    grammar.add(ParseRule("noun", [T("man")]))
    grammar.add(ParseRule("noun", [T("dog")]))
    grammar.add(ParseRule("verb", [T("bites")]))

Invoking the parser
-------------------

Having defined our grammar, we can attempt to parse it. Parsing operates on an iterator of token objects, There is no
lexer included. In the example above we have assumed that the tokens are Python strings, but they can be anything.
Often a formal lexer is not needed - we can use ``string.split`` to produce lists of strings.

The parser is invoked with the `parse` function::

    from earley_parser import parse
    parse_forest = parse(grammar, "sentence", "man bites dog".split())

    print(parse_forest.single())
    # (sentence: (noun: 'man') (verb: 'bites') (noun: 'dog'))

Parse results
-------------

`parse` returns a `ParseForest` that contains a collection of `ParseTree` objects. By calling `single()` we
check that there is exactly one possible parse tree, and return it.
See :ref:`ambiguity` for more details.

`ParseTree` objects themselves are a fairly straightforward representation. `ParseTree.rule` contains the ParseRule
used to match the tokens, and `ParseTree.children` contains a value for each symbol of the rule, where the value is
the token matched for terminals, or another `ParseTree` for nonterminals.


Optional, Star and Plus
-----------------------

Any `Symbol` can be declared with ``optional=True`` to make it nullable - it must occur zero or one times. Similarly,
``star=True`` allows any number of occurences, min zero, and ``plus=True`` allows any number of occurences, min one.
In the resulting parse tree, skipped optional symbols are represented with ``None``. star and plus elements become
tuples::

    grammar.add(ParseRule("relative", [T("step", optional=True), T("sister")]))
    grammar.add(ParseRule("relative", [T("great", star=True), T("grandfather")]))

    print(parse(grammar, "relative", "sister".split()).single())
    # (relative: None 'sister')

    print(parse(grammar, "relative", "step sister".split()).single())
    # (relative: 'step' 'sister')

    print(parse(grammar, "relative", "grandfather".split()).single())
    # (relative: () 'grandfather')

    print(parse(grammar, "relative", "great great grandfather".split()).single())
    # (relative: ('great', 'great') 'grandfather')

.. _greedy:

Greedy Symbols
--------------

Like in a regular expression, you can mark parts of the grammar as ``greedy`` or ``lazy``. In case of ambiguity
the parser will preferentially prefer the parse tree with the more (or fewer) number of occurrences. lazy and greedy
can only be used in combination with optional, plus or star::

    grammar.add(ParseRule("described relative", [NT("adjective", star=True), NT("relative")]))
    grammar.add(ParseRule("adjective", [T("awesome")]))
    grammar.add(ParseRule("adjective", [T("great")]))

    print(parse(grammar, "described relative", "great grandfather".split()).single())
    # -- raises AmbiguousParseError

    grammar.add(ParseRule("described relative 2", [NT("adjective", star=True, greedy=True), NT("relative")]))

    print(parse(grammar, "described relative 2", "great grandfather".split()).single())
    # (described relative 2: ((adjective: 'great'),) (relative: () 'grandfather'))

Greediness only trims ambiguous possibilities, so will never cause a sentence fail to parse.

It only affects choices the parser makes when reading from left to right, which means you will still get
ambiguity if the leftmost symbol isn't marked.

For non-terminals, settings ``prefer_early`` and ``prefer_late`` work analogously. They instruct the parser that
if there are several possible productions that could be used for a given symbol, to prefer the first (or last) one
in order of definition in the grammar::

    grammar.add(ParseRule("dinner order", [T("I"), T("want"), NT("item", prefer_early=True)]))
    grammar.add(ParseRule("item", [T("ham")]))
    grammar.add(ParseRule("item", [T("eggs")]))
    grammar.add(ParseRule("item", [T("ham"), T("and"), T("eggs")]))
    grammar.add(ParseRule("item", [NT("item", prefer_early=True), T("and"), NT("item", prefer_early=True)]))

    print(parse(grammar, "dinner order", "I want eggs and ham".split()).single())
    # (dinner order: 'I' 'want' (item: (item: 'eggs') 'and' (item: 'ham')))

    print(parse(grammar, "dinner order", "I want ham and eggs".split()).single())
    # (dinner order: 'I' 'want' (item: 'ham' 'and' 'eggs'))


Penalty
-------

As mentioned above, greedy and related settings only trim ambiguity when the two options have so far parsed identically.

In some circumstances, you wish to avoid a particular, no matter how different the alternatives are. You can associate
a penalty with each rule. The parser sums up all the penalties associated with a given parse, and choose only possibly
parses with the lowest sum. This can have wide ranging effects on eliminating ambiguity. Penalties can be viewed as very
lightweight support for probabilistic parsing::

    grammar.add(ParseRule("sentence", [NT("noun"), T("like"), T("a"), NT("noun")]))
    grammar.add(ParseRule("sentence", [NT("noun"), T("flies"), T("like"), T("a"), NT("noun")]))
    grammar.add(ParseRule("noun", [T("fruit"), T("flies")], penalty=1))
    grammar.add(ParseRule("noun", [T("fruit")]))
    grammar.add(ParseRule("noun", [T("banana")]))

    print(parse(grammar, "sentence", "fruit flies like a banana".split()).single())
    # (sentence: (noun: 'fruit') 'flies' 'like' 'a' (noun: 'banana'))

In the example above the parser chose to avoid the other possible parse
``(sentence: (noun: 'fruit' 'flies') 'like' 'a' (noun: 'banana'))`` because it contains a rule with a penalty.

Penalties can be considered an experimental feature. Most of the time, you can just add more greedy settings to
get the desired effect.
