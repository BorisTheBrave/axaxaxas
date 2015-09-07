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

        def merge_vertical(self, context, values):
            ...

        def merge_horizontal(self, context, values):
            ...

Then you can run your builder against a parse forest using `ParseForest.apply`. The parse forest will then invoke
methods on your builder as it walks over the possible parse tree. Each method is given some context, and the
value currently being built, and returns a new value updated for what occured in the parse.
In this way, you can build a complete picture of the parse tree, one step at a time.

The passed ``context`` is a `BuilderContext` with fields `rule <BuilderContext.rule>`,
`symbol_index <BuilderContext.symbol_index>`, `start_index <BuilderContext.start_index>` and
`end_index <BuilderContext.end_index>` that give details about where in the rule and where in the token stream
this invocation is occuring.

First apply will call `start_rule` for the matched rule. The result from that is passed to the other methods.

 - `start_rule` is called at the start of each parsed rule.
 - `terminal` is called when a terminal is parsed.
 - `extend` is called when a given symbol in a rule has been parsed. It is passed both the previous value for that rule
   and the extension_value describing what was parsed for that symbol.
 - `skip_optional` is called in place of `extend` when an ``optional`` symbol is skipped over.
 - `begin_multiple` and `end_multiple` are caused when a ``star`` or ``plus`` symbol is first encountered and left.
   Between them, any number of `extend` calls may be made, all corresponding to the same symbol.
 - `merge_vertical` and `merge_horizontal` are called when there is an ambiguity in the grammar, and multiple possible
   parses reach the same point (and are hereafter shared).


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

Ambiguity
---------

When there are multiple possible parse trees, sequences of builder results that are shared between parse trees
will only get invoked once, then stored and re-used. This is why some context is omitted from builder calls,
as the call may be used in several contexts. This is also why it is important not to mutate the passed in prev_value,
as it may be used in other contexts. You should always return a fresh value that represents whatever change you
need to make to prev value.

`merge_vertical` is called when there are multiple possible `ParseRule` objects with the same head that match the same
sequence of tokens. The BuilderContext indicates the non terminal symbol they both match. Conversely,
`merge_horizontal` is called when there are multiple possible parses for a single `ParseRule`. In most use cases,
these methods will share the same implementation.

Here is an example of the call sequence for an ambiguous parse of ``["hello"]`` by grammar::

    rule1 = ParseRule("sentence", [T("hello")])
    rule2 = ParseRule("sentence", [T("hello")])

    v1 = builder.start_rule({rule1, 0})
    v2 = builder.terminal({rule1, 0}, "hello")
    v3 = builder.extend({rule1, 0}, v1, v2)
    v4 = builder.start_rule({rule2, 0})
    v5 = builder.terminal({rule2, 0}, "hello")
    v6 = builder.extend({rule2, 0}, v4, v5)
    v7 = builder.merge_vertical({None, 0}, [v3, v6])

(Note that in this special case where the top level symbol itself is ambiguous, then ``None`` is passed in as the rule
being merged).

You can handle ambiguity directly using the `merge_vertical` and `merge_horizontal` method of builder.
But a common form of handling is to simply treat possible every parse tree independently, and just return an list or
iterator of the result for each parse tree. Utility methods `make_list_builder` and `make_iter_builder` let you
do exactly that. Just pass them a builder which has no ambiguity handling
and they return a new builder that invokes the original builder and combines the results efficiently into a list or
iterator. They directly correspond to the `ParseForest.all` and `ParseForest.__iter__` methods.

