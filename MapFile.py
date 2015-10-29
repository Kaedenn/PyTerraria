#!/usr/bin/env python

import os
import sys
import FileMetadata
from BinaryStream import BinaryStream

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
        self._is_verbose = verbose
        if fname is not None and fobj is not None:
            raise ValueError("fname and fobj are mutually exclusive")
        if fname is None and fobj is not None:
            self.Load(fobj)
        if fname is not None and fobj is None:
            self.Load(open(fname, 'r'))

    def verbose(self, *args):
        if self._is_verbose:
            for arg in args:
                sys.stderr.write("%s\n" % (arg,))

    def Load(self, fobj):
        self._stream = BinaryStream(fobj, verbose=self._is_verbose)
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
        self.verbose("Offset: %s" % (self._stream.get_pos(),))
        self.LoadTiles()
        self.LoadWorld(4200, 1200)

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
        self.verbose("numTileOpts = %d" % (self._numTileOpts,))
        assert_eq(self._numTileOpts, 419)
        self._numWallOpts = self._stream.readInt16()
        self.verbose("numWallOpts = %d" % (self._numWallOpts,))
        assert_eq(self._numWallOpts, 225)
        self._unknown3 = self._stream.readInt16()
        assert_eq(self._unknown3, 3)
        self._unknown255_1 = self._stream.readInt16()
        assert_eq(self._unknown255_1, 256)
        self._unknown255_2 = self._stream.readInt16()
        assert_eq(self._unknown255_2, 256)
        self._unknown255_3 = self._stream.readInt16()
        assert_eq(self._unknown255_3, 256)
        self._tileOptMap = self._stream.readBitArrayOfSize(self._numTileOpts)
        self.verbose("read tile opt map")
        self._wallOptMap = self._stream.readBitArrayOfSize(self._numWallOpts)
        self.verbose("read wall opt map")

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

    def LoadTiles(self):
        self._tileTypes = [0]*(self._totalTileOpts + self._totalWallOpts +
                               self._unknown3 + self._unknown255_1 +
                               self._unknown255_2 + self._unknown255_3 + 2)
        self._tileTypes[0] = 0
        self.verbose("Total tile types: %s" % (len(self._tileTypes),))

    def LoadWorld(self, width, height):
        for y in range(height):
            for x in range(width):
                header1 = self._stream.readByte()
                header2 = 0 if (header1 & 1) == 0 else self._stream.readByte()
                mask14 = (header1 & 14) >> 3
                flag14 = (mask14 in (1, 2, 7))
                tileIdx = 0
                if (header1 & 16) != 16:
                    tileIdx = self._stream.readByte()
                else:
                    tileIdx = self._stream.readUInt16()
                tileLight = 0
                if (header1 & 32) != 32:
                    light = 255
                else:
                    light = self._stream.readByte()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        m = Map(fname=sys.argv[1], verbose=True)

