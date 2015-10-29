#!/usr/bin/env python

import os
import sys

import Header
import BinaryStream
from BinaryStream import BinaryStream
import IDs
import Tile
import Chest

VERBOSE_MODE = False

def verbose(string):
    if VERBOSE_MODE:
        sys.stderr.write(string)
        sys.stderr.write("\n")

def warn(string):
    import warnings
    warnings.warn(string)

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

class WorldFlags(object):
    Flags = (
        ("WorldId", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("LeftWorld", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("RightWorld", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TopWorld", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("BottomWorld", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TilesHigh", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TilesWide", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("ExpertMode", BinaryStream.BooleanType, Header.Version147),
        ("CreationTime", BinaryStream.UInt64Type, Header.Version147),
        ("MoonType", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("TreeX0", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TreeX1", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TreeX2", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TreeStyle0", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TreeStyle1", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TreeStyle2", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TreeStyle3", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackX0", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackX1", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackX2", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackStyle0", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackStyle1", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackStyle2", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("CaveBackStyle3", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("IceBackStyle", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("JungleBackStyle", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("HellBackStyle", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("SpawnX", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("SpawnY", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("GroundLevel", BinaryStream.DoubleType, Header.CompatibleVersion),
        ("RockLevel", BinaryStream.DoubleType, Header.CompatibleVersion),
        ("Time", BinaryStream.DoubleType, Header.CompatibleVersion),
        ("DayTime", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("MoonPhase", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("BloodMoon", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("IsEclipse", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DungeonX", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("DungeonY", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("IsCrimson", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedBoss1", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedBoss2", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedBoss3", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedQueenBee", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedMechBoss1", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedMechBoss2", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedMechBoss3", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedMechBossAny", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedPlantBoss", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedGolemBoss", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedSlimeKingBoss", BinaryStream.BooleanType, Header.Version147),
        ("SavedGoblin", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("SavedWizard", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("SavedMech", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedGoblins", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedClown", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedFrost", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("DownedPirates", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("ShadowOrbSmashed", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("SpawnMeteor", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("ShadowOrbCount", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("AltarCount", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("HardMode", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("InvasionDelay", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("InvasionSize", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("InvasionType", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("InvasionX", BinaryStream.DoubleType, Header.CompatibleVersion),
        ("SlimeRainTime", BinaryStream.DoubleType, Header.Version147),
        ("SundialCooldown", BinaryStream.SInt8Type, Header.Version147),
        ("TempRaining", BinaryStream.BooleanType, Header.CompatibleVersion),
        ("TempRainTime", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("TempMaxRain", BinaryStream.SingleType, Header.CompatibleVersion),
        ("OreTier1", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("OreTier2", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("OreTier3", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("BGTree", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGCorruption", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGJungle", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGSnow", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGHallow", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGCrimson", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGDesert", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("BGOcean", BinaryStream.SInt8Type, Header.CompatibleVersion),
        ("CloudBGActive", BinaryStream.UInt32Type, Header.CompatibleVersion),
        ("NumClouds", BinaryStream.UInt16Type, Header.CompatibleVersion),
        ("WindSpeedSet", BinaryStream.SingleType, Header.CompatibleVersion),
        ("NumAnglers", BinaryStream.UInt32Type, Header.Version95),
        ("Anglers", None, Header.Version95), # requires manual parsing
        ("SavedAngler", BinaryStream.BooleanType, Header.Version99),
        ("AnglerQuest", BinaryStream.UInt32Type, Header.Version101),
        ("SavedStylist", BinaryStream.BooleanType, Header.Version104),
        ("SavedTaxCollector", BinaryStream.BooleanType, Header.Version140),
        ("InvasionSizeStart", BinaryStream.UInt32Type, Header.Version140),
        ("CultistDelay", BinaryStream.UInt32Type, Header.Version140),
        ("KilledMobCount", BinaryStream.UInt16Type, Header.Version140),
        ("KilledMobs", None, Header.Version140), # requires manual parsing
        ("FastForwardTime", BinaryStream.BooleanType, Header.Version140),
        ("DownedFishron", BinaryStream.BooleanType, Header.Version140),
        ("DownedMartians", BinaryStream.BooleanType, Header.Version140),
        ("DownedLunaticCultist", BinaryStream.BooleanType, Header.Version140),
        ("DownedMoonlord", BinaryStream.BooleanType, Header.Version140),
        ("DownedHalloweenKing", BinaryStream.BooleanType, Header.Version140),
        ("DownedHalloweenTree", BinaryStream.BooleanType, Header.Version140),
        ("DownedChristmasQueen", BinaryStream.BooleanType, Header.Version140),
        ("DownedSanta", BinaryStream.BooleanType, Header.Version140),
        ("DownedChristmasTree", BinaryStream.BooleanType, Header.Version140),
        ("DownedCelestialColar", BinaryStream.BooleanType, Header.Version140),
        ("DownedCelestialVortex", BinaryStream.BooleanType, Header.Version140),
        ("DownedCelestialNebula", BinaryStream.BooleanType, Header.Version140),
        ("DownedCelestialStardust", BinaryStream.BooleanType, Header.Version140),
        ("CelestialSolarActive", BinaryStream.BooleanType, Header.Version140),
        ("CelestialVortexActive", BinaryStream.BooleanType, Header.Version140),
        ("CelestialNebulaActive", BinaryStream.BooleanType, Header.Version140),
        ("CelestialStardustActive", BinaryStream.BooleanType, Header.Version140),
        ("Apocalypse", BinaryStream.BooleanType, Header.Version140),
        ("UnknownFlags", None, Header.CompatibleVersion) # future proofing, requires manual parsing
    )
    def __init__(self, version):
        self.Title = ''      # ILString
        for flag in WorldFlags.Flags:
            setattr(self, flag[0], 0 if flag[1] is not None else [])

    def setFlag(self, flag, value):
        setattr(self, flag, value)

    def getFlag(self, flag):
        return getattr(self, flag)

class World(object):
    def _PosToIdx(self, x, y):
        return y * self._extents[0] + x

    def _IdxToPos(self, idx):
        return (idx % self._extents[0], int(idx / self._extents[0]))

    def _ensure_offset(self, offset, or_fatal=False):
        if or_fatal and self._stream.get_pos() != offset:
            raise RuntimeError("Stream position %d not at expected offset %d" %
                               (self._stream.get_pos(), offset))
        self._stream.seek_set(offset)

    def __init__(self, fname=None, fobj=None, load_tiles=True,
                 verbose=False, debug=False):
        global VERBOSE_MODE
        self._extents = None
        self._header = None
        self._flags = None
        self._tiles = None
        self._chests = None
        self._signs = None
        self._npcs = None

        VERBOSE_MODE = VERBOSE_MODE or verbose or debug
        self._debug_enabled = debug
        self._should_load_tiles = load_tiles
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
        self._stream = BinaryStream(fobj)

    def _start_debug_frame(self):
        self._debugging = []

    def _add_debug(self, message, *args):
        if self._debug:
            self._debugging.append(message % args)

    @staticmethod
    def ListWorlds():
        worlds = []
        if os.path.exists(WORLDPATH_LINUX):
            for f in os.listdir(WORLDPATH_LINUX):
                fp = os.path.join(WORLDPATH_LINUX, f)
                if f.endswith('.wld'):
                    w = World()
                    w.Open(open(fp, 'r'))
                    w.LoadSectionHeader()
                    w.LoadHeaderFlags()
                    worlds.append((f, w.GetHeaderFlag('Title'), fp))
        verbose(str(worlds))
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
            self._stream = BinaryStream(fobj)
        # Populate self._header
        self.LoadSectionHeader()

        offsets = self._header.SectionPointers
        verbose("Header size: %s" % (offsets[1] - offsets[0],))
        verbose("Tile data size: %s" % (offsets[2] - offsets[1],))
        verbose("Chest data size: %s" % (offsets[3] - offsets[2],))
        verbose("Sign data size: %s" % (offsets[4] - offsets[3],))

        assert self._stream.get_pos() == self._header.GetFlagsPointer()
        # Populate self._flags
        self.LoadHeaderFlags()
        assert self._stream.get_pos() == self._header.GetTilesPointer()
        self._extents = [self._flags.TilesWide, self._flags.TilesHigh]
        if self._should_load_tiles:
            # Populate self._tiles
            self.LoadTileData(self._flags.TilesWide, self._flags.TilesHigh)
            assert self._stream.get_pos() == self._header.GetChestsPointer()
        else:
            self._stream.seek_set(self._header.GetChestsPointer())
        self.LoadAllChests()
        assert self._stream.get_pos() == self._header.GetSignsPointer()
        #self.LoadAllSigns()
        #assert self._stream.get_pos() == self._header.GetNPCsPointer()
        #self.LoadNPCs()
        #if self._header.Version >= Header.Version140:
        #    self.LoadMobs()
        #    assert self._stream.get_pos() == self._header.GetTileEntitiesPointer()
        #    self.LoadTileEntities()
        #assert self._stream.get_pos() == self._header.GetFooterPointer()
        #self.LoadFooter()

    def LoadSectionHeader(self, stream=None):
        if stream is None:
            stream = self._stream
        header = Header.WorldFileHeader()
        header.Version = stream.readUInt32()
        header.MetaMagic = stream.readUInt64()
        header.MetaRevision = stream.readUInt32()
        header.WorldBits = stream.readUInt64()
        numSectionPointers = stream.readUInt16()
        verbose("number of sections: %s" % (numSectionPointers,))
        for i in range(numSectionPointers):
            header.SectionPointers[i] = stream.readUInt32()
        header.ImportantTiles = stream.readBitArray()
        self._header = header

    def LoadHeaderFlags(self, stream=None):
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
                verbose("Manually processing %s" % (name,))
                # special parsing
                if name == "Anglers":
                    anglers = self._LoadAnglers(flags.NumAnglers)
                    verbose("Loaded anglers: %r" % (anglers,))
                    flags.setFlag(name, anglers)
                elif name == "KilledMobs":
                    killcount = self._LoadKilledMobs(flags.KilledMobCount)
                    verbose("Loaded mob kill count: %r" % (killcount,))
                    flags.setFlag(name, killcount)
                elif name == "UnknownFlags":
                    flags.setFlag(name, self._LoadUnknownHeaders())
                else:
                    assert typename is not None, "invalid flag %s" % (name,)
            else:
                value = BinaryStream.ScalarReaderLookup[typename](stream)
                verbose("flag %s == 0x%x (%d)" % (name, value, value))
                if name.startswith('OreTier'):
                    try:
                        verbose("flag %s = 0x%x (%s)" % (name, value, IDs.TileID[value]))
                    except KeyError as e:
                        # If the value is not a valid tile, then we're not in
                        # hard mode yet
                        assert not flags.getFlag('HardMode')
                flags.setFlag(name, value)
        self._flags = flags

    def _LoadAnglers(self, num_anglers):
        anglers = []
        verbose("Processing %d anglers" % (num_anglers,))
        for i in range(num_anglers):
            anglers.append(self._stream.readString())
        return anglers

    def _LoadKilledMobs(self, num_mobs):
        mobs = []
        verbose("Processing %d mobs" % (num_mobs,))
        for i in range(num_mobs):
            mobs.append(self._stream.readUInt32())
        return mobs

    def _LoadUnknownHeaders(self):
        nflags = self._header.SectionPointers[1] - self._stream.get_pos()
        if nflags == 0:
            verbose("No flags present")
        else:
            verbose("%d flag(s) present" % (nflags,))
        flags = []
        for i in range(nflags):
            verbose("Reading flag %d" % (i,))
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
        while x < width and self._stream.get_pos() < endPos:
            y = 0
            while y < height and self._stream.get_pos() < endPos:
                self._start_debug_frame()
                self._add_debug("Start loading tile [%d, %d]", x, y)
                self._add_debug("Tile stream pos: %s", self._stream.get_pos())
                tile, rle = -1, 0
                try:
                    tile, rle = self._LoadOneTile()
                except (IndexError, TypeError, ValueError) as e:
                    print("Pos: %s" % (self._stream.get_pos(),))
                    print("Bytes left to parse: %s" % (endPos - self._stream.get_pos(),))
                    print("\n".join(self._debugging))
                    print("Tiles loaded successfully: %d" % (nloaded,))
                    raise
                nloaded += 1
                nprocessed += 1
                self._add_debug("Loaded %d, processed %d", nloaded, nprocessed)
                self._add_debug("Tile %s, rle %s", tile, rle)
                tiles[self._PosToIdx(x, y)] = tile
                while rle > 0:
                    y += 1
                    self._add_debug("Processing RLE %d [%d, %d]", rle, x, y)
                    tiles[self._PosToIdx(x, y)] = tile
                    nprocessed += 1
                    rle -= 1
                y += 1
            x += 1
        if self._stream.get_pos() > endPos:
            overread = endPos - self._stream.get_pos()
            warn("Read %d bytes past the end of the section!" % (overread,))
        elif self._stream.get_pos() == endPos and (x < width or y < height):
            xerr = width - x
            yerr = height - y
            warn("Incomplete section! Terminated on tile (%d, %d)" % (x, y))
            warn("Rows left to parse: %d, columns left to parse: %d" %
                    (xerr, yerr))
        verbose("Actually loaded %d tiles" % (nloaded,))
        verbose("Actually processed %d tiles" % (nprocessed,))
        self._tiles = tiles

    def _LoadOneTile(self):
        tile = Tile.Tile()
        rle = 0
        header1 = self._stream.readUInt8()
        header2 = 0
        header3 = 0
        if test_bit(header1, BIT_MOREHDR):
            header2 = self._stream.readUInt8()
        if test_bit(header2, BIT_MOREHDR):
            header3 = self._stream.readUInt8()
        if test_bit(header3, BIT_MOREHDR):
            print(bin(header1), bin(header2), bin(header3))
            raise NotImplementedError("Tile with more than two headers not" +
                                      " supported!")

        self._add_debug("Loading tile headers %b %b %b", header1, header2, header3)
        # process header1
        if test_bit(header1, BIT_ACTIVE):
            tile.IsActive = True
            if test_bit(header1, BIT_TYPE16B):
                tile.Type = self._stream.readUInt16()
            else:
                tile.Type = self._stream.readUInt8();
            self._add_debug("Tile type = %x", tile.Type)
            if self._header.ImportantTiles[tile.Type]:
                self._add_debug("Tile is important, reading u,v")
                tile.U = self._stream.readInt16()
                tile.V = self._stream.readInt16()
                if tile.Type == Tile.TileTypes.Timer:
                    tile.V = 0
            else:
                tile.U = -1
                tile.V = -1
            if test_bit(header3, BIT_TCOLOR):
                tile.TileColor = self._stream.readUInt8()
        if test_bit(header1, BIT_HASWALL): # bit[2] = 4
            tile.Wall = self._stream.readUInt8()
            if test_bit(header3, BIT_WCOLOR): # bit[4] = 16
                tile.WallColor = self._stream.readUInt8()
        tile.LiquidType = ((header1 & MASK_LIQUID) >> 3) # bits[3:5] = 24
        if tile.LiquidType != 0:
            tile.LiquidAmount = self._stream.readUInt8()

        # process header2
        if test_bit(header2, BIT_REDWI):
            tile.WireRed = True
        if test_bit(header2, BIT_GREENWI):
            tile.WireGreen = True
        if test_bit(header2, BIT_BLUEWI):
            tile.WireBlue = True
        tile.BrickStyle = ((header2 & MASK_BSTYLE) >> 4) # bits[4:7] = 112

        # process header3
        if test_bit(header3, BIT_ACTUATE):
            tile.Actuator = True
        if test_bit(header3, BIT_INACTIV):
            tile.InActive = True

        # process RLE
        rleType = ((header1 & MASK_HASRLE) >> 6)
        if rleType == 0:
            rle = 0
        elif rleType == 1:
            rle = self._stream.readUInt8()
            self._add_debug("rleType = %d, rle = %d", rleType, rle)
        else:
            rle = self._stream.readInt16()
            self._add_debug("rleType = %d, rle = %d", rleType, rle)

        self._add_debug("Loaded tile %s (rle %s)", tile, rle)
        return tile, rle

    def LoadAllChests(self):
        self._ensure_offset(self._header.GetChestsPointer())
        chests = []
        totalChests = self._stream.readUInt16()
        maxItems = self._stream.readUInt16()
        itemsPerChest = maxItems
        overflowItems = 0
        if maxItems >= Chest.MAX_ITEMS:
            itemsPerChest = Chest.MAX_ITEMS
            overflowItems = maxItems - Chest.MAX_ITEMS
        verbose("Reading %d chests, %d items (%d overflow)" % (totalChests,
                maxItems, overflowItems))
        for i in range(0, totalChests):
            chests.append(self._LoadOneChest(itemsPerChest, overflowItems))
        verbose("Read %d chests" % (totalChests,))
        self._chests = chests

    def _LoadOneChest(self, itemsPerChest, overflowItems):
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
        self._debug("%s" % (c,))
        return c

    def LoadAllSigns(self):
        self._ensure_offset(self._header.GetSignsPointer())

    def _LoadOneSign(self):
        pass

    def LoadNPCs(self):
        pass

    def LoadMobs(self):
        pass

    def LoadTileEntities(self):
        pass

    def LoadFooter(self):
        pass

    def EachTile(self):
        "Returns an iterable of (row, col, Tile) for each tile"
        for y in xrange(self.GetHeaderFlag('TilesHigh')):
            for x in xrange(self.GetHeaderFlag('TilesWide')):
                yield y, x, self.GetTile(x, y)

    def GetTile(self, i, j):
        return self._tiles[self._PosToIdx(i, j)]

    def GetHeaderFlags(self):
        flags = []
        for flag, _, _ in WorldFlags.Flags:
            flags.append((flag, self._flags.getFlag(flag)))
        return dict(flags)

    def GetHeaderFlag(self, flag):
        return self._flags.getFlag(flag)

    def CountTiles(self):
        counts = {}
        for tile in self._tiles:
            if tile is not None and tile.IsActive:
                if tile.Type not in counts:
                    counts[tile.Type] = 1
                else:
                    counts[tile.Type] += 1
        return counts

