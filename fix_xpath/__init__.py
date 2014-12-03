from lxml.etree import XPath, XPathSyntaxError


class MaxRecursionDepthHit(Exception):
    """Internal error, raised to limit recursion."""
    pass


class BracketPairs:
    PAIRS = ('[]', '()', '{}')
    MATCHING_CLOSERS = dict(tuple(pair) for pair in PAIRS)
    MATCHING_OPENERS = {v: k for k, v in MATCHING_CLOSERS.iteritems()}
    CLOSERS = frozenset(MATCHING_OPENERS.keys())
    OPENERS = frozenset(MATCHING_CLOSERS.keys())


def _find_mismatch(expression, pairs=BracketPairs.PAIRS):
    if pairs is not BracketPairs.PAIRS:
        matching_closers = dict(tuple(pair) for pair in pairs)
        matching_openers = {v: k for k, v in matching_closers.iteritems()}
        closers = frozenset(matching_openers.keys())
        openers = frozenset(matching_closers.keys())
    else:
        matching_closers, matching_openers, closers, openers = (
            BracketPairs.MATCHING_CLOSERS,
            BracketPairs.MATCHING_OPENERS,
            BracketPairs.CLOSERS,
            BracketPairs.OPENERS,
        )

    stack = []
    for i, char in enumerate(expression):
        if char in closers:
            if not stack:
                return matching_openers[char], slice(0, i + 1)
            prev_i, prev_brace = stack.pop()
            closer = matching_closers[prev_brace]
            if char != closer:
                return closer, slice(prev_i, i + 1)
            continue
        if char in openers:
            stack.append((i, char))

    if stack:
        prev_i, prev_brace = stack.pop()
        return matching_closers[prev_brace], slice(prev_i, i + 2)

    return
        

def _fix_brackets(expression, compile, depth, max_depth, min_depth):
    if depth > max_depth:
        raise MaxRecursionDepthHit("Recursion limit hit.")

    parse_error = _find_mismatch(expression)
    if parse_error is None:
        compile(expression)
        yield expression
        return
    
    missing_brace, location = parse_error
    
    new_expressions = (
        ''.join((expression[:i], missing_brace, expression[i:]))
        for i in
        xrange(location.start, location.stop)
    )
    checked_expressions = []
    if depth >= min_depth:
        for new_expression in new_expressions:
            try:
                compile(new_expression)
                yield new_expression
            except (MaxRecursionDepthHit, XPathSyntaxError):
                pass
            checked_expressions.append(new_expression)
    else:
        checked_expressions = new_expressions

    for checked_expression in checked_expressions:
        try:
            child_expressions = _fix_brackets(
                checked_expression, 
                compile=compile, 
                depth=depth + 1, 
                max_depth=max_depth,
                min_depth=min_depth,
            )
            for child_expression in child_expressions:
                yield child_expression
        except (MaxRecursionDepthHit, XPathSyntaxError):
            continue
    
    raise XPathSyntaxError("Could not fix `{}`".format(expression))


def fix_brackets(expression, compile=XPath, max_depth=3):
    for i in xrange(max_depth):
        try:
            return next(_fix_brackets(expression, compile, 0, i + 1, i))
        except XPathSyntaxError:
            pass
    raise XPathSyntaxError("Could not fix `{}`".format(expression))


if __name__ == '__main__':
    # Some small tests
    good_exp = ".//*[contains(text(), 'xyz')]//span[@value = '123']/b"
    bad_exps = (
        ".//*[contains(text(), 'xyz')//span[@value = '123']/b",
        ".//*[contains(text(, 'xyz')]//span[@value = '123']/b",
        ".//*[contains(text(), 'xyz']//span[@value = '123']/b",
        ".//*[contains(text(), 'xyz')//span[@value = '123'/b",
        "(.//*[contains(text(), 'xyz']//span[@value = '123']/b)1]",
    )

    assert fix_brackets(good_exp) == good_exp
    
    for bad_exp in bad_exps:
        print bad_exp
        fixed = fix_brackets(bad_exp)
        print fixed
        assert fixed != bad_exp
        XPath(fixed)
        print

    print "All tests passed."