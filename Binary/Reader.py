#!/usr/bin/env python

"""
Reader: parsing strings one byte at a time

See help(__module__.Reader) for an explanation on how the stream works.

Two special data types not understood by the Python struct module:

1) 7-bit packed integer (result: a python integer)
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

2) Extended Pascal string (result: a python string)
    First, write the length of the string as a 7-bit packed integer. Then,
    write every character's ordinal as a single byte. Encoding isn't checked,
    but for best results use UTF-8 or UTF-16 encoded strings.

    The "extended" in "extended Pascal string" refers to the length being
    stored as a packed 7-bit integer rather than a single byte. This "length"
    is actually the number of bytes occupied by the stored string, so larger
    encodings like UTF-16 will have larger sizes than UTF-8 or ASCII.

This module understands another data type, the "packed bit array" which
reserves two bytes for the length of the array (in bits) followed by one byte
for each eight bits. Why the size isn't a packed 7-bit integer is beyond me.
"""

import os
import struct

import IO

def _pl(word, count):
    return word + ("" if count == 1 else "s")

def _make_reader(t, scalar=True, bounds=None, endian='<'):
    typeid, nbytes = t
    ts = "%s%s" % (endian, typeid)
    def reader(self):
        # ends up being a member function of the Reader object
        bytevals = struct.unpack_from(ts, self._content, offset=self._pos)
        self._pos += nbytes
        return bytevals[0] if scalar else bytevals
    reader.__name__ = "reader_%s_%d" % (typeid if typeid != '?' else 'B',
                                        nbytes)
    reader.__doc__ = "Reads %d %s as a %s" % (nbytes, _pl("byte", nbytes),
                                              IO.TypeName(t, endian))
    if bounds is not None:
        low, high = bounds
        def checker(self):
            value = reader(self)
            if not low <= value <= high:
                raise IO.DataError("Value %s not between [%s,%s]" % (value,
                                                                     low,
                                                                     high))
            return value
        checker.__name__ = reader.__name__ + "_checked"
        checker.__doc__ = reader.__doc__ + " (between [%s,%s])" % (low, high)
        return checker
    return reader

class Reader(object):
    """
    Read a string (or other buffer-like object) as a stream of packed binary
    values.

    Although the underlying content of the class is a single cohesive buffer,
    this class exposes functions to act like a stream. This is for convenience
    on both the implementation and the end-user sides.

    The class can read almost all of the typical struct types and can also
    read certain Microsoft .NET-specific types, such as packed 7-bit integers
    and extended Pascal strings.

    Packed 7-bit integers encode numeric values of arbitrary size. The low
    seven bits encode numeric information, while the highest bit states
    whether or not there's a subsequent byte present.

    Extended Pascal strings are like normal Pascal strings in that the size of
    the string is stored immediately before the string, except that the size
    is encoded as a packed 7-bit integer. This allows for strings longer than
    255 characters.

    Extended Pascal strings of zero length are perfectly legal; they're
    encoded as a single zero byte.

    Booleans are implemented via a C99 extension to the struct module and are
    bounds-checked to be either 0 or 1.
    """
    ReadBoolean = _make_reader(IO.BooleanType, bounds=(0, 1))
    ReadByte = _make_reader(IO.ByteType)
    ReadInt8 = _make_reader(IO.SInt8Type)
    ReadUInt8 = _make_reader(IO.UInt8Type)
    ReadInt16 = _make_reader(IO.SInt16Type)
    ReadUInt16 = _make_reader(IO.UInt16Type)
    ReadInt32 = _make_reader(IO.SInt32Type)
    ReadUInt32 = _make_reader(IO.UInt32Type)
    ReadInt64 = _make_reader(IO.SInt64Type)
    ReadUInt64 = _make_reader(IO.UInt64Type)
    ReadSingle = _make_reader(IO.SingleType)
    ReadDouble = _make_reader(IO.DoubleType)

    Types = (
        IO.BooleanType, IO.ByteType,
        IO.SInt8Type, IO.UInt8Type,
        IO.SInt16Type, IO.UInt16Type,
        IO.SInt32Type, IO.UInt32Type,
        IO.SInt64Type, IO.UInt64Type,
        IO.SingleType, IO.DoubleType
    )

    ScalarReaders = (
        ReadInt8, ReadUInt8,
        ReadInt8, ReadUInt8,
        ReadInt16, ReadUInt16,
        ReadInt32, ReadUInt32,
        ReadInt64, ReadUInt64,
        ReadSingle, ReadDouble
    )

    ScalarReaderLookup = dict(zip(Types, ScalarReaders))

    def __init__(self, string, verbose=False, debug=False):
        """Creates a Reader instance.
        @param string - string-like buffer object (see below)
        @param verbose - output progress/debugging information (default=False)
        @param debug - store information on the frequency of sizes read

        The string param must be some kind of buffer, either a str, bytes,
        bytearray, memoryview, or some other object supporting the following
        three operations:
            Iteration:
                for c in string: ...
            Slicing:
                return string[pos:pos+8]
            Length:
                if pos < len(string): ...
        """
        self._content = string
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

    def get_pos(self):
        "Returns the current position in the stream"
        return self._pos

    def tell(self):
        "Returns the current position in the stream (alias for self.get_pos)"
        return self.get_pos()

    def getContent(self, remainder=False):
        "Get the reader's underlying buffer and position (or just remainder)"
        if remainder:
            return self._content[self._pos:]
        return self._content, self._pos

    def ReadString(self, length=None):
        """Reads an extended Pascal string.
        Reads the length as a 7-bit packed integer only if length is omitted.
        See module docstring for an explanation on extended Pascal strings"""
        if length is None:
            length = self.ReadPacked7Int()
        return self._next(length) if length > 0 else ''

    def ReadPacked7Int(self):
        """Reads a packed 7-bit integer.
        See module docstring for an explanation on 7-bit packed integers"""
        byte = self.ReadUInt8()
        value = (byte & 0x7f)
        shift = 7
        while (byte & 0x80) != 0:
            byte = self.ReadUInt8()
            value |= ((byte & 0x7f) << shift)
            shift += 7
        return value

    def ReadBitArray(self, nbits=None):
        """Reads a packed bit array.
        Reads the first 16 bits as the length of the array beforehand if nbits
        is omitted (or None). Why this isn't a packed 7-bit integer is beyond
        me."""
        if nbits is None:
            nbits = self.ReadInt16()
        bits = []
        mask = 0x80 # implies high bit is never used
        byte = 0
        i = 0
        while i < nbits:
            if mask < 0x80:
                mask = (mask << 1)
            else:
                byte = self.ReadByte()
                mask = 1
            bits.append((byte & mask) == mask)
            i += 1
        return bits

ScalarReaderLookup = Reader.ScalarReaderLookup

