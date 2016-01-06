#!/usr/bin/env python

import itertools
from shapely.geometry import Polygon

def Simplify(poly, epsilon=0.5):
    """Simplifies a polygon according to @param epsilon (default 0.5) using
    the Ramer-Douglas-Peucker algorithm. Values of epsilon less than 1 result
    in a polygon with the same exact perimeter, just represented in as few
    points as possible.
    
    The polygon argument must be a sequence of points:
        [(x1, y1), (x2, y2), ...]
    """
    simplified = Polygon(poly).simplify(epsilon)
    line_ring = list(simplified.array_interface_base['data'])
    points = zip(line_ring[::2], line_ring[1::2])
    return list([int(p), int(q)] for p,q in points)

def PointsToChain(points):
    chainify = lambda up, down: itertools.chain(up, reversed(down))
    return chainify(*itertools.izip(*points))
