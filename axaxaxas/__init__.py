from collections import defaultdict, namedtuple
from functools import partial
from abc import ABCMeta, abstractmethod

# Symbol, NonTerminal, Terminal are convenience classes for the symbols that compose a ParseRule
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
    """Represents a non-terminal symbol in the grammar, matching tokens according to
    any ParseRules with the specified `head`"""
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
    """Represents a terminal symbol in the grammar, matching a single token of the input"""
    def __init__(self, token, **kwargs):
        Symbol.__init__(self, **kwargs)
        self.token = token

    is_terminal = True

    def match(self, token):
        """Returns true if token is matched by this Terminal"""
        return token == self.token

    def __repr__(self):
        return "Terminal({0!r})".format(self.token)

    def __str__(self):
        # Depends on the token type, but reasonable assumption that
        # str returns the original text of the token.
        # Then there's an extra repr which makes sense
        # in the context of ParseRule.__str__
        return repr(str(self.token))


class ParseRule:
    """Represents a single production in a context free grammar."""
    def __init__(self, head, symbols, *,
                 # Rudimentary ambiguity resolution
                 penalty=0):
        #: The left-hand-side of the production, a string indicating the name of the symbol produced.
        self.head = head
        #: The right-hand-side of the production, a list of terminals and non-terminals (symbols).
        self.symbols = symbols
        #: The numeric penalty assigned to this rule when resolving ambiguity.
        self.penalty = penalty

    def __repr__(self):
        return "ParseRule({0!r}, {1!r})".format(self.head, self.symbols)

    def __str__(self):
        return "<{0}> ::= {1}".format(self.head, " ".join(map(str,self.symbols)))


class ParseTree:
    """Tree structure representing a sucessfully parsed rule"""
    def __init__(self, rule, children=None):
        #: The `ParseRule` matched against.
        self.rule = rule
        #: Tuple of matched items, one for each symbol of `rule`. Each item
        #: is either a token, a `ParseTree`, None or a tuple.
        self.children = children or tuple()

    def extend(self, child):
        return ParseTree(self.rule, self.children + (child,))

    def replace_last(self, child):
        return ParseTree(self.rule, self.children[:-1] + (child,))

    def __repr__(self):
        return "(" + self.rule.head + ": " + " ".join(map(repr, self.children)) + ")"

    def to_tuple(self):
        return id(self.rule), self.children

    def __hash__(self):
        return hash(self.to_tuple())

    def __eq__(self, other):
        return self.to_tuple() == other.to_tuple()


class ParseError(Exception):
    """Base parse error"""
    def __init__(self, message, start_index, end_index):
        super(ParseError, self).__init__(message)
        #: A text description of the error
        self.message = message
        #: Index of the first token where the problem is
        self.start_index = start_index
        #: Index of the last token where the problem is
        self.end_index = end_index

class AmbiguousParseError(ParseError):
    """Indicates that there were multiple possible parses in a context that requires only one"""
    def __init__(self, message, start_index, end_index, values):
        super(AmbiguousParseError, self).__init__(message, start_index, end_index)
        #: A list of all the ambiguous parse trees.
        #: Note that these parsetrees are subtrees of the entire parse, and may
        #: be only partially constructed
        self.values = values

class NoParseError(ParseError):
    """Indicates there were no possible parses"""
    def __init__(self, message, start_index, end_index, encountered, expected_terminals, expected):
        super(NoParseError, self).__init__(message, start_index, end_index)
        #: The token that we failed at, or ``None`` for end of stream.
        self.encountered = encountered
        #: List of all terminal symbols that tried and failed to match `encountered`
        self.expected_terminals = expected_terminals
        #: List of terminal and non-terminal symbols summarizing `expected_terminals`
        self.expected = expected


class InfiniteParseError(ParseError):
    """Indicates there were infinite possible parses"""
    pass

BuilderContext = namedtuple("BuilderContext",[
    "rule",
    "symbol_index",
    "start_index",
    "end_index",
])
BuilderContext.__doc__ = """Contains information about the location and rule currently being parsed. The exact
meaning is specific to each method of `Builder`.

.. py:attribute:: rule

    The relevant `ParseRule`. Can be ``None`` for `merge_vertical` calls at the top level.

.. py:attribute:: symbol_index

    ``context.rule.symbols[context.symbol_index]`` indicates the relevant symbol of the rule. Note `symbol_index`
    may be ``len(context.rule.symbols)`` in some circumstances.

.. py:attribute:: start_index

    The first token in the relevant range of tokens.

.. py:attribute:: end_index

    After the last token in the relevant range of tokens.
"""

