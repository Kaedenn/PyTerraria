#!/usr/bin/env python

"""
Module for handling Terraria world files

class World:
    See the World class docstring for usage.
"""

import collections
import copy
import cProfile
import os
import pstats
import StringIO
import sys
import time
from warnings import warn

import Header
from WorldFlags import WorldFlags
import BinaryString
import IDs
import Tile
import Chest
import Entity
from Region.Poly import PointsToChain

class _G(object):
    def __init__(self):
        self.VERBOSE_MODE = False
        self.DEBUG_MODE = False

G = _G()

BORDER_TILES = 40
SIZE_SMALL = (4200, 1200)
SIZE_MEDIUM = (6400, 1800)
SIZE_LARGE = (8400, 2400)
SIZE_UNKNOWN = (-1, -1)

def SizeToStr(size):
    if size == SIZE_SMALL:
        return "Small"
    if size == SIZE_MEDIUM:
        return "Medium"
    if size == SIZE_LARGE:
        return "Large"
    return "Unknown"

def verbose(string, *args):
    "Output string % args if G.VERBOSE_MODE is True"
    if G.VERBOSE_MODE:
        sys.stdout.flush()
        if args:
            sys.stderr.write(string % args)
        else:
            sys.stderr.write(string)
        sys.stderr.write("\n")

def debug(string, *args):
    "Output string % args if G.DEBUG_MODE is True"
    if G.DEBUG_MODE:
        sys.stdout.flush()
        if args:
            sys.stderr.write(string % args)
        else:
            sys.stderr.write(string)
        sys.stderr.write("\n")

WORLDPATH_LINUX = os.path.expanduser("~/.local/share/Terraria/Worlds")
WORLDPATH_WINDOWS = None

class BiomeDefinition(object):
    def __init__(self, tile_contribute, min_size, win_size):
        """
        tile_contribute:
            dictionaries of tile ID to number denoting the value of that
            particular tile, like ForestGrass->1, LihzahrdBrick->3 (or w/e)
        """
        self._tiles = tile_contribute
        self._min = min_size
        self._window = win_size

    def Threshold(self):
        return self._min

    def WindowSize(self):
        return self._window

    def TileValue(self, tile_obj):
        return self._tiles.get(tile_obj.Tile, 0)

