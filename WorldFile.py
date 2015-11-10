#!/usr/bin/env python

import argparse
import csv
import os
import sys

import Match

import Header
import IDs
import World

"""
Copy/paste for the python interactive interpreter:
if True:
    World = reload(World)
    w = World.World()
    w.Load(open("/home/kaedenn/.local/share/Terraria/Worlds/World_1.wld"))

Tiles are accessible if they're between x=40 and x=8357
"""

def _make_token_from(title):
    r = ''
    for ch in title:
        if ch.isalnum():
            r += ch
        else:
            r += '_'
    return r

def _tile_to_string(tile):
    fmt = "%d %s (u:%d, v:%d) %d %s" % (
            tile.Type, IDs.TileID[tile.Type], tile.U, tile.V,
            tile.Wall, IDs.WallID[tile.Wall])
    item = IDs.tile_to_item(tile.Type, tile.U, tile.V, noexcept=True)
    if item != IDs.INVALID:
        try:
            fmt += " %d %s" % (item, IDs.ItemID[item])
        except KeyError as e:
            print(fmt, item)
            raise
    return fmt

def _main():
    p = argparse.ArgumentParser(usage="%(prog)s [args] <path>", epilog = """
The <path> argument is first interpreted as a path to a world file, including
the .wld suffix, then the file name of a world file without the .wld suffix,
and then the title of a world as seen in-game.

Be forewarned: the tile table arguments generate a LOT of output, so you will
want to redirect them to a file. The result is valid Python script; variable
will be a 2D list named TILES_<worldname>. Importing the resulting script can
cause Python to segfault on large worlds.

Use --help-table for help on the tile table arguments.
Use --help-find for help on the find argument.
Use --find-examples for example values for the find argument.
""", formatter_class=argparse.RawTextHelpFormatter)
    
    HELP_TABLE = """Using the tile table arguments:

With just --tile-table, the output will be:
TILES_World_1 = [ # All non-alnum characters are converted to _
    [(ID, Wall), (ID, Wall), ...], # First row of tiles in World 1
    [(ID, Wall), (ID, Wall), ...], # Second row of tiles in World 1
    ...
]

If --tile-table-ids is present, (ID, Wall) will be replaced with ID:
TILES_World_1 = [
    [ID, ID, ...],
    [ID, ID, ...],
    ...
]

If --tile-table-uv is present, each entry will contain U, V values:
TILES_World_1 = [
    [(ID, U, V), (ID, U, V), ...],
    [(ID, U, V), (ID, U, V), ...],
    ...
]

If --tile-table-expr is present, the output will be just an expression:
[
    [(ID, Wall), (ID, Wall), ...],
    [(ID, Wall), (ID, Wall), ...],
    ...
]

If --tile-table-packed is present, each tile will be a packed 64-bit integer:
Bit     0 1 2 3 4 5 6 7 8 9 a b c d e f 0 1 2 3 4 5 6 7 8 9 a b c d e f
Content <- tile type -----------------> <- tile u -------------------->
Bit     0 1 2 3 4 5 6 7 8 9 a b c d e f 0 1 2 3 4 5 6 7 8 9 a b c d e f
Content <- tile v --------------------> <- wall ------> <- flags ----->
"""

    HELP_FIND = """Using the find argument:

The value passed via --find matches a set of numbers. The --find argument can
be passed as many times as desired. The syntax is akin to the following
grammar:

// First TermItem matches tile.Type, second tile.U, third tile.V
Expr := TermItem (';' TermItem (';' TermItem))

TermItem := TermSet
TermSet := TermRange (',' TermRange)*
TermRange := Number ('-' Number)
Number := HexNumber | DecNumber | "None" | ""
HexNumber = <number in hexadecimal notation>
DecNumber = <number in decimal notation>

Using "None" or the empty string for Number matches any value

For example,
"1" finds all tiles with Type == 1
"1;2;3" finds all tiles with Type == 1, U == 2, V == 3
"1-3;4" finds all tiles with Type in (1, 2, 3) and U == 4
"1,3;5" finds all tiles with Type in (1, 3) and U == 5
"1,3,5-9;10" finds all tiles with Type in (1, 3, 5, 6, 7, 8, 9, 10) and U == 10
"1,3,5-9;2,4,6-10;3,5,8-10" finds all tiles with Type in (1, 3, 5, 6, 7, 8, 9),
    U in (2, 4, 6, 7, 8, 9, 10), and V in (3, 5, 8, 9, 10)
"1;None;3" finds all tiles with Type == 1 and V == 3
"1;;3" also finds all tiles with Type == 1 and V == 3
"""

    FIND_EXAMPLES = """Useful values for the find argument:

To find all gem tiles:
    --find '63-68;178'
    --find 'Sapphire;Ruby;Emerald;Topaz;Amethyst;Diamond;ExposedGems'
    --find 'Sapphire-Diamond;ExposedGems'

To find all tiles of a given name:
    --find Silt
    --find Slush
    --find Adamantite
"""
    p.add_argument("path", nargs='?', default=None,
                   help="a world file path, file name, or world name")
    p.add_argument("-T", "--ignore-tiles", action="store_true",
                   help="don't load tile data")
    p.add_argument("-C", "--ignore-chests", action="store_true",
                   help="don't load chests")
    p.add_argument("-S", "--ignore-signs", action="store_true",
                   help="don't load signs")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="be more verbose")
    p.add_argument("-d", "--debug", action="store_true",
                   help="be extremely verbose")

    o = p.add_argument_group("Output Specification")
    o.add_argument("--pointers", action="store_true",
                   help="display file offset pointers")
    o.add_argument("--world-flags", action="store_true",
                   help="display the world flags")
    o.add_argument("--kills", action="store_true",
                   help="display mob/banner kill counts")
    o.add_argument("--less-than-50", action="store_true",
                   help="display only mob/banner kill counts less than 50")
    o.add_argument("--sort-kills", choices=("banner", "count", "id", "mob"),
                   default=None, help="sort kill counts by choice given")
    o.add_argument("--counts", action="store_true",
                   help="display tile counts")
    o.add_argument("--gem-counts", action="store_true",
                   help="display gem tile counts")
    o.add_argument("-t", action="store_true",
                   help="format numerical outputs as tables")
    o.add_argument("--npcs", action="store_true",
                   help="print all NPCs")
    o.add_argument("--tents", action="store_true",
                   help="print all tile entities")

    f = p.add_argument_group("Find Arguments")
    f.add_argument("--find", action="append", metavar="EXPR",
                   help="print locations of tiles (see --help-find)")
    f.add_argument("--find-examples", action="store_true",
                   help="display various useful arguments to --find")
    f.add_argument("-o", "--out", type=str, default=None, metavar="PATH",
                   help="write the find results to this file")
    f.add_argument("--out-csv", action="store_true",
                   help="write the find results in CSV format")
    f.add_argument("--density", action="store_true",
                   help="output a file suitable for density analysis")
    f.add_argument("--help-find", action="store_true",
                   help="display help on the find argument")

    t = p.add_argument_group("Tile Table Arguments")
    t.add_argument("--tile-table", action="store_true",
                   help="print a complete tile table (redirect to a file!)")
    t.add_argument("--tile-table-ids", action="store_true",
                   help="only print tile IDs when writing the tile table")
    t.add_argument("--tile-table-uv", action="store_true",
                   help="print tile ID and frame coordinates (U,V)")
    t.add_argument("--tile-table-expr", action="store_true",
                   help="suppress assignment expr in the tile table")
    t.add_argument("--tile-table-packed", action="store_true",
                   help="output tiles as a packed 64bit integer")
    t.add_argument("--help-table", action="store_true",
                   help="display help on the tile table arguments")
    args = p.parse_args()

    if args.help_table or args.help_find:
        if args.help_table:
            print(HELP_TABLE)
        if args.help_find:
            print(HELP_FIND)
        raise SystemExit(0)

    if args.find_examples:
        print(FIND_EXAMPLES)

    if any((args.tile_table_ids, args.tile_table_uv, args.tile_table_expr,
            args.tile_table_packed)) and not args.tile_table:
        args.tile_table = True

    if args.ignore_tiles and args.tile_table:
        p.error("--ignore-tiles and --tile-table are mutually exclusive")

    World.VERBOSE_MODE = args.verbose or args.debug
    World.DEBUG_MODE = args.debug

    w = World.World(load_tiles=(not args.ignore_tiles),
                    load_chests=(not args.ignore_chests),
                    load_signs=(not args.ignore_signs),
                    verbose=args.verbose, debug=args.debug)

    if args.path is None:
        World.verbose("Nothing to do; exiting")
        raise SystemExit(0)

    path = args.path
    if not os.path.exists(path):
        path = World.World.FindWorld(args.path)

    w.Load(open(path, 'r'))

    if args.pointers:
        h = w.GetHeader()
        flags = h.GetFlagsPointer()
        tiles = h.GetTilesPointer()
        chests = h.GetChestsPointer()
        signs = h.GetSignsPointer()
        npcs = h.GetNPCsPointer()
        tents = h.GetTileEntitiesPointer()
        footer = h.GetFooterPointer()
        npcs_size = tents - npcs
        if h.Version < Header.Version140:
            npcs_size = footer - npcs
        fmt = "%s: %d (%d bytes)"
        if args.t:
            print("%-13s %8s %s" % ("Section", "Offset", "Size (bytes)"))
            fmt = "%-13s %8d %8d"
        print(fmt % ("Flags", flags, tiles-flags))
        print(fmt % ("Tiles", tiles, chests-tiles))
        print(fmt % ("Chests", chests, signs-chests))
        print(fmt % ("Signs", signs, npcs-signs))
        print(fmt % ("NPCs", npcs, npcs_size))
        if h.Version >= Header.Version140:
            print(fmt % ("Tile Entities", tents, footer-tents))
        print(fmt % ("Footer", footer, h.FileSize-footer))

    if args.world_flags:
        h = w.GetWorldFlags()
        for k,v in h:
            if k.startswith('OreTier'):
                print("%s = %d %s" % (k, v, IDs.TileID[int(v)]))
            else:
                print("%s = %s" % (k, v))

    if args.kills:
        fmt = "%d %d %s"
        if args.t:
            print("%-5s %4s %s" % ("Kills", "ID", "Name"))
            fmt = "%5d %4d %s"
        results = []
        for bannerid, killcount in enumerate(w.GetWorldFlag("KilledMobs")):
            if args.less_than_50 and killcount >= 50:
                continue
            if bannerid < len(IDs.BannerToNPC):
                npc = IDs.BannerToNPC[bannerid]
                if npc in IDs.NPCID and npc != 0:
                    results.append((killcount, npc, IDs.NPCID[npc]))
                elif npc != 0:
                    results.append((killcount, npc, "<id-not-enumerated>"))
        if args.sort_kills == "count":
            results.sort(key=lambda v: v[0])
        elif args.sort_kills == "id":
            results.sort(key=lambda v: v[1])
        elif args.sort_kills == "mob":
            results.sort(key=lambda v: v[2])
        for result in results:
            print(fmt % result)

    if args.counts:
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks --counts")
        counts = w.CountTiles()
        types = sorted(counts.keys())
        for t in types:
            print("%-6d %d %s" % (counts[t], t, IDs.TileID[t]))

    if args.gem_counts:
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks --gem-counts")
        results = []
        for row, col, tile in w.EachTile():
            if IDs.Tiles['Sapphire'] <= tile.Type <= IDs.Tiles['Diamond']:
                results.append((tile.Type, None))
            elif tile.Type == IDs.Tiles['SmallPiles']:
                item = IDs.tile_to_item(tile.Type, tile.U, tile.V)
                if item != IDs.INVALID:
                    results.append((tile.Type, item))
        counts = {}
        for t, i in results:
            if (t, i) not in counts:
                counts[(t, i)] = 0
            counts[(t, i)] += 1
        for ti in sorted(counts):
            t, i = ti
            c = counts[ti]
            tname = IDs.TileID[t]
            iname = IDs.ItemID[i] if i is not None else 0
            if i is None:
                print("%d %d %s" % (c, t, tname))
            else:
                print("%d %d %s %d %s" % (c, t, tname, i, iname))

    if args.find:
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks --find")
        # TODO: provide configuration to specify EXACTLY the format of
        # the tile string (perhaps a custom printf-like syntax? or
        # something like that?)
        # TODO: incorporate density analysis (input: window size)
        terms = list([Match.Match(m, IDs.Tiles) for m in args.find])
        matches = []
        for row, col, tile in w.EachTile():
            for term in terms:
                if term.match(tile.Type, tile.U, tile.V):
                    matches.append((tile, col, row))
        out = sys.stdout
        if args.out is not None:
            out = open(args.out, 'w')
        if args.density:
            width = w.GetWorldFlag('TilesWide')
            height = w.GetWorldFlag('TilesHigh')
            m = [[0]*(width) for _ in xrange(height)]
            for t, c, r in matches:
                m[r][c] += 1
            writer = csv.writer(out)
            writer.writerows(m)
        else:
            header = "Tile,X,Y\n" if args.out_csv else "Tile (x, y)\n"
            entry = '"%s",%d,%d\n' if args.out_csv else "%s (%d, %d)\n"
            out.write(header)
            for t, c, r in matches:
                out.write(entry % (_tile_to_string(t), c, r))

    if args.tile_table:
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks tile table arguments")
        var = "TILES_%s = [" % (_make_token_from(w.GetWorldFlag("Title")),)
        if args.tile_table_expr:
            var = "["
        print(var)
        for row in range(w.GetWorldFlag("TilesHigh")):
            # w.EachTile() won't work here because of how this is laid out
            tileRow = []
            for col in range(w.GetWorldFlag("TilesWide")):
                tile = w.GetTile(col, row)
                if args.tile_table_ids:
                    tileRow.append(tile.ToSimpleType())
                elif args.tile_table_uv:
                    tileRow.append((tile.Type, tile.U, tile.V))
                elif args.tile_table_packed:
                    tileRow.append(tile.ToPackedInt64())
                else:
                    tileRow.append(tile.ToSimpleID())
            print("    [%s]," % (", ".join(str(i) for i in tileRow),))
        print("]")

    if args.npcs:
        for npc in w.GetNPCs():
            print(npc)

    if args.tents:
        for tent in w.GetTileEntities():
            print(tent)

if __name__ == "__main__":
    _main()

