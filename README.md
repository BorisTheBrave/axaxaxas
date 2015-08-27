Axaxaxas
=======================

Axaxaxas is a Python 3.3 implementation of an [Earley Parser](https://en.wikipedia.org/wiki/Earley_parser). 
Earley parsers are a robust parser that can recognize any context-free grammar, with good support for amiguous grammars.
They have linear performance for a wide class of grammars, and worst case O(n^3).
  
The main goals of this implementation are ease of use, customization, and requiring no pre-processing step
for the grammar. You may find the 
[Marpa](https://jeffreykegler.github.io/Marpa-web-site/) project better suits high performance needs.

Features
--------
 - Complete Earley Parser implemenation
 - Native support for higher level constructs such as optional elements and [Kleene stars](https://en.wikipedia.org/wiki/Kleene_star)
 - Many options for taming ambiguity
 - Completely customizable tokens, terminals and parse trees
 - No pre-processing step at all - grammars can be changed on the fly
 
Usage
-----

This section assumes you are familiar with the basic terminology involved in parsing Context Free grammars.

### Defining a Grammar

A grammar is stored as a collection of `ParseRule` objects inside a `ParseRuleSet`. Each `ParseRule` is a single
production from a "head" (symbol named by string), to a list of `Symbol` objects. Multiple `ParseRule` objects with
the same head define alternative productions.

For example, the following [Backus-Naur](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_Form) notated grammar:

    <sentence> ::= <noun> <verb> <noun>
    <noun> ::= "man" | "dog"
    <verb> ::= "bites"

Would be expressed:

    from symbols import Terminal as T, NonTerminal as NT
    from earley_parser import ParseRule, ParseRuleSet
    
    grammar = ParseRuleSet()
    grammar.add(ParseRule("sentence", [NT("noun"), NT("verb"), NT("noun")]))
    grammar.add(ParseRule("noun", [T("man")]))
    grammar.add(ParseRule("noun", [T("dog")]))
    grammar.add(ParseRule("verb", [T("bites")]))
    
### Invoking the parser

Having defined our grammar, we can attempt to parse it. Parsing operates on an iterator of token objects, There is no
lexer included. In the example above we have assumed that the tokens are Python strings, but they can be anything.
Often a formal lexer is not needed - we can use `string.split` to produce lists of strings. 

The parser is invoked with the `parse` function.

    from earley_parser import parse
    parse_forest = parse(grammar, "sentence", "man bites dog".split())
    
    print(parse_forest.single())
    # (sentence: (noun: 'man') (verb: 'bites') (noun: 'dog'))

### Parse results

`parse` returns a `ParseForest` that contains a collection of `ParseTree` objects. By calling `.single()` we
check that there is exactly one possible parse tree, and return it. 
See [Handling Ambiguity](#HandlingAmbiguity) for more details.

`ParseTree` objects themselves are a fairly straightforward representation. `ParseTree.rule` contains the ParseRule
used to match the tokens, and `ParseTree.children` contains a value for each symbol of the rule, where the value is
the token matched for terminals, or another `ParseTree` for nonterminals. 


### Optional, Star and Plus

Any symbol can be declared with `optional=True` to make it nullable - it must occur zero or one times. Similarly,
`star=True` allows any number of occurences, min zero, and `plus=True` allows any number of occurences, min one.
In the resulting parse tree, skipped optional symbols are represented with `None`. star and plus elements become
tuples.

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



### Greedy Symbols
<a name="Greedy"/>
Like in a regular expression, you can mark parts of the grammar as `greedy` or `lazy`. In case of ambiguity
the parser will preferentially prefer the parse tree with the more (or fewer) number of occurrences. lazy and greedy
can only be used in combination with optional, plus or star.

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

For non-terminals, settings `prefer_early` and `prefer_late` work analogously. They instruct the parser that
if there are several possible productions that could be used for a given symbol, to prefer the first (or last) one
in order of definition in the grammar.

    grammar.add(ParseRule("dinner order", [T("I"), T("want"), NT("item", prefer_early=True)]))
    grammar.add(ParseRule("item", [T("ham")]))
    grammar.add(ParseRule("item", [T("eggs")]))
    grammar.add(ParseRule("item", [T("ham"), T("and"), T("eggs")]))
    grammar.add(ParseRule("item", [NT("item", prefer_early=True), T("and"), NT("item", prefer_early=True)]))
    
    print(parse(grammar, "dinner order", "I want eggs and ham".split()).single())
    # (dinner order: 'I' 'want' (item: (item: 'eggs') 'and' (item: 'ham')))
    
    print(parse(grammar, "dinner order", "I want ham and eggs".split()).single())
    # (dinner order: 'I' 'want' (item: 'ham' 'and' 'eggs'))


### Penalty

As mentioned above, greedy and related settings only trim ambiguity when the two options have so far parsed identically.

In some circumstances, you wish to avoid a particular, no matter how different the alternatives are. You can associate
a penalty with each rule. The parser sums up all the penalties associated with a given parse, and choose only possibly
parses with the lowest sum. This can have wide ranging effects on eliminating ambiguity. Penalties can be viewed as very
lightweight support for probabilistic parsing.

    grammar.add(ParseRule("sentence", [NT("noun"), T("like"), T("a"), NT("noun")]))
    grammar.add(ParseRule("sentence", [NT("noun"), T("flies"), T("like"), T("a"), NT("noun")]))
    grammar.add(ParseRule("noun", [T("fruit"), T("flies")], penalty=1))
    grammar.add(ParseRule("noun", [T("fruit")]))
    grammar.add(ParseRule("noun", [T("banana")]))
    
    print(parse(grammar, "sentence", "fruit flies like a banana".split()).single())
    # (sentence: (noun: 'fruit') 'flies' 'like' 'a' (noun: 'banana'))
    
In the example above the parser chose to avoid the other possible parse 
`(sentence: (noun: 'fruit' 'flies') 'like' 'a' (noun: 'banana'))` because it contains a rule with a penalty.

Penalties can be considered an experimental feature. Most of the time, you can just add more greedy settings to 
get the desired effect.

Customization
-------------
### Tokens
The parser works on a stream of tokens. Tokens can be any python object, they are not expected to have any particular 
behaviour. You may want to provide useful `__repr__` and `__str__` methods to give better error messages.

Thus, the `parse` function can work just as effectively on a stream of `str`, `bytes` or a stream of single characters 
(a [scannerless parser](https://en.wikipedia.org/wiki/Scannerless_parsing)). A common technique is for the
lexer to produce some sort of Token object that includes a text string and additional annotations. 
For example [the Natural Language Toolkit](http://www.nltk.org) can mark each token with the relevant part of speech.

### Symbols
Symbols are objects used to define the right hand side of a `ParseRule` production. Two Symbols, `NonTerminal` and
`Terminal` are provided in the `symbols` module. Anything that duck-types the same as these can be used however.

This is mostly useful for re-defining `Terminal.match`, which is the method responsible for determining if
a given token matches the terminal. The default `Terminal` class matches by equality, but, for example, 
you may have terminals that match entire classes of tokens.

### Customizing ParseTrees
There is no way to customize the `ParseTree` class. But you can avoid using it entirely by writing your own
Builder. Builders specify a semantic action to take at each step of the parse, allowing you to build your own
parse trees or abstract syntax trees directly from a `ParseForest`. See [Handling Ambiguity > Builders](#Builders)
for more details.

### Customizing Grammars

You can override `ParseRuleSet.get(head)` with anything that returns a list of `ParseRule` objects. As there is no
preprocessing done on the rules, you can generate an a grammar on the fly. You can use this feature to parse
context sensitive grammars, by passing any relevant context as part of the head, and adjusting the non-terminals
of the returned rules to forward on relevant context. This will probably lead to very long parse times unless
care is applied.

Handling Ambiguity
------------------
<a name="HandlingAmbiguity"/>
The `parse` function returns a `ParseForest`. A `ParseForest` is an efficient shared representation of multiple 
possible `ParseTree` objects. For some grammars, therefore, you must be careful dealing with `ParseForest` objects
as they may contains exponentially many possible parses.

### single, all, count, and \_\_iter\_\_

These are the basic methods for extracting parse trees from the forest.

`ParseForest.single()` returns the unique tree in the forest, if there is one, or throws `AmbiguousParseError` (see 
[Errors and Edge Cases](#errors))
 
`ParseForest.count()` returns a count of all the trees.

`ParseForest.all()` returns a list of all the trees in the forest. It can be quite large.

`ParseForest.__iter__()` iterates over all the trees in the forest. It is quite a bit slower than `all`, but it
doesn't load all the trees into memory at once. 

### Greedy Rules

Using the `greedy`,`lazy`,`prefer_early`,`prefer_late` and `penalty` settings described in [usage](#Greedy) allows you
to eliminate alternative parses. In the extreme case of marking every nonterminal with `prefer_early` and
every `optional`, `star` and `plus` symbol with `greedy`, then you will never have an ambiguous parse. 

### Builders
<a name="Builders"/>
Builders are an advanced way to process a ParseForest. Builder's can take advantage of the shared representation the 
parse trees inside a forest, and choose how to handle ambiguity.

To use builders, you must define your own builder class inheriting from `Builder`:

    class MyBuilder(Builder):
        def start_rule(self, context):
            ...
    
        def terminal(self, context, token):
            ...
    
        def skip_optional(self, context, prev_value):
            ...
    
        def begin_multiple(self, context, prev_value):
            ...
    
        def end_multiple(self, context, prev_value):
            ...
    
        def extend(self, context, prev_value, extension_value):
            ...
    
        def merge(self, context, values):
            ...

Then you can run your builder against a parse forest using `ParseForest.apply`. The parse forest will then invoke
methods on your builder as it walks over the possible parse tree. 
The passed `context` is a `BuilderContext` with fields `rule`, `symbol_index`, `start_index` and `end_index` that give
details about where in the rule and where in the token stream this invocation is occuring. 

First apply will call `start_rule` for the matched rule. It will then take the output of that and pass it into the other methods, which are responsible for transforming the 
value according to what is occuring in the parse. The same process occurs for all matched rules in the parse,
with the return value from the builder completed rules being passed as the `extension_value` for any Terminals
that matched that rule. In this way, you can build a complete picture of the parse tree, one step at a time.

 - `start_rule` is called at the start of each parsed rule.
 - `terminal` is called when a terminal is parsed.
 - `extend` is called when a given symbol in a rule has been parsed. It is passed both the previous value for that rule
   and the extension_value describing what was parsed for that symbol.
 - `skip_optional` is called in place of `extend` when an `optional` symbol is skipped over.
 - `begin_multiple` and `end_multiple` are caused when a `star` or `plus` symbol is first encountered and left.
   Between them, any number of `extend` calls may be made, all corresponding to the same symbol.
 - `merge` is called when there is an ambiguity in the grammar, and multiple possible parses reach the same point
   (and are hereafter shared).

For example, suppose that the parse forest only contains a single parse tree, which looks like this:

    (rule 1: "a" (rule 2: "b") "c")
     
In other words, we've parsed the token stream `["a", "b", "c"]` with the following grammar:
     
    rule1 = ParseRule("rule 1", [T("a"), NT("rule 2"), T("c")])
    rule2 = ParseRule("rule 2", [T("b")])
     
Then the following methods would get invoked during `apply` (though not necessary in this order).

    v1 = builder.start_rule({rule1, 0})
    v2 = builder.terminal({rule1, 0}, "a")
    v3 = builder.extend({rule1, 0}, v1, v2)
    v4 = builder.start_rule({rule2, 0})
    v5 = builder.token({rule2, 0}, "b")
    v6 = builder.extend({rule2, 0}, v4, v5)
    v7 = builder.extend({rule1, 1}, v3, v6)
    v8 = builder.token({rule1, 2}, "c")
    v9 = builder.extend({rule1, 2}, v7, v8)
    return v9
    
When there are multiple possible parse trees, sequences of builder results that are shared between parse trees
will only get invoked once, then stored and re-used. This is why some context is omitted from builder calls,
as the call may be used in several contexts. This is also why it is important not to mutate the passed in prev_value,
as it may be used in other contexts. You should always return a fresh value that represents whatever change you
need to make to prev value.

Here is an example of the call sequence for an ambiguous parse of `["hello"]` by grammar:

    rule1 = ParseRule("sentence", [T("hello")])
    rule2 = ParseRule("sentence", [T("hello")])

    v1 = builder.start_rule({rule1, 0})
    v2 = builder.terminal({rule1, 0}, "hello")
    v3 = builder.extend({rule1, 0}, v1, v2)
    v4 = builder.start_rule({rule2, 0})
    v5 = builder.terminal({rule2, 0}, "hello")
    v6 = builder.extend({rule2, 0}, v4, v5)
    v7 = builder.merge({None, 0}, [v3, v6])
    
(Note this this special case where the top level symbol itself is ambiguous, then `None` is passed in as the rule
being merged).

You can handle ambiguity directly using the `merge` method of builder. But a common form of handling is to simply
treat possible every parse tree independently, and just return an list or iterator of the result for each parse tree.
Utility methods `make_list_builder` and `make_iter_builder`. Just pass them a builder which has no ambiguity handling
and they return a new builder that invokes the original builder and combines the results efficiently into a list or 
iterator. They directly correspond to the `ParseForest.all` and `ParseForest.__iter__` methods.

You may find it easier to study the definitions of `CountingBuilder` and `SingleParseTree` builder, which are
internal classes used for implementing `ParseForest.count()` and `ParseForest.single()`, as they are both
fairly straightforward. `SingleParseTree` can be easily adapted to building arbitrary abstract syntax trees,
or performing other semantic actions according to the parse.

Errors and Edge Cases
-------------------
<a name="Errors"/>
There are 3 possible ways that parsing can fail. All of them raise subclasses of `ParseError`. All instances
of `ParseError` contain a `message`, and fields `start_index`, `end_index` indicating where in the token stream
the error is occurring.

### No parse
When the parser can find no possible parse for a token stream, it raises `NoParseError`. The location will be the 
furthest the parse got before there were no possible parses. Additional fields are included:
 - `encountered` - The token we failed at, or `None` if the end of the stream was reached.
 - `expected_terminals` - All the terminals that were evaluated against encountered (and failed)
 - `expected` - Similar to `expected_terminals`, except the parser includes any non-terminals that could
   have started at the encountered token, and hides any terminals or non-terminals that are implicitly covered 
   another one. This is usually a higher level summary of what was expected at any given point.

Note, you can override method `ParseRuleSet.is_anonymous(head)` to return true for some heads. Any anonymous rule
will never be eligible to appear in `expected`. This is useful if you are transforming or generating the grammar,
and some rules don't make sense to report.

### Ambiguous Parse
Ambiguous parses are not an immediate error. The `parse` function simply returns a forest which contains all
possible parse trees. However, if you call `ParseForest.single` and there is ambiguity, then `AmbiguousParseError`
will be thrown. It will indicate the earliest possible ambiguity, but there may be others. The error will contain a 
field called `values` containing the possible alternatives parses. However, it only contains a subtree of the full parse
tree, and additionally, it may be only halfway through building a rule, so the subtree may be missing elements.
These limitations ensure that `values` is the short list. It is recommended you do not use `ParseForest.single` if 
you need more detail on ambiguity.

### Infinite Parse
In some obscure grammars it is possible to define rules that have an infinite number of possible parses. Here is a 
simple example:

    ParseRule("s", [NT("s")]
    ParseRule("s", [T("word")]
    
When parsing `["word"]`, all the following are valid parse trees:
 
    (s: word)
    (s: (s: word))
    (s: (s: (s: word)))
    ...
    
In this circumstance, `parse` throws `InfiniteParseError`. You can avoid this error with the right use of greedy and
penalty settings as they are evaluated before checking for infinite parses.
 
It's possible to improve support for infinite parses if there is demand. Let me know.

### Other notes

The order of evaluation for trimming ambiguity is:

 - penalty
 - greedy and lazy
 - prefer_early and prefer_late
 
The `unparse` method can be used to convert `ParseTree` objects back into lists of tokens.

TODO
----
 - [Joop Leo's LR performance enhancements](http://loup-vaillant.fr/tutorials/earley-parsing/right-recursion)
 - Better handling of infinite grammars
 - Token lookahead
 - Fast-first option
 - Handle infinite parses better.

