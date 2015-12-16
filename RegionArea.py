#!/usr/bin/env python

import ast
import argparse
import csv
import os
import sys
import time
from shapely.geometry import Point, Polygon, MultiPolygon

import IDs

G = {'VERBOSE': False}

def verbose(message, *args):
    if G['VERBOSE']:
        if args:
            sys.stderr.write(message % args)
        else:
            sys.stderr.write(message)
        sys.stderr.write("\n")

class NamedMultiPolygon(MultiPolygon):
    def __init__(self, name, points, *args, **kwargs):
        super(NamedMultiPolygon, self).__init__(points, *args, **kwargs)
        self._name = name
    def name(self):
        return self._name
    def union(self, other):
        result = super(NamedMultiPolygon, self).union(other)
        return NamedMultiPolygon(self._name, [result])
    def intersection(self, other):
        result = super(NamedMultiPolygon, self).intersection(other)
        return NamedMultiPolygon(self._name, [result])
    def difference(self, other):
        result = super(NamedMultiPolygon, self).difference(other)
        return NamedMultiPolygon(self._name, [result])
    def symmetric_difference(self, other):
        result = super(NamedMultiPolygon, self).symmetric_difference(other)
        return NamedMultiPolygon(self._name, [result])

class WorldPolySet(object):
    def __init__(self, name="World", noexcept=False):
        self._polys = []
        self._poly_lookup = {}
        self._noexcept = noexcept
        self._tok_special = (
            '+xmin', '+xmax', '+ymin', '+ymax', '+name', '+color'
        )
        self._tok_operator = (
            'UNION', 'INTERSECTION', 'DIFFERENCE', 'SYMMETRIC_DIFFERENCE'
        )
        self._name = "World"
        self._colors = {}
        self._xmin = 0
        self._xmax = 0
        self._ymin = 0
        self._ymax = 0

    def _raise(self, exception):
        if not self._noexcept:
            raise exception
        # all calling functions return False on error with noexcept set
        return False

    def coalesce(self):
        if len(self._polys) == 0:
            return None
        result = self._polys[0]
        for poly in self._polys[1:]:
            result = result.union(poly)
        return result

    def _update_lims(self, namedpoly):
        minx, miny, maxx, maxy = namedpoly.bounds
        self._xmin = min(self._xmin, minx)
        self._xmax = max(self._xmax, maxx)
        self._ymin = min(self._ymin, miny)
        self._ymax = max(self._ymax, maxy)

    def _parse_special(self, op, val):
        if op == '+xmin':
            self._xmin = int(val)
        elif op == '+xmax':
            self._xmax = int(val)
        elif op == '+ymin':
            self._ymin = int(val)
        elif op == '+ymax':
            self._ymax = int(val)
        elif op == '+color':
            world, color = val.split(None, 1)
            self._colors[world] = color
        elif op == '+name':
            self._name = val
        return True

    def _do_operator(self, result, op, name):
        if op == 'UNION':
            return result.union(self._poly_lookup[name])
        if op == 'INTERSECTION':
            return result.intersection(self._poly_lookup[name])
        if op == 'DIFFERENCE':
            return result.difference(self._poly_lookup[name])
        if op == 'SYMMETRIC_DIFFERENCE':
            return result.symmetric_difference(self._poly_lookup[name])

    def _parse_operator(self, name, op, args):
        arglist = args.split()
        result = self._poly_lookup[arglist[0]]
        result = result.union(result)   # to make a copy of it
        result._name = name
        for arg in arglist[1:]:
            try:
                result = self._do_operator(result, op, arg)
            except KeyError as e:
                return self._raise(RuntimeError("World %s not found" % (arg,),
                                                e))
        self._poly_lookup[name] = result
        self._polys.append(result)
        self._update_lims(result)
        return True

    def parse_line(self, line):
        l = line.strip()
        if len(l) == 0 or l[0] == '#':
            return True
        if ' ' not in l:
            return self._raise(RuntimeError("Invalid line: %r" % (line,)))
        name, val = l.split(None, 1)
        if name in self._tok_special:
            return self._parse_special(name, val)
        if val.split(None, 1)[0] in self._tok_operator:
            op, args = val.split(None, 1)
            return self._parse_operator(name, op, args)
        poly = Polygon(ast.literal_eval(val))
        self._poly_lookup[name] = NamedMultiPolygon(name, [poly])
        self._polys.append(self._poly_lookup[name])
        self._update_lims(self._poly_lookup[name])
        return True

    def parse_lines(self, lines):
        return all(self.parse_line(l) for l in lines)

    def color(self, polyname, default=None):
        return self._colors.get(polyname, default)

    def polys(self):
        return tuple(self._polys)

    def name(self):
        return self._name

    def names(self):
        return tuple(p.name() for p in self._polys)

    def box(self):
        return (self._xmin, self._ymin), (self._xmax, self._ymax)

class FindFile(object):
    FMT_DEDUCE = 0
    FMT_FIND = 1
    FMT_CSV = 2

    def __init__(self, path=None, type=FMT_DEDUCE):
        # dict(TileID -> list((x, y), (x2, y2), ...)
        self._points = {}
        self._format = type
        self._colors = self._load_colors()
        if path is not None:
            self.Load(path=path)

    def Load(self, path=None, file=None, type=FMT_DEDUCE):
        fobj = None
        self._format = type
        if path is not None:
            fobj = open(path, 'r')
        elif file is not None:
            fobj = file
        else:
            raise ValueError("Nothing to load in FindFile.Load")
        reader = csv.reader(fobj)
        self._headers(next(reader))
        if self._format == FindFile.FMT_DEDUCE:
            raise ValueError("Unknown format for %s: %s" % (path, file))
        elif self._format == FindFile.FMT_FIND:
            return self._load_old(reader)
        elif self._format == FindFile.FMT_CSV:
            return self._load_csv(reader)
        else:
            raise ValueError("Invalid format type %s" % (type,))

    def Color(self, tid):
        if self._format != FindFile.FMT_CSV:
            return None
        return self._colors.get(tid, (0,0,0))

    def _load_colors(self):
        reader = csv.reader(open("MapTile_Colors.csv", "r"))
        next(reader) # discard headers
        colors = {}
        for line in reader:
            colors[int(line[0])] = line[2:]
        verbose("loaded %d colors", len(colors))
        return colors

    def _load_old(self, fobj):
        # tileid, x, y
        for line in csv.reader(fobj):
            if not line[1].isdigit() or not line[2].isdigit():
                continue
            self._add_point(line[0], float(line[1]), float(line[2]))

    def _load_csv(self, reader):
        for line in reader:
            if line[self._tidpos] == "-1":
                continue
            line2 = [int(i) if i.isdigit() else i for i in line]
            tid = line2[self._tidpos]
            x = line2[self._xpos]
            y = line2[self._ypos]
            self._add_point(tid, x, y)

    def _add_point(self, id, x, y):
        if id not in self._points:
            self._points[id] = []
        self._points[id].append(Point(x, y))

    def __iter__(self):
        return iter((v,k) for k in self._points for v in self._points[k])

    def _deduce_format(self, headers):
        if len(headers) == 3:
            return FindFile.FMT_FIND
        return FindFile.FMT_CSV

    def _headers(self, headers):
        verbose("parsing headers: %s", headers)
        if self._format == FindFile.FMT_DEDUCE:
            self._format = self._deduce_format(headers)
        self._tidpos = headers.index('Tile')
        self._xpos = headers.index('x')
        self._ypos = headers.index('y')

def do_search(polygons, points):
    results = {'+counts': {}}
    for point, ptname in points:
        for poly in polygons.polys():
            polname = poly.name()
            if polname not in results:
                results[polname] = []
                results['+counts'][polname] = {}
            if poly.contains(point):
                if ptname not in results['+counts'][polname]:
                    results['+counts'][polname][ptname] = 0
                results[polname].append((ptname, point))
                results['+counts'][polname][ptname] += 1
    return results

def draw_r(regions, points, **kwargs):
    # initialize the environment
    from rpy2.interactive import process_revents
    from rpy2.robjects import r
    from rpy2.robjects.packages import importr
    NA = r("NA")[0]
    RGB = lambda rgb: r.rgb(*rgb, maxColorValue=256)
    C = lambda seq: r.c(*seq)
    OOB = 40
    graphics = importr("graphics")
    grDevices = importr("grDevices")
    process_revents.start()
    graphics.par(bg="white")
    graphics.split_screen(r.c(2, 1))
    graphics.split_screen(r.c(1, 2), screen=2)
    graphics.screen(1)
    # prepare the regions for plotting
    ul, lr = regions.box()
    xlim = r.c(ul[0], lr[0])
    ylim = r.c(lr[1], ul[1])
    # create the main plot window
    graphics.plot(r.c(), r.c(), main=regions.name(), type="p", pch="+",
            xlim=xlim, ylim=ylim, xlab="", ylab="",
            xaxp=r.c(0, lr[0], lr[0]/200), yaxp=r.c(0, lr[1], lr[1]/200),
            bg="white")
    # plot the polygons in the order given
    order = sorted(regions.polys(), key=lambda p: p.area, reverse=True)
    for poly in order:
        xs, ys = zip(*poly.boundary[0].coords)
        color = regions.color(poly.name(), default=NA)
        cr, cg, cb = r.col2rgb(color)
        rgb = r.rgb(cr, cg, cb, alpha=128, maxColorValue=255)
        graphics.polygon(C(xs), C(ys), col=rgb)
    # plot the grid
    graphics.abline(v=r.c(OOB, lr[0]-OOB), lty=2)
    graphics.abline(h=r.seq(0, lr[1], 200), col="lightgray", lty=2)
    graphics.abline(v=r.seq(0, lr[0], 200), col="lightgray", lty=2)
    # plot the points
    xs, ys, names = zip(*[(pt[0].x, pt[0].y, pt[1]) for pt in points])
    colors = [RGB(points.Color(name)) for name in names]
    graphics.points(C(xs), C(ys), xlab="", ylab="", pch="+", col=C(colors))
    # save as a png
    if "png" in kwargs:
        grDevices.dev_print(grDevices.png, file=kwargs['png'], width=lr[0],
                height=lr[1])
    # derive legend contents: colors, counts, names
    tid_counts = {}
    uniq_tids = []
    for n in names:
        if n not in uniq_tids:
            tid_counts[n] = 0
            uniq_tids.append(n)
        tid_counts[n] += 1
    uniq_colors = [RGB(points.Color(tid)) for tid in uniq_tids]
    uniq_names = [("%d\t%s" % (i, IDs.TileID[i])) for i in uniq_tids]
    name_counts = [("%d\t%s: %d" % (k, IDs.TileID[k], v)) for (k,v) in \
            tid_counts.items()]
    # display the colors legend
    legend_args = dict(y_intersp=0.7, cex=0.7)
    graphics.screen(3)
    graphics.legend("center", title="Tile Colors", legend=C(uniq_names),
            col=C(uniq_colors), pch="+", pt_cex=1, **legend_args)
    # display the counts legend
    graphics.screen(4)
    graphics.legend("center", title="Tile Counts", legend=C(name_counts),
            **legend_args)
    # sleep until the window is closed
    while grDevices.dev_list() != r("NULL"):
        time.sleep(0.1)

def _main():
    p = argparse.ArgumentParser(usage="%(prog)s <polyfile> <findfile>")
    p.add_argument("poly", type=str, help="path to the polygon file")
    p.add_argument("find", type=str, help="path to the find file")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("-p", action="store_true",
                   help="list all items in each region")
    p.add_argument("-d", action="store_true",
                   help="display (in a table) all items in each region")
    p.add_argument("--draw", action="store_true",
                   help="draw the regions and points using the rpy2 package")
    p.add_argument("--png", type=str, metavar="FILE",
                   help="save output to a png file")
    args = p.parse_args()
    G['VERBOSE'] = args.verbose
    points = FindFile(path=args.find)
    polyset = WorldPolySet()
    polyset.parse_lines(open(args.poly, 'r'))
    results = do_search(polyset, points)
    for k in polyset.names():
        if args.p:
            print("Region %s has %d entries" % (k, len(results[k])))
            if G['VERBOSE'] and len(results[k]) > 0:
                print('Region %s first result: %s' % (k, results[k][0]))
        if args.d:
            print("Region %s has entry counts: %s" % (k, results['+counts'][k]))
    if args.draw:
        draw_r(polyset, points, png=args.png)

if __name__ == "__main__":
    _main()

