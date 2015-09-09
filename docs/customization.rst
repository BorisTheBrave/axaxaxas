Customization
=============

Tokens
------
The parser works on a stream of tokens. Tokens can be any python object, they are not expected to have any particular
behaviour. You may want to provide useful ``__repr__`` and ``__str__`` methods to give better error messages.

Thus, the `parse` function can work just as effectively on a stream of ``str``, ``bytes`` or a stream of single characters
(a `scannerless parser <https://en.wikipedia.org/wiki/Scannerless_parsing>`_). A common technique is for the
lexer to produce some sort of Token object that includes a text string and additional annotations.
For example `the Natural Language Toolkit <http://www.nltk.org>`_ can mark each token with the relevant part of speech.

Symbols
-------
Symbols are objects used to define the right hand side of a `ParseRule` production. Two Symbols, `NonTerminal` and
`Terminal` are provided in the `symbols` module. Anything that duck-types the same as these can be used however.

This is mostly useful for re-defining `Terminal.match`, which is the method responsible for determining if
a given token matches the terminal. The default `Terminal` class matches by equality, but, for example,
you may have terminals that match entire classes of tokens.

Customizing ParseTrees
----------------------
There is no way to customize the `ParseTree` class. But you can avoid using it entirely by writing your own
`Builder`. Builders specify a semantic action to take at each step of the parse, allowing you to build your own
parse trees or abstract syntax trees directly from a `ParseForest`. See :ref:`builders`
for more details.

Customizing Grammars
--------------------

You can override `ParseRuleSet.get` with anything that returns a list of `ParseRule` objects. As there is no
preprocessing done on the rules, you can generate a grammar on the fly. You can use this feature to parse
context sensitive grammars, by passing any relevant context as part of the head, and adjusting the non-terminals
of the returned rules to forward on relevant context. This will probably lead to very long parse times unless
care is applied.
