#!/usr/bin/env python

"""
Binary Stream: reading files one byte at a time

See help(__module__.BinaryString) for an explanation on how the stream works.

Special data types not understood by the Python struct module:

7-bit packed integer: input: a python integer
    This method is used to store integers in the fewest number of bytes
    necessary. In theory, this format can store integers of arbitrary size.

    Encoding:
        While the number given is greater than 0x7f, write out the lowest
        seven bits and set the high bit of the output to one. Then, shift
        the number given to the right seven places. Repeat.
    Decoding:
        Read a byte and set the lowest seven-bits to the current value.
        While the high bit is set on the byte read, read the next byte, then
        omit the highest bit, shift it to the left by the number of bytes
        read multiplied by seven, and add it to the current value. Repeat
        while the highest bit is set on the byte read.

    Examples:
        0x7f -> "\\x7f"
        0x80 -> "\\x80\\0x01"

Extended Pascal string: input: a python string
    First, write the length of the string as a 7-bit packed integer. Then,
    write every character's ordinal as a single byte. Encoding isn't checked,
    but for best results use UTF-8 or UTF-16 encoded strings.

    The "extended" in "extended Pascal string" refers to the length being
    stored as a packed 7-bit integer rather than a single byte. This "length"
    is actually the number of bytes occupied by the stored string, so larger
    encodings like UTF-16 will have larger sizes than UTF-8 or ASCII.
"""

import os
import struct

BooleanType = ('?', 1)
ByteType = ('B', 1)
SInt8Type = ('b', 1)
UInt8Type = ('B', 1)
SInt16Type = ('h', 2)
UInt16Type = ('H', 2)
SInt32Type = ('i', 4)
UInt32Type = ('I', 4)
SInt64Type = ('q', 8)
UInt64Type = ('Q', 8)
SingleType = ('f', 4)
DoubleType = ('d', 8)

TypeNames = {
    BooleanType: 'boolean',
    SInt8Type: 'signed 8-bit integer',
    UInt8Type: 'unsigned 8-bit integer',
    SInt16Type: 'signed 16-bit integer',
    UInt16Type: 'unsigned 16-bit integer',
    SInt32Type: 'signed 32-bit integer',
    UInt32Type: 'unsigned 32-bit integer',
    SInt64Type: 'signed 64-bit integer',
    UInt64Type: 'unsigned 64-bit integer',
    SingleType: 'single-precision float',
    DoubleType: 'double-precision float'
}

class DataError(IOError):
    def __init__(self, *args, **kwargs):
        super(DataError, self).__init__(*args, **kwargs)

def _make_reader(t, scalar=True, bounds=None):
    typeid, nbytes = t
    ts = "<%s" % (typeid,)
    def reader(self):
        bytevals = struct.unpack_from(ts, self._content, offset=self._pos)
        self._pos += nbytes
        #bytevals = struct.unpack(ts, self._next(nbytes))
        return bytevals[0] if scalar else bytevals
    reader.__doc__ = "Reads %d byte%s as a little-endian %s type" % (
            nbytes, "" if nbytes == 1 else "s", TypeNames[t])
    if bounds is not None:
        low, high = bounds
        def checker(self):
            value = reader(self)
            if not low <= value <= high:
                raise DataError("Value %s not between [%s,%s]" % (value, low,
                    high))
            return value
        checker.__doc__ = reader.__doc__ + " (between [%s,%s])" % (low, high)
        return checker
    return reader

def _make_writer(t, scalar=True):
    typeid, nbytes = t
    ts = "<%s" % (typeid,)
    def writer(self, data):
        bytevals = struct.pack(ts, data)
        self.write(bytevals[0] if scalar else bytevals)
    writer.__doc__ = "Writes %d byte%s as a little-endian %s type" % (
            nbytes, "" if nbytes == 1 else "s", TypeNames[t])
    return writer

