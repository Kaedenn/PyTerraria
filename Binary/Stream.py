#!/usr/bin/env python

import os
import struct

class Type(object):
    Boolean = ('?', 1)
    Byte = ('B', 1)
    SInt8 = ('b', 1)
    UInt8 = ('B', 1)
    SInt16 = ('h', 2)
    UInt16 = ('H', 2)
    SInt32 = ('i', 4)
    UInt32 = ('I', 4)
    SInt64 = ('q', 8)
    UInt64 = ('Q', 8)
    Single = ('f', 4)
    Double = ('d', 8)

def _wrapper_decorator(funcname):
    def wrapper(self, *args, **kwargs):
        if hasattr(self._stream, funcname):
            fn = getattr(self._stream, funcname)
            return fn(*args, **kwargs)
        raise NotImplementedError("Function %s not available" % (funcname,))
    wrapper.__name__ = funcname
    return wrapper

class BinaryStream(object):
    def __init__(self, stream=None, path=None, mode='rb'):
        if stream is not None:
            self._stream = stream
        elif path is not None:
            if 'b' not in mode:
                mode = mode + 'b'
            self._stream = open(path, mode)
        else:
            raise TypeError("required argument 'stream' or 'path' missing")

    def _verify_int_size(self, size):
        if size not in (0, 1, 8, 16, 32, 64):
            raise ValueError("Size %s not a power of two < 64" % (size,))

    def _get_int_fmt(self, size, signed, endian='<'):
        # special-case things like terminators or empty values
        if size == 0:
            return ''
        fmts = {
            1: 'b',
            8: 'b',
            16: 'h',
            32: 'i',
            64: 'q'
        }
        return "%s%s" % (endian, fmts[size] if signed else fmts[size].upper())

    read = _wrapper_decorator('read')
    readline = _wrapper_decorator('readline')
    write = _wrapper_decorator('write')
    seek = _wrapper_decorator('seek')
    close = _wrapper_decorator('close')
    closed = _wrapper_decorator('closed')
    flush = _wrapper_decorator('flush')
    isatty = _wrapper_decorator('isatty')
    next = _wrapper_decorator('next')
    reset = _wrapper_decorator('reset')
    tell = _wrapper_decorator('tell')
    truncate = _wrapper_decorator('truncate')

    def ReadSigned(self, size):
        self._verify_int_size(size)
        fmt = self._get_int_fmt(size, True)
        nbytes = struct.calcsize(fmt)
        return struct.unpack(fmt, self.read(nbytes))[0]

    def ReadUnsigned(self, size):
        self._verify_int_size(size)
        fmt = self._get_int_fmt(size, False)
        nbytes = struct.calcsize(fmt)
        return struct.unpack(fmt, self.read(nbytes))[0]

    def ReadSingle(self):
        fmt = '<f'
        nbytes = struct.calcsize(fmt)
        return struct.unpack(fmt, self.read(nbytes))[0]

    def ReadDouble(self):
        fmt = '<d'
        nbytes = struct.calcsize(fmt)
        return struct.unpack(fmt, self.read(nbytes))[0]

    def ReadCString(self):
        result = []
        value = self.ReadByte()
        while value != 0:
            result.append(value)
            value = self.ReadByte()
        return ''.join(result)

    def ReadPascalString(self, width=8):
        self._verify_int_size(width)
        size = self.ReadUnsigned(width)
        return self.read(size)

    def ReadExtendedPascalString(self):
        size = self.ReadPacked7Int()
        return self.read(size)

    def ReadPacked7Int(self):
        byte = self.ReadByte()
        value = (byte & 0x7f)
        shift = 7
        while (byte & 0x80) != 0:
            byte = self.ReadByte()
            value |= ((byte & 0x7f) << shift)
            shift += 7
        return value

    def ReadBitArray(self, nbits=None):
        if nbits is None:
            nbits = self.ReadSInt16()
        bits = []
        mask = 0x80
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

    def ReadBoolean(self):
        return bool(self.ReadUInt8())

    def ReadByte(self):
        return self.ReadUInt8()

    def ReadSInt8(self):
        return self.ReadSigned(8)

    def ReadUInt8(self):
        return self.ReadUnsigned(8)

    def ReadSInt16(self):
        return self.ReadSigned(16)

    def ReadUInt16(self):
        return self.ReadUnsigned(16)

    def ReadSInt32(self):
        return self.ReadSigned(32)

    def ReadUInt32(self):
        return self.ReadUnsigned(32)

    def WriteSigned(self, number, size):
        self._verify_int_size(size)
        fmt = self._get_int_fmt(size, True)
        self.write(struct.pack(fmt, number))

    def WriteUnsigned(self, number, size):
        self._verify_int_size(size)
        fmt = self._get_int_fmt(size, False)
        self.write(struct.pack(fmt, number))

    def WriteSingle(self, number):
        fmt = '<f'
        self.write(struct.pack(fmt, number))

    def WriteDouble(self, number):
        fmt = '<d'
        self.write(struct.pack(fmt, number))

    def WriteCString(self, string):
        self.write(string)
        self.WriteByte(0)

    def WritePascalString(self, string, width=8):
        self._verify_int_size(width)
        self.WriteUnsigned(len(string), width)
        self.write(string)

    def WriteExtendedPascalString(self, string):
        self.WritePacked7Int(len(string))
        self.write(string)

    def WritePacked7Int(self, number):
        while number > 0x7f:
            self.WriteByte((number & 0x7f) | 0x80)
            number = number >> 7
        if number > 0:
            self.WriteByte(number)

    def WriteBitArray(self, bits):
        self.WriteSInt16(len(bits))
        i = 0
        value = 0
        mask = 1
        while i < len(bits):
            if bits[i]:
                value |= mask
            if mask == 0x80:
                self.WriteByte(value)
                value = 0
                mask = 1
            else:
                mask = mask << 1
            i += 1
        if mask != 1:
            self.WriteByte(value)


    def WriteBoolean(self, value):
        return self.WriteUInt8(1 if value else 0)

    def WriteByte(self, value):
        return self.WriteUInt8(value)

    def WriteSInt8(self, value):
        return self.WriteSigned(value, 8)

    def WriteUInt8(self, value):
        return self.WriteUnsigned(value, 8)

    def WriteSInt16(self, value):
        return self.WriteSigned(value, 16)

    def WriteUInt16(self, value):
        return self.WriteUnsigned(value, 16)

    def WriteSInt32(self, value):
        return self.WriteSigned(value, 32)

    def WriteUInt32(self, value):
        return self.WriteUnsigned(value, 32)