class Builder(metaclass=ABCMeta):
    """Abstract base class for constructing parse trees and other objects from a `ParseForest`.
    See :ref:`builders` for more details."""
    @abstractmethod
    def start_rule(self, context):
        """Called when a new rule is started"""
        pass

    @abstractmethod
    def end_rule(self, context, prev_value):
        """Called when a new rule is completed"""
        pass

    @abstractmethod
    def terminal(self, context, token):
        """Called when a terminal is matched"""
        pass

    @abstractmethod
    def skip_optional(self, context, prev_value):
        """Called when an ``optional`` symbol is skipped over"""
        pass

    @abstractmethod
    def begin_multiple(self, context, prev_value):
        """Called when a ``plus`` or ``star`` symbols is enountered"""

    @abstractmethod
    def end_multiple(self, context, prev_value):
        """Called when there are no more matches for a ``plus`` or ``star`` symbol"""
        pass

    @abstractmethod
    def extend(self, context, prev_value, extension_value):
        """Called when a symbol is matched. Potentially multiple times for a ``star`` or ``plus`` symbol"""
        pass

    def merge(self, context, values):
        """Called when there are multiple possible parses, unless `merge_vertical` and
        `merge_horizontal` is overriden."""
        raise AmbiguousParseError("Ambiguous parse.", context.start_index, context.end_index, values)

    def merge_vertical(self, context, values):
        """Called when multiple possible `ParseRule` objects could match a non terminal"""
        return self.merge(context, values)

    def merge_horizontal(self, context, values):
        """Called when there are multiple possible parses of a `ParseRule`."""
        return self.merge(context, values)


class CountingBuilder(Builder):
    """Counts the number of possible parses"""
    def start_rule(self, context):
        return 1

    def end_rule(self, context, prev_value):
        return prev_value

    def terminal(self, context, token):
        return 1

    def skip_optional(self, context, prev_value):
        return prev_value

    def begin_multiple(self, context, prev_value):
        return prev_value

    def end_multiple(self, context, prev_value):
        return prev_value

    def extend(self, context, prev_value, extension_value):
        return prev_value * extension_value

    def merge_vertical(self, context, values):
        return sum(values)

    def merge_horizontal(self, context, values):
        return sum(values)


class SingleParseTreeBuilder(Builder):
    """Builds a single parse tree, or raises AmbiguousParseError"""
    def start_rule(self, context):
        return ParseTree(context.rule)

    def end_rule(self, context, prev_value):
        return prev_value

    def terminal(self, context, token):
        return token

    def skip_optional(self, context, prev_value):
        return prev_value.extend(None)

    def begin_multiple(self, context, prev_value):
        return prev_value.extend(tuple())

    def end_multiple(self, context, prev_value):
        return prev_value

    def extend(self, context, prev_value, extension_value):
        if context.rule.symbols[context.symbol_index].multiple:
            return prev_value.replace_last(prev_value.children[-1] + (extension_value,))
        else:
            return prev_value.extend(extension_value)

class ListBuilder(Builder):
    """Wraps another builder, adding ambiguity support by producing lists of values"""
    def __init__(self, underlying):
        self.underlying = underlying

    def start_rule(self, context):
        return [self.underlying.start_rule(context)]

    def end_rule(self, context, prev_value):
        return [self.underlying.end_rule(context, prev_underlying) for prev_underlying in prev_value]

    def terminal(self, context, token):
        return [self.underlying.terminal(context, token)]

    def skip_optional(self, context, prev_value):
        return [self.underlying.skip_optional(context, prev_underlying) for prev_underlying in prev_value]

    def begin_multiple(self, context, prev_value):
        return [self.underlying.begin_multiple(context, prev_underlying) for prev_underlying in prev_value]

    def end_multiple(self, context, prev_value):
        return [self.underlying.end_multiple(context, prev_underlying) for prev_underlying in prev_value]

    def extend(self, context, prev_value, extension_value):
        results = []
        for prev_underlying in prev_value:
            for extension_underlying in extension_value:
                results.append(self.underlying.extend(context, prev_underlying, extension_underlying))
        return results

    def merge(self, context, values):
        results = []
        for value in values:
            results.extend(value)
        return results

