#!/usr/bin/env python

import itertools

def PointsToChain(points):
    chainify = lambda up, down: itertools.chain(up, reversed(down))
    return chainify(*itertools.izip(*points))
