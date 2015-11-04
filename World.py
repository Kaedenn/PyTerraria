#!/usr/bin/env python

import os
import sys

import Header
from Header import CompatibleVersion, Version147, Version140, Version104, \
                   Version101, Version99, Version95
import BinaryString
import IDs
import Tile
import Chest

VERBOSE_MODE = False

def verbose(string, *args):
    if VERBOSE_MODE:
        if args:
            sys.stderr.write(string % args)
        else:
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
        ("WorldId", BinaryString.UInt32Type, CompatibleVersion),
        ("LeftWorld", BinaryString.UInt32Type, CompatibleVersion),
        ("RightWorld", BinaryString.UInt32Type, CompatibleVersion),
        ("TopWorld", BinaryString.UInt32Type, CompatibleVersion),
        ("BottomWorld", BinaryString.UInt32Type, CompatibleVersion),
        ("TilesHigh", BinaryString.UInt32Type, CompatibleVersion),
        ("TilesWide", BinaryString.UInt32Type, CompatibleVersion),
        ("ExpertMode", BinaryString.BooleanType, Version147),
        ("CreationTime", BinaryString.UInt64Type, Version147),
        ("MoonType", BinaryString.SInt8Type, CompatibleVersion),
        ("TreeX0", BinaryString.UInt32Type, CompatibleVersion),
        ("TreeX1", BinaryString.UInt32Type, CompatibleVersion),
        ("TreeX2", BinaryString.UInt32Type, CompatibleVersion),
        ("TreeStyle0", BinaryString.UInt32Type, CompatibleVersion),
        ("TreeStyle1", BinaryString.UInt32Type, CompatibleVersion),
        ("TreeStyle2", BinaryString.UInt32Type, CompatibleVersion),
        ("TreeStyle3", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackX0", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackX1", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackX2", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackStyle0", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackStyle1", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackStyle2", BinaryString.UInt32Type, CompatibleVersion),
        ("CaveBackStyle3", BinaryString.UInt32Type, CompatibleVersion),
        ("IceBackStyle", BinaryString.UInt32Type, CompatibleVersion),
        ("JungleBackStyle", BinaryString.UInt32Type, CompatibleVersion),
        ("HellBackStyle", BinaryString.UInt32Type, CompatibleVersion),
        ("SpawnX", BinaryString.UInt32Type, CompatibleVersion),
        ("SpawnY", BinaryString.UInt32Type, CompatibleVersion),
        ("GroundLevel", BinaryString.DoubleType, CompatibleVersion),
        ("RockLevel", BinaryString.DoubleType, CompatibleVersion),
        ("Time", BinaryString.DoubleType, CompatibleVersion),
        ("DayTime", BinaryString.BooleanType, CompatibleVersion),
        ("MoonPhase", BinaryString.UInt32Type, CompatibleVersion),
        ("BloodMoon", BinaryString.BooleanType, CompatibleVersion),
        ("IsEclipse", BinaryString.BooleanType, CompatibleVersion),
        ("DungeonX", BinaryString.UInt32Type, CompatibleVersion),
        ("DungeonY", BinaryString.UInt32Type, CompatibleVersion),
        ("IsCrimson", BinaryString.BooleanType, CompatibleVersion),
        ("DownedBoss1", BinaryString.BooleanType, CompatibleVersion),
        ("DownedBoss2", BinaryString.BooleanType, CompatibleVersion),
        ("DownedBoss3", BinaryString.BooleanType, CompatibleVersion),
        ("DownedQueenBee", BinaryString.BooleanType, CompatibleVersion),
        ("DownedMechBoss1", BinaryString.BooleanType, CompatibleVersion),
        ("DownedMechBoss2", BinaryString.BooleanType, CompatibleVersion),
        ("DownedMechBoss3", BinaryString.BooleanType, CompatibleVersion),
        ("DownedMechBossAny", BinaryString.BooleanType, CompatibleVersion),
        ("DownedPlantBoss", BinaryString.BooleanType, CompatibleVersion),
        ("DownedGolemBoss", BinaryString.BooleanType, CompatibleVersion),
        ("DownedSlimeKingBoss", BinaryString.BooleanType, Version147),
        ("SavedGoblin", BinaryString.BooleanType, CompatibleVersion),
        ("SavedWizard", BinaryString.BooleanType, CompatibleVersion),
        ("SavedMech", BinaryString.BooleanType, CompatibleVersion),
        ("DownedGoblins", BinaryString.BooleanType, CompatibleVersion),
        ("DownedClown", BinaryString.BooleanType, CompatibleVersion),
        ("DownedFrost", BinaryString.BooleanType, CompatibleVersion),
        ("DownedPirates", BinaryString.BooleanType, CompatibleVersion),
        ("ShadowOrbSmashed", BinaryString.BooleanType, CompatibleVersion),
        ("SpawnMeteor", BinaryString.BooleanType, CompatibleVersion),
        ("ShadowOrbCount", BinaryString.SInt8Type, CompatibleVersion),
        ("AltarCount", BinaryString.UInt32Type, CompatibleVersion),
        ("HardMode", BinaryString.BooleanType, CompatibleVersion),
        ("InvasionDelay", BinaryString.UInt32Type, CompatibleVersion),
        ("InvasionSize", BinaryString.UInt32Type, CompatibleVersion),
        ("InvasionType", BinaryString.UInt32Type, CompatibleVersion),
        ("InvasionX", BinaryString.DoubleType, CompatibleVersion),
        ("SlimeRainTime", BinaryString.DoubleType, Version147),
        ("SundialCooldown", BinaryString.SInt8Type, Version147),
        ("TempRaining", BinaryString.BooleanType, CompatibleVersion),
        ("TempRainTime", BinaryString.UInt32Type, CompatibleVersion),
        ("TempMaxRain", BinaryString.SingleType, CompatibleVersion),
        ("OreTier1", BinaryString.UInt32Type, CompatibleVersion),
        ("OreTier2", BinaryString.UInt32Type, CompatibleVersion),
        ("OreTier3", BinaryString.UInt32Type, CompatibleVersion),
        ("BGTree", BinaryString.SInt8Type, CompatibleVersion),
        ("BGCorruption", BinaryString.SInt8Type, CompatibleVersion),
        ("BGJungle", BinaryString.SInt8Type, CompatibleVersion),
        ("BGSnow", BinaryString.SInt8Type, CompatibleVersion),
        ("BGHallow", BinaryString.SInt8Type, CompatibleVersion),
        ("BGCrimson", BinaryString.SInt8Type, CompatibleVersion),
        ("BGDesert", BinaryString.SInt8Type, CompatibleVersion),
        ("BGOcean", BinaryString.SInt8Type, CompatibleVersion),
        ("CloudBGActive", BinaryString.UInt32Type, CompatibleVersion),
        ("NumClouds", BinaryString.UInt16Type, CompatibleVersion),
        ("WindSpeedSet", BinaryString.SingleType, CompatibleVersion),
        ("NumAnglers", BinaryString.UInt32Type, Version95),
        ("Anglers", None, Version95), # requires manual parsing
        ("SavedAngler", BinaryString.BooleanType, Version99),
        ("AnglerQuest", BinaryString.UInt32Type, Version101),
        ("SavedStylist", BinaryString.BooleanType, Version104),
        ("SavedTaxCollector", BinaryString.BooleanType, Version140),
        ("InvasionSizeStart", BinaryString.UInt32Type, Version140),
        ("CultistDelay", BinaryString.UInt32Type, Version140),
        ("KilledMobCount", BinaryString.UInt16Type, Version140),
        ("KilledMobs", None, Version140), # requires manual parsing
        ("FastForwardTime", BinaryString.BooleanType, Version140),
        ("DownedFishron", BinaryString.BooleanType, Version140),
        ("DownedMartians", BinaryString.BooleanType, Version140),
        ("DownedLunaticCultist", BinaryString.BooleanType, Version140),
        ("DownedMoonlord", BinaryString.BooleanType, Version140),
        ("DownedHalloweenKing", BinaryString.BooleanType, Version140),
        ("DownedHalloweenTree", BinaryString.BooleanType, Version140),
        ("DownedChristmasQueen", BinaryString.BooleanType, Version140),
        ("DownedSanta", BinaryString.BooleanType, Version140),
        ("DownedChristmasTree", BinaryString.BooleanType, Version140),
        ("DownedCelestialColar", BinaryString.BooleanType, Version140),
        ("DownedCelestialVortex", BinaryString.BooleanType, Version140),
        ("DownedCelestialNebula", BinaryString.BooleanType, Version140),
        ("DownedCelestialStardust", BinaryString.BooleanType, Version140),
        ("CelestialSolarActive", BinaryString.BooleanType, Version140),
        ("CelestialVortexActive", BinaryString.BooleanType, Version140),
        ("CelestialNebulaActive", BinaryString.BooleanType, Version140),
        ("CelestialStardustActive", BinaryString.BooleanType, Version140),
        ("Apocalypse", BinaryString.BooleanType, Version140),
        ("UnknownFlags", None, CompatibleVersion) # future proofing, and
                                                  # requires manual parsing
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

    def __init__(self, fname=None, fobj=None,
                 load_tiles=True,
                 load_chests=True,
                 load_signs=True,
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
        self._should_load_chests = load_chests
        self._should_load_signs = load_signs
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
        self._stream = BinaryString.BinaryString(fobj)

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
                    w.LoadSectionHeader()
                    w.LoadHeaderFlags()
                    worlds.append((f, w.GetHeaderFlag('Title'), fp))
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
            self._stream = BinaryString.BinaryString(fobj)
        # Populate self._header
        self.LoadSectionHeader()

        offsets = self._header.SectionPointers
        verbose("Header size: %s" % (offsets[1] - offsets[0],))
        verbose("Tile data size: %s" % (offsets[2] - offsets[1],))
        verbose("Chest data size: %s" % (offsets[3] - offsets[2],))
        verbose("Sign data size: %s" % (offsets[4] - offsets[3],))

        assert self._pos() == self._header.GetFlagsPointer()
        # Populate self._flags
        self.LoadHeaderFlags()
        assert self._pos() == self._header.GetTilesPointer()
        self._extents = [self._flags.TilesWide, self._flags.TilesHigh]
        if self._should_load_tiles:
            # Populate self._tiles
            self.LoadTileData(self._flags.TilesWide, self._flags.TilesHigh)
            assert self._pos() == self._header.GetChestsPointer()
        else:
            self._stream.seek_set(self._header.GetChestsPointer())
        if self._should_load_chests:
            self.LoadAllChests()
            assert self._pos() == self._header.GetSignsPointer()
        else:
            self._stream.seek_set(self._header.GetSignsPointer())
        if self._should_load_signs:
            self.LoadAllSigns()
            assert self._pos() == self._header.GetNPCsPointer()
        else:
            self._stream.seek_set(self._header.GetNPCsPointer())
        self.LoadNPCs()
        if self._header.Version >= Version140:
            assert self._pos() == self._header.GetTileEntitiesPointer()
            self.LoadTileEntities()
        assert self._pos() == self._header.GetFooterPointer()
        self.LoadFooter()

    def LoadSectionHeader(self, stream=None):
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
            verbose("No flags present")
        else:
            verbose("%d flag(s) present" % (nflags,))
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
                tile, rle = self._LoadOneTile()
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

        self._add_debug("Loading tile headers %d %d %d", header1, header2,
                        header3)
        # process header1
        if test_bit(header1, BIT_ACTIVE):
            tile.IsActive = True
            if test_bit(header1, BIT_TYPE16B):
                tile.Type = self._stream.readUInt16()
            else:
                tile.Type = self._stream.readUInt8();
            if self._header.ImportantTiles[tile.Type]:
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
        if header2 > 0:
            if test_bit(header2, BIT_REDWI):
                tile.WireRed = True
            if test_bit(header2, BIT_GREENWI):
                tile.WireGreen = True
            if test_bit(header2, BIT_BLUEWI):
                tile.WireBlue = True
            tile.BrickStyle = ((header2 & MASK_BSTYLE) >> 4) # bits[4:7] = 112

        # process header3
        if header3 > 0:
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
        else:
            rle = self._stream.readInt16()

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
        for i in range(totalChests):
            chests.append(self._LoadOneChest(itemsPerChest, overflowItems))
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
        return c

    def LoadAllSigns(self):
        self._ensure_offset(self._header.GetSignsPointer())
        signs = []
        totalSigns = self._stream.readInt16()
        verbose("Loading %d total signs", totalSigns)
        for i in range(totalSigns):
            text = self._stream.readString()
            self._debug("Sign text: %s" % (text,))
            x = self._stream.readInt32()
            y = self._stream.readInt32()
            verbose("Loaded sign (%d, %d): %s", x, y, text)
            self._debug("Offset: %d", self._pos())
            signs.append((x, y, text))
        self._signs = signs

    def LoadNPCs(self):
        self._ensure_offset(self._header.GetNPCsPointer())
        npcs = []
        mobs = []
        while self._stream.readBoolean():
            npc = {}
            npc['Name'] = self._stream.readString()
            npc['DisplayName'] = self._stream.readString()
            npc['Position'] = {}
            npc['Position']['X'] = self._stream.readSingle()
            npc['Position']['Y'] = self._stream.readSingle()
            npc['Homeless'] = self._stream.readBoolean()
            npc['Home'] = {}
            npc['Home']['X'] = self._stream.readInt32()
            npc['Home']['Y'] = self._stream.readInt32()
            npcs.append(npc)
        self._npcs = npcs
        if self._header.Version >= Version140:
            while self._stream.readBoolean():
                mob = {'Name': None, 'Position': {'X': -1, 'Y': -1}}
                mob['Name'] = self._stream.readString()
                mob['Position']['X'] = self._stream.readSingle()
                mob['Position']['Y'] = self._stream.readSingle()
                mobs.append(mob)
        self._mobs = mobs
        verbose("Loaded %d NPCs and %d mobs", len(self._npcs), len(self._mobs))

    def LoadTileEntities(self):
        self._ensure_offset(self._header.GetTileEntitiesPointer())
        tents = []
        count = self._stream.readInt32()
        for i in range(count):
            entity = {'Type': -1, 'ID': -1, 'Position': {'X': -1, 'Y': -1}}
            entity['Type'] = self._stream.readByte()
            entity['Id'] = self._stream.readInt32()
            entity['Position']['X'] = self._stream.readInt16()
            entity['Position']['Y'] = self._stream.readInt16()
            if entity['Type'] == 0: # dummy
                entity['NPC'] = self._stream.readInt16()
            elif entity['Type'] == 1:   # item frame
                entity['ItemNetID'] = self._stream.readInt16()
                entity['Prefix'] = self._stream.readByte()
                entity['Stack'] = self._stream.readInt16()
            tents.append(entity)
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
        for y in xrange(self.GetHeaderFlag('TilesHigh')):
            for x in xrange(self.GetHeaderFlag('TilesWide')):
                yield y, x, self.GetTile(x, y)

    def GetTile(self, i, j):
        return self._tiles[self._PosToIdx(i, j)]

    def GetHeaderFlags(self):
        flags = []
        for flag, _, _ in WorldFlags.Flags:
            flags.append((flag, self._flags.getFlag(flag)))
        return tuple(flags)

    def GetHeaderFlag(self, flag):
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

