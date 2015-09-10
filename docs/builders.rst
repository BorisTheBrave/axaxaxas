.. _builders:

Builders
========

Builders are an advanced way to process a `ParseForest`. Builders can take advantage of the shared representation the
parse trees inside a forest, and choose how to handle ambiguity.

To use builders, you must define your own builder class inheriting from `Builder`::

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

Then you can run your builder against a parse forest using `ParseForest.apply`. The parse forest will then invoke
methods on your builder as it walks over the possible parse tree. Each method is given some context, and the
value currently being built, and returns a new value updated for what occured in the parse.
In this way, you can build a complete picture of the parse tree, one step at a time.

The passed ``context`` is a `BuilderContext` with fields `rule <BuilderContext.rule>`,
`symbol_index <BuilderContext.symbol_index>`, `start_index <BuilderContext.start_index>` and
`end_index <BuilderContext.end_index>` that give details about where in the rule and where in the token stream
this invocation is occuring.

First `apply` will call `start_rule` for the matched rule. The result from that is passed to the other methods.

 - `start_rule` is called at the start of each parsed rule.
 - `terminal` is called when a terminal is parsed.
 - `extend` is called when a given symbol in a rule has been parsed. It is passed both the previous value for that rule
   and the extension_value describing what was parsed for that symbol.
 - `skip_optional` is called in place of `extend` when an ``optional`` symbol is skipped over.
 - `begin_multiple` and `end_multiple` are caused when a ``star`` or ``plus`` symbol is first encountered and left.
   Between them, any number of `extend` calls may be made, all corresponding to the same symbol.


You may find it easier to study the definitions of ``CountingBuilder`` and ``SingleParseTree`` builder, which are
internal classes used for implementing `ParseForest.count()` and `ParseForest.single()`, as they are both
fairly straightforward. ``SingleParseTree`` can be easily adapted to building arbitrary abstract syntax trees,
or performing other semantic actions according to the parse.

Example
-------

For example, suppose that the parse forest only contains a single parse tree, which looks like this::

    (rule 1: "a" (rule 2: "b") "c")

In other words, we've parsed the token stream ``["a", "b", "c"]`` with the following grammar::

    rule1 = ParseRule("rule 1", [T("a"), NT("rule 2"), T("c")])
    rule2 = ParseRule("rule 2", [T("b")])

Then the following methods would get invoked during `apply` (though not necessary in this order)::

    v1 = builder.start_rule({rule2, 0})
    v2 = builder.terminal({rule2, 0}, 'b')
    v3 = builder.extend({rule2, 0}, v1, v2)
    v4 = builder.start_rule({rule1, 0})
    v5 = builder.terminal({rule1, 0}, 'a')
    v6 = builder.extend({rule1, 0}, v4, v5)
    v7 = builder.extend({rule1, 1}, v6, v3)
    v8 = builder.terminal({rule1, 1}, 'c')
    v9 = builder.extend({rule1, 2}, v7, v8)

Ambiguity
---------
When there are multiple possible parse trees, sequences of builder results that are shared between parse trees
will only get invoked once, then stored and re-used. This is why some context is omitted from builder methods,
as the call may be used in several contexts. This is also why it is important not to mutate the passed in prev_value,
as it may be used in other contexts. You should always return a fresh value that represents whatever change you
need to make to prev value.

The easiest way to handle amiguity is to use utility methods `make_list_builder` and `make_iter_builder`. These methods
accept a builder with no ambiguity handling, and returns a new builder that simply treats every possible parse tree
independently, and return a list or iterable respectively. They directly correspond to the `ParseForest.all` and
`ParseForest.__iter__` methods, which include some additional details.

If you do wish to directly handle ambiguity. You must override either the `merge` method, or both the
`merge_horizontal` and `merge_vertical` methods. All these methods work the same way: you are passed a list of values
that each represent an alternative parse of the same sequence of tokens for the same parse rule or symbol, and you
must return a single value aggregating them.

A merge is "vertical", and calls `merge_vertical` when there are multiple possible `ParseRule` objects with the same
head that match the same sequence of tokens. The `BuilderContext` indicates the non terminal symbol they both match.
Conversely, `merge_horizontal` is called when there are multiple possible parses for a single `ParseRule`. In most use
cases, these methods will share the same implementation, so you are free to override `merge` instead.

Here is an example of the call sequence for an ambiguous parse of ``["hello"]`` by grammar::

    rule1 = ParseRule("sentence", [T("hello")])
    rule2 = ParseRule("sentence", [T("hello")])

    v1 = builder.start_rule({rule1, 0})
    v2 = builder.terminal({rule1, 0}, 'hello')
    v3 = builder.extend({rule1, 0}, v1, v2)
    v4 = builder.start_rule({rule2, 0})
    v5 = builder.terminal({rule2, 0}, 'hello')
    v6 = builder.extend({rule2, 0}, v4, v5)
    v7 = builder.merge_vertical({None, 0}, [v6, v3])

(Note that in this special case where the top level symbol itself is ambiguous, then ``None`` is passed in as the rule
being merged).

Here's another example, ambiguously parsing ``["a"]``::

    sentence = ParseRule("sentence", [NT("X"),NT("Y")])
    X        = ParseRule("X", [T("a", optional=True)])
    Y        = ParseRule("Y", [T("a", optional=True)])

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

The two above examples give a visual indication of the terminology "vertical" and "horizontal". In the first,
``rule1`` and ``rule2`` are ambiguous and in vertically column in the grammar definition. In the second, ``X`` and
``Y`` are ambiguous, and are horizontally next to each other in a single grammar rule.