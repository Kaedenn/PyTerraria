#!/usr/bin/env python

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

Types = (
    BooleanType, ByteType,
    SInt8Type, UInt8Type,
    SInt16Type, UInt16Type,
    SInt32Type, UInt32Type,
    SInt64Type, UInt64Type,
    SingleType, DoubleType
)

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

LittleEndian = '<'
BigEndian = '>'
NativeEndian = ''

EndianNames = {
    '<': 'little-endian',
    '>': 'big-endian',
    '': 'native endian'
}

def GetFormat(type, endian):
    return "%s%s" % (endian, type[0])

def Pack(type, value, endian='<'):
    return struct.pack(GetFormat(type, endian), value)

def Unpack(type, bytes, endian='<'):
    return struct.unpack(GetFormat(type, endian), bytes)

def TypeName(t, endian='<'):
    return "%s %s" % (EndianNames.get(endian, 'unknown endian'), TypeNames[t])

class DataError(IOError):
    def __init__(self, *args, **kwargs):
        super(DataError, self).__init__(*args, **kwargs)