class BinaryString(object):
    """Planned features:
    1) Inherit class file and operate on a stream, not a str
    2) Implement symmetric writers
    """
    readBoolean = _make_reader(BooleanType, bounds=(0, 1))
    readByte = _make_reader(ByteType)
    readInt8 = _make_reader(SInt8Type)
    readUInt8 = _make_reader(UInt8Type)
    readInt16 = _make_reader(SInt16Type)
    readUInt16 = _make_reader(UInt16Type)
    readInt32 = _make_reader(SInt32Type)
    readUInt32 = _make_reader(UInt32Type)
    readInt64 = _make_reader(SInt64Type)
    readUInt64 = _make_reader(UInt64Type)
    readSingle = _make_reader(SingleType)
    readDouble = _make_reader(DoubleType)

    Types = (
        BooleanType, ByteType,
        SInt8Type, UInt8Type,
        SInt16Type, UInt16Type,
        SInt32Type, UInt32Type,
        SInt64Type, UInt64Type,
        SingleType, DoubleType
    )

    ScalarReaders = (
        readInt8, readUInt8,
        readInt8, readUInt8,
        readInt16, readUInt16,
        readInt32, readUInt32,
        readInt64, readUInt64,
        readSingle, readDouble
    )

    ScalarReaderLookup = dict(zip(Types, ScalarReaders))

    def __init__(self, data, verbose=False, debug=False, asis=False):
        """Creates a BinaryString instance.
        @param data - either a file-like object or a string-like object
        @param verbose - output progress/debugging information (default=False)
        @param debug - store information on the frequency of sizes read
        @param asis - do not call read() even if it exists

        If @param data has a read() method, it is called and the result is
        stored instead (unless asis=True).
        """
        self._content = data
        if hasattr(data, 'read') and not asis:
            self._content = data.read()
        self._pos = 0
        self._verbose_on = verbose
        self._debug_on = debug
        self._debug_counts = {}

    def _debug_tally(self, nbytes):
        if self._debug_on:
            if nbytes not in self._debug_counts:
                self._debug_counts[nbytes] = 1
            else:
                self._debug_counts[nbytes] += 1

    def _verbose(self, string, *args):
        if self._verbose_on:
            print(string % args if args else string)

    def _next(self, nbytes):
        result = self._content[self._pos:self._pos+nbytes]
        self._pos += nbytes
        if self._pos > len(self._content):
            nb = self._pos - len(self._content)
            raise EOFError("Attempt to read %d bytes beyond EOF" % (nb,))
        if self._debug_on and not result and nbytes > 0:
            off_pr, off_po = self._pos-nbytes, self._pos
            print("Read of %d bytes yields no data" % (nbytes,))
            print("Offset pre-read %s, post-read %s" % (off_pr, off_po))
            print("Length of stream: %s" % (len(self._content),))
        self._debug_tally(nbytes)
        if nbytes == 1:
            return result[0]
        return result

    def _clamp_pos(self):
        if self._pos < 0:
            self._verbose("Bad negative position %d; clamping" % (self._pos,))
            self._pos = 0
        elif self._pos > len(self._content):
            self._verbose("Position %d beyond EOF; clamping" % (self._pos))
            self._pos = len(self._content)

    def getReadStats(self):
        "If __init__(debug=True), returns debugging counts"
        return self._debug_counts

    def seek(self, nbytes, whence=os.SEEK_CUR):
        "Seek relative to the current position by nbytes"
        if whence == os.SEEK_CUR:
            self._pos += nbytes
        elif whence == os.SEEK_SET:
            self._pos = nbytes
        elif whence == os.SEEK_END:
            self._pos = len(self._content) + nbytes
        self._clamp_pos()

    def seek_cur(self, nbytes):
        "Seek relative to the current position by nbytes"
        return self.seek(nbytes, whence=os.SEEK_CUR)

    def seek_set(self, pos):
        "Seek to the absolute offset given by pos"
        return self.seek(pos, whence=os.SEEK_SET)

    def seek_end(self, nbytes=0):
        "Seek to nbytes (usually negative) after stream end"
        return self.seek(nbytes, whence=os.SEEK_END)

    def tell(self):
        "Returns the current position in the stream"
        return self.get_pos()

    def get_pos(self):
        "Returns the current position in the stream"
        return self._pos

    def getContent(self, remainder=False):
        "Get the reader's underlying buffer, optionally starting at self._pos"
        if remainder:
            return self._content[self._pos:]
        return self._content, self._pos

    def readString(self, length=None):
        """Reads an extended Pascal string.
        Reads the length as a 7-bit packed integer if length is None.
        See module docstring for an explanation on extended Pascal strings"""
        if length is None:
            length = self.readPacked7Int()
        return self._next(length) if length > 0 else ''

    def readPacked7Int(self):
        """Reads a packed 7-bit integer.
        See module docstring for an explanation on 7-bit packed integers"""
        byte = self.readUInt8()
        value = (byte & 0x7f)
        shift = 7
        while (byte & 0x80) != 0:
            byte = self.readUInt8()
            value |= ((byte & 0x7f) << shift)
            shift += 7
        return value

    def readBitArray(self, nbits=None):
        """Reads a packed bit array.
        Reads the first 16 bits as the length of the array beforehand if nbits
        is omitted (or None)"""
        if nbits is None:
            nbits = self.readInt16()
        bits = []
        mask = 128 # implies high bit is never used
        byte = 0
        for i in range(nbits):
            if mask < 128:
                mask = (mask << 1)
            else:
                byte = self.readByte()
                mask = 1
            bits.append((byte & mask) == mask)
        return bits

    def write(self, data):
        l, r = self._content[:self._pos], self._content[self._pos+len(data):]
        self._content = "".join(l, data, r)
        self._pos += len(data)

ScalarReaderLookup = BinaryString.ScalarReaderLookup

