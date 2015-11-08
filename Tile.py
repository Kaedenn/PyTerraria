#!/usr/bin/env python

import IDs

# Is there another byte of metadata present?
BIT_MOREHDR = 0b00000001 # All Headers: 1
# Is a tile present at this entry?
BIT_ACTIVE =  0b00000010 # Header 1: 2
# Does this entry have a wall?
BIT_HASWALL = 0b00000100 # Header 1: 4
# Does this entry have liquid?
MASK_LIQUID = 0b00011000 # Header 1: 24 (8+16)
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

class BrickStyles(object):
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
        values = [BrickStyles.Full,
                  BrickStyles.HalfBrick,
                  BrickStyles.SlopeTopLeftDown,
                  BrickStyles.SlopeBottomLeftDown,
                  BrickStyles.SlopeTopLeftUp,
                  BrickStyles.SlopeBottomLeftUp,
                  BrickStyles.Unknown06,
                  BrickStyles.Unknown07]
        if BrickStyles.Full <= value <= BrickStyles.Unknown07:
            return values[value]

class LiquidTypes(object):
    None_ = 0
    Water = 1
    Lava = 2
    Honey = 3
    @staticmethod
    def From(value):
        values = [LiquidTypes.None_,
                  LiquidTypes.Water,
                  LiquidTypes.Lava,
                  LiquidTypes.Honey]
        if LiquidTypes.None_ <= value <= LiquidTypes.Honey:
            return values[value]

class TileTypes(object):
    "NOTE: Please use the IDs module instead of this incomplete list!"
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
    SerializedAttributes = (
        ('IsActive', False),
        ('WireRed', False),
        ('WireGreen', False),
        ('WireBlue', False),
        ('TileColor', 0),
        ('Type', 0),
        ('Wall', 0),
        ('WallColor', 0),
        ('LiquidType', LiquidTypes.None_),
        ('LiquidAmount', 0),
        ('BrickStyle', BrickStyles.Full),
        ('Actuator', False),
        ('InActive', False),
        ('U', -1),
        ('V', -1)
    )
    SerializedLookup = dict(SerializedAttributes)

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
        self.InActive = False   # inactive due to actuator
        self.U = -1 # int16
        self.V = -1 # int16

    def ToSimpleType(self):
        if self.IsActive:
            return self.Type
        return -1

    def ToSimpleID(self):
        return self.ToSimpleType(), self.Wall

    def ToPackedInt64(self):
        result = (self.Type & 0xffff)
        result = (result << 16) | (self.U & 0xffff)
        result = (result << 16) | (self.V & 0xffff)
        result = (result << 8) | (self.Wall & 0xff)
        flags = ((self.IsActive << 7) |
                 (self.WireRed << 6) |
                 (self.WireGreen << 5) |
                 (self.WireBlue << 4) |
                 (1 << 3 if self.LiquidType != LiquidTypes.None_ else 0) |
                 (1 << 2 if self.BrickStyle != BrickStyles.Full else 0) |
                 (self.Actuator << 1) |
                 (self.InActive << 0))
        return hex(result << 8 | flags)
    
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
    "Returns (tile, rle) pair"
    test = lambda val,mask: (val & mask) == mask
    t = Tile()
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
    t.LiquidType = LiquidTypes.From((header1 & MASK_LIQUID) >> 3)
    if t.LiquidType != 0:
        t.LiquidAmount = stream.readUInt8()
    if header2 != 0:
        t.WireRed = test(header2, BIT_REDWI)
        t.WireGreen = test(header2, BIT_GREENWI)
        t.WireBlue = test(header2, BIT_BLUEWI)
        t.BrickStyle = BrickStyles.From((header2 & MASK_BSTYLE) >> 4)
    if header3 != 0:
        t.Actuator = test(header3, BIT_ACTUATE)
        t.InActive = test(header3, BIT_INACTIV)

    rleType = ((header1 & MASK_HASRLE) >> 6)
    rle = 0
    if rleType == 1:
        rle = stream.readUInt8()
    elif rleType != 0:
        rle = stream.readInt16()

    return t, rle


