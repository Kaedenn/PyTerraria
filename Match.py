#!/usr/bin/env python

TOK_EXPRSEP = ';'
TOK_TERMSEP = ','
TOK_RANGE   = '-'
TOK_NONE    = "None"

class MatchSyntaxError(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(MatchSyntaxError, self).__init__(*args, **kwargs)

class Build(object):
    """Assisted building of match expressions
Given:
Nothing, Expr = Build.Nothing, Build.Expr
TermSet, TermRange = Build.TermSet, Build.TermRange

Use:
Expr(TermSet(1, 2, TermRange(8, 20))) -> [1, 2] + range(8, 21), [], []
Expr(Nothing(), TermSet(44, 88)) -> [], [44, 88], []
    """
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

class Match(object):
    """
Match(expr, names=None) -> sequence of integers

Parses @param expr and returns an iterable of integers specified by the
expression. The expression has the grammar:

Expr := TermSet (';' TermSet (';' TermSet))

TermSet := Term (',' Term)*
Term := Number | Number '-' Number | "None" | ""
Number := HexNumber | DecNumber | Identifier
HexNumber = <number in hexadecimal notation>
DecNumber = <number in decimal notation>
Identifier = <any key in @param names to __init__>

Using "None" or the empty string for the term matches any value

The @param names is an optional dictionary of strings to numbers. The
Number token, if not a valid number, is passed through the dictionary
to find a value.
"""
    def __init__(self, expr, names=None):
        self._raw_expr = expr
        self._names = {} if names is None else names
        self._expr = self._parse_match(expr)

    def _parse_match(self, expr):
        parts = expr.split(TOK_EXPRSEP)
        if len(parts) > 3:
            raise MatchSyntaxError("Expression %s has too many parts" % (expr,))
        while len(parts) < 3:
            parts.append(None)
        return tuple(self._parse_part(p) for p in parts)

    def _parse_part(self, part):
        if part is None or len(part) == 0 or part == TOK_NONE:
            return
        terms = part.split(TOK_TERMSEP)
        return sum([list(self._parse_range(t)) for t in terms], [])

    def _parse_range(self, r):
        nums = r.split(TOK_RANGE)
        if len(nums) == 1:
            return [self._parse_num(nums[0])]
        if len(nums) == 2:
            return range(self._parse_num(nums[0]), self._parse_num(nums[1])+1)
        raise MatchSyntaxError("Invalid term: %s" % (r,))

    def _parse_num(self, num):
        if num in self._names:
            return self._names[num]
        try:
            return int(num, 0)
        except ValueError as e:
            raise MatchSyntaxError("Token %s not a number" % (num,), e)

    def extract(self):
        return self._expr

    def match(self, v1, v2=None, v3=None):
        for p,v in zip(self._expr, (v1, v2, v3)):
            if p is not None and v not in p:
                return False
        return True

def _do_test(expr, r1=None, r2=None, r3=None, names=None):
    m = Match(expr, names)
    p1, p2, p3 = m.extract()
    print("%s -> %s %s %s" % (expr, p1, p2, p3))
    assert (p1 == r1), "test %s result 1 %s != %s" % (expr, p1, r1)
    assert (p2 == r2), "test %s result 2 %s != %s" % (expr, p2, r2)
    assert (p3 == r3), "test %s result 3 %s != %s" % (expr, p3, r3)
    print("PASS")

if __name__ == "__main__":
    # test trivial
    _do_test('')
    # test one
    _do_test("1", [1])
    # test two
    _do_test("1;2", [1], [2])
    # test three
    _do_test("1;2;3", [1], [2], [3])
    # test pair
    _do_test("1,2", [1, 2])
    # test two pairs
    _do_test("1,2;3,4", [1, 2], [3, 4])
    # test range
    _do_test("1-5", [1, 2, 3, 4, 5])
    # test two ranges
    _do_test("1-5;2-10", [1, 2, 3, 4, 5], [2, 3, 4, 5, 6, 7, 8, 9, 10])
    # test two triples with ranges
    _do_test("1,3,5-9;2,4,6-10", [1, 3, 5, 6, 7, 8, 9], [2, 4, 6, 7, 8, 9, 10])
    # test three triples with ranges
    _do_test("1,3,5-9;2,4,6-10;3,4,5,6-9",
             [1, 3, 5, 6, 7, 8, 9],
             [2, 4, 6, 7, 8, 9, 10],
             [3, 4, 5, 6, 7, 8, 9])
    # test empty item
    _do_test("1;;3", [1], None, [3])
    # test None item (equivalent to empty)
    _do_test("1;None;3", [1], None, [3])
    # test trivial names
    _do_test("One", [1], names={'One': 1})
    # test names range
    _do_test("One-Five", [1, 2, 3, 4, 5], names={'One': 1, 'Five': 5})


