#!/usr/bin/env python

import ast
from shapely.geometry import Point, Polygon, MultiPolygon

class NamedMultiPolygon(MultiPolygon):
    def __init__(self, name, points, *args, **kwargs):
        super(NamedMultiPolygon, self).__init__(points, *args, **kwargs)
        self._name = name
    def name(self):
        return self._name
    def union(self, other):
        result = super(NamedMultiPolygon, self).union(other)
        return NamedMultiPolygon(self._name, [result])
    def intersection(self, other):
        result = super(NamedMultiPolygon, self).intersection(other)
        return NamedMultiPolygon(self._name, [result])
    def difference(self, other):
        result = super(NamedMultiPolygon, self).difference(other)
        return NamedMultiPolygon(self._name, [result])
    def symmetric_difference(self, other):
        result = super(NamedMultiPolygon, self).symmetric_difference(other)
        return NamedMultiPolygon(self._name, [result])

class WorldPolySet(object):
    def __init__(self, name="World", noexcept=False):
        self._polys = []
        self._poly_lookup = {}
        self._noexcept = noexcept
        self._tok_special = (
            '+xmin', '+xmax', '+ymin', '+ymax', '+name', '+color'
        )
        self._tok_operator = (
            'UNION', 'INTERSECTION', 'DIFFERENCE', 'SYMMETRIC_DIFFERENCE'
        )
        self._name = "World"
        self._colors = {}
        self._xmin = 0
        self._xmax = 0
        self._ymin = 0
        self._ymax = 0

    def _raise(self, exception):
        if not self._noexcept:
            raise exception
        # all calling functions return False on error with noexcept set
        return False

    def coalesce(self):
        if len(self._polys) == 0:
            return None
        result = self._polys[0]
        for poly in self._polys[1:]:
            result = result.union(poly)
        return result

    def _update_lims(self, namedpoly):
        minx, miny, maxx, maxy = namedpoly.bounds
        self._xmin = min(self._xmin, minx)
        self._xmax = max(self._xmax, maxx)
        self._ymin = min(self._ymin, miny)
        self._ymax = max(self._ymax, maxy)

    def _parse_special(self, op, val):
        if op == '+xmin':
            self._xmin = int(val)
        elif op == '+xmax':
            self._xmax = int(val)
        elif op == '+ymin':
            self._ymin = int(val)
        elif op == '+ymax':
            self._ymax = int(val)
        elif op == '+color':
            world, color = val.split(None, 1)
            self._colors[world] = color
        elif op == '+name':
            self._name = val
        return True

    def _do_operator(self, result, op, name):
        if op == 'UNION':
            return result.union(self._poly_lookup[name])
        if op == 'INTERSECTION':
            return result.intersection(self._poly_lookup[name])
        if op == 'DIFFERENCE':
            return result.difference(self._poly_lookup[name])
        if op == 'SYMMETRIC_DIFFERENCE':
            return result.symmetric_difference(self._poly_lookup[name])

    def _parse_operator(self, name, op, args):
        arglist = args.split()
        result = self._poly_lookup[arglist[0]]
        result = result.union(result)   # to make a copy of it
        result._name = name
        for arg in arglist[1:]:
            try:
                result = self._do_operator(result, op, arg)
            except KeyError as e:
                return self._raise(RuntimeError("World %s not found" % (arg,),
                                                e))
        self._poly_lookup[name] = result
        self._polys.append(result)
        self._update_lims(result)
        return True

    def parse_line(self, line):
        l = line.strip()
        if len(l) == 0 or l[0] == '#':
            return True
        if ' ' not in l:
            return self._raise(RuntimeError("Invalid line: %r" % (line,)))
        name, val = l.split(None, 1)
        if name in self._tok_special:
            return self._parse_special(name, val)
        if val.split(None, 1)[0] in self._tok_operator:
            op, args = val.split(None, 1)
            return self._parse_operator(name, op, args)
        poly = Polygon(ast.literal_eval(val))
        self._poly_lookup[name] = NamedMultiPolygon(name, [poly])
        self._polys.append(self._poly_lookup[name])
        self._update_lims(self._poly_lookup[name])
        return True

    def parse_lines(self, lines):
        return all(self.parse_line(l) for l in lines)

    def color(self, polyname, default=None):
        return self._colors.get(polyname, default)

    def polys(self):
        return tuple(self._polys)

    def name(self):
        return self._name

    def names(self):
        return tuple(p.name() for p in self._polys)

    def box(self):
        return (self._xmin, self._ymin), (self._xmax, self._ymax)


