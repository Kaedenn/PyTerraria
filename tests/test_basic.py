#!/usr/bin/env python

# basic test: ensure test harness import works
import tests

# basic test: ensure import works
import World

print("Number of worlds present: %d" % (len(World.ListWorlds()),))
for w in World.ListWorlds():
    print("World found: %s" % (w,))