# Taken from Main.cs, Player.cs, and Lighting.cs from the decompiled Terraria
# source code. Terraria uses 45 for the window size (Lighting.offScreenTiles)
Zone_Corrupt = BiomeDefinition({
    IDs.Tile.CorruptGrass: 1,
    IDs.Tile.CorruptPlants: 1,
    IDs.Tile.Ebonstone: 1,
    IDs.Tile.CorruptThorns: 1,
    IDs.Tile.Ebonsand: 1,
    IDs.Tile.CorruptIce: 1,
    IDs.Tile.CorruptSandstone: 1,
    IDs.Tile.CorruptHardenedSand: 1,
    IDs.Tile.Sunflower: -5
}, 200, 45)
Zone_Holy = BiomeDefinition({
    IDs.Tile.HallowedGrass: 1,
    IDs.Tile.HallowedPlants: 1,
    IDs.Tile.HallowedPlants2: 1,
    IDs.Tile.Pearlstone: 1,
    IDs.Tile.Pearlsand: 1,
    IDs.Tile.HallowedIce: 1,
    IDs.Tile.HallowSandstone: 1,
    IDs.Tile.HallowHardenedSand: 1
}, 100, 45)
Zone_Meteor = BiomeDefinition({
    IDs.Tile.Meteorite: 1
}, 50, 45)
Zone_Jungle = BiomeDefinition({
    IDs.Tile.JungleGrass: 1,
    IDs.Tile.JunglePlants: 1,
    IDs.Tile.JungleVines: 1,
    IDs.Tile.JunglePlants2: 1,
    IDs.Tile.LihzahrdBrick: 1
}, 80, 45)
Zone_Snow = BiomeDefinition({
    IDs.Tile.SnowBlock: 1,
    IDs.Tile.SnowBrick: 1,
    IDs.Tile.IceBlock: 1,
    IDs.Tile.BreakableIce: 1,
    IDs.Tile.HallowedIce: 1,
    IDs.Tile.CorruptIce: 1,
    IDs.Tile.FleshIce: 1
}, 300, 45)
Zone_Crimson = BiomeDefinition({
    IDs.Tile.FleshGrass: 1,
    IDs.Tile.FleshIce: 1,
    IDs.Tile.Crimstone: 1,
    IDs.Tile.CrimsonSandstone: 1,
    IDs.Tile.CrimsonHardenedSand: 1,
    IDs.Tile.Crimsand: 1,
    IDs.Tile.CrimtaneThorns: 1,
    IDs.Tile.Sunflower: -5
}, 200, 45)
Zone_Desert = BiomeDefinition({
    IDs.Tile.Sand: 1,
    IDs.Tile.Ebonsand: 1,
    IDs.Tile.Pearlsand: 1,
    IDs.Tile.Crimsand: 1,
    IDs.Tile.HardenedSand: 1,
    IDs.Tile.CorruptHardenedSand: 1,
    IDs.Tile.HallowHardenedSand: 1,
    IDs.Tile.CrimsonHardenedSand: 1,
    IDs.Tile.Sandstone: 1,
    IDs.Tile.CorruptSandstone: 1,
    IDs.Tile.HallowSandstone: 1,
    IDs.Tile.CrimsonSandstone: 1
}, 1000, 45)
Zone_Glowshroom = BiomeDefinition({
    IDs.Tile.MushroomGrass: 1,
    IDs.Tile.MushroomPlants: 1,
    IDs.Tile.MushroomTrees: 1
}, 100, 45)
Zone_WaterCandle = BiomeDefinition({IDs.Tile.WaterCandle: 1}, 1, 45)
Zone_PeaceCandle = BiomeDefinition({IDs.Tile.PeaceCandle: 1}, 1, 45)

def PolyMatch_Tile(tileid):
    """
    Used for World.GetPolygon:
        poly = w.GetPolygon(PolyMatch_Tile(IDs.Tile.LihzahrdBrick))
    """
    return lambda t: t.Type == tileid

def PolyMatch_Wall(wallid):
    """
    Used for World.GetPolygon:
        poly = w.GetPolygon(PolyMatch_Wall(IDs.Wall.LihzahrdBrickUnsafe))
    """
    return lambda t: t.Wall == wallid

def PolyMatch(tileid, wallid):
    """
    Used for World.GetPolygon:
        poly = w.GetPolygon(PolyMatch(IDs.Tile.LihzahrdBrick,
                                      IDs.Wall.LihzahrdBrickUnsafe))
    Satisfied for tiles matching both the tile id and wall id given, so
    the above is equivalent to:
        tfn = PolyMatch_Tile(IDs.Tile.LihzahrdBrick)
        wfn = PolyMatch_Wall(IDs.Wall.LihzahrdBrickUnsafe)
        poly = w.GetPolygon(lambda tile: tfn(tile) and wfn(tile))
    """
    return lambda t: t.Type == tileid and t.Wall == wallid

