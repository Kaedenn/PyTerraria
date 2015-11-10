#!/usr/bin/env python

import ctypes

import IDs

# Is there another byte of metadata present?
BIT_MOREHDR = 0b00000001 # All Headers: 1
# Is a tile present at this entry?
BIT_ACTIVE =  0b00000010 # Header 1: 2
# Does this entry have a wall?
BIT_HASWALL = 0b00000100 # Header 1: 4
# Does this entry have liquid?
MASK_LIQUID = 0b00011000 # Header 1: 24 (8+16)
# How many bits to shift to go from Header 1 to LiquidType
SHFT_LIQUID = 3
# Does this entry have a 16bit tile type?
BIT_TYPE16B = 0b00100000 # Header 1: 32
# Does this entry's tile have a color?
BIT_TCOLOR =  0b00001000 # Header 3: 8
# Does this entry's wall have a color?
BIT_WCOLOR =  0b00010000 # Header 3: 16
# Does this entry have a red wire?
BIT_REDWI =   0b00000010 # Header 2: 2
# Does this entry have a green wire?
BIT_GREENWI = 0b00000100 # Header 2: 4
# Does this entry have a blue wire?
BIT_BLUEWI =  0b00001000 # Header 2: 8
# Does this brick have a style?
MASK_BSTYLE = 0b01110000 # Header 2: 112
# How many bits to shift to go from Header 2 to BrickStyle
SHFT_BSTYLE = 4
# Does this entry have an actuator?
BIT_ACTUATE = 0b00000010 # Header 3: 2
# Is this entry inactive due to an actuator?
BIT_INACTIV = 0b00000100 # Header 3: 4
# Does this entry have an RLE?
MASK_HASRLE = 0b11000000 # Header 1: 192 (128+64)
# Is this RLE of type 1? (8bit RLE)
BIT_HASRLE1 = 0b01000000 # Header 1: 64
# Is this RLE of type 2? (16bit RLE)
BIT_HASRLE2 = 0b10000000 # Header 1: 128
# How many bits to shift to go from Header 1 to RLE
SHFT_RLE    = 6

class BrickStyle(object):
    Full = 0
    HalfBrick = 1
    SlopeTopLeftDown = 2
    SlopeBottomLeftDown = 3
    SlopeTopLeftUp = 4
    SlopeBottomLeftUp = 5
    Unknown06 = 6
    Unknown07 = 7
    @staticmethod
    def From(value):
        "Converts a number to a brick style (or None on failure)"
        values = [BrickStyle.Full,
                  BrickStyle.HalfBrick,
                  BrickStyle.SlopeTopLeftDown,
                  BrickStyle.SlopeBottomLeftDown,
                  BrickStyle.SlopeTopLeftUp,
                  BrickStyle.SlopeBottomLeftUp,
                  BrickStyle.Unknown06,
                  BrickStyle.Unknown07]
        if BrickStyle.Full <= value <= BrickStyle.Unknown07:
            return values[value]

class LiquidType(object):
    None_ = 0
    Water = 1
    Lava = 2
    Honey = 3
    @staticmethod
    def From(value):
        "Converts a number to a liquid type (or None on failure)"
        values = [LiquidType.None_,
                  LiquidType.Water,
                  LiquidType.Lava,
                  LiquidType.Honey]
        if LiquidType.None_ <= value <= LiquidType.Honey:
            return values[value]

