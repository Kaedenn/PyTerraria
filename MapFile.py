#!/usr/bin/env python

import os
import struct
import sys
import zlib
import FileMetadata
from BinaryString import BinaryString

"""
Sections:
    Tile Options    12 options per tile
    Wall Options    2 options per wall
    Liquid Options  3 options total
    Sky Gradients   256 options
    Dirt Gradiets   256 options
    Rock Gradients  256 options

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

def test_bit(value, bit):
    return (value & bit) == bit

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
    def __init__(self, fname=None, fobj=None, verbose=False):
        self._header = None
        self._tile_types = 0
        self._wall_types = 0
        self._water_types = 0
        self._lava_types = 0
        self._honey_types = 0
        self._heaven_and_hell_types = 0
        self._background_types = 0;
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
        self._is_verbose = verbose
        self._log = ''
        if fname is not None and fobj is not None:
            raise ValueError("fname and fobj are mutually exclusive")
        if fname is None and fobj is not None:
            self.Load(fobj)
        if fname is not None and fobj is None:
            self.Load(open(fname, 'r'))

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
            raise

    def _Load(self, fobj):
        self._stream = BinaryString(fobj.read(), verbose=self._is_verbose)
        self._header = FileHeader(verbose=self._is_verbose)
        self._numTileOpts = -1
        self._tileOptMap = None
        self._tileOpts = None
        self._totalTileOpts = 0
        self._numWallOpts = -1
        self._wallOptMap = None
        self._wallOpts = None
        self._totalWallOpts = 0
        self.LoadMetadata()
        self.LoadCounts()
        self.LoadOpts()
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

    def GenerateTileTypes(self):
        self._tileTypes = [0]*(self._totalTileOpts + self._totalWallOpts +
                               self._numLiquidOpts + self._numSkyOpts +
                               self._numDirtOpts + self._numRockOpts + 2)
        self._tileTypes[0] = 0
        #self._colorTypes = [(0, 0, 0, 0)]*len(self._numColors)
        self.verbose("Total tile types: %s" % (len(self._tileTypes),))

    def LoadMapTiles(self, width, height):
        self.verbose("Offset: %s" % (self._stream.get_pos(),))
        data = zlib.decompress(self._stream.getContent(remainder=True), -15)
        stream = BinaryString(data)
        offsets = [0, 0, 0, 0, 0, 0]
        x, y = 0, 0
        while y < height:
            while x < width:
                self.log(x, y, width, height, stream)
                assert x >= 0
                header1 = stream.readByte()
                header2 = 0 if (header1 & 1) == 0 else stream.readByte()
                section = (header1 & 14) >> 3
                hasOwnType = (section in (1, 2, 7))
                tileIdx = 0
                if hasOwnType:
                    if (header1 & 16) != 16:
                        tileIdx = stream.readByte()
                    else:
                        tileIdx = stream.readUInt16()
                light = 0
                if (header1 & 32) != 32:
                    light = 255
                else:
                    light = stream.readByte()
                rleType = ((header1 & 192) >> 6)
                rle = 0
                if rleType == 1:
                    rle = stream.readByte()
                elif rleType == 2:
                    rle = stream.readInt16()
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
                        if y < WORLD_SURFACE:
                            pass
                            #offset = num7 * y / Main.worldSurface;
                            #tileIdx += num23 + offset;
                        else:
                            pass
                            # y = num26
                    tile = [self._tileTypes[tileIdx], light, (header2 >> 1) & 31]
                    # SetTile(x, y, tile)
                    if light == 256:
                        while rle > 0:
                            x += 1
                            # SetTile(x, y, tile)
                            rle -= 1
                    else:
                        while rle > 0:
                            x += 1
                            tile[1] = stream.readByte()
                            # SetTile(x, y, tile)
                            rle -= 1
                x += 1
            y += 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        m = Map(fname=sys.argv[1], verbose=True)

