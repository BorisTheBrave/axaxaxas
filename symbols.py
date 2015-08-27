# Convenience classes for the symbols that compose a ParseRule
# These classes are duck-typed, so you don't have to use the ones here

class Symbol:
    """Base class for non-terminals and terminals, this is used when defining ParseRule objects"""
    def __init__(self, *, star=False, optional=False, plus=False, name=None, greedy=False, lazy=False):
        # Mutually exclusive settings
        assert int(star) + int(optional) + int(plus) <= 1
        assert not (lazy and greedy)
        # Lazy/Greedy only make sense on star/optional/plus
        assert not (lazy or greedy) or (star or optional or plus)
        self.optional = optional
        self.multiple = star or plus
        if optional or star:
            self.min_occurs = 0
        else:
            self.min_occurs = 1
        self.name = name
        self.greedy = greedy
        self.lazy = lazy

    def _specifier(self):
        t = ""
        if self.multiple and self.min_occurs==0:
            t = "*"
        elif self.multiple and self.min_occurs!=0:
            t = "+"
        elif self.optional:
            t = "?"
        if self.lazy:
            t += "?"
        elif self.greedy:
            t += "*" # not exactly standard, but I think people will get it
        return t


class NonTerminal(Symbol):
    def __init__(self, head, prefer_early=False, prefer_late=False, **kwargs):
        Symbol.__init__(self, **kwargs)
        self.head = head
        assert not (prefer_early and prefer_late)
        self.prefer_early = prefer_early
        self.prefer_late = prefer_late

    is_terminal = False

    def __repr__(self):
        return "NonTerminal({0!r})".format(self.head)

    def __str__(self):
        return "<{0}>{1}".format(self.head, self._specifier())


class Terminal(Symbol):
    def __init__(self, token, **kwargs):
        Symbol.__init__(self, **kwargs)
        self.token = token

    is_terminal = True

    def match(self, token):
        return token == self.token

    def __repr__(self):
        return "Terminal({0!r})".format(self.token)

    def __str__(self):
        # Depends on the token type, but reasonable assumption that
        # str returns the original text of the token.
        # Then there's an extra repr which makes sense
        # in the context of ParseRule.__str__
        return repr(str(self.token))
