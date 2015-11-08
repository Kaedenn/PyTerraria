#!/usr/bin/env python

import os
import sys
import warnings

import Header
from Header import CompatibleVersion, Version147, Version140, Version104, \
                   Version101, Version99, Version95
from WorldFlags import WorldFlags
import BinaryString
import IDs
import Tile
import Chest
import Entity

VERBOSE_MODE = False

def verbose(string, *args):
    if VERBOSE_MODE:
        if args:
            sys.stderr.write(string % args)
        else:
            sys.stderr.write(string)
        sys.stderr.write("\n")

def warn(string, *args):
    warnings.warn(string % args if args else string)

def test_bit(value, bit):
    return (value & bit) == bit

WORLDPATH_LINUX = os.path.expanduser("~/.local/share/Terraria/Worlds")

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

class World(object):
    def _PosToIdx(self, x, y):
        return y * self._width + x

    def _IdxToPos(self, idx):
        return (idx % self._width, int(idx / self._width))

    def _ensure_offset(self, offset, or_fatal=False):
        if or_fatal and self._stream.get_pos() != offset:
            raise RuntimeError("Stream position %d not at expected offset %d" %
                               (self._stream.get_pos(), offset))
        self._stream.seek_set(offset)

    def __init__(self, fname=None, fobj=None,
                 load_tiles=True,
                 load_chests=True,
                 load_signs=True,
                 load_npcs=True,
                 load_tents=True,
                 verbose=False, debug=False):
        global VERBOSE_MODE
        self._extents = None
        self._header = None
        self._flags = None
        self._tiles = None
        self._chests = None
        self._signs = None
        self._npcs = None
        self._width, self._height = 0, 0
        self._extents = [0, 0]

        VERBOSE_MODE = VERBOSE_MODE or verbose or debug
        self._debug_enabled = debug
        self._should_load_tiles = load_tiles
        self._should_load_chests = load_chests
        self._should_load_signs = load_signs
        self._should_load_npcs = load_npcs
        self._should_load_tents = load_tents
        self._start_debug_frame()
        if fname is not None and fobj is not None:
            raise ValueError("fname and fobj are mutually exclusive")
        if fname is None and fobj is not None:
            self.Load(fobj)
        if fname is not None and fobj is None:
            self.Load(open(fname, 'r'))

    def _debug(self, message, *args):
        if self._debug_enabled:
            if len(args) > 0:
                sys.stderr.write(message % args)
            else:
                sys.stderr.write(message)
            sys.stderr.write("\n")

    def Open(self, fobj):
        self._stream = BinaryString.BinaryString(fobj.read(), debug=self._debug_enabled)

    def _start_debug_frame(self):
        self._debugging = []

    def _add_debug(self, message, *args):
        if self._debug_enabled:
            self._debugging.append(message % args)

    def _pos(self):
        return self._stream.get_pos()

    @staticmethod
    def ListWorlds():
        worlds = []
        if os.path.exists(WORLDPATH_LINUX):
            for f in os.listdir(WORLDPATH_LINUX):
                fp = os.path.join(WORLDPATH_LINUX, f)
                if f.endswith('.wld'):
                    w = World()
                    w.Open(open(fp, 'r'))
                    w.LoadFileHeader()
                    w.LoadWorldFlags()
                    worlds.append((f, w.GetWorldFlag('Title'), fp))
        return worlds

    @staticmethod
    def FindWorld(worldname, failquiet=False):
        fp = os.path.join(WORLDPATH_LINUX, worldname + ".wld")
        if os.path.exists(fp):
            return fp
        for fn, title, fp in World.ListWorlds():
            if worldname == title:
                return fp
        if not failquiet:
            raise RuntimeError("World %s not found" % (worldname,))

    def Load(self, fobj=None):
        if fobj is not None:
            self._stream = BinaryString.BinaryString(fobj.read(), debug=self._debug_enabled)
        # Populate self._header
        self.LoadFileHeader()

        offsets = self._header.SectionPointers
        verbose("Header size: %s" % (offsets[1] - offsets[0],))
        verbose("Tile data size: %s" % (offsets[2] - offsets[1],))
        verbose("Chest data size: %s" % (offsets[3] - offsets[2],))
        verbose("Sign data size: %s" % (offsets[4] - offsets[3],))

        assert self._pos() == self._header.GetFlagsPointer()
        # Populate self._flags
        self.LoadWorldFlags()
        assert self._pos() == self._header.GetTilesPointer()
        self._width = self._flags.TilesWide
        self._height = self._flags.TilesHigh
        self._extents = [self._flags.TilesWide, self._flags.TilesHigh]
        if self._should_load_tiles:
            # Populate self._tiles
            self.LoadTileData(self._flags.TilesWide, self._flags.TilesHigh)
            assert self._pos() == self._header.GetChestsPointer()
        else:
            self._stream.seek_set(self._header.GetChestsPointer())
        if self._should_load_chests:
            self.LoadChests()
            assert self._pos() == self._header.GetSignsPointer()
        else:
            self._stream.seek_set(self._header.GetSignsPointer())
        if self._should_load_signs:
            self.LoadSigns()
            assert self._pos() == self._header.GetNPCsPointer()
        else:
            self._stream.seek_set(self._header.GetNPCsPointer())
        self.LoadNPCs()
        if self._header.Version >= Version140:
            assert self._pos() == self._header.GetTileEntitiesPointer()
            self.LoadTileEntities()
        assert self._pos() == self._header.GetFooterPointer()
        self.LoadFooter()

        if self._debug_enabled:
            stats = self._stream.getReadStats().items()
            stats.sort()
            print("Read statistics (size, number of times read):")
            for nbytes, ntimes in stats:
                print("%d\t%d" % (nbytes, ntimes))

    def LoadFileHeader(self, stream=None):
        if stream is None:
            stream = self._stream
        header = Header.WorldFileHeader()
        header.Version = stream.readUInt32()
        header.MetaMagic = stream.readUInt64()
        header.MetaRevision = stream.readUInt32()
        header.WorldBits = stream.readUInt64()
        numSectionPointers = stream.readUInt16()
        pos = stream.get_pos()
        stream.seek_end()
        header.FileSize = stream.get_pos()
        stream.seek_set(pos)
        verbose("number of sections: %s" % (numSectionPointers,))
        for i in range(numSectionPointers):
            header.SectionPointers[i] = stream.readUInt32()
        header.ImportantTiles = stream.readBitArray()
        self._header = header

    def LoadWorldFlags(self, stream=None):
        if stream is None:
            stream = self._stream
        if self._header is None or not self._header.Version:
            raise RuntimeError("Must load file header before world flags")
        self._ensure_offset(self._header.GetFlagsPointer())
        flags = WorldFlags(self._header.Version)
        flags.Title = stream.readString()
        for flag in WorldFlags.Flags:
            name, typename, ver = flag
            if ver > self._header.Version:
                verbose("Skipping %s due to version mismatch" % (name,))
                continue # ignore those flags
            if typename is None:
                # special parsing
                if name == "Anglers":
                    anglers = self._LoadAnglers(flags.NumAnglers)
                    flags.setFlag(name, anglers)
                elif name == "KilledMobs":
                    killcount = self._LoadKilledMobs(flags.KilledMobCount)
                    flags.setFlag(name, killcount)
                elif name == "UnknownFlags":
                    flags.setFlag(name, self._LoadUnknownHeaders())
                else:
                    assert typename is not None, "invalid flag %s" % (name,)
            else:
                value = BinaryString.ScalarReaderLookup[typename](stream)
                verbose("flag %s == 0x%x (%d)" % (name, value, value))
                if name.startswith('OreTier'):
                    try:
                        verbose("flag %s = 0x%x (%s)" % (name, value,
                                                         IDs.TileID[value]))
                    except KeyError as e:
                        # If the value is not a valid tile, then we're not in
                        # hard mode yet
                        assert not flags.getFlag('HardMode')
                flags.setFlag(name, value)
        self._flags = flags

    def _LoadAnglers(self, num_anglers):
        anglers = []
        for i in range(num_anglers):
            anglers.append(self._stream.readString())
        return anglers

    def _LoadKilledMobs(self, num_mobs):
        mobs = []
        for i in range(num_mobs):
            mobs.append(self._stream.readUInt32())
        return mobs

    def _LoadUnknownHeaders(self):
        nflags = self._header.SectionPointers[1] - self._pos()
        if nflags == 0:
            verbose("No unknown header flags present")
        else:
            verbose("%d unknown header flag(s) present" % (nflags,))
        flags = []
        for i in range(nflags):
            flags.append(self._stream.readUInt8())
        return flags

    def LoadTileData(self, width, height):
        self._ensure_offset(self._header.GetTilesPointer())
        verbose("Loading %d tiles (%d by %d)" % (width*height, width, height))
        startPos = self._header.SectionPointers[1]
        endPos = self._header.SectionPointers[2]
        section_size = endPos - startPos
        verbose("Section is %s bytes long" % (section_size,))
        tiles = [None]*(width*height)
        x, y = 0, 0
        nloaded = 0
        nprocessed = 0
        while x < width and self._pos() < endPos:
            y = 0
            while y < height and self._pos() < endPos:
                tile, rle = Tile.FromStream(self._stream, self._header.ImportantTiles)
                nloaded += 1
                nprocessed += 1
                tiles[self._PosToIdx(x, y)] = tile
                while rle > 0:
                    y += 1
                    tiles[self._PosToIdx(x, y)] = tile
                    nprocessed += 1
                    rle -= 1
                y += 1
            x += 1
        if self._pos() > endPos:
            overread = endPos - self._pos()
            warn("Read %d bytes past the end of the section!" % (overread,))
        elif self._pos() == endPos and (x < width or y < height):
            xerr = width - x
            yerr = height - y
            warn("Incomplete section! Terminated on tile (%d, %d)" % (x, y))
            warn("Rows left to parse: %d, columns left to parse: %d" %
                    (xerr, yerr))
        verbose("Actually loaded %d tiles" % (nloaded,))
        verbose("Actually processed %d tiles" % (nprocessed,))
        self._tiles = tiles

    def LoadChests(self):
        self._ensure_offset(self._header.GetChestsPointer())
        chests = []
        totalChests = self._stream.readUInt16()
        maxItems = self._stream.readUInt16()
        itemsPerChest = maxItems
        overflowItems = 0
        if maxItems >= Chest.MAX_ITEMS:
            itemsPerChest = Chest.MAX_ITEMS
            overflowItems = maxItems - Chest.MAX_ITEMS
        for i in range(totalChests):
            x = self._stream.readInt32()
            y = self._stream.readInt32()
            name = self._stream.readString()
            c = Chest.Chest(name, x, y)
            for slot in range(itemsPerChest):
                stack = self._stream.readInt16()
                if stack > 0:
                    item = self._stream.readInt32()
                    prefix = self._stream.readUInt8()
                    c.Set(slot, item, prefix, stack)
            for slot in range(overflowItems):
                stack = self._stream.readInt16()
                if stack > 0:
                    item = self._stream.readInt32()
                    prefix = self._stream.readUInt8()
                    c.overflow_items.append(((item, prefix), stack))
            verbose("Loaded chest %s", c)
            chests.append(c)
        verbose("Loaded %d total chests", totalChests)
        self._chests = chests

    def LoadSigns(self):
        self._ensure_offset(self._header.GetSignsPointer())
        signs = []
        totalSigns = self._stream.readInt16()
        for i in range(totalSigns):
            text = self._stream.readString()
            self._debug("Sign text: %s" % (text,))
            x = self._stream.readInt32()
            y = self._stream.readInt32()
            verbose("Loaded sign (%d, %d): %s", x, y, repr(text))
            self._debug("Offset: %d", self._pos())
            signs.append((x, y, text))
        verbose("Loaded %d total signs", totalSigns)
        self._signs = signs

    def LoadNPCs(self):
        self._ensure_offset(self._header.GetNPCsPointer())
        npcs = []
        mobs = []
        while self._stream.readBoolean():
            name = self._stream.readString()
            dispname = self._stream.readString()
            pos_x = self._stream.readSingle()
            pos_y = self._stream.readSingle()
            pos = (pos_x, pos_y)
            homeless = self._stream.readBoolean()
            home_x = self._stream.readInt32()
            home_y = self._stream.readInt32()
            home = (home_x, home_y)
            npc = Entity.NPCEntity(name=name, display_name=dispname, pos=pos,
                    homeless=homeless, home=home)
            verbose("Loaded NPC: %s", npc)
            npcs.append(npc)
        self._npcs = npcs
        if self._header.Version >= Version140:
            while self._stream.readBoolean():
                name = self._stream.readString()
                pos_x = self._stream.readSingle()
                pos_y = self._stream.readSingle()
                pos = (pos_x, pos_y)
                mob = Entity.MobEntity(name=name, pos=pos)
                verbose("Loaded mob: %s", mob)
                mobs.append(mob)
        self._mobs = mobs
        verbose("Loaded %d NPCs and %d mobs", len(self._npcs), len(self._mobs))

    def LoadTileEntities(self):
        self._ensure_offset(self._header.GetTileEntitiesPointer())
        tents = []
        count = self._stream.readInt32()
        for i in range(count):
            tent = None
            type_ = self._stream.readByte()
            id_ = self._stream.readInt32()
            pos_x = self._stream.readInt16()
            pos_y = self._stream.readInt16()
            pos = (pos_x, pos_y)
            if type_ == Entity.ENTITY_DUMMY:
                npc = self._stream.readInt16()
                tent = Entity.DummyTileEntity(type=type_, id=id_, pos=pos, npc=npc)
            elif type_ == Entity.ENTITY_ITEM_FRAME:
                item = self._stream.readInt16()
                prefix = self._stream.readByte()
                stack = self._stream.readInt16()
                tent = Entity.ItemFrameTileEntity(type=type_, id=id_, pos=pos,
                        item=item, prefix=prefix, stack=stack)
            verbose("Loaded tile entity: %s", tent)
            tents.append(tent)
        self._tents = tents

    def LoadFooter(self):
        self._ensure_offset(self._header.GetFooterPointer())
        footer = {'Loaded': False, 'Title': None, 'WorldID': None}
        footer['Loaded'] = self._stream.readBoolean()
        footer['Title'] = self._stream.readString()
        footer['WorldID'] = self._stream.readInt32()
        self._footer = footer

    def GetHeader(self):
        return self._header

    def EachTile(self):
        "Returns an iterable of (row, col, Tile) for each tile"
        for y in xrange(self.GetWorldFlag('TilesHigh')):
            for x in xrange(self.GetWorldFlag('TilesWide')):
                yield y, x, self.GetTile(x, y)

    def GetTile(self, i, j):
        return self._tiles[self._PosToIdx(i, j)]

    def GetWorldFlags(self):
        flags = []
        for flag, _, _ in WorldFlags.Flags:
            flags.append((flag, self._flags.getFlag(flag)))
        return tuple(flags)

    def GetWorldFlag(self, flag):
        return self._flags.getFlag(flag)

    def GetNPCs(self):
        return self._npcs

    def GetTileEntities(self):
        return self._tents

    def CountTiles(self):
        counts = {}
        for tile in self._tiles:
            if tile is not None and tile.IsActive:
                if tile.Type not in counts:
                    counts[tile.Type] = 1
                else:
                    counts[tile.Type] += 1
        return counts