def make_list_builder(builder):
    """Takes a `Builder` which lacks an implementation for `merge_horizontal` and `merge_vertical`, and returns a
    new `Builder` that will accumulate all possible built parse trees into a list"""
    return ListBuilder(builder)

# Mini Stackless lazy evaluation framework
# I'm sure in Python 3.5 this could be written much nicer
# with async for.
# The basic idea is that a Thunk represents a deferred computation, which
# can be "forced" to get the exact value. Thunks never force other thunks,
# instead there is a trampoline mechanism that does the forcing for them, so
# that no matter how much the thunks are nested, they don't use more stack.
# Unfortunately, this design forces a tail-recursive coding style.
class Thunk:
    def __init__(self, f, then=None):
        self.f = f
        self.then = then

    def force(self):
        v = self
        thens = []
        while True:
            if isinstance(v, Thunk):
                if v.then is not None:
                    thens.append(v.then)
                v = v.f()
                continue
            if thens:
                v = thens.pop()(v)
                continue
            break

        return v

def thunk_iter(l, index=0):
    def f():
        if index < len(l):
            return (l[index], thunk_iter(l, index+1))
        else:
            return None
    return Thunk(f)

def thunk_bind(t, f):
    return Thunk(lambda: t, f)

def thunk_map(i, selector):
    def f(cons):
        if cons is None:
            return None
        head, tail = cons
        return (selector(head), thunk_map(tail, selector))
    return thunk_bind(i, f)

def thunk_concat(it1, it2):
    def f(cons):
        if cons is None:
            return it2
        head, tail = cons
        return (head, thunk_concat(tail, it2))
    return thunk_bind(it1, f)

def thunk_flatten(it_of_it):
    def f(cons):
        if cons is None:
            return None
        head, tail = cons
        return thunk_concat(head, thunk_flatten(tail))
    return thunk_bind(it_of_it, f)

def thunk_cross(it1, it2, f):
    return thunk_flatten(thunk_map(it1, lambda v1: thunk_map(it2, lambda v2: f(v1, v2))))

class IterBuilder(Builder):
    """Returns an over all possible parses. Lazy and stackless"""
    def __init__(self, underlying):
        self.underlying = underlying

    def start_rule(self, context):
        return thunk_iter([self.underlying.start_rule(context)])

    def end_rule(self, context, prev_value):
        return thunk_map(prev_value, partial(self.underlying.end_rule, context))

    def terminal(self, context, token):
        return thunk_iter([self.underlying.terminal(context, token)])

    def skip_optional(self, context, prev_value):
        return thunk_map(prev_value, partial(self.underlying.skip_optional, context))

    def begin_multiple(self, context, prev_value):
        return thunk_map(prev_value, partial(self.underlying.begin_multiple, context))

    def end_multiple(self, context, prev_value):
        return thunk_map(prev_value, partial(self.underlying.end_multiple, context))

    def extend(self, context, prev_value, extension_value):
        return thunk_cross(prev_value, extension_value, partial(self.underlying.extend, context))

    def merge(self, context, values):
        return thunk_flatten(thunk_iter(values))

def make_iter_builder(builder):
    """Takes a `Builder` which lacks an implemenation for `merge_horizontal` and `merge_vertical`, and returns a
    new `Builder` that will accumulate all possible built parse trees into an iterator."""
    return IterBuilder(builder)

class ParseForest:
    """Represents a collection of related `ParseTree` objects."""
    # The PartialRule objects themselves already form the forest. This just adds post processing
    # to that data structure for a variety of effects, plus a nicer API.
    def __init__(self, top_partial_rule):
        self.top_partial_rule = top_partial_rule

        self.dests = {}
        self._compute_dests()

        self._trim_penalty()

        self._trim_greedy()

        self._trim_loops()

    def single(self):
        """Returns the only `ParseTree` in the collection, or throws if there are multiple."""
        return self.apply(SingleParseTreeBuilder())

    def all(self):
        """Returns a list of the contained `ParseTree` objects"""
        return self.apply(make_list_builder(SingleParseTreeBuilder()))

    def count(self):
        """Returns a count of the contained `ParseTree` objects"""
        return self.apply(CountingBuilder())

    @property
    def internal_node_count(self):
        return len(self.dests)

    def __iter__(self):
        """Iterators over the list of contained `ParseTree` objects. Calling `all` is somewhat faster"""
        thunk_iterator = self.apply(make_iter_builder(SingleParseTreeBuilder()))
        while True:
            cons = thunk_iterator.force()
            if cons is None:
                break
            head, thunk_iterator = cons
            yield head

    def __len__(self):
        return self.count()

    def apply(self, builder):
        """Constructs a result step at a time using the given `Builder`."""
        memo = {}
        stack = [(self.top_partial_rule, True)]
        while stack:
            current_rule, first_time = stack.pop()
            if current_rule in memo:
                continue
            is_gamma = current_rule.rule.symbols and isinstance(current_rule.rule.symbols[0], GammaNonTerminal)
            if first_time:
                if current_rule.sources is None:
                    if is_gamma:
                        value = None
                    else:
                        context = BuilderContext(current_rule.rule, 0, current_rule.start_index, current_rule.end_index)
                        value = builder.start_rule(context)
                        if current_rule.is_complete:
                            context = BuilderContext(current_rule.rule, current_rule.state, current_rule.start_index, current_rule.end_index)
                            value = builder.end_rule(context, value)
                    memo[current_rule] = value
                else:
                    stack.append((current_rule, False))
                    for source0, source1 in current_rule.sources:
                        if isinstance(source0, PartialRule):
                            stack.append((source0, True))
                        if isinstance(source1, PartialRule):
                            stack.append((source1, True))
            else:
                skip_sentinel = object()
                values_by_source0 = defaultdict(list)
                for source0, source1 in current_rule.sources:
                    if source1 is None:
                        value1 = skip_sentinel
                    else:
                        if isinstance(source1, PartialRule):
                            value1 = memo[source1]
                        else:
                            value1 = builder.terminal(context, source1)
                    values_by_source0[id(source0), source0].append(value1)
                values = []
                for (_, source0), current_values in values_by_source0.items():
                    if isinstance(source0, PartialRule):
                        value0 = memo[source0]
                    else:
                        assert False
                    rule = source0.rule
                    next_symbol = source0.next_symbol
                    symbol_index = source0.state
                    context = BuilderContext(rule, symbol_index, source0.start_index, source0.end_index)
                    if next_symbol.multiple and source0.sub_state == 0:
                        # This was the first call to skip/extend, need to actually create the array
                        value0 = builder.begin_multiple(context, value0)

                    has_skip = any(value is skip_sentinel for value in current_values)
                    has_non_skip = any(value is not skip_sentinel for value in current_values)
                    assert has_skip != has_non_skip

                    if has_skip:
                        assert len(current_values) == 1
                        if next_symbol.multiple:
                            value = builder.end_multiple(context, value0)
                        else:
                            value = builder.skip_optional(context, value0)
                    else:
                        if len(current_values) == 1:
                            value = current_values[0]
                        else:
                            merge_context = BuilderContext(rule, symbol_index, source0.end_index, current_rule.end_index)
                            value = builder.merge_vertical(merge_context, current_values)
                        if not is_gamma:
                            value = builder.extend(context, value0, value)
                    values.append(value)
                if len(values) == 1:
                    value = values[0]
                else:
                    assert not is_gamma
                    context = BuilderContext(rule, current_rule.state, current_rule.start_index, current_rule.end_index)
                    value = builder.merge_horizontal(context, values)
                if current_rule.is_complete and not is_gamma:
                    context = BuilderContext(rule, current_rule.state, current_rule.start_index, current_rule.end_index)
                    value = builder.end_rule(context, value)
                memo[current_rule] = value
        return memo[self.top_partial_rule]

    def _trim_penalty(self):
        # This is definitely not going to work
        # With respect to some of the fiddlier possibilities of
        # looping grammars, but those are largely unimportant.
        # For reference, a correct way would be to use Dijkestra's algorithm,
        # which has no problem with loops.
        stack = [(self.top_partial_rule, True)]
        penalties = {}
        visited = set()
        def score_pair(source0, source1):
            # 3 possibilities. If not visited, then it's a token and has zero penalty.
            # If it is visited, it has either been assigned a penalty, or it's part of a loop
            p0 = penalties.get(source0, 0) if source0 in visited else 0
            p1 = penalties.get(source1, 0) if source1 in visited else 0
            return p0 + p1
        while stack:
            current, first = stack.pop()
            if not isinstance(current, PartialRule):
                continue
            if first:
                if current in visited:
                    continue
                visited.add(current)
                if current.sources is None:
                    penalties[current] = current.rule.penalty
                else:
                    stack.append((current, False))
                    for source0, source1 in current.sources:
                        stack.append((source0, True))
                        stack.append((source1, True))
            else:
                min_penalty = float("inf")
                max_penalty = -float("inf")
                for source0, source1 in current.sources:
                    p = score_pair(source0, source1)
                    min_penalty = min(min_penalty, p)
                    max_penalty = max(max_penalty, p)
                if min_penalty != max_penalty:
                    for source0, source1 in list(current.sources):
                        if score_pair(source0, source1) != min_penalty:
                            self._remove_link(source0, source1, current)
                penalties[current] = min_penalty

    def _trim_loops(self):
        # Tarjan's.
        # This is a stackless variant - full_stack is the hoisted recursive calls
        # and short_stack is the stack actually used by the algorithm.
        # This detects Strongly Connected Components. In principle, we could use this information
        # when walking the ParseForest to omit loops without huge amounts of book keeping
        # But who needs that feature?

        index = 0
        indices = {}
        lowlinks = {}
        short_stack = []
        short_stack_set = set()
        full_stack = [(self.top_partial_rule, None, None)]
        while full_stack:
            stack_item = full_stack.pop()
            current, source_iterator, parent = stack_item
            if source_iterator is None:
                # Initialize this node
                indices[current] = index
                # Using inf here is useful for connected components of size 1 (the common case)
                # as we can distinguish between those with a self-loop and those without
                lowlinks[current] = float("inf")
                index += 1
                short_stack.append(current)
                short_stack_set.add(current)
                if current.sources is None:
                    source_iterator = iter([])
                else:
                    source_iterator = (source for pair in current.sources for source in pair)
                stack_item = current, source_iterator, parent

            # Either process a single item from source_iterator
            # Or do the end_of loop processing
            loop_complete = False
            try:
                source = next(source_iterator)
            except StopIteration:
                loop_complete = True

            if not loop_complete:
                # Schedule the next iteration of the loop
                full_stack.append(stack_item)

                if source not in indices:
                    # Recurse (skipping leaf nodes, which are uninteresting)
                    if isinstance(source, PartialRule) and source.sources is not None:
                        full_stack.append((source, None, current))
                    continue
                elif source in short_stack_set:
                    lowlinks[current] = min(lowlinks[current], indices[source])
            else:
                # End of loop
                if lowlinks[current] == float("inf"):
                    # Strongly-connected component of size 1, with no self loops
                    # Do nothing
                    child = short_stack.pop()
                    short_stack_set.remove(child)
                    assert child is current
                elif lowlinks[current] == indices[current]:
                    # This means we've completed a strongly connected component (SCC).
                    # The elements of short_stack which are between current and the top (inclusive)
                    # Having identified a SCC, we just throw. Maybe better handling later?
                    scc_set = set()
                    while True:
                        child = short_stack.pop()
                        short_stack_set.remove(child)
                        scc_set.add(child)
                        if child is current:
                            break
                    raise InfiniteParseError(current.start_index, current.end_index, "Infinite parse")

                # Fill in source lowlink. In normal this line appears just under the recursive call,
                # but it was easier to move it here when transforming to stackless style
                if parent is not None:
                    lowlinks[parent] = min(lowlinks[parent], lowlinks[current], indices[current])

    def _compute_dests(self):
        """Fills in self.dests with the reverse pointers to partial_rule.sources"""
        stack = [(self.top_partial_rule, True)]
        while stack:
            current, is_first = stack.pop()
            if not isinstance(current, PartialRule):
                continue
            if is_first:
                if current in self.dests:
                    continue
                self.dests[current] = set()
                if current.sources is None:
                    continue
                stack.append((current, False))
                for prev_item, extension in current.sources:
                    stack.append((prev_item, True))
                    stack.append((extension, True))
            else:
                for prev_item, extension in current.sources:
                    self.dests[prev_item].add((current, extension))

    def _trim_greedy(self):
        """Removes any links that have a better choice available, according to greedy/lazy/prefer_early/prefer_late"""
        stack = [(self.top_partial_rule, True)]
        visited = set()
        while stack:
            current, is_first = stack.pop()
            if not isinstance(current, PartialRule):
                continue
            if is_first:
                if current in visited:
                    continue
                visited.add(current)
                stack.append((current, False))
                if current.sources is not None:
                    for source0, source1 in current.sources:
                        stack.append((source0, True))
                        stack.append((source1, True))
            else:
                # Check to see if all the sources of this current
                # Have trimmed it. If so, this node is dead.
                if current.sources is not None and len(current.sources) == 0:
                    for next_item, extension in list(self.dests[current]):
                        self._remove_link(current, extension, next_item)
                # Check if there's actual work
                if current.is_complete:
                    continue
                next_symbol = current.next_symbol
                # NB: Greedy / lazy runs before prefer_early/late.
                # This makes sense if you think of the implicit rules that optional/multiple
                # is standing for.
                if next_symbol.greedy or next_symbol.lazy:
                    # Run over the destinations, and determine if there is both
                    # skip and extend dests
                    has_skip_extend = set(extension is None for next_item, extension in self.dests[current])
                    # If there are both, then de
                    if len(has_skip_extend) == 2:
                        for next_item, extension in list(self.dests[current]):
                            if (extension is None) == next_symbol.greedy:
                                self._remove_link(current, extension, next_item)
                if not next_symbol.is_terminal and (next_symbol.prefer_early or next_symbol.prefer_late):
                    # Run over destinations, and determine the earliest/latest rule
                    min_priority = float("inf")
                    max_priority = -float("inf")
                    for next_item, extension in self.dests[current]:
                        min_priority = min(min_priority, extension.rule.priority)
                        max_priority = max(max_priority, extension.rule.priority)
                    if min_priority != max_priority:
                        keep_priority = min_priority if next_symbol.prefer_early else max_priority
                        for next_item, extension in list(self.dests[current]):
                            if extension.rule.priority != keep_priority:
                                self._remove_link(current, extension, next_item)

    def _remove_link(self, before_partial_rule, extension, after_partial_rule, no_dest=False):
        after_partial_rule.sources.remove((before_partial_rule, extension))
        if not no_dest:
            self.dests[before_partial_rule].remove((after_partial_rule, extension))


class PartialRule:
    """Represents partial parse of a specified rule, plus some bookkeeping info.
     This is often called an Earley Item in the literature"""

    def __init__(self, rule, state, sub_state, start_index, end_index, sources=None):
        self.rule = rule
        self.state = state
        self.sub_state = sub_state
        self.start_index = start_index
        self.end_index = end_index
        # Set of pairs of (prev_state, extension)
        # This is the only mutable part of PartialRule
        self.sources = sources

    @property
    def is_complete(self):
        return len(self.rule.symbols) == self.state

    @property
    def next_symbol(self):
        return self.rule.symbols[self.state]

    def extend(self, token_or_partial_rule, end_index):
        if self.next_symbol.multiple:
            next_sub_state = self.sub_state + 1
            if next_sub_state > self.next_symbol.min_occurs:
                next_sub_state = self.next_symbol.min_occurs
            # This is a hack. In principle there is nothing wrong with
            # not stepping next_sub_state for star rules - it's not used.
            # But in practise doing so can generate loops in the grammar which
            # are awkward to represent in the graph of partial_rules.
            # It's mostly harmless to have a few extra states as we'll just
            # miss a few memoization opportunities.
            if next_sub_state == 0:
                next_sub_state = 1
            return PartialRule(self.rule,
                               self.state,
                               next_sub_state,
                               self.start_index,
                               end_index,
                               set([(self, token_or_partial_rule)]))
        else:
            return PartialRule(self.rule,
                               self.state + 1,
                               0,
                               self.start_index,
                               end_index,
                               set([(self, token_or_partial_rule)]))

    def skip(self):
        if self.next_symbol.multiple:
            # May not skip if we don't meet the minimum number of occurences
            if self.sub_state < self.next_symbol.min_occurs:
                return None
            return PartialRule(self.rule,
                               self.state + 1,
                               0,
                               self.start_index,
                               self.end_index,
                               set([(self, None)]))
        else:
            assert self.next_symbol.optional
            return PartialRule(self.rule,
                               self.state + 1,
                               0,
                               self.start_index,
                               self.end_index,
                               set([(self, None)]))

    def __repr__(self):
        return repr(
            tuple([self.rule.head, self.state, self.sub_state, self.start_index, self.end_index]))

    def to_tuple(self):
        return (id(self.rule), self.state, self.sub_state, self.start_index, self.end_index)

    def __hash__(self):
        return hash(self.to_tuple())

    def __eq__(self, other):
        return self.to_tuple() == other.to_tuple()


