#!/usr/bin/env python

"""
Writer: parsing strings one byte at a time

See help(__module__.Writer) for an explanation on how the stream works.

Two special data types not understood by the Python struct module:

1) 7-bit packed integer (result: a python integer)
    This method is used to store integers in the fewest number of bytes
    necessary. In theory, this format can store integers of arbitrary size.

    Encoding:
        While the number given is greater than 0x7f, write out the lowest
        seven bits and set the high bit of the output to one. Then, shift
        the number given to the right seven places. Repeat.
    Decoding:
        Write a byte and set the lowest seven-bits to the current value.
        While the high bit is set on the byte write, write the next byte, then
        omit the highest bit, shift it to the left by the number of bytes
        write multiplied by seven, and add it to the current value. Repeat
        while the highest bit is set on the byte write.

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

import cStringIO
import os
import struct

import IO

def _pl(word, count):
    return word + ("" if count == 1 else "s")

def _make_writer(t, scalar=True, endian='<'):
    typeid, nbytes = t
    ts = "%s%s" % (endian, typeid)
    def writer(self, value):
        # ends up being a member function of the Writer object
        data = struct.pack(ts, value)
        assert len(data) == struct.calcsize(ts)
        self._buffer.write(data)
    tnames = {'?': 'B'}
    writer.__name__ = "writer_%s_%d" % (tnames.get(typeid, typeid), nbytes)
    writer.__doc__ = "Writes %d %s as a %s" % (nbytes, _pl("byte", nbytes),
                                               IO.TypeName(t, endian))
    return writer

class Writer(object):
    WriteBoolean = _make_writer(IO.BooleanType)
    WriteByte = _make_writer(IO.ByteType)
    WriteInt8 = _make_writer(IO.SInt8Type)
    WriteUInt8 = _make_writer(IO.UInt8Type)
    WriteInt16 = _make_writer(IO.SInt16Type)
    WriteUInt16 = _make_writer(IO.UInt16Type)
    WriteInt32 = _make_writer(IO.SInt32Type)
    WriteUInt32 = _make_writer(IO.UInt32Type)
    WriteInt64 = _make_writer(IO.SInt64Type)
    WriteUInt64 = _make_writer(IO.UInt64Type)
    WriteSingle = _make_writer(IO.SingleType)
    WriteDouble = _make_writer(IO.DoubleType)

    Types = (
        IO.BooleanType, IO.ByteType,
        IO.SInt8Type, IO.UInt8Type,
        IO.SInt16Type, IO.UInt16Type,
        IO.SInt32Type, IO.UInt32Type,
        IO.SInt64Type, IO.UInt64Type,
        IO.SingleType, IO.DoubleType
    )

    ScalarWriters = (
        WriteInt8, WriteUInt8,
        WriteInt8, WriteUInt8,
        WriteInt16, WriteUInt16,
        WriteInt32, WriteUInt32,
        WriteInt64, WriteUInt64,
        WriteSingle, WriteDouble
    )

    ScalarWriterLookup = dict(zip(Types, ScalarWriters))

    def __init__(self, buffobj, verbose=False):
        self._buffer = buffobj
        self._verbose_on = verbose

    def _verbose(self, string, *args):
        if self._verbose_on:
            print(string % args if args else string)

    def seek(self, nbytes, whence=os.SEEK_CUR):
        pass

    def seek_cur(self, nbytes):
        return self.seek(nbytes, os.SEEK_CUR)

    def seek_set(self, pos):
        return self.seek(pos, os.SEEK_SET)

    def seek_end(self, nbytes=0):
        return self.seek(nbytes, os.SEEK_END)

    def get_pos(self):
        pass

    def tell(self):
        return self.get_pos()

    def WriteString(self, data):
        self.WritePacked7Int(len(data))
        for ch in data:
            self.WriteUint8(ch) # FIXME: encodings, non 8-bit chars

    def WritePacked7Int(self, number):
        curr = number
        while curr > 0:
            self.WriteByte(curr & 0x7f)
            curr >>= 7  # FIXME

    def WriteBitArray(self, bits):
        norm = ['1' if bit else '0' for bit in bits]
        endpos = len(norm) - len(norm)%8
        start, end = norm[:endpos], norm[endpos:]
        # first group each pair of bits
        pairs = [[i,j] for i,j in zip(start[::2], start[1::2])]
        # then group each pair of pairs into quartets
        quads = [i+j for i,j in zip(pairs[::2], pairs[1::2])]
        # then group each of those into octets
        octs = [i+j for i,j in zip(quads[::2], quads[1::2])]
        # then join them for the resulting byte array
        bytes = [''.join(oct) for oct in octs]
        self.WriteInt16(len(bits))
        for byte in bytes:
            self.WriteByte(byte)

ScalarWriterLookup = Writer.ScalarWriterLookup

