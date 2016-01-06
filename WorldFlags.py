#!/usr/bin/env python

import Header
from Header import CompatibleVersion, Version147, Version140, Version104, \
                   Version101, Version99, Version95
import BinaryString

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
        self._version = version
        self.Title = ''      # ILString
        for flag, type, ver in WorldFlags.Flags:
            value = 0 if type is not None else []
            setattr(self, flag, value)

    def set(self, flag, value):
        setattr(self, flag, value)

    def get(self, flag):
        return getattr(self, flag)

