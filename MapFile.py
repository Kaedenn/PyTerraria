#!/usr/bin/env python

import csv
import os
import struct
import sys
import zlib
import FileMetadata
from BinaryString import BinaryString
import IDs
import World
import Tile

"""
Sections:
    Tile Options    12 options per tile     (MapTile_Colors)
    Wall Options    2 options per wall      (MapTile_WallColors)
    Liquid Options  3 options total         (MapTile_LiquidColors)
    Sky Gradients   256 options
    Dirt Gradiets   256 options
    Rock Gradients  256 options

Liquid Colors:
    Water:  9,61,191
    Lava:   253,32,3
    Honey:  254,194,20

Gradients:
    0 -> 255 fade between two colors:
        C1*(1-i/255) + C2*(i/255)

Sky Colors:
Color1: 50,40,256
Color2: 145,185,256

Dirt Colors:
Color1: 88,61,46
Color2: 37,78,123

Rock Colors:
Color1: 74,67,60
Color2: 53,70,97

Color Lookup:
Lookup[0] = Transparent
TilePosition = 1

Things left to do:

!) Figure out what the map stores and what I need to calculate
!) Figure out what can be persisted and what must be calculated

1) Implement the tile->color lookup table (MapHelper::Initialize)
    * Store as a serialized asset in an external file?
2) Implement the tile->map tile conversion (MapHelper::CreateMapTile)
    * Implement polymorphically?
    * Implement as a serialized mapping (id, wall, u, v, light, ...?) -> (tile, opt)
3) Implement the options array in full (MapHelper::Initialize, Map.GenerateTileTypes)
    * Store as a serialized asset in an external file?
"""

FILE_MAGIC = FileMetadata.FILE_MAGIC
FILE_MAGIC_MAP = FileMetadata.FILE_MAGIC_MAP

assert_handlers = []
def assert_eq(lhs, rhs):
    if lhs != rhs:
        print("Assertion %s == %s failed" % (lhs, rhs))
    for h in assert_handlers:
        h()
    assert(lhs == rhs)

def _clamp(uv, low, high):
    if low <= uv <= high:
        res = uv
    elif uv < low:
        res = low
    elif uv > high:
        res = high
    return int(res)

class FileHeader(object):
    def __init__(self, version=0, magic=0, rev=0, verbose=False):
        self.Version = version
        self.MetaMagic = magic
        self.MetaRevision = rev
        self.WorldBits = 0
        self._is_verbose = verbose

    def verbose(self, *args):
        if self._is_verbose:
            for arg in args:
                sys.stderr.write("FileHeader: %s\n" % (arg,))

    def AssertValid(self):
        assert_eq((self.MetaMagic & FILE_MAGIC), FILE_MAGIC)
        fileType = (self.MetaMagic & ~FILE_MAGIC) >> 56
        self.verbose("File has type %s (%d)" % (FileMetadata.FILETYPES[fileType],
                                                fileType))
        assert_eq(self.MetaMagic, FILE_MAGIC_MAP)
        assert self.Version >= FileMetadata.CompatibleVersion
        self.verbose("File has been modified %d times" % (self.MetaRevision,))

class Map(object):
    LOOKUP_NONE = 0
    LOOKUP_TILE = 1
    LOOKUP_LIQUID = 2
    LOOKUP_WALL = 3
    LOOKUP_SKY = 4
    LOOKUP_DIRT = 5
    LOOKUP_ROCK = 6
    def __init__(self, fname=None, fobj=None, verbose=False):
        self._header = None
        self.HeaderEmpty = 0
        self.HeaderTile = 1
        self.HeaderWall = 2
        self.HeaderWater = 3
        self.HeaderLava = 4
        self.HeaderHoney = 5
        self.HeaderHeavenAndHell = 6
        self.HeaderBackground = 7
        self.MaxTileOpts = 12
        self.MaxWallOpts = 2
        self.MaxLiquidTypes = 3
        self.MaxSkyGradients = 256
        self.MaxDirtGradients = 256
        self.MaxRockGradients = 256
        self.tileOptionCounts = [0]*419
        self.tileLookup = [[None]*self.MaxTileOpts for _ in xrange(419)]
        self.liquidLookup = [None]*(self.MaxLiquidTypes+1)
        self.wallLookup = [[None]*self.MaxWallOpts for _ in xrange(225)]
        self.skyLookup = [None]*self.MaxSkyGradients
        self.dirtLookup = [None]*self.MaxDirtGradients
        self.rockLookup = [None]*self.MaxRockGradients
        self.colorLookup = []
        self.skyGradient = ((50, 40, 255), (145, 185, 255))
        self.dirtGradient = ((88, 61, 46), (37, 78, 123))
        self.rockGradient = ((74, 67, 60), (53, 70, 97))
        self.missingTiles = []
        self.missingWalls = []
        self._groundLevel = None
        self._rockLevel = None
        self._is_verbose = verbose
        self._raw_tiles = {}
        self._log = ''

        tileColors = list(csv.reader(open("MapTile_Colors.csv")))
        for t,o,r,g,b in tileColors[1:]:
            t, o = int(t), int(o)
            r, g, b = int(r), int(g), int(b)
            self.tileLookup[t][o] = (r, g, b)

        liquidColors = list(csv.reader(open("MapTile_LiquidColors.csv")))
        for t, r, g, b in liquidColors[1:]:
            t = int(t)
            r, g, b = int(r), int(g), int(b)
            self.liquidLookup[t+1] = (r, g, b)

        wallColors = list(csv.reader(open("MapTile_WallColors.csv")))
        for t,o,r,g,b in wallColors[1:]:
            t, o = int(t), int(o)
            r, g, b = int(r), int(g), int(b)
            self.wallLookup[t][o] = (r, g, b)

        for i in range(1, IDs.Tile.Count):
            if set(self.tileLookup[i]) == set([None]):
                self.missingTiles.append(i)

        for i in range(1, IDs.Wall.Count):
            if set(self.wallLookup[i]) == set([None]):
                self.missingWalls.append(i)

        if fname is not None and fobj is not None:
            raise ValueError("fname and fobj are mutually exclusive")
        if fname is None and fobj is not None:
            self.Load(fobj)
        if fname is not None and fobj is None:
            self.Load(open(fname, 'r'))

    def GetLookup(self, lookup_id):
        lookups = {
            Map.LOOKUP_TILE: self.tileLookup,
            Map.LOOKUP_LIQUID: self.liquidLookup,
            Map.LOOKUP_WALL: self.wallLookup,
            Map.LOOKUP_SKY: self.skyLookup,
            Map.LOOKUP_DIRT: self.dirtLookup,
            Map.LOOKUP_ROCK: self.rockLookup}
        if lookup_id in lookups:
            return lookups[lookup_id]
        raise IndexError("Lookup ID %s invalid" % (lookup_id,))

    def TileToLookup(self, tile, i=None, j=None, light=255,
                     transparentTiles=False,
                     transparentWalls=False,
                     transparentLiquid=False,
                     transparentBg=False):
        """
        Returns which lookup table (see Map.LOOKUP_* constants), lookup
        index, and lookup option for the tile object given
        """
        lookup, option = 0, 0
        type = tile.Type
        wall = tile.Wall
        extra = 0
        if tile.IsActive and \
                type not in self.missingTiles and \
                not transparentTiles:
            # Case 1: active tiles
            if type == IDs.Tile.RainbowBrick:
                extra = tile.TileColor
            if type == IDs.Tile.DemonAltar:
                if tile.U >= 54:
                    option = 1
            elif type == IDs.Tile.Sunflower:
                if tile.U < 34:
                    option = 1
            elif type == IDs.Tile.Pots:
                # these can't be factored by more than 2 (trust me, I tried)
                if tile.V < 144:
                    option = 0
                elif tile.V < 252:
                    option = 1
                elif tile.V < 360 or 900 < tile.V < 1008:
                    option = 2
                elif tile.V < 468:
                    option = 3
                elif tile.V < 576:
                    option = 4
                elif tile.V < 648:
                    option = 5
                elif tile.V < 792:
                    option = 6
                elif tile.V < 898:
                    option = 8
                elif tile.V < 1006:
                    option = 7
                elif tile.V < 1114:
                    option = 0
                elif tile.V < 1222:
                    option = 3
                else:
                    option = 7
            elif type == IDs.Tile.ShadowOrbs:
                if tile.U >= 36:
                    option = 1
            elif type == IDs.Tile.LongMoss:
                option = _clamp(tile.U / 22, 0, 5)
            elif type == IDs.Tile.SmallPiles:
                if tile.V < 18:
                    u = tile.U / 18
                    if u < 6 or 28 <= u <= 32:
                        option = 0
                    elif u < 22 or 33 <= u <= 35:
                        option = 1
                    elif u < 28:
                        option = 2
                    elif u < 48:
                        option = 3
                    elif u < 54:
                        option = 4
                else:
                    u = tile.U / 36
                    if u < 6 or 19 <= u <= 24 or u == 33 or 38 <= u <= 40:
                        option = 0
                    elif u < 16:
                        option = 2
                    elif u < 19 or 31 <= u <= 32:
                        option = 1
                    elif u < 31:
                        option = 3
                    elif u < 38:
                        option = 4
            elif type == IDs.Tile.LargePiles:
                u = tile.U / 54
                if u < 7:
                    option = 2
                elif u < 22 or u in (33, 34, 35):
                    option = 0
                elif u < 25:
                    option = 1
                elif u == 25:
                    option = 5
                elif u < 32:
                    option = 3
            elif type == IDs.Tile.LargePiles2:
                u = tile.U / 54
                if u < 3 or u in (14, 15, 16):
                    option = 0
                elif u < 6:
                    option = 6
                elif u < 9:
                    option = 7
                elif u < 14:
                    option = 4  # the code literally has these two
                elif u < 18:
                    option = 4  # the code literally has these two
                elif u < 23:
                    option = 8
                elif u < 25:
                    option = 0
                elif u < 29:
                    option = 1
            elif type in (IDs.Tile.ImmatureHerbs, IDs.Tile.MatureHerbs,
                          IDs.Tile.BloomingHerbs):
                option = _clamp(tile.U / 18, 0, 6)
            elif type == IDs.Tile.AdamantiteForge:
                option = 1 if tile.U >= 52 else 0
            elif type == IDs.Tile.MythrilAnvil:
                option = 1 if tile.U >= 28 else 0
            elif type == IDs.Tile.PressurePlates:
                option = 1 if tile.U != 0 else 0
            elif type == IDs.Tile.Painting3X3:
                u = tile.U / 54 + tile.V / 54 * 36
                if 0 <= u <= 11 or 47 <= u <= 53:
                    option = 0
                elif 12 <= u <= 15 or 18 <= u <= 35:
                    option = 1
                elif 16 <= u <= 17:
                    option = 2
                elif 41 <= u <= 45:
                    option = 3
                elif u == 46:
                    option = 4
            elif type == IDs.Tile.Painting6X4:
                if 22 <= tile.V / 72 <= 24:
                    option = 1
            elif type == IDs.Tile.Torches:
                if tile.U < 66:
                    pass    # the decompiled code literally has this
                option = 0
            elif type == IDs.Tile.Containers:
                u = tile.U / 36
                if u in (1, 2, 10, 13, 15): # Gold Chest
                    option = 1
                elif u in (3, 4):   # Shadow
                    option = 2
                elif u == 6:        # Unknown
                    option = 3
                elif u in (11, 17): # Water
                    option = 4
            elif type == IDs.Tile.Statues:
                if 1548 <= tile.U <= 1654:
                    option = 1
                elif 1656 <= tile.U <= 1798:
                    option = 2
            elif type == IDs.Tile.HolidayLights:
                if j is not None:
                    option = j % 3
            elif type == IDs.Tile.RainbowBrick:
                if j is not None:
                    option = j % 3
            elif type == IDs.Tile.Stalactite:
                if tile.U < 54:
                    option = 0
                elif tile.U < 106 or tile.U >= 216:
                    option = 1
                elif tile.U >= 162:
                    option = 3
                else:
                    option = 2
            elif type == IDs.Tile.ExposedGems:
                option = _clamp(tile.U / 18, 0, 6)
            elif type == IDs.Tile.DyePlants:
                option = tile.U / 34;
            else:
                option = 0
            assert option < len(self.tileLookup[tile.Type])
            return Map.LOOKUP_TILE, tile.Type, option
        elif tile.LiquidType != Tile.LiquidType.None_ and \
                tile.LiquidAmount > 32 and not transparentLiquid:
            # Case 2: inactive tiles with liquid
            return Map.LOOKUP_LIQUID, tile.LiquidType, 0
        elif wall != 0 and \
                wall not in self.missingWalls and \
                not transparentWalls:
            # Case 3: walls
            extra = tile.WallColor
            if wall == IDs.Wall.Planked and i is not None:
               option = i % 2
            elif wall in (IDs.Wall.PurpleStainedGlass,
                          IDs.Wall.YellowStainedGlass,
                          IDs.Wall.BlueStainedGlass,
                          IDs.Wall.GreenStainedGlass,
                          IDs.Wall.RedStainedGlass,
                          IDs.Wall.Glass,
                          IDs.Wall.Confetti):
               extra = 0
            else:
               option = 0
            return Map.LOOKUP_WALL, wall, option
        elif i is not None and j is not None and not transparentBg:
            # Case 4: inactive tiles with a gradient
            if j < self._groundLevel:
                return Map.LOOKUP_SKY, 0, 0
            elif j < self._rockLevel:
                return Map.LOOKUP_DIRT, 0, 0
            elif j < self._height - 204:
                return Map.LOOKUP_ROCK, 0, 0
            else:
                return Map.LOOKUP_ROCK, 1, 0
        return Map.LOOKUP_NONE, 0, 0

    def DoColorLookup(self, key, lookup, option=0):
        "Usage: m.DoColorLookup(*m.TileToLookup(t, i, j))"
        result = None
        if key == Map.LOOKUP_NONE:
            result = None
        elif key == Map.LOOKUP_TILE:
            result = self.tileLookup[lookup][option]
        elif key == Map.LOOKUP_LIQUID:
            result = self.liquidLookup[lookup]
        elif key == Map.LOOKUP_WALL:
            result = self.wallLookup[lookup][option]
        elif key == Map.LOOKUP_SKY:
            result = self.skyGradient[lookup]
        elif key == Map.LOOKUP_DIRT:
            result = self.dirtGradient[lookup]
        elif key == Map.LOOKUP_ROCK:
            result = self.rockGradient[lookup]
        else:
            print("Invalid lookup: %s %s %s" % (key, lookup, option))
            result = (255, 255, 255)
        return result

    def rawget(self):
        return self._raw_tiles

    def rawset(self, x, y, tile):
        self._raw_tiles[(x, y)] = tile

    def log(self, x, y, w, h, stream):
        self._log = "x:%d y:%d wxh: %dx%d pos: %d" % (x, y, w, h, stream.get_pos())

    def verbose(self, *args):
        if self._is_verbose:
            for arg in args:
                sys.stderr.write("%s\n" % (arg,))

    def Load(self, fobj):
        try:
            self._Load(fobj)
        except (IOError, EOFError, IndexError, AssertionError) as e:
            print(self._log)
            print(self._raw_tiles)
            raise

    def _Load(self, fobj):
        self._stream = BinaryString(fobj.read(), verbose=self._is_verbose)
        self._header = FileHeader(verbose=self._is_verbose)
        self._groundLevel = None
        self._rockLevel = None
        self._numTileOpts = -1
        self._tileOptMap = None
        self._tileOpts = None
        self._totalTileOpts = 0
        self._numWallOpts = -1
        self._wallOptMap = None
        self._wallOpts = None
        self._totalWallOpts = 0
        self._width = None
        self._height = None
        self.LoadMetadata()
        self.LoadCounts()
        self.LoadOpts()
        self.LoadReferencedWorld()
        self.GenerateTileTypes()
        self.LoadMapTiles(self._maxTilesX, self._maxTilesY)

    def LoadMetadata(self):
        self._header.Version = self._stream.readUInt32()
        self._header.MetaMagic = self._stream.readUInt64()
        self._header.MetaRevision = self._stream.readUInt32()
        self._header.WorldBits = self._stream.readUInt64()
        self._header.AssertValid()

    def LoadCounts(self):
        self._worldName = self._stream.readString()
        self._worldID = self._stream.readInt32()
        self._maxTilesY = self._stream.readInt32()
        self._maxTilesX = self._stream.readInt32()
        self._numTileOpts = self._stream.readInt16()
        self._numWallOpts = self._stream.readInt16()
        self._numLiquidOpts = self._stream.readInt16()
        self._numSkyOpts = self._stream.readInt16()
        self._numDirtOpts = self._stream.readInt16()
        self._numRockOpts = self._stream.readInt16()
        self._tileOptMap = self._stream.readBitArray(self._numTileOpts)
        self._wallOptMap = self._stream.readBitArray(self._numWallOpts)

    def LoadOpts(self):
        self._tileOpts = [1]*self._numTileOpts
        self._wallOpts = [1]*self._numWallOpts
        for i in range(self._numTileOpts):
            if self._tileOptMap[i]:
                self._tileOpts[i] = self._stream.readByte()
                self._totalTileOpts += self._tileOpts[i]
        self.verbose("read all tile opts")
        for i in range(self._numWallOpts):
            if self._wallOptMap[i]:
                self._wallOpts[i] = self._stream.readByte()
                self._totalWallOpts += self._wallOpts[i]
        self.verbose("read all wall opts")

    def FromWorld(self, world):
        self._world = world
        self._groundLevel = world.GetFlag('GroundLevel')
        self._rockLevel = world.GetFlag('RockLevel')
        self._width = world.Width()
        self._height = world.Height()

    def LoadReferencedWorld(self):
        w = World.World(load_tiles=False, load_chests=False, load_signs=False,
                        load_npcs=False, load_tents=False)
        w.Load(open(World.World.FindWorld(worldid=self._worldID)))
        self._world = w
        self._groundLevel = w.GetFlag('GroundLevel')
        self._rockLevel = w.GetFlag('RockLevel')
        self._width = w.Width()
        self._height = w.Height()

    def GenerateTileTypes(self):
        self._tileTypes = [0]*(self._totalTileOpts + self._totalWallOpts +
                               self._numLiquidOpts + self._numSkyOpts +
                               self._numDirtOpts + self._numRockOpts + 2)
        self._tileTypes[0] = 0
        self._posTileOpts = 0
        self._posWallOpts = 0
        self._posLiquidOpts = 0
        self._posSkyOpts = 0
        self._posDirtOpts = 0
        self._posRockOpts = 0
        #self._colorTypes = [(0, 0, 0, 0)]*len(self._numColors)
        self.verbose("Total tile types: %s" % (len(self._tileTypes),))

    def LoadMapTiles(self, width, height):
        self.verbose("Offset: %s" % (self._stream.get_pos(),))
        data = zlib.decompress(self._stream.getContent(remainder=True), -15)
        stream = BinaryString(data)
        print(' '.join(hex(ord(c))[2:] for c in stream._content[stream._pos:stream._pos+32]))
        offsets = [0, 0, 0, 0, 0, 0]
        x, y = 0, 0
        while y < height:
            while x < width:
                self.log(x, y, width, height, stream)
                assert x >= 0
                header1 = stream.readByte()
                header2 = stream.readByte() if (header1 & 1) == 1 else 0
                section = (header1 & 14) >> 1
                hasOwnType = (section in (1, 2, 7))
                tileIdx = 0
                if hasOwnType:
                    if (header1 & 16) != 16:
                        tileIdx = stream.readByte()
                    else:
                        tileIdx = stream.readUInt16()
                light = 255 if (header1 & 32) != 32 else stream.readByte()
                rleType = ((header1 & 192) >> 6)
                rle = 0
                if rleType == 1:
                    rle = stream.readByte()
                elif rleType == 2:
                    rle = stream.readInt16()
                else:
                    rle = 0
                self.rawset(x, y, (header1, header2, tileIdx, light, rle, section))
                if section == 0:
                    x += rle
                else:
                    if section == 1:
                        pass
                        # tileIdx += posTileOpts
                    elif section == 2:
                        pass
                        # tileIdx += posWallOpts
                    elif section in (3, 4, 5):
                        pass
                        # tileIdx += num22 + section - 3
                    elif section == 6:
                        pass
                        #if y < self._groundLevel:
                        #    offset = num7 * y / self._groundLevel
                        #    tileIdx += num23 + offset;
                        #else:
                        #    y = num26
                    #tile = [self._tileTypes[tileIdx], light, (header2 >> 1) & 31]
                    tile = [tileIdx, light, (header2 >> 1) & 31]
                    self.rawset(x, y, (header1, header2, tileIdx, light, rle, section))
                    # SetTile(x, y, tile)
                    if light == 256:
                        while rle > 0:
                            x += 1
                            # SetTile(x, y, tile)
                            self.rawset(x, y, (header1, header2, tileIdx, light, rle, section))
                            rle -= 1
                    else:
                        while rle > 0:
                            x += 1
                            tile[1] = stream.readByte()
                            self.rawset(x, y, (header1, header2, tileIdx, light, rle, section))
                            # SetTile(x, y, tile)
                            rle -= 1
                x += 1
            y += 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        m = Map(fname=sys.argv[1], verbose=True)
        if '-p' in sys.argv:
            for k,v in m.rawget().iteritems():
                print(k, v)
