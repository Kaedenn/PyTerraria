#!/usr/bin/env python

import IDs

class Item(object):
    def __init__(self, itemid, prefix=0, stack=1):
        self.item = itemid
        self.prefix = prefix
        self.stack = stack

    def __str__(self):
        fmt = "%s %s"
        if self.stack > 1:
            fmt += " (%d)" % (self.stack,)
        s = fmt % (IDs.Prefixes[self.prefix], IDs.ItemID[self.item])
        return s.strip()
    
    def __repr__(self):
        return "Item(%d, %d, %d)" % (self.item, self.prefix, self.stack)