class World(object):
    """
    An object wrapping a Terraria world

    World.__init__ parameters:
        fname       (str) path to a Terraria world file (ending in .wld)
        fobj        (file) opened file object of a Terraria world file
        read_only   (bool) if false, allow tile modification (see below)
        load_tiles  (bool) whether or not to load the world tiles
        load_chests (bool) whether or not to load the world chests
        load_signs  (bool) whether or not to load the world signs
        load_npcs   (bool) whether or not to load the world NPCs
        load_tents  (bool) whether or not to load the world tile entities
        progress    (bool) show progress during loading
        verbose     (bool) show diagnostic information
        debug       (bool) show even more diagnostic information

    "Read Only" worlds:
        If read_only=True (the default), then duplicated tiles in a sequence
        will all be references to the same tile instance, so modifying one
        tile will modify all of them. This will lead to unexpected side-effects
        and cause problems.
        Otherwise, if read_only=False, then all tiles will be individual
        instances, so modifying one does not modify any others.
    """
    def __init__(self, fname=None, fobj=None,
                 read_only=True,
                 load_tiles=True,
                 load_chests=True,
                 load_signs=True,
                 load_npcs=True,
                 load_tents=True,
                 progress=False,
                 verbose=False, debug=False,
                 progress_delay=0.2,
                 profile=False):
        """See the World class or World module docstring"""
        self._readonly = read_only
        self._header = None
        self._flags = None
        self._tiles = None
        self._chests = None
        self._signs = None
        self._npcs = None
        self._tents = None
        self._width = 0
        self._height = 0
        self._loaded = False
        self._last_progress_time = 0
        self._curr_progress_time = 0
        self._progress_delay = progress_delay
        self._profiler = cProfile.Profile() if profile else None
        self._prof_stats = []
        self._tile_counts = collections.defaultdict(int)
        self._wall_counts = collections.defaultdict(int)

        G.VERBOSE_MODE = G.VERBOSE_MODE or verbose or debug
        G.DEBUG_MODE = G.DEBUG_MODE or debug
        self._last_progress_len = 0
        self._show_progress = progress
        self._should_load_tiles = load_tiles
        self._should_load_chests = load_chests
        self._should_load_signs = load_signs
        self._should_load_npcs = load_npcs
        self._should_load_tents = load_tents
        self._max_progress_len = 0
        self._last_progress_len = 0
        if fname is not None and fobj is not None:
            raise ValueError("fname and fobj are mutually exclusive")
        if fname is None and fobj is not None:
            self.Load(fobj)
        if fname is not None and fobj is None:
            self.Load(open(fname, 'r'))

    def ProfStart(self):
        if self._profiler is not None:
            self._profiler.enable()

    def ProfEnd(self):
        if self._profiler is not None:
            self._profiler.disable()
            self._profiler.create_stats()
            self._profiler.print_stats(sort='cumulative')

    def GetProfileStats(self):
        return self._prof_stats

    def __repr__(self):
        if self._loaded:
            return "<Terraria World %r (%d, %d)>" % (self._flags.Title,
                    self._width, self._height)
        return super(World, self).__repr__()

    def _PosToIdx(self, x, y):
        return y * self._width + x

    def _IdxToPos(self, idx):
        return (idx % self._width, int(idx / self._width))

    def _ensure_offset(self, offset, or_fatal=False):
        if or_fatal and self._pos() != offset:
            raise RuntimeError("Stream position %d not at expected offset %d" %
                               (self._pos(), offset))
        self._stream.seek_set(offset)

    def _progress(self, message=None, *args, **kwargs):
        force = kwargs.get('force', None)
        if not self._show_progress:
            return
        self._curr_progress_time = time.time()
        delay = self._curr_progress_time - self._last_progress_time
        if delay < self._progress_delay and not force:
            return
        if message is not None:
            m = (message % args) if args else str(message)
            self._max_progress_len = max((len(m), self._max_progress_len))
            sys.stderr.write(m)
        sys.stderr.write(" "*self._max_progress_len + "\r")
        self._last_progress_time = self._curr_progress_time

    progress = _progress

    def _pos(self):
        return self._stream.get_pos()

    def Open(self, fobj=None, fname=None):
        """Specify the file object or file name to read from. This actually
        loads the contents of the file into memory."""
        if fobj is None and fname is not None:
            fobj = open(fname, 'r')
        elif fobj is None and fname is None:
            raise RuntimeError("Must provide either file object or file path")
        self._stream = BinaryString.BinaryString(fobj.read(),
                                                 debug=G.DEBUG_MODE)

    @staticmethod
    def ListWorlds():
        """Returns a list of worlds (filename, world, filepath). The world
        is a valid world instance with the header and world flags loaded."""
        worlds = []
        if os.path.exists(WORLDPATH_LINUX):
            for f in os.listdir(WORLDPATH_LINUX):
                fp = os.path.join(WORLDPATH_LINUX, f)
                if f.endswith('.wld'):
                    w = World()
                    w.Open(open(fp, 'r'))
                    w.LoadHeader()
                    w.LoadFlags()
                    worlds.append((f, w, fp))
        verbose("Discovered %d worlds", len(worlds))
        return worlds

    @staticmethod
    def FindWorld(worldname=None, worldid=None, failquiet=False, doopen=False):
        """Returns the file path to the world specified, either by file name
        (without .wld suffix), world name as seen in-game, or world ID. Raises
        an exception if no matching world is found, unless @param failquiet is
        True.

        If @param doopen is True, return an opened file object."""
        if worldname is None and worldid is None:
            raise RuntimeError("must provide either worldname or worldid")
        if worldname is not None:
            fp = os.path.join(WORLDPATH_LINUX, worldname + ".wld")
            if os.path.exists(fp):
                return open(fp, 'r') if doopen else fp
        for fn, w, fp in World.ListWorlds():
            if worldname is not None and worldname == w.GetFlag('Title'):
                return open(fp, 'r') if doopen else fp
            elif worldid is not None and worldid == w.GetFlag('WorldId'):
                return open(fp, 'r') if doopen else fp
        if not failquiet:
            raise RuntimeError("World %s not found" % (worldname,))
        verbose("No world matching (n=%r, id=%r) found", worldname, worldid)

    # {{{ Region <Loaders> begin

    def Load(self, fobj=None):
        """Loads the world given by @param fobj (if present) or the value of
        @param fname or @param fobj passed to __init__.

        Use the arguments to __init__ to suppress loading certain sections.
        """
        if fobj is not None:
            self._stream = BinaryString.BinaryString(fobj.read(),
                                                     debug=G.DEBUG_MODE)
        # Populate self._header
        self.LoadHeader()

        offsets = self._header.SectionPointers
        verbose("Header size: %s" % (offsets[1] - offsets[0],))
        verbose("Tile data size: %s" % (offsets[2] - offsets[1],))
        verbose("Chest data size: %s" % (offsets[3] - offsets[2],))
        verbose("Sign data size: %s" % (offsets[4] - offsets[3],))

        self._progress("Loading world flags")
        assert self._pos() == self._header.GetFlagsPointer()
        self.LoadFlags()
        assert self._pos() == self._header.GetTilesPointer()
        self._width = self._flags.TilesWide
        self._height = self._flags.TilesHigh
        if self._should_load_tiles:
            self._progress("Loading tiles...")
            self.LoadTiles(self._flags.TilesWide, self._flags.TilesHigh)
            assert self._pos() == self._header.GetChestsPointer()
        else:
            self._stream.seek_set(self._header.GetChestsPointer())
        if self._should_load_chests:
            self._progress("Loading chests...")
            self.LoadChests()
            assert self._pos() == self._header.GetSignsPointer()
        else:
            self._stream.seek_set(self._header.GetSignsPointer())
        if self._should_load_signs:
            self._progress("Loading signs...")
            self.LoadSigns()
            assert self._pos() == self._header.GetNPCsPointer()
        else:
            self._stream.seek_set(self._header.GetNPCsPointer())
        if self._should_load_npcs:
            self._progress("Loading NPCs...")
            self.LoadNPCs()
        else:
            self._stream.seek_set(self._header.GetTileEntitiesPointer())
        if self._header.Version >= Header.Version140:
            if self._should_load_tents:
                assert self._pos() == self._header.GetTileEntitiesPointer()
                self._progress("Loading tile entities...")
                self.LoadTileEntities()
            else:
                self._stream.seek_set(self._header.GetFooterPointer())
        assert self._pos() == self._header.GetFooterPointer()
        self._progress("Loading footer")
        self.LoadFooter()
        verbose("Loaded footer: %s", self._footer)
        if not self._footer['Loaded']:
            warn("Invalid footer detected!")
        if self._footer['Title'] != self.GetFlag('Title'):
            warn("Footer title %r does not match header title %r" % (
                 self._footer['Title'], self.GetFlag('Title')))
        if self._footer['WorldID'] != self.GetFlag('WorldId'):
            warn("Footer ID %s does not match header ID %s" % (
                 self._footer['WorldID'], self.GetFlag('WorldId')))
        self._progress(force=True)

        if G.DEBUG_MODE:
            stats = self._stream.getReadStats().items()
            stats.sort()
            print("Read statistics (size, number of times read):")
            for nbytes, ntimes in stats:
                print("%d\t%d" % (nbytes, ntimes))

    def LoadHeader(self, stream=None):
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
        self._loaded = True

    def LoadFlags(self, stream=None):
        if stream is None:
            stream = self._stream
        if self._header is None or not self._header.Version:
            raise RuntimeError("Must load file header before world flags")
        self._ensure_offset(self._header.GetFlagsPointer())
        flags = WorldFlags(self._header.Version)
        flags.Title = stream.readString()
        num_flags = len(WorldFlags.Flags)
        for i, flag in enumerate(WorldFlags.Flags):
            self._progress("Loading world flags... %d/%d", i, num_flags)
            name, typename, ver = flag
            if ver > self._header.Version:
                verbose("Skipping %s due to version mismatch" % (name,))
                continue # ignore those flags
            if typename is None:
                # special parsing
                if name == "Anglers":
                    anglers = self._LoadAnglers(flags.NumAnglers)
                    flags.set(name, anglers)
                elif name == "KilledMobs":
                    killcount = self._LoadKilledMobs(flags.KilledMobCount)
                    flags.set(name, killcount)
                elif name == "UnknownFlags":
                    flags.set(name, self._LoadUnknownHeaders())
                else:
                    assert typename is not None, "invalid flag %s" % (name,)
            else:
                value = BinaryString.ScalarReaderLookup[typename](stream)
                verbose("flag %s == 0x%x (%d)" % (name, value, value))
                if name.startswith('OreTier'):
                    if IDs.valid_tile(value):
                        verbose("flag %s = 0x%x (%d %s)" % (name, value, value,
                                IDs.TileID[value]))
                    elif flags.get('HardMode'):
                        warn("Bad ore tier: %s, %s" % (name, value))
                flags.set(name, value)
        self._width = flags.TilesWide
        self._height = flags.TilesHigh
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

    def LoadTiles(self, w, h):
        self.ProfStart()
        self._ensure_offset(self._header.GetTilesPointer())
        verbose("Loading %d tiles (%d by %d)" % (w*h, w, h))
        start = self._header.SectionPointers[1]
        end = self._header.SectionPointers[2]
        size = end - start
        verbose("Section is %s bytes long" % (size,))
        tiles = [None]*(w*h)
        x, y = 0, 0
        nloaded = 0
        # renaming shortcuts
        important = self._header.ImportantTiles
        while x < w and self._pos() < end:
            y = 0
            while y < h and self._pos() < end:
                bytes_loaded = self._pos() - start
                self._progress("Loading tiles... %d/%d %d%%",
                               bytes_loaded-start, size,
                               bytes_loaded*100/size)
                i = self._PosToIdx(x, y)
                tile, rle = Tile.FromStream(self._stream, important)
                if tile.IsActive:
                    self._tile_counts[tile.Type] += max(rle, 1)
                if tile.Wall != 0:
                    self._wall_counts[tile.Wall] += max(rle, 1)
                nloaded += 1
                tiles[i] = tile
                while rle > 0:
                    y += 1
                    i += w
                    if self._readonly:
                        tiles[i] = tile
                    else:
                        # extremely expensive, so do it only when required
                        tiles[i] = copy.copy(tile)
                    rle -= 1
                y += 1
            x += 1
        if self._pos() > end:
            overread = end - self._pos()
            warn("Read %d bytes past the end of the section!" % (overread,))
        elif self._pos() == end and (x < w or y < h):
            xerr = w - x
            yerr = h - y
            warn("Incomplete section! Terminated on tile (%d, %d)" % (x, y))
            warn("Rows left: %d, columns left: %d" % (xerr, yerr))
        verbose("Actually loaded %d tiles" % (nloaded,))
        self._tiles = tiles
        self.ProfEnd()

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
            self._progress("Loading chests... %d/%d", i, totalChests)
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
            self._progress("Loading signs... %d/%d", i, totalSigns)
            text = self._stream.readString()
            debug("Sign text: %s" % (text,))
            x = self._stream.readInt32()
            y = self._stream.readInt32()
            verbose("Loaded sign (%d, %d): %s", x, y, repr(text))
            debug("Offset: %d", self._pos())
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
            homeless = self._stream.readBoolean()
            home_x = self._stream.readInt32()
            home_y = self._stream.readInt32()
            npc = Entity.NPCEntity(name=name, display_name=dispname,
                                   pos=(pos_x, pos_y), homeless=homeless,
                                   home=(home_x, home_y))
            verbose("Loaded NPC: %s", npc)
            npcs.append(npc)
        self._npcs = npcs
        if self._header.Version >= Header.Version140:
            while self._stream.readBoolean():
                name = self._stream.readString()
                pos_x = self._stream.readSingle()
                pos_y = self._stream.readSingle()
                mob = Entity.MobEntity(name=name, pos=(pos_x, pos_y))
                verbose("Loaded mob: %s", mob)
                mobs.append(mob)
        self._mobs = mobs
        verbose("Loaded %d NPCs and %d mobs", len(self._npcs), len(self._mobs))

    def LoadTileEntities(self):
        self._ensure_offset(self._header.GetTileEntitiesPointer())
        tents = []
        count = self._stream.readInt32()
        for i in range(count):
            self._progress("Loading tile entities... %d/%d", i, count)
            tent = None
            type_ = self._stream.readByte()
            id_ = self._stream.readInt32()
            pos_x = self._stream.readInt16()
            pos_y = self._stream.readInt16()
            if type_ == Entity.ENTITY_DUMMY:
                npc = self._stream.readInt16()
                tent = Entity.DummyTileEntity(type=type_, id=id_,
                                              pos=(pos_x, pos_y), npc=npc)
            elif type_ == Entity.ENTITY_ITEM_FRAME:
                item = self._stream.readInt16()
                prefix = self._stream.readByte()
                stack = self._stream.readInt16()
                tent = Entity.ItemFrameTileEntity(type=type_, id=id_,
                                                  pos=(pos_x, pos_y),
                                                  item=item, prefix=prefix,
                                                  stack=stack)
            else:
                warn("Unknown tile entity: %d" % (type_,))
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

    # }}} Region <Loaders> end

    def GetHeader(self):
        return self._header

    def EachTile(self, rowcol=True, unreachable=True, progress=None):
        """Returns an iterable of (row, col, Tile) for each tile
        @param rowcol (default: True)
            If false, result is an iterable of (col, row, Tile), aka (x, y, t)
        @param unreachable (default: True)
            If false, omit unreachable tiles (outer 40 tiles)
        """
        ymin = 0 if unreachable else 40
        xmin = 0 if unreachable else 40
        ymax = self._height if unreachable else self._height - 40
        xmax = self._width if unreachable else self._width - 40
        total = (xmax-xmin)*(ymax-ymin)
        curr = 0
        for y in xrange(ymin, ymax):
            for x in xrange(xmin, xmax):
                if progress is not None:
                    curr += 1
                    self._progress("%s %d/%d %d%%", progress, curr, total,
                                   curr*100/total)
                if rowcol:
                    yield y, x, self._tiles[self._PosToIdx(x, y)]
                else:
                    yield x, y, self._tiles[self._PosToIdx(x, y)]
        if progress is not None:
            self._progress(force=True)

    def Width(self):
        return self._width

    def Height(self):
        return self._height

    def GetTile(self, x, y):
        "Return the Tile object at x, y"
        return self._tiles[self._PosToIdx(x, y)]

    def GetTiles(self, rows, cols):
        """
        Return all tiles in rows, cols:
        @param rows - an iterable of rows to get
        @param cols - an iterable of cols to get
        """
        for r in rows:
            for c in cols:
                yield self._tiles[self._PosToIdx(c, r)]

    def __getitem__(self, idx):
        """
        World itemgetter
        If w = World(), then:
            w[a, b] obtains the tile at row=a, col=b
            w[a, ...] obtains all tiles at row=a
            w[::2, b] obtains every even tile at col=b
            w[::2, :5] obtains every even tile from columns 0 < b < 5

        __getitem__ requires one argument: a pair of two objects. Each object
        can be either a single number, a slice, or an Ellipsis.
        """
        r, c = Ellipsis, Ellipsis
        try:
            r, c = idx
        except (TypeError, ValueError) as e:
            raise ValueError("__getitem__ requires a pair (r,c)", e)
        notNoneElse = lambda value: value if value is not None else default
        def parseGetItemArg(arg, maxVal):
            if arg == Ellipsis:
                return range(maxVal)
            elif isinstance(arg, slice):
                return range(notNoneElse(arg.start, 0),
                             notNoneElse(arg.stop, maxVal),
                             notNoneElse(arg.step, 1))
            elif arg < 0:
                return [maxVal + arg]
            return [arg]
        rows = parseGetItemArg(r, self._height)
        cols = parseGetItemArg(c, self._width)
        # special case instance of asking for just one tile
        if len(rows) == 1 and len(cols) == 1:
            return self._tiles[self._PosToIdx(cols[0], rows[0])]
        return self.GetTiles(rows, cols)

    def GetFlags(self):
        "Return a tuple of (flagName, flagValue)"
        return tuple((f, self._flags.get(f)) for f,_,_ in WorldFlags.Flags)

    def GetFlag(self, flag):
        "Return the value of @param flag"
        return self._flags.get(flag)

    def GetNPCs(self):
        "Return the loaded NPCs"
        return self._npcs

    def GetTileEntities(self):
        "Return the loaded tile entities"
        return self._tents

    def GetLevels(self):
        "Returns a dictionary of strings (name) to number (depth)"
        w, h = self.Width(), self.Height()
        surf = self.GetFlag('GroundLevel')
        rock = self.GetFlag('RockLevel')
        space = surf / 5 + (w**2) / 1764000 + 65
        caves = rock + (1080 / 2) / 16 + 3
        hell = h - 204
        lava = int((rock+hell)/2) + 3
        return {
            'Space': space,
            'Caves': caves,
            'Hell': hell,
            'Surface': surf,
            'Rock': rock,
            'Lava': lava
        }

    def GetPolygon(self, match_fn, simplify=False, epsilon=0.5, multi=False,
                   xmin=None, xmax=None, ymin=None, ymax=None,
                   shortcircuit=False, progress=None):
        """
        Returns a (possibly concave) polygon of all tile positions satisfying
        the match function given by @param match_fn. See the module-level
        PolyMatch_Tile, PolyMatch_Wall, and PolyMatch functions.

        If @param multi is True, the result is a list of polygons, rather than
        a single polygon.

        If @param simplify is True, then the result is passed through the
        shapely module's implementation of the Ramer-Douglas-Peucker
        algorithm.

        If @param shortcircuit is True, then the search will end on the first
        column having zero matching tiles, rather than the last column. This
        works well for things like the Temple or an unmodified Jungle or Snow.

        Unless otherwise specified via @param epsilon, simplification is done
        with an epsilon of half a tile, so only the straight-line segments are
        simplified (i.e. only extraneous colinear tiles are removed). The
        epsilon is a minimum offset for points to be pruned, usually between
        0.5 and around 4 or 5. Larger values result in smaller polygons. Note
        that this algorithm does not work on "noisy" polygons with large
        vertex angle variation.
        """
        simplify_fn = lambda p: p
        if simplify:
            import Region.Poly
            simplify_fn = lambda p: Region.Poly.Simplify(p, epsilon)
        xmin = 0 if xmin is None else xmin
        xmax = self.Width() if xmax is None else xmax
        ymin = 0 if ymin is None else ymin
        ymax = self.Height() if ymax is None else ymax
        xseq = xrange(xmin, xmax)
        yseq = xrange(ymin, ymax)
        polys = []
        points = []
        # 1) generate a sequence of (top, bottom) point pairs
        for x in xseq:
            if progress is not None:
                self._progress("%s %d/%d %d%%", progress, x-xmin, xmax-xmin,
                               (x-xmin)*100/(xmax-xmin))
            start = None
            end = None
            for y in yseq:
                if match_fn(self._tiles[self._PosToIdx(x, y)]):
                    if start is None:
                        start = [x, y]
                    end = [x, y]
            if start is not None: # implies: end is not None
                points.append([start, end])
            else:
                if multi and len(points) > 0:
                    polys.append(points)
                    points = []
                if shortcircuit and len(polys) > 0:
                    break
        if len(points) > 0:
            verbose("Adding points: %s", points)
            polys.append(points)
        # 2) convert those to polygons
        results = []
        for poly in polys:
            verbose("Evaluating %s", poly)
            if len(poly) < 3:
                warn("Discarding line segment %s" % (poly,))
                continue
            results.append(simplify_fn(PointsToChain(poly)))
        if progress is not None:
            self._progress(force=True)
        return results if multi else results[0]

    def GetBiomes(self, biome_def, progress=None):
        from Region.Density import DensityCalculator
        calc = DensityCalculator(self.Width(), self.Height(),
                                 biome_def.WindowSize())
        for x, y, t in self.EachTile(rowcol=False, progress=progress):
            v = biome_def.TileValue(t)
            if v != 0:
                calc.add_point(x, y, v)
        # a point (x,y) is part of a biome if that point's value is no less
        # than biome_def.Threshold(), akin to: (won't work, but it's the idea)
        #   [point for point in calc if point.value >= biome_def.Threshold()]
        biome_matrix = calc.get_matrix() >= biome_def.Threshold()

        # clockwise tracing around points greater than the biome minimum
        # should result in a crisp polygon edge, which can be simplified
        # via the normal algorithm
        # edge has matching biome on the right, non-matching on the left,
        # so it's essentially an arrow
        #
        # state of scan: single point and an arrow leading towards the next
        # single point (edge detection!!)

    def Crimson(self):
        "True if world is Crimson, False otherwise"
        return bool(self.GetFlag('IsCrimson'))

    def Corruption(self):
        "True if world is not Crimson, False otherwise"
        return not self.Crimson()

    def GetSize(self):
        "Returns one of World.SIZE_* constants, or World.SIZE_UNKNOWN"
        size = (self.Width(), self.Height())
        if size in (SIZE_SMALL, SIZE_MEDIUM, SIZE_LARGE):
            return size
        return SIZE_UNKNOWN

    def Expert(self):
        "True if world is in Expert Mode, False otherwise"
        return bool(self.GetFlag('ExpertMode'))

    def Title(self):
        return self.GetFlag('Title')

    def GetTileCounts(self):
        return self._tile_counts

    def GetTileCount(self, tile):
        "Number of occurrences of tile ID given"
        return self._tile_counts[tile]

    def GetWallCounts(self):
        return self._wall_counts

    def GetWallCount(self, wall):
        "Number of occurrences of wall ID given"
        return self._wall_counts[wall]

ListWorlds = World.ListWorlds
FindWorld = World.FindWorld

