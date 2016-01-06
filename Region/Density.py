#!/usr/bin/env python

import numpy as np
import PIL.Image

class DensityCalculator(object):
    def __init__(self, width, height, window_size=50):
        self._width = width
        self._height = height
        self._window_size = window_size
        self._density = np.asmatrix(np.ndarray((self._width, self._height),
                                               dtype=(np.int_, np.int_)))
        self._max = 0

    def add_point(self, x, y, weight=1):
        xmin = max(0, x-self._window_size)
        xmax = min(self._width, x+self._window_size)
        ymin = max(0, y-self._window_size)
        ymax = min(self._height, y+self._window_size)
        self._density[xmin:xmax, ymin:ymax] += weight
        self._max = max(self._max, self._density[xmin:xmax, ymin:ymax].max())

    def get_density(self, x, y, scale_to=None, scale_int=False):
        value = self._density[x, y]
        if scale_to is not None and self._max != 0:
            value = scale_to*value/self._max
            if scale_int:
                value = int(value)
        return value

    def get_matrix(self):
        return self._density

    def width(self):
        return self._width

    def height(self):
        return self._height

def load_density(path):
    fobj = open(path)
    result = []
    for line in fobj:
        result.append([int(i) for i in line.strip().split()])
    return np.asmatrix(np.array(result, dtype=(np.int_, np.int_)))

def density_to_png(matrix, path):
    img = PIL.Image.new('RGB', matrix.shape)
    copy = matrix.copy()
    copy = 255 - copy*255/copy.max()
    for xi in xrange(matrix.shape[0]):
        for yi in xrange(matrix.shape[1]):
            v = copy[xi, yi]
            img.putpixel((xi, yi), (v, v, v))
    img.save(path)
