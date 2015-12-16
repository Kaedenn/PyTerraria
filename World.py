#!/usr/bin/env python

"""
Module for handling Terraria world files

class World:
    See the World class docstring for usage.
"""

import copy
import os
import sys
import time
from warnings import warn

import Header
from Header import CompatibleVersion, Version147, Version140, Version104, \
                   Version101, Version99, Version95
from WorldFlags import WorldFlags
import BinaryString
import IDs
import Tile
import Chest
import Entity

class _G(object):
    def __init__(self):
        self.VERBOSE_MODE = False
        self.DEBUG_MODE = False

G = _G()

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
                 progress_delay=0.2):
        """See the World class or World module docstring"""
        self._readonly = read_only
        self._extents = None
        self._header = None
        self._flags = None
        self._tiles = None
        self._chests = None
        self._signs = None
        self._npcs = None
        self._width, self._height = 0, 0
        self._extents = [0, 0]
        self._loaded = False
        self._last_progress_time = 0
        self._curr_progress_time = 0
        self._progress_delay = progress_delay

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

    def __repr__(self):
        if self._loaded:
            return "<Terraria World %r (%d, %d)>" % (self._flags.Title,
                    self._width, self._height)
        return super(World, self).__repr__()

    def _PosToIdx(self, x, y):
        if 0 <= x < self._width and 0 <= y < self._height:
            return y * self._width + x
        raise RuntimeError("Invalid OOB tile position (%s,%s)" % (x, y))

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
            m = message % args if args else str(message)
            self._max_progress_len = max((len(m), self._max_progress_len))
            sys.stderr.write(m)
        sys.stderr.write(" "*self._max_progress_len + "\r")
        self._last_progress_time = self._curr_progress_time

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
                    w.LoadFileHeader()
                    w.LoadWorldFlags()
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
            if worldname is not None and worldname == w.GetWorldFlag('Title'):
                return open(fp, 'r') if doopen else fp
            elif worldid is not None and worldid == w.GetWorldFlag('WorldId'):
                return open(fp, 'r') if doopen else fp
        if not failquiet:
            raise RuntimeError("World %s not found" % (worldname,))
        verbose("No world matching (n=%r, id=%r) found", worldname, worldid)

    def Load(self, fobj=None):
        """Loads the world given by @param fobj (if present) or the value of
        @param fname or @param fobj passed to __init__.

        Use the arguments to __init__ to suppress loading certain sections.
        """
        if fobj is not None:
            self._stream = BinaryString.BinaryString(fobj.read(),
                                                     debug=G.DEBUG_MODE)
        # Populate self._header
        self.LoadFileHeader()

        offsets = self._header.SectionPointers
        verbose("Header size: %s" % (offsets[1] - offsets[0],))
        verbose("Tile data size: %s" % (offsets[2] - offsets[1],))
        verbose("Chest data size: %s" % (offsets[3] - offsets[2],))
        verbose("Sign data size: %s" % (offsets[4] - offsets[3],))

        self._progress("Loading world flags")
        assert self._pos() == self._header.GetFlagsPointer()
        self.LoadWorldFlags()
        assert self._pos() == self._header.GetTilesPointer()
        self._width = self._flags.TilesWide
        self._height = self._flags.TilesHigh
        self._extents = [self._flags.TilesWide, self._flags.TilesHigh]
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
        if self._header.Version >= Version140:
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
        if self._footer['Title'] != self.GetWorldFlag('Title'):
            warn("Footer title %r does not match header title %r" % (
                self._footer['Title'], self.GetWorldFlag('Title')))
        if self._footer['WorldID'] != self.GetWorldFlag('WorldId'):
            warn("Footer ID %s does not match header ID %s" % (
                self._footer['WorldID'], self.GetWorldFlag('WorldId')))
        self._progress(force=True)

        if G.DEBUG_MODE:
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
        self._loaded = True

    def LoadWorldFlags(self, stream=None):
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
                    if IDs.valid_tile(value):
                        verbose("flag %s = 0x%x (%d %s)" % (name, value, value,
                            IDs.TileID[value]))
                    elif flags.getFlag('HardMode'):
                        warn("Bad ore tier: %s, %s" % (name, value))
                flags.setFlag(name, value)
        self._width = flags.TilesWide
        self._height = flags.TilesHigh
        self._extents = [flags.TilesWide, flags.TilesHigh]
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
                        bytes_loaded-start, size, bytes_loaded*100/size)
                i = self._PosToIdx(x, y)
                tile, rle = Tile.FromStream(self._stream, important)
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
            warn("Rows left to parse: %d, columns left to parse: %d" %
                    (xerr, yerr))
        verbose("Actually loaded %d tiles" % (nloaded,))
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
            self._progress("Loading tile entities... %d/%d", i, count)
            tent = None
            type_ = self._stream.readByte()
            id_ = self._stream.readInt32()
            pos_x = self._stream.readInt16()
            pos_y = self._stream.readInt16()
            pos = (pos_x, pos_y)
            if type_ == Entity.ENTITY_DUMMY:
                npc = self._stream.readInt16()
                tent = Entity.DummyTileEntity(type=type_, id=id_, pos=pos,
                                              npc=npc)
            elif type_ == Entity.ENTITY_ITEM_FRAME:
                item = self._stream.readInt16()
                prefix = self._stream.readByte()
                stack = self._stream.readInt16()
                tent = Entity.ItemFrameTileEntity(type=type_, id=id_, pos=pos,
                                                  item=item, prefix=prefix,
                                                  stack=stack)
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
                    self._progress("%s %d/%d %d%%" % (progress, curr,
                        total, curr*100/total))
                if rowcol:
                    yield y, x, self._tiles[self._PosToIdx(x, y)]
                else:
                    yield x, y, self._tiles[self._PosToIdx(x, y)]

    def Width(self):
        return self._width

    def Height(self):
        return self._height

    def GetTile(self, i, j):
        "Return the Tile object at x=i, y=j"
        if not (0 <= i < self._width) or not (0 <= j < self._height):
            raise IndexError("(%d,%d) must be between (0, 0) and (%d, %d)" %
                    (i, j, self._width, self._height))
        return self._tiles[self._PosToIdx(i, j)]

    def GetTiles(self, rows, cols):
        """Return all tiles in rows, cols:
        @param rows - an iterable of rows to get
        @param cols - an iterable of cols to get"""
        for r in rows:
            for c in cols:
                yield self._tiles[self._PosToIdx(c, r)]

    def __getitem__(self, idx):
        r, c = Ellipsis, Ellipsis
        try:
            r, c = idx
        except (TypeError, ValueError) as e:
            raise ValueError("__getitem__ requires a pair (r,c)", e)
        rows = [r]
        cols = [c]
        if r == Ellipsis:
            rows = range(self._height)
        elif isinstance(r, slice):
            start = r.start if r.start is not None else 0
            stop = r.stop if r.stop is not None else self._height
            step = r.step if r.step is not None else 1
            rows = range(start, stop, step)
        elif r < 0:
            while r < 0:
                r = self._height + r
            rows = [r]
        if c == Ellipsis:
            cols = range(self._width)
        elif isinstance(c, slice):
            start = c.start if c.start is not None else 0
            stop = c.stop if c.stop is not None else self._width
            step = c.step if c.step is not None else 1
            cols = range(start, stop, step)
        elif c < 0:
            while c < 0:
                c = self._width + c
            cols = [c]
        verbose("Returning %d tiles", len(rows)*len(cols))
        if len(rows) == 1 and len(cols) == 1:
            return self._tiles[self._PosToIdx(cols[0], rows[0])]
        return self.GetTiles(rows, cols)

    def GetWorldFlags(self):
        "Return a tuple of (flagName, flagValue)"
        flags = []
        for flag, _, _ in WorldFlags.Flags:
            flags.append((flag, self._flags.getFlag(flag)))
        return tuple(flags)

    def GetWorldFlag(self, flag):
        "Return the value of @param flag"
        return self._flags.getFlag(flag)

    def GetNPCs(self):
        return self._npcs

    def GetTileEntities(self):
        return self._tents

    def CountTiles(self):
        "Returns a dict of numeric tile type to frequency counts"
        counts = {}
        for tile in self._tiles:
            if tile is not None and tile.IsActive:
                if tile.Type not in counts:
                    counts[tile.Type] = 1
                else:
                    counts[tile.Type] += 1
        verbose("Active tile types: %d", len(counts.keys()))
        return counts

