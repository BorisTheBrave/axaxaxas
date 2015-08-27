.. _errors:

Errors and Edge Cases
=====================

There are 3 possible ways that parsing can fail. All of them raise subclasses of `ParseError`. All instances
of `ParseError` contain a :attr:`~earley_parser.ParseError.message`, and fields
:attr:`~earley_parser.ParseError.start_index`, :attr:`~earley_parser.ParseError.end_index` indicating where in
the token stream the error is occurring.

No parse
--------
When the parser can find no possible parse for a token stream, it raises `NoParseError`. The location will be the
furthest the parse got before there were no possible parses. Additional fields are included:

 - `encountered` - The token we failed at, or ``None`` if the end of the stream was reached.
 - `expected_terminals` - All the terminals that were evaluated against encountered (and failed)
 - `expected` - Similar to `expected_terminals`, except the parser includes any non-terminals that could
   have started at the encountered token, and hides any terminals or non-terminals that are implicitly covered
   another one. This is usually a higher level summary of what was expected at any given point.

Note, you can override method `ParseRuleSet.is_anonymous()` to return true for some heads. Any anonymous rule
will never be eligible to appear in `expected`. This is useful if you are transforming or generating the grammar,
and some rules don't make sense to report.

Ambiguous Parse
---------------
Ambiguous parses are not an immediate error. The `parse` function simply returns a forest which contains all
possible parse trees. However, if you call `ParseForest.single` and there is ambiguity, then `AmbiguousParseError`
will be thrown. It will indicate the earliest possible ambiguity, but there may be others. The error will contain a
field called `values` containing the possible alternatives parses. However, it only contains a subtree of the full parse
tree, and additionally, it may be only halfway through building a rule, so the subtree may be missing elements.
These limitations ensure that `values` is the short list. It is recommended you do not use `ParseForest.single` if
you need more detail on ambiguity.

Infinite Parse
--------------
In some obscure grammars it is possible to define rules that have an infinite number of possible parses. Here is a
simple example::

    ParseRule("s", [NT("s")]
    ParseRule("s", [T("word")]

When parsing ``["word"]``, all the following are valid parse trees::

    (s: word)
    (s: (s: word))
    (s: (s: (s: word)))
    ...

In this circumstance, `parse` throws `InfiniteParseError`. You can avoid this error with the right use of greedy and
penalty settings as they are evaluated before checking for infinite parses.

It's possible to improve support for infinite parses if there is demand. Let me know.

Other notes
-----------

The order of evaluation for trimming ambiguity is:

 - ``penalty``
 - ``greedy`` and ``lazy``
 - ``prefer_early`` and ``prefer_late``

The `unparse` method can be used to convert `ParseTree` objects back into lists of tokens.