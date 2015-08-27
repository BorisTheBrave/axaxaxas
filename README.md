Axaxaxas
=======================

Axaxaxas - *making sense of nonsense*.

Axaxaxas is a Python 3.3 implementation of an [Earley Parser](https://en.wikipedia.org/wiki/Earley_parser). 
Earley parsers are a robust parser that can recognize any context-free grammar, with good support for amiguous grammars.
They have linear performance for a wide class of grammars, and worst case O(n^3).
  
The main goals of this implementation are ease of use, customization, and requiring no pre-processing step
for the grammar. You may find the 
[Marpa](https://jeffreykegler.github.io/Marpa-web-site/) project better suits high performance needs.

Documentation can be found at http://axaxaxas.readthedocs.org

Features
--------
 - Complete Earley Parser implemenation
 - Native support for higher level constructs such as optional elements and [Kleene stars](https://en.wikipedia.org/wiki/Kleene_star)
 - Many options for taming ambiguity
 - Completely customizable tokens, terminals and parse trees
 - No pre-processing step at all - grammars can be changed on the fly
 
TODO
----
 - [Joop Leo's LR performance enhancements](http://loup-vaillant.fr/tutorials/earley-parsing/right-recursion)
 - Better handling of infinite grammars
 - Token lookahead
 - Fast-first option
 - Handle infinite parses better.

License
-------
MIT License (MIT)

Copyright (c) 2015 Adam Newgas