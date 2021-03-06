from lxml.etree import XPath, XPathSyntaxError


class _BracketPairs:
    PAIRS = ('[]', '()',)
    MATCHING_CLOSERS = dict(tuple(pair) for pair in PAIRS)
    MATCHING_OPENERS = {v: k for k, v in MATCHING_CLOSERS.iteritems()}
    CLOSERS = frozenset(MATCHING_OPENERS.keys())
    OPENERS = frozenset(MATCHING_CLOSERS.keys())


def _find_mismatch(expression, pairs):
    if pairs is not _BracketPairs.PAIRS:
        matching_closers = dict(tuple(pair) for pair in pairs)
        matching_openers = {v: k for k, v in matching_closers.iteritems()}
        closers = frozenset(matching_openers.keys())
        openers = frozenset(matching_closers.keys())
    else:
        matching_closers, matching_openers, closers, openers = (
            _BracketPairs.MATCHING_CLOSERS,
            _BracketPairs.MATCHING_OPENERS,
            _BracketPairs.CLOSERS,
            _BracketPairs.OPENERS,
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
        

def _fix_brackets(expression, check_syntax, bracket_pairs, depth, min_depth, max_depth):
    parse_error = _find_mismatch(expression, bracket_pairs)
    if parse_error is None:
        check_syntax(expression)
        yield expression
        return
    
    missing_brace, location = parse_error
    
    new_expressions = (
        ''.join((expression[:i], missing_brace, expression[i:]))
        for i in
        xrange(location.start, location.stop)
    )
    if depth >= min_depth:
        checked_expressions = []
        for new_expression in new_expressions:
            try:
                check_syntax(new_expression)
                yield new_expression
            except XPathSyntaxError:
                pass
            checked_expressions.append(new_expression)
    else:
        checked_expressions = new_expressions

    if not depth + 1 > max_depth:
        for checked_expression in checked_expressions:
            try:
                child_expressions = _fix_brackets(
                    checked_expression, 
                    check_syntax=check_syntax, 
                    bracket_pairs=bracket_pairs,
                    depth=depth + 1, 
                    max_depth=max_depth,
                    min_depth=min_depth,
                )
                for child_expression in child_expressions:
                    yield child_expression
            except XPathSyntaxError:
                continue
    
    raise XPathSyntaxError("Could not fix `{}`".format(expression))


def fix_brackets(expression, check_syntax=XPath, max_depth=3, bracket_pairs=_BracketPairs.PAIRS):
    """
    Attempt to fix missing brackets in an XPath expression. Raises 
    XPathSyntaxError on failure.

    :param str expression: XPath expression to be fixed.
    :param str->T check_syntax: Function used to validate XPath. Must raise 
        XPathSyntaxError on failure.
    :param int max_depth: Maximum search depth. Equivalent to "maximum expected
        number of errors."
    :param list[str] bracket_pairs: Pairs of brackets to match on. Defaults to
        [] and ().

    :rtype str: Syntactically valid XPath expression.
    """
    for i in xrange(max_depth):
        try:
            return next(_fix_brackets(
                expression, 
                check_syntax=check_syntax, 
                bracket_pairs=bracket_pairs, 
                depth=0, 
                min_depth=i - 1, 
                max_depth=i
            ))
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