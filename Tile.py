#!/usr/bin/env python

import IDs

class BrickStyles(object):
    Full = 0
    HalfBrick = 1
    SlopeTopLeftDown = 2
    SlopeBottomLeftDown = 3
    SlopeTopLeftUp = 4
    SlopeBottomLeftUp = 5
    Unknown06 = 6
    Unknown07 = 7
    @classmethod
    def From(value):
        values = [Full, HalfBrick, SlopeTopLeftDown, SlopeBottomLeftDown,
                  SlopeTopLeftUp, SlopeBottomLeftUp, Unknown06, Unknown07]
        if Full <= value <= Unknown07:
            return values[value]

class LiquidTypes(object):
    None_ = 0
    Water = 1
    Lava = 2
    Honey = 3

class TileTypes(object):
    DirtBlock = 0
    StoneBlock = 1
    Torch = 4
    Tree = 5
    Platform = 19
    Chest = 21
    Sunflower = 27
    Chandelier = 34
    Sign = 55
    MushroomTree = 72
    GraveMarker = 85
    Dresser = 88
    EbonsandBlock = 112
    PearlsandBlock = 116
    IceByRod = 127
    Timer = 144

class Tile(object):
    def __init__(self):
        self.IsActive = False
        self.WireRed = False
        self.WireGreen = False
        self.WireBlue = False
        self.TileColor = 0 # byte
        self.Type = 0 # ushort
        self.Wall = 0 # byte
        self.WallColor = 0 # byte
        self.LiquidType = LiquidTypes.None_
        self.LiquidAmount = 0 # byte
        self.BrickStyle = BrickStyles.Full
        self.Actuator = False
        self.InActive = False
        self.U = 0 # int16
        self.V = 0 # int16
        self._numProperties = 15

        # not serialized
        self.uvTileCache = 0xffff
        self.uvWallCache = 0xffff
        self.lazyMergeId = 0xff
        self.hasLazyChecked = False

    def ToSimpleType(self):
        if self.IsActive:
            return self.Type
        return -1

    def ToSimpleID(self):
        return self.ToSimpleType(), self.Wall
    
    def IsChest(self):
        return self.Type in (TileTypes.Chest, TileTypes.Dresser)

    def IsSign(self):
        return self.Type in (TileTypes.Sign, TileTypes.GraveMarker)

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        content = ", ".join((
            "%s = %s" % ("IsActive", self.IsActive),
            "%s = %s" % ("WireRed", self.WireRed),
            "%s = %s" % ("WireGreen", self.WireGreen),
            "%s = %s" % ("WireBlue", self.WireBlue),
            "%s = %s" % ("TileColor", self.TileColor),
            "%s = %s" % ("Type", self.Type),
            "%s = %s" % ("Name", IDs.TileID[self.Type]),
            "%s = %s" % ("Wall", self.Wall),
            "%s = %s" % ("WallColor", self.WallColor),
            "%s = %s" % ("LiquidType", self.LiquidType),
            "%s = %s" % ("LiquidAmount", self.LiquidAmount),
            "%s = %s" % ("BrickStyle", self.BrickStyle),
            "%s = %s" % ("Actuator", self.Actuator),
            "%s = %s" % ("InActive", self.InActive),
            "%s = %s" % ("U", self.U),
            "%s = %s" % ("V", self.V)
        ))
        return "Tile(%s)" % (content,)