class ParseRuleSet:
    """Stores a set of `ParseRule`, with fast retrieval by rule head"""
    def __init__(self):
        self._rules = defaultdict(list)

    def get(self, head, lookahead_token=None):
        """Returns a list of `ParseRule` objects with matching head"""
        return self._rules[head]

    def add(self, rule):
        """Adds a new `ParseRule` to the set"""
        self._rules[rule.head].append(rule)
        rule.priority = len(self._rules[rule.head])

    def is_anonymous(self, head):
        """Returns true if a given head symbol should be omitted from error reporting"""
        return False


class PartialRuleSet:
    # Behaves like a set, only it will merge sources,
    # And provide a canonical identity
    def __init__(self):
        self.d = {}

    def add(self, partial_rule):
        canon_rule = self.d.get(partial_rule, None)
        if canon_rule is None:
            self.d[partial_rule] = partial_rule
            return partial_rule
        else:
            if canon_rule.sources is None:
                assert partial_rule.sources is None
            else:
                canon_rule.sources.update(partial_rule.sources)
            return None

    def __iter__(self):
        return iter(self.d)

class GammaNonTerminal:
    def __init__(self, head):
        self.head = head
    is_terminal = False
    optional = False
    multiple = False
    greedy = False
    lazy = False
    prefer_early = False
    prefer_late = False

