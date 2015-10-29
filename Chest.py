#!/usr/bin/env python

import Item

MAX_ITEMS = 50

class Chest(object):
    def __init__(self, name = "", x = 0, y = 0):
        self.items = [None]*50
        self.overflow_items = []
        self.chest_id = 0
        self.name = name
        self.x = x
        self.y = y

    def SetItem(self, slot, item):
        self.items[slot] = item

    def Set(self, slot, item, prefix=None, stack=1):
        self.items[slot] = Item.Item(item, prefix, stack)

    def Get(self, slot):
        return self.items[slot]

    def ContentsString(self):
        return " ".join(str(i) for i in self.items)

    def __str__(self):
        fmt = "Chest '%s' at (%d, %d) with %d item%s"
        nitems = len([i for i in self.items if i is not None])
        return fmt % (self.name, self.x, self.y, nitems,
                      's' if nitems != 1 else '')

    def __repr__(self):
        fmt = "Chest(%s, %d, %d, %s)"
        if len(list(i for i in self.items if i is not None)) == 0:
            return fmt % (self.name, self.x, self.y, "'no items'")
        return fmt % (self.name, self.x, self.y, self.items)
