#!/usr/bin/env python

import struct

def _make_reader(t, scalar=True):
    typeid, nbytes = t
    def reader(self):
        if self._paranoid:
            assert struct.calcsize('<%s' % (typeid,)) == nbytes
        bytevals = struct.unpack('<%s' % (typeid,), self._next(nbytes))
        return bytevals[0] if scalar else bytevals
    return reader

class BinaryStream(object):
    BooleanType = ('b', 1)
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

    readBoolean = _make_reader(BooleanType)
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

    def __init__(self, fobj, verbose=False, paranoid=False):
        self._content = fobj.read()
        self._pos = 0
        self._verbose_on = verbose
        self._paranoid = paranoid

    def _verbose(self, string, *args, **kwargs):
        if self._verbose_on:
            if args:
                print(string % args)
            else:
                print(string)
            if kwargs:
                print(kwargs)

    def _next(self, nbytes):
        result = self._content[self._pos:self._pos+nbytes]
        self._pos += nbytes
        if len(result) == 0:
            print("Read of %d bytes yields no data: %r" % (nbytes, result))
            print("Offset (pre-read) %s, post-read %s" % (self._pos-nbytes, self._pos))
            print("Content was %r" % (self._content[self._pos-nbytes:self._pos],))
        return result if nbytes > 1 else result[0]

    def seek(self, nbytes):
        self._pos += nbytes

    def seek_set(self, pos):
        self._pos = pos

    def seek_end(self, nbytes):
        self._pos = len(self._content) - nbytes

    def get_pos(self):
        return self._pos

    def readString(self):
        length = self.readPacked7Int()
        return self._next(length) if length > 0 else ''
    
    def readPacked7Int(self):
        byte = self.readUInt8()
        value = byte
        while (byte & 0b10000000) == 0b10000000:
            byte = self.readUInt8()
            value = ((value << 7) | byte)
        return value

    def readBitArray(self):
        nbits = self.readInt16()
        return self.readBitArrayOfSize(nbits)

    def readBitArrayOfSize(self, nbits):
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

#def packString(numbers):
#    return ''.join(struct.pack('<c', chr(number)) for number in numbers)
#
#def unpackBits(bits):
#    return [''.join(reversed(bin(i)[2:])) for i in bits]
#
#def packBits(bits):
#    packed = []
#    for bit in bits:
#        s = bin(bit)[2:]
#        s = "0"*(8-len(s)%8) + s
#        print s
#        assert len(s)%8 == 0
#        packed.append(s)
#    return int(''.join(packed))
#
#def doTest():
#    testBitArray()
#    testString()
#
#def testBitArray():
#    b = packString((24, 0, 0b11011000, 0b00001100, 0b11110000))
#    s = StringIO.StringIO(b)
#    reader = BinaryStream(s, verbose=True)
#    bits = reader.readBitArray()
#    assert len(bits) == 24
#    expected = [0, 0, 0, 1, 1, 0, 1, 1,
#                0, 0, 1, 1, 0, 0, 0, 0,
#                0, 0, 0, 0, 1, 1, 1, 1]
#    expected = [bool(i) for i in expected]
#    assert len(expected) == len(bits)
#    print(expected)
#    print(bits)
#    for i in range(len(bits)):
#        assert expected[i] == bits[i]
#
#def testString():
#    s = "\x0cHello there!"
#    print(repr(s))
#    b = StringIO.StringIO(s)
#    reader = BinaryStream(b, verbose=True)
#    actual = reader.readString()
#    print(actual)
#    assert len(actual) == len(s[1:])
#    assert len(actual) == ord(s[0])
#    assert actual == s[1:]
#
#if __name__ == "__main__":
#    import StringIO
#    doTest()
#