def unparse(parse_tree):
    """Converts a `ParseTree` back to a list of tokens"""
    if isinstance(parse_tree, (tuple, list)):
        results = []
        for r in map(unparse, parse_tree):
            results.extend(r)
        return results
    if parse_tree is None:
        return []
    if not isinstance(parse_tree, ParseTree):
        return [parse_tree]
    results = []
    for child in parse_tree.children:
        results.extend(unparse(child))
    return results

# The code below is a modified Earley Parser.
# 1) The parse tree is not built from the table, it's built in the PartialRules themselves,
#    which form a DAG.
# 2) optional, star, and plus are built straight into the rules. This is mostly for convenience.
#    This only takes two tweaks to the parser - each rule is checked to see if it can Skipped,
#    i.e. advanced without consuming a token, and when scanning/completing some rules, the state counter
#    is not advanced in some cases. Extra state called sub_state is needed to record if we've found at least one
#    item.
# 3) There's a distinction between PartialRules waiting for completion, and PartialRules that still need some other
#    sort of processing. I just find it a bit easier to think about, and they use different storage data structures.
#    We address "the problem of epilson" (i.e. the fact that for nonterminals that can match the empty string,
#    the set used for completion rules is still being written to), by storing completed items in a separate
#    structure. Aycock and Horspool's solution is much neater, but requires pre-computation.
#      Aycock & Horspool "Practical Earley Parsing", The Computer Journal, Vol. 45, No. 6, 2002
#
# TODO: Apply this optimization? http://loup-vaillant.fr/tutorials/earley-parsing/right-recursion

def parse(rule_set, head, tokens, *, fail_if_empty=True):
    """Parses a stream of ``tokens`` according to the grammer in ``rule_set`` by attempting to match
    the non-terminal specified by ``head``."""
    # Returns a PartialRule that represents a parse forest

    token_stream = list(tokens)

    # We enforce single object identify amongst PartialRules
    # so that we can keep references to them in sources
    # and update those references
    canon_rules = [PartialRuleSet()]

    def make_canon(partial_rule):
        return canon_rules[partial_rule.end_index].add(partial_rule)

    # List of dict of suspended rules keyd by what they are waiting for
    pending_rules = []
    # List of dict of completed rules keyd by their head
    completed_rules = []
    # We start with a fake rule called gamma that matches head
    # This awkwardness is because we don't otherwise have an object for
    # "all the rules with the starting head"
    gamma_rule = ParseRule("anon gamma", [GammaNonTerminal(head)])
    current_rules = set([make_canon(PartialRule(gamma_rule, 0, 0, 0, 0))])
    # Likewise we need a fake token at the end
    # Because one more loop is required to close all the objects
    end_sentinel = object()

    next_rules = set()
    final_state = None
    for index, token in enumerate(token_stream + [end_sentinel]):
        pending_rules.append(defaultdict(list))
        completed_rules.append(defaultdict(list))
        canon_rules.append(PartialRuleSet())
        terminal_partial_rules = []
        while current_rules:
            partial_rule = current_rules.pop()
            if partial_rule is None:
                continue
            if partial_rule.is_complete:
                # Completion
                if token is end_sentinel and partial_rule.rule is gamma_rule and partial_rule.start_index == 0:
                    # Don't return immediately when we've found the final state
                    # as there may be more completions filling in sources
                    final_state = partial_rule
                for progressed_rule in pending_rules[partial_rule.start_index][partial_rule.rule.head]:
                    current_rules.add(make_canon(progressed_rule.extend(partial_rule, index)))
                if partial_rule.start_index == index:
                    completed_rules[partial_rule.start_index][partial_rule.rule.head].append(partial_rule)
            else:
                symbol = partial_rule.next_symbol
                # Some head's are considered "anonymous" and we expand them instead of reporting them.
                # TODO: empty is here as a quick hack. Need to figure out how to give sensible reporting for any
                # possibly empty rule
                if not symbol.is_terminal:
                    # Prediction
                    head = symbol.head
                    pending_rules[-1][head].append(partial_rule)
                    for rule in rule_set.get(head):
                        current_rules.add(make_canon(PartialRule(rule, 0, 0, index, index)))
                    for completed_rule in completed_rules[index][head]:
                        assert completed_rule.end_index == index
                        current_rules.add(make_canon(partial_rule.extend(completed_rule, completed_rule.end_index)))
                elif symbol.is_terminal:
                    # Scanning
                    if token is not end_sentinel and symbol.match(token):
                        next_rules.add(make_canon(partial_rule.extend(token, index + 1)))
                    terminal_partial_rules.append(partial_rule)
                # Skipping
                if symbol.optional or symbol.multiple:
                    skipped = partial_rule.skip()
                    if skipped is not None:
                        current_rules.add(make_canon(skipped))
        current_rules, next_rules = next_rules, set()
        if len(current_rules) == 0 and final_state is None:
            if token is end_sentinel and not fail_if_empty:
                return ParseForest(PartialRule(ParseRule("gamma", []), 0, 0, 0, 0))

            # We have a list of all terminals that were evaluated,
            # But we can give higher level information about what was expected
            open_set = set(terminal_partial_rules)
            visited = set()
            children = defaultdict(list)
            exits = []
            while open_set:
                partial_rule = open_set.pop()
                if partial_rule in visited:
                    continue
                visited.add(partial_rule)
                if partial_rule.rule is gamma_rule:
                    exits.append(partial_rule)
                elif partial_rule.state == 0 and partial_rule.sub_state == 0:
                    parent_list = list(pending_rules[index][partial_rule.rule.head])
                    assert len(parent_list) > 0
                    for parent in parent_list:
                        children[parent].append(partial_rule)
                        open_set.add(parent)
                else:
                    exits.append(partial_rule)
            non_anon_exits = set()
            while exits:
                exit = exits.pop()
                next_symbol = exit.next_symbol
                if not next_symbol.is_terminal:
                    if rule_set.is_anonymous(next_symbol.head) or exit.rule is gamma_rule:
                        exits.extend(children[exit])
                        continue
                non_anon_exits.add(exit)
            encountered_token = token if token is not end_sentinel else None
            encountered_token_str = repr(token) if token is not end_sentinel else "end"
            expected = ", ".join(sorted(set(str(partial_rule.next_symbol) for partial_rule in non_anon_exits)))
            raise NoParseError("Unexpected {0}, was expecting {1}.".format(encountered_token_str, expected),
                               index, index,
                               encountered_token,
                               [partial_rule.next_symbol for partial_rule in terminal_partial_rules],
                               [partial_rule.next_symbol for partial_rule in non_anon_exits])

        # With a front to back order of evaluation, we don't need this any longer
        completed_rules[index] = None

    return ParseForest(final_state)

__all__ = [
    "ParseRule",
    "ParseTree",
    "ParseError",
    "AmbiguousParseError",
    "NoParseError",
    "InfiniteParseError",
    "ParseForest",
    "ParseRuleSet",
    "unparse",
    "parse",
    "Builder",
    "make_list_builder",
    "make_iter_builder",
    "Symbol",
    "NonTerminal",
    "Terminal",
]