Reference
=========
Parsing
-------

.. module:: axaxaxas

.. autoclass:: ParseRule
    :members:

.. autoclass:: ParseTree
    :members:

.. autoclass:: ParseForest
    :members:

    .. automethod:: __iter__

.. autoclass:: ParseRuleSet
    :members:

.. autofunction:: parse

.. autofunction:: unparse

Errors
------
.. autoclass:: ParseError
    :members:

.. autoclass:: AmbiguousParseError
    :members:

.. autoclass:: NoParseError
    :members:

.. autoclass:: InfiniteParseError
    :members:


Building
--------

.. autoclass:: BuilderContext

.. autoclass:: Builder
    :members:

.. autofunction:: make_list_builder

.. autofunction:: make_iter_builder


Symbols
-------

.. autoclass:: Symbol
    :members:

.. autoclass:: NonTerminal
    :members:

.. autoclass:: Terminal
    :members:
