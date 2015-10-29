#!/usr/bin/env python

TOK_EXPRSEP = ';'
TOK_TERMSEP = ','
TOK_RANGE   = '-'
TOK_NONE    = "None"
TOK_HEX     = "0x"

class MatchSyntaxError(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(MatchSyntaxError, self).__init__(*args, **kwargs)

class Build(object):
    @staticmethod
    def Nothing():
        return TOK_NONE
    @staticmethod
    def Expr(t1=None, t2=None, t3=None):
        return TOK_EXPRSEP.join((str(t1), str(t2), str(t3)))
    @staticmethod
    def TermSet(*args):
        return TOK_TERMSEP.join(str(arg) for arg in args)
    @staticmethod
    def TermRange(num1, num2):
        return str(num1) + TOK_RANGE + str(num2)

def _parse_num(num):
    if num.startswith(TOK_HEX):
        return int(num, 16)
    if not num.isdigit():
        raise MatchSyntaxError("Token %s not a number" % (num,))
    return int(num)

def _parse_range(r):
    nums = r.split(TOK_RANGE)
    if len(nums) == 1:
        return [_parse_num(nums[0])]
    if len(nums) == 2:
        return range(_parse_num(nums[0]), _parse_num(nums[1])+1)
    raise MatchSyntaxError("Invalid term: %s" % (r,))

def _parse_part(part):
    if part is None or len(part) == 0 or part == TOK_NONE:
        return
    terms = part.split(TOK_TERMSEP)
    return sum([list(_parse_range(t)) for t in terms], [])

def parse_match(expr):
    """
parse_match(expr) -> sequence of integers

Parses @param expr and returns an iterable of integers specified by the
expression. The expression has the grammar:

Expr := TermSet (';' TermSet (';' TermSet))

TermSet := Term (',' Term)*
Term := Number | Number '-' Number | "None" | ""
Number := HexNumber | DecNumber
HexNumber = <number in hexadecimal notation>
DecNumber = <number in decimal notation>

Using "None" or the empty string for the term matches any value
"""
    parts = expr.split(TOK_EXPRSEP)
    if len(parts) > 3:
        raise MatchSyntaxError("Expression %s has too many parts" % (expr,))
    while len(parts) < 3:
        parts.append(None)
    return tuple(_parse_part(p) for p in parts)

def do_match(match, v1, v2, v3):
    p1, p2, p3 = match
    if p1 is not None and v1 not in p1:
        return False
    if p2 is not None and v2 not in p2:
        return False
    if p3 is not None and v3 not in p3:
        return False
    return True

def _do_test(expr, result1 = None, result2=None, result3=None):
    p1, p2, p3 = parse_match(expr)
    print("%s -> %s %s %s" % (expr, p1, p2, p3))
    assert (p1 == result1), "test %s result 1 %s != %s" % (expr, p1, result1)
    assert (p2 == result2), "test %s result 2 %s != %s" % (expr, p2, result2)
    assert (p3 == result3), "test %s result 3 %s != %s" % (expr, p3, result3)
    print("PASS")

if __name__ == "__main__":
    _do_test('')
    _do_test("1", [1])
    _do_test("1;2", [1], [2])
    _do_test("1;2;3", [1], [2], [3])
    _do_test("1,2", [1, 2])
    _do_test("1,2;3,4", [1, 2], [3, 4])
    _do_test("1-5", [1, 2, 3, 4, 5])
    _do_test("1-5;2-10", [1, 2, 3, 4, 5], [2, 3, 4, 5, 6, 7, 8, 9, 10])
    _do_test("1,3,5-9;2,4,6-10", [1, 3, 5, 6, 7, 8, 9], [2, 4, 6, 7, 8, 9, 10])
    _do_test("1,3,5-9;2,4,6-10;3,4,5,6-9",
             [1, 3, 5, 6, 7, 8, 9],
             [2, 4, 6, 7, 8, 9, 10],
             [3, 4, 5, 6, 7, 8, 9])
    _do_test("1;;3", [1], None, [3])
    _do_test("1;None;3", [1], None, [3])

