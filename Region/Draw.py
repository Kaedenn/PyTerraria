#!/usr/bin/env python

import rpy2.interactive.process_revents
from rpy2.robjects import r
from rpy2.robjects.packages import importr

class Drawer(object):
    def __init__(self, polyfile=None, findfile=None, bg="white"):
        self._graphics = importr("graphics")
        self._grDevices = importr("grDevices")
        rpy2.interactive.process_revents.start()

        self._NA = r("NA")[0]
        self._C = lambda seq: r.c(*seq)

        self._polyfile = polyfile
        self._findfile = findfile

        self._replot()

    def _replot(self):
        if self._grDevices.dev_list() != r("NULL"):
            self._grDevices.dev_off()
        self._graphics.par(bg)
        self._graphics.split_screen(r.c(2,1))
        self._graphics.split_screen(r.c(1, 2), screen=2)
        self._graphics.screen(1)

        self._plot_regions()

    def _plot_regions(self):
        pass
