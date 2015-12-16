#!/usr/bin/env python

import argparse
import csv
import os
import sys

import Match

import Header
import IDs
import World
import MapFile

try:
    import PIL.Image
    HAVE_PIL = True
    PIL_ERROR = None
except ImportError as e:
    HAVE_PIL = False
    PIL_ERROR = e

"""
Copy/paste for the python interactive interpreter:
if True:
    World = reload(World)
    w = World.World()
    w.Load(open("/home/kaedenn/.local/share/Terraria/Worlds/World_1.wld"))

Tiles are accessible if they're between x=40 and x=8357
"""

def _box(x, y, w, h):
    return [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]

def _box2(x1, x2, y1, y2):
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

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

def _generate_polygons(world):
    """
    Generating world polygons (accurately!) is hard.

    0) The origin of the map (0,0) is at the upper left corner.
    1) The world has a border 40 tiles wide on all four edges. These tiles
       are inaccessible without mods.
       1.5) The outermost 10 tiles of the border seem to be especially
            off-limits
    2) World width and height are measured in tiles, as integers:
       world.Width()
       world.Height()
    3) The effective reachable tiles are:
       40 <= Player.X <= world.Width() - 40
       40 <= Player.Y + Player.Height <= world.Height() - 40
    4) The border between "Surface" and "Space" is defined as the following
       being >= 1.0 for Surface and < 1.0 for Space
        num5 = World.TilesWide / 4200
        num6 = num5 * num5
          (Player.Y - (65.0 + 10.0 * num6)) / (WorldSurface / 5.0)

          (Y - (65 + 10 * (Width / 4200)**2)) / (Surface / 5) == 0
          Y - (65 + 10 * (Width / 4200) ** 2) == Surface / 5
          Y = Surface / 5 + 65 + 10 * (Width / 4200)**2
          Y = S / 5 + (Width**2) / 1764000 + 65
    """
    b = 40  # border tiles
    w, h = world.Width(), world.Height()
    top, left, bottom, right = b, b, h-b, w-b
    surf = world.GetWorldFlag('GroundLevel')
    rock = world.GetWorldFlag('RockLevel')
    space = surf / 5 + (w**2) / 1764000 + 65
    caves = rock + (1080 / 2) / 16 + 3
    hell = h-204
    dungeon = world.GetWorldFlag('DungeonX'), world.GetWorldFlag('DungeonY')

    World.verbose('Width: %d', w)
    World.verbose('Height: %d', h)
    World.verbose('Surface: %d', surf)
    World.verbose('Rock: %d', rock)
    World.verbose('Dungeon: %s', dungeon)
    World.verbose('Accessible tiles wide: %d', right-left)
    World.verbose('Accessible tiles high: %d', bottom-top)
    World.verbose('Guess for surface/space height: %s', space)
    #World.verbose('Guess for underworld: %d', y-200)
    #World.verbose('Guess for water/lava: %d', y/2 + (rock-surf-200))
    #World.verbose('Guess for something: %d', surf+(y/5))
    # Underworld:
    #   Player.Y > (World.Height - 204)
    # Caverns:
    #   Player.Y > Main.RockLayer + (1080 / 2) / 16 + 1
    # Underground:
    #   (Player.Y + Player.Height * 2) - World.Surface * 2 > 0
    polys = []
    polys.append(("+xmin", 0))
    polys.append(("+xmax", w))
    polys.append(("+ymin", 0))
    polys.append(("+ymax", h))
    polys.append(("+name", world.GetWorldFlag("Title")))
    polys.append(('World', _box2(left, right, top, bottom)))
    polys.append(('Surface', _box2(left, right, top, surf)))
    polys.append(('Rock', _box2(left, right, surf, rock)))
    polys.append(('Caves', _box2(left, right, rock, bottom)))
    polys.append(('Caverns', _box2(left, right, caves, h-204)))
    polys.append(('Hell', _box2(left, right, h-204, bottom)))
    polys.append(('Space', _box2(left, right, surf, space)))
    polys.append(('Jungle', _box2(b, b, b, b))) # FIXME
    polys.append(('Temple', _box2(b, b, b, b))) # FIXME
    polys.append(('Water', _box2(b, b, b, b)))  # FIXME
    polys.append(('Lava', _box2(b, b, b, b)))   # FIXME
    polys.append(('OceanL', _box2(b, b, b, b))) # FIXME
    polys.append(('OceanR', _box2(b, b, b, b))) # FIXME
    polys.append(('OOB_L', _box2(0, b, 0, h)))
    polys.append(('OOB_T', _box2(0, w, 0, b)))
    polys.append(('OOB_R', _box2(right, w, 0, h)))
    polys.append(('OOB_B', _box2(0, w, bottom, h)))
    return polys

def _get_levels(world):
    w, h = world.Width(), world.Height()
    surf = world.GetWorldFlag('GroundLevel')
    rock = world.GetWorldFlag('RockLevel')
    space = surf / 5 + (w**2) / 1764000 + 65
    caves = rock + (1080 / 2) / 16 + 3
    hell = h-204
    return space, caves, hell

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

The --format option takes a Python "new-style" format string of the form
"%(Tile)s %(Name)s %(U)s %(V)s"
which will result in the tiles being displayed according to that format.

The valid format keywords (see Tile.Tile.SerializedLookup) are:
    IsActive    (boolean) whether or not a tile is present
    Tile        tile's numeric id (use x for hex format)
    Name        tile's name according to IDs.py
    Wall        the tile's wall as a numeric id
    WallName    name of the tile's wall according to IDs.py
    TileColor   the tile's (packed) painted color
    WallColor   the wall's (packed) painted color
    WireRed     (boolean) whether or not the tile has a red wire
    WireGreen   (boolean) whether or not the tile has a green wire
    WireBlue    (boolean) whether or not the tile has a blue wire
    LiquidType  what kind of liquid is present (none, water, lava, honey)
    LiquidAmount    how much liquid is present (0-255)
    BrickStyle  the tile's slope style
    Actuator    whether or not an actuator is present
    InActive    whether or not the tile is inactive due to an actuator
    U           tile's FrameX value
    V           tile's FrameY value

All of the format keys except Name are numeric. Name is a string.
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

To format the results as "Tile Name U V":
    --find Silt,Slush --format "%(Tile)s %(Name)s %(U)s %(V)s"
"""
    p.add_argument("path", nargs='?', default=None,
                   help="a world file path, file name, or world name")
    p.add_argument("-l", "--list", action="store_true",
                   help="list all worlds")
    p.add_argument("-T", "--ignore-tiles", action="store_true",
                   help="don't load tile data")
    p.add_argument("-C", "--ignore-chests", action="store_true",
                   help="don't load chests")
    p.add_argument("-S", "--ignore-signs", action="store_true",
                   help="don't load signs")
    p.add_argument("--csv", action="store_true",
                   help="where possible, output in csv")
    p.add_argument("-o", "--out", type=str, default=None, metavar="PATH",
                   help="output results here (in CSV format if --csv)")
    p.add_argument("-a", "--append", action="store_true",
                   help="open PATH arg to --out for appending")
    p.add_argument("-p", "--progress", action="store_true",
                   help="display world loading progress")
    p.add_argument("--allow-writing", action="store_true",
                   help="allow modifying the tiles (makes loading very slow)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="be more verbose")
    p.add_argument("-d", "--debug", action="store_true",
                   help="be extremely verbose")

    o = p.add_argument_group("Examining Properties")
    o.add_argument("--pointers", action="store_true",
                   help="display file offset pointers")
    o.add_argument("--flags", action="store_true",
                   help="display the world flags")
    o.add_argument("--kills", action="store_true",
                   help="display mob/banner kill counts")
    o.add_argument("--less-than-50", action="store_true",
                   help="display only mob/banner kills less than 50")
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
    o.add_argument("--poly", action="store_true",
                   help="print some polygon regions")

    f = p.add_argument_group("The Find Argument")
    f.add_argument("--find", action="append", metavar="EXPR",
                   help="print locations of tiles (see --help-find)")
    f.add_argument("--find-examples", action="store_true",
                   help="display various useful arguments to --find")
    f.add_argument("--format", type=str, default=None, metavar="FMT",
                   help="use FMT for printing tiles")
    f.add_argument("--reachable", action="store_true",
                   help="only match reachable tiles")
    f.add_argument("--detailed-csv", action="store_true",
                   help="produce a CSV suited for processing in R (overrides "
                        "--format)")
    f.add_argument("--density", action="store_true",
                   help="output a file suitable for density analysis")
    f.add_argument("--help-find", action="store_true",
                   help="display help on the find argument and exit")

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
                   help="display help on the tile table arguments and exit")

    i = p.add_argument_group("Image Arguments")
    i.add_argument("--png", action="store_true",
                   help="generate a minimap-style PNG (use --out)")
    i.add_argument("--no-tiles", action="store_true",
                   help="do not output tiles; assume all tiles are inactive")
    i.add_argument("--no-walls", action="store_true",
                   help="do not output walls; completely ignore them")
    i.add_argument("--no-liquid", action="store_true",
                   help="make all liquids transparent")
    i.add_argument("--no-bg", action="store_true",
                   help="make inactive tiles without walls transparent")
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

    if args.find:
        # pre-verify all the find patterns are valid
        for m in args.find:
            Match.Match(m, names=IDs.Tiles)

    tile2str = lambda t: _tile_to_string(t)
    if args.format:
        tile2str = lambda t: t.Format(args.format)

    out = sys.stdout
    if args.out is not None:
        out = open(args.out, 'w' if not args.append else 'a')

    # redundant because World.__init__ args do the same thing
    World.G.VERBOSE_MODE = args.verbose or args.debug
    World.G.DEBUG_MODE = args.debug

    world_args = dict(read_only=(not args.allow_writing),
                      load_tiles=(not args.ignore_tiles),
                      load_chests=(not args.ignore_chests),
                      load_signs=(not args.ignore_signs),
                      load_npcs=True,
                      load_tents=True,
                      progress=args.progress,
                      verbose=args.verbose,
                      debug=args.debug)

    w = World.World(**world_args)

    if args.list:
        worlds = World.World.ListWorlds()
        for _, wld, fp in worlds:
            wn = wld.GetWorldFlag('Title')
            wid = wld.GetWorldFlag('WorldId')
            print("World %s: ID %d, Path: %s" % (wn, wid, fp))

    if args.path is None:
        World.verbose("Nothing to do; exiting")
        raise SystemExit(0)

    path = args.path
    if not os.path.exists(path):
        if path.isdigit():
            path = World.World.FindWorld(worldid=int(path))
        else:
            path = World.World.FindWorld(worldname=args.path)

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
        rows = [
            ["Section", "Offset", "Size (bytes)"],
            ["Flags", flags, tiles-flags],
            ["Tiles", tiles, chests-tiles],
            ["Chests", chests, signs-chests],
            ["Signs", signs, npcs-signs],
            ["NPCs", npcs, npcs_size]
        ]
        if h.Version >= Header.Version140:
            rows.append(["Tile Entities", tents, footer-tents])
        rows.append(["Footer", footer, h.FileSize-footer])
        if args.csv:
            csv.writer(sys.stdout).writerows(rows)
        else:
            fmt = "%s: %d (%d bytes)"
            if args.t:
                print("%-13s %8s %s" % ("Section", "Offset", "Size (bytes)"))
                fmt = "%-13s %8d %8d"
            for row in rows[1:]:
                print(fmt % tuple(row))

    if args.flags:
        h = w.GetWorldFlags()
        fmt = "%s = %s"
        fmt_ore = "%s = %d %s"
        if args.csv:
            wr = csv.writer(sys.stdout)
            wr.writerow(["Flag", 'Value'])
            for k,v in h:
                if k.startswith('OreTier'):
                    wr.writerow([k, "%d %s" % (v, IDs.TileID[int(v)])])
                else:
                    wr.writerow([k, v])
        else:
            if args.t:
                key_width = max([len(i) for i,_ in h])
                fmt = "%%-%ds %%s" % (key_width,)
                fmt_ore = "%%-%ds %%d %%s" % (key_width,)
            for k,v in h:
                if k.startswith('OreTier'):
                    print(fmt_ore % (k, v, IDs.TileID[int(v)]))
                else:
                    print(fmt % (k, v))

    if args.kills:
        fmt = "%d %d %s"
        if args.t and not args.csv:
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
        if args.csv:
            rows = [["Kills", "ID", "Name"]] + results
            csv.writer(sys.stdout).writerows(rows)
        else:
            for result in results:
                print(fmt % result)

    if args.counts:
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks --counts")
        counts = w.CountTiles()
        types = sorted(counts.keys())
        if args.csv:
            rows = [["Tile", "Tile Name", "Count"]]
            rows = rows + [[t, IDs.TileID[t], counts[t]] for t in types]
            csv.writer(sys.stdout).writerows(rows)
        else:
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

    if args.density:
        outcsv = csv.writer(out)
        # The -1 is to omit the "Count" entry at the end
        header = [IDs.TileID[k] for k in sorted(IDs.TileID)][:-1]
        outcsv.writerow(header)
        for row in xrange(w.Height()):
            counts = [0]*len(header)
            for tile in w[row,...]:
                if tile.IsActive:
                    counts[tile.Type] += 1
            outcsv.writerow(counts)

    if args.find:
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks --find")
        terms = list([Match.Match(m, IDs.Tiles) for m in args.find])
        matches = []
        for row, col, tile in w.EachTile(unreachable=not args.reachable,
                                         progress="Searching..."):
            for term in terms:
                if term.match(tile.Type, tile.U, tile.V, tile.Wall):
                    matches.append((tile, col, row))
                    break
        if args.csv:
            colors = list(csv.reader(open("MapTile_Colors.csv")))[1:]
            colorlist = [[int(i) for i in c] for c in colors]
            colordict = dict((tuple(d[0:2]), d[2:]) for d in colorlist)
            writer = csv.writer(out)
            
            if args.detailed_csv:
                writer.writerow(['Attribute', 'Value', 'Tile', 'Name', 'Red',
                                 'Green', 'Blue', 'x', 'y'])
                space, caves, hell = _get_levels(w)
                rock = w.GetWorldFlag('RockLevel')
                writer.writerow(['Surface', w.GetWorldFlag('GroundLevel'), -1,
                                 '', 0, 0, 0, 0, 0])
                writer.writerow(['Rock', w.GetWorldFlag('RockLevel'), -1,
                                 '', 0, 0, 0, 0, 0])
                writer.writerow(['Space', space, -1, '', 0, 0, 0, 0, 0])
                writer.writerow(['Caves', caves, -1, '', 0, 0, 0, 0, 0])
                writer.writerow(['Hell', hell, -1, '', 0, 0, 0, 0, 0])
                writer.writerow(['Lava', int((rock+hell)/2)+3, -1, '',
                                 0, 0, 0, 0, 0])
                for t, c, r in matches:
                    color = colordict[(t.Type, 0)]
                    writer.writerow(["", "", t.Type, t.Name, color[0],
                                     color[1], color[2], c, r])
            else:
                writer.writerow(['Tile', 'x', 'y'])
                for t, c, r in matches:
                    writer.writerow([tile2str(t), c, r])
        else:
            header = "Tile (x, y)\n"
            entry = "%s (%d, %d)\n"
            out.write(header)
            for t, c, r in matches:
                out.write(entry % (tile2str(t), c, r))

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
                elif args.format:
                    tileRow.append(tile.Format(args.format))
                else:
                    tileRow.append(tile.ToSimpleID())
            print("    [%s]," % (", ".join(str(i) for i in tileRow),))
        print("]")

    if args.poly:
        for k,v in _generate_polygons(w):
            out.write("%-10s %s\n" % (k, v))

    if args.npcs:
        for npc in w.GetNPCs():
            print(npc)

    if args.tents:
        for tent in w.GetTileEntities():
            print(tent)

    if args.png:
        if not args.out:
            p.error("--png requires --out to be specified")
        if args.ignore_tiles:
            p.error("--ignore-tiles blocks --png argument")
        if not HAVE_PIL:
            p.error("Please install PIL before using --png: %s" % (PIL_ERROR,))
        m = MapFile.Map()
        m.FromWorld(w)
        img = PIL.Image.new('RGBA', (w.Width(), w.Height()))
        argsEachTile = {}
        argsTileToLookup = {}
        if args.progress:
            argsEachTile['progress'] = "Writing image..."
        for x, y, t in w.EachTile(rowcol=False, **argsEachTile):
            if args.no_tiles:
                argsTileToLookup['transparentTiles'] = True
            if args.no_walls:
                argsTileToLookup['transparentWalls'] = True
            if args.no_liquid:
                argsTileToLookup['transparentLiquid'] = True
            if args.no_bg:
                argsTileToLookup['transparentBg'] = True
            table, lookup, option = m.TileToLookup(t, x, y, **argsTileToLookup)
            if args.no_bg and table in (MapFile.Map.LOOKUP_SKY,
                                        MapFile.Map.LOOKUP_DIRT,
                                        MapFile.Map.LOOKUP_ROCK):
                continue
            color = m.DoColorLookup(table, lookup, option)
            if color is None:
                continue
            img.putpixel((x, y), color)
        img.save(args.out)

if __name__ == "__main__":
    _main()