class Tile(object):
    SerializedAttributes = (
        ('IsActive', False),
        ('WireRed', False),
        ('WireGreen', False),
        ('WireBlue', False),
        ('TileColor', 0),
        ('Type', 0),
        ('Wall', 0),
        ('WallColor', 0),
        ('LiquidType', LiquidType.None_),
        ('LiquidAmount', 0),
        ('BrickStyle', BrickStyle.Full),
        ('Actuator', False),
        ('InActive', False),
        ('U', -1),
        ('V', -1)
    )
    SerializedLookup = dict(SerializedAttributes)

    def __init__(self, lazy=False):
        if not lazy:
            self.IsActive = False
            self.WireRed = False
            self.WireGreen = False
            self.WireBlue = False
            self.TileColor = 0 # byte
            self.Type = 0 # ushort
            self.Wall = 0 # byte
            self.WallColor = 0 # byte
            self.LiquidType = LiquidType.None_
            self.LiquidAmount = 0 # byte
            self.BrickStyle = BrickStyle.Full
            self.Actuator = False
            self.InActive = False   # inactive due to actuator
            self.U = -1 # int16
            self.V = -1 # int16

    def __getattr__(self, attrib):
        return Tile.SerializedLookup[attrib]

    def ToSimpleType(self):
        "Returns the tile's type, if active, otherwise -1"
        if self.IsActive:
            return self.Type
        return -1

    def ToSimpleID(self):
        "Returns the tile's type and wall as a pair"
        return self.ToSimpleType(), self.Wall

    def ToPackedInt64(self):
        """Packs the tile's data in a 64bit integer.
        Note that this omits the tile's LiquidAmount. That would require an
        extra eight bits.
        <MSB>
        16 bits: tile.Type
        16 bits: tile.U
        16 bits: tile.V
        8 bits: tile.Wall
        1 bit: tile.IsActive
        1 bit: tile.WireRed
        1 bit: tile.WireGreen
        1 bit: tile.WireBlue
        1 bit: tile.LiquidType
        1 bit: tile.BrickStyle
        1 bit: tile.Actuator
        1 bit: tile.InActive
        <LSB>
        """
        result = ctypes.ulonglong(self.Type & 0xffff)
        result = (result << 16) | (self.U & 0xffff)
        result = (result << 16) | (self.V & 0xffff)
        result = (result << 8) | (self.Wall & 0xff)
        flags = ((self.IsActive << 7) |
                 (self.WireRed << 6) |
                 (self.WireGreen << 5) |
                 (self.WireBlue << 4) |
                 (1 << 3 if self.LiquidType != LiquidType.None_ else 0) |
                 (1 << 2 if self.BrickStyle != BrickStyle.Full else 0) |
                 (self.Actuator << 1) |
                 (self.InActive << 0))
        return hex(result << 8 | flags)

    def ToPacked(self):
        """Returns a sequence of bytes completely describing the tile
        The result is a sequence of 16 bytes, or two int64_ts
        """
        pass

    def FromPacked(self, data):
        "Parses a sequence of bytes from Tile.ToPacked() to construct a tile"
        pass
    
    def IsChest(self):
        return self.Type in (TileTypes.Chest, TileTypes.Dresser)

    def IsSign(self):
        return self.Type in (TileTypes.Sign, TileTypes.GraveMarker)

    def GetWire(self):
        return self.WireRed, self.WireGreen, self.WireBlue

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __neq__(self, other):
        return repr(self) != repr(other)

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

def FromStream(stream, importantTiles):
    "Returns (tile, rle) pair given a stream and the list of important tiles"
    test = lambda val,mask: (val & mask) == mask
    t = Tile(lazy=True)     # profiled, does make a difference (36s -> 32s)
    rle = 0
    header1 = stream.readUInt8()
    header2 = stream.readUInt8() if test(header1, BIT_MOREHDR) else 0
    header3 = stream.readUInt8() if test(header2, BIT_MOREHDR) else 0
    if test(header1, BIT_ACTIVE):
        t.IsActive = True
        if test(header1, BIT_TYPE16B):
            t.Type = stream.readUInt16()
        else:
            t.Type = stream.readUInt8()
        if t.Type < len(importantTiles) and importantTiles[t.Type]:
            t.U = stream.readInt16()
            t.V = stream.readInt16()
            if t.Type == IDs.Tile.Timers:
                t.V = 0
        if test(header3, BIT_TCOLOR):
            t.TileColor = stream.readUInt8()
    if test(header1, BIT_HASWALL):
        t.Wall = stream.readUInt8()
        if test(header3, BIT_WCOLOR):
            t.WallColor = stream.readUInt8()
    t.LiquidType = LiquidType.From((header1 & MASK_LIQUID) >> SHFT_LIQUID)
    if t.LiquidType != 0:
        t.LiquidAmount = stream.readUInt8()
    if header2 != 0:
        t.WireRed = test(header2, BIT_REDWI)
        t.WireGreen = test(header2, BIT_GREENWI)
        t.WireBlue = test(header2, BIT_BLUEWI)
        t.BrickStyle = BrickStyle.From((header2 & MASK_BSTYLE) >> SHFT_BSTYLE)
    if header3 != 0:
        t.Actuator = test(header3, BIT_ACTUATE)
        t.InActive = test(header3, BIT_INACTIV)

    rleType = ((header1 & MASK_HASRLE) >> SHFT_RLE)
    rle = 0
    if rleType == 1:
        rle = stream.readUInt8()
    elif rleType != 0:
        rle = stream.readInt16()

    return t, rle


