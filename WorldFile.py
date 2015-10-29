#!/usr/bin/env python

import argparse
import os
import sys

import Match

import IDs
import World

"""
Copy/paste for the python interactive interpreter:
if True:
    World = reload(World)
    w = World.World()
    w.Load(open("/home/kaedenn/.local/share/Terraria/Worlds/World_1.wld"))
"""

def _make_token_from(title):
    r = ''
    for ch in title:
        if ch.isalnum():
            r += ch
        else:
            r += '_'
    return r

def _find_world(worldname):
    path_lin = os.path.expanduser("~/.local/share/Terraria/Worlds")
    if os.path.exists(path_lin):
        world = os.path.join(path_lin, worldname + ".wld")
        if not os.path.exists(world):
            raise RuntimeError("%s not a valid path" % (world,))
        return world
    else:
        raise RuntimeError("Terraria world folder not found")

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
Use --help-match for help on the find argument.
""", formatter_class=argparse.RawTextHelpFormatter)
    
    HELP_TABLE = """
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
"""

    HELP_FIND = """
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
    p.add_argument("path",
                   help="a world file path, world name, or world file name")
    p.add_argument("-w", "--world", default=None,
                   help="file name of world to load")
    p.add_argument("--headers", action="store_true",
                   help="display the world header flags")
    p.add_argument("--kills", action="store_true",
                   help="display mob/banner kill counts")
    p.add_argument("--less-than-50", action="store_true",
                   help="display only mob/banner kill counts less than 50")
    p.add_argument("--sort-kills", choices=("banner", "count", "id", "mob"),
                   default=None,
                   help="sort kill counts by either banner id, kill count,"
                        " mob ID, or mob name")
    p.add_argument("--counts", action="store_true",
                   help="display tile counts")
    p.add_argument("--gem-counts", action="store_true",
                   help="display gem tile counts")
    p.add_argument("--tile-table", action="store_true",
                   help="print a complete tile table (redirect to a file!)")
    p.add_argument("--tile-table-ids", action="store_true",
                   help="only print tile IDs when writing the tile table")
    p.add_argument("--tile-table-uv", action="store_true",
                   help="print tile ID and frame coordinates (U,V)")
    p.add_argument("--tile-table-expr", action="store_true",
                   help="suppress assignment expr in the tile table")
    p.add_argument("--ignore-tiles", action="store_true",
                   help="do not load tile data")
    p.add_argument("-t", action="store_true",
                   help="format kill counts as a table")
    p.add_argument("--find", action="append",
                   help="print locations of t or t,u,v")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="be more verbose")
    p.add_argument("-d", "--debug", action="store_true",
                   help="be extremely verbose")
    p.add_argument("--help-table", action="store_true",
                   help="display help on the tile table arguments")
    p.add_argument("--help-find", action="store_true",
                   help="display help on the find argument")
    args = p.parse_args()

    if args.tile_table_ids or args.tile_table_uv and not args.tile_table:
        args.tile_table = True

    if args.ignore_tiles and args.tile_table:
        p.error("--ignore-tiles and --tile-table are mutually exclusive")

    if args.verbose or args.debug:
        global VERBOSE_MODE
        VERBOSE_MODE = True
        World.VERBOSE_MODE = True

    path = args.path
    if not os.path.exists(path):
        path = World.World.FindWorld(args.path)

    w = World.World(load_tiles=(not args.ignore_tiles),
                    verbose=args.verbose, debug=args.debug)
    w.Load(open(path, 'r'))

    if args.headers:
        h = w.GetHeaderFlags()
        for k,v in h:
            print("%s = %s" % (k, v))

    if args.kills:
        fmt = "%d %d %s"
        if args.t:
            print("%-5s %4s %s" % ("Kills", "ID", "Name"))
            fmt = "%5d %4d %s"
        results = []
        for bannerid, killcount in enumerate(w.GetHeaderFlag("KilledMobs")):
            if args.less_than_50 and killcount >= 50:
                continue
            if bannerid < len(IDs.BannerToNPC):
                npc = IDs.BannerToNPC[bannerid]
                if npc in IDs.NPCID:
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
        counts = w.CountTiles()
        types = sorted(counts.keys())
        for t in types:
            print("%-6d %d %s" % (counts[t], t, IDs.TileID[t]))

    if args.gem_counts:
        results = []
        for row in range(w.GetHeaderFlag("TilesHigh")):
            for col in range(w.GetHeaderFlag("TilesWide")):
                tile = w.GetTile(col, row)
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
        exprs = list([Match.parse_match(m) for m in args.find])
        for row, col, tile in w.EachTile():
            for expr in exprs:
                if Match.do_match(expr, tile.Type, tile.U, tile.V):
                    print("%s (%d, %d)" % (_tile_to_string(tile), col, row))

    if args.tile_table:
        if args.tile_table_expr:
            print('[')
        else:
            print("TILES_%s = [" % (_make_token_from(w.GetHeaderFlag("Title")),))
        for row in range(w.GetHeaderFlag("TilesHigh")):
            tileRow = []
            for col in range(w.GetHeaderFlag("TilesWide")):
                tile = w.GetTile(col, row)
                if args.tile_table_ids:
                    tileRow.append(tile.ToSimpleType())
                elif args.tile_table_uv:
                    tileRow.append((tile.Type, tile.U, tile.V))
                else:
                    tileRow.append(tile.ToSimpleID())
            print("    %s," % (tileRow,))
        print("]")

if __name__ == "__main__":
    _main()

