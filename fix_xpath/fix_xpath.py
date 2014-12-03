from lxml.etree import XPath, XPathSyntaxError


class MaxRecursionDepthHit(Exception):
    pass


def find_mismatch(expression, pairs=('[]', '()', '{}')):
    pairs = [tuple(pair) for pair in pairs]
    open_braces = {open_brace for open_brace, __ in pairs}
    close_braces = {close_brace for __, close_brace in pairs}
    braces = open_braces | close_braces

    stack = []
    for i, char in enumerate(expression):
        if char in close_braces:
            if not stack:
                matching_opener = next(
                    open_brace 
                    for open_brace, close_brace in
                    pairs
                    if close_brace == char
                )
                return matching_opener, slice(0, i + 1)
            prev_i, prev_brace = stack.pop()
            pair = (prev_brace, char)
            if not (prev_brace, char) in pairs:
                matching_closer = next(
                    close_brace 
                    for open_brace, close_brace in
                    pairs
                    if open_brace == prev_brace
                )
                return matching_closer, slice(prev_i, i + 1)
            continue
        if char in open_braces:
            stack.append((i, char))

    if stack:
        prev_i, prev_brace = stack.pop()
        matching_closer = next(
            close_brace 
            for open_brace, close_brace in
            pairs
            if open_brace == prev_brace
        )
        return matching_closer, slice(prev_i, i + 2)
    return
        

def fix_braces(expression, compile=XPath, depth=0, max_depth=3):
    if depth > max_depth:
        raise MaxRecursionDepthHit("Recursion limit hit.")

    parse_error = find_mismatch(expression)
    if not parse_error:
        return expression
    
    missing_brace, location = parse_error
    for i in xrange(location.start, location.stop):
        ammended_expression = ''.join((expression[:i], missing_brace, expression[i:]))
        try:
            fixed_expression = fix_braces(
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
    bad_exp = ".//*[contains(text(), 'xyz')//span[@value = '123']/b"
    bad_exp_2 = ".//*[contains(text(, 'xyz')]//span[@value = '123']/b"
    bad_exp_3 = ".//*[contains(text(), 'xyz']//span[@value = '123']/b"
    worse_exp = ".//*[contains(text(), 'xyz')//span[@value = '123'/b"
    worse_exp2 = "(.//*[contains(text(), 'xyz']//span[@value = '123']/b)1]"
    
    assert fix_braces(good_exp) == good_exp
    
    fixed = fix_braces(bad_exp)
    print bad_exp
    print fixed
    assert fixed != bad_exp
    XPath(fixed)
    print

    fixed = fix_braces(bad_exp_2)
    print bad_exp_2
    print fixed
    assert fixed != bad_exp_2
    XPath(fixed)
    print

    fixed = fix_braces(bad_exp_3)
    print bad_exp_3
    print fixed
    assert fixed != bad_exp_3
    XPath(fixed)
    print

    fixed = fix_braces(worse_exp)
    print worse_exp
    print fixed
    assert fixed != worse_exp
    XPath(fixed)
    print

    fixed = fix_braces(worse_exp2)
    print worse_exp2
    print fixed
    assert fixed != worse_exp2
    XPath(fixed)
    print

    print "All tests passed."