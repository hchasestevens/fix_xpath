from lxml.etree import XPath, XPathSyntaxError


class MaxRecursionDepthHit(Exception):
    """Internal error, raised to limit recursion."""
    pass


def _find_mismatch(expression, pairs=('[]', '()', '{}')):
    pairs = [tuple(pair) for pair in pairs]
    matching_closers = dict(tuple(pair) for pair in pairs)
    matching_openers = {v: k for k, v in matching_closers.iteritems()}
    closers = frozenset(matching_openers.keys())
    openers = frozenset(matching_closers.keys())

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
        

def fix_brackets(expression, compile=XPath, depth=0, max_depth=3):
    if depth > max_depth:
        raise MaxRecursionDepthHit("Recursion limit hit.")

    parse_error = _find_mismatch(expression)
    if not parse_error:
        return expression
    
    missing_brace, location = parse_error
    for i in xrange(location.start, location.stop):
        ammended_expression = ''.join((expression[:i], missing_brace, expression[i:]))
        try:
            fixed_expression = fix_brackets(
                ammended_expression,
                depth=depth + 1
            )
            compile(fixed_expression)
            return fixed_expression
        except (MaxRecursionDepthHit, XPathSyntaxError):
            continue
    
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