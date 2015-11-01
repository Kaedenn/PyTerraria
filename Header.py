#!/usr/bin/env python

CompatibleVersion = 102
Version147 = 147
Version140 = 140
Version104 = 104
Version101 = 101
Version99 = 99
Version95 = 95
TileCount = 314
FrameWidth = 18

INVALID_POINTER = -1
SECTION_FLAGS = 0
SECTION_TILES = 1
SECTION_CHESTS = 2
SECTION_SIGNS = 3
SECTION_NPCS = 4
# SECTION_MOBS isn't enumerated; it's part of SECTION_NPCS
SECTION_TENTS = 5
SECTION_FOOTER_OLD = 5
SECTION_FOOTER_140 = 6
SectionCount = 10

RELOGIC_MAGIC = 27981915666277746
FILETYPE_WORLD = 1

class WorldFileHeader(object):
    ExpectedMetaMagic = RELOGIC_MAGIC | (FILETYPE_WORLD << 56)

    def __init__(self, version=0, magic=0, rev=0):
        self.Version = version
        self.MetaMagic = magic
        self.MetaRevision = rev
        self.WorldBits = 0
        self.SectionPointers = [-1] * SectionCount
        self.FileSize = 0
        self.ImportantTiles = []

    def AssertValid(self):
        assert self.MetaMagic == WorldFileHeader.ExpectedMetaMagic
    def GetFlagsPointer(self):
        return self.SectionPointers[SECTION_FLAGS]
    def GetTilesPointer(self):
        return self.SectionPointers[SECTION_TILES]
    def GetChestsPointer(self):
        return self.SectionPointers[SECTION_CHESTS]
    def GetSignsPointer(self):
        return self.SectionPointers[SECTION_SIGNS]
    def GetNPCsPointer(self):
        return self.SectionPointers[SECTION_NPCS]
    def GetTileEntitiesPointer(self):
        if self.Version >= Version140:
            return self.SectionPointers[SECTION_TENTS]
        else:
            return INVALID_POINTER
    def GetFooterPointer(self):
        if self.Version >= Version140:
            return self.SectionPointers[SECTION_FOOTER_140]
        else:
            return self.SectionPointers[SECTION_FOOTER_OLD]

