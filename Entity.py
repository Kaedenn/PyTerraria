#!/usr/bin/env python

ENTITY_DUMMY = 0
ENTITY_ITEM_FRAME = 1

class EntityType(object):
    Unknown = 0
    NPC = 1
    Mob = 2
    TileEntity_Dummy = 3
    TileEntity_ItemFrame = 4

class Entity(object):
    def __init__(self, type=EntityType.Unknown, pos=None, **kwargs):
        self.Type = type
        self.Position = pos
        self.Attributes = kwargs

    def Set(self, attr, value):
        self.Attributes[attr] = value

    def Get(self, attr):
        return self.Attributes.get(attr, None)

    def __str__(self):
        return "Entity %s at %s: %s" % (self.Type, self.Position,
                self.Attributes)
    
    def __repr__(self):
        return "Entity(type=%s, pos=%s, **%s)" % (
                self.Type, self.Position, self.Attributes)

class NPCEntity(Entity):
    ATTR_NAME = "Name"
    ATTR_DISPNAME = "DisplayName"
    ATTR_HOMELESS = "Homeless"
    ATTR_HOME = "Home"
    def __init__(self, name=None, display_name=None, pos=None, homeless=False,
                 home=None):
        super(NPCEntity, self).__init__(EntityType.NPC, pos)
        super_ = super(NPCEntity, self)
        super_.Set(NPCEntity.ATTR_NAME, name)
        super_.Set(NPCEntity.ATTR_DISPNAME, display_name)
        super_.Set(NPCEntity.ATTR_HOMELESS, homeless)
        super_.Set(NPCEntity.ATTR_HOME, home)

    def __str__(self):
        return "NPC '%s the %s' at %s: Home: %s, Homeless: %s" % (
                self.Get(NPCEntity.ATTR_DISPNAME),
                self.Get(NPCEntity.ATTR_NAME),
                self.Position,
                self.Get(NPCEntity.ATTR_HOME),
                self.Get(NPCEntity.ATTR_HOMELESS))

class MobEntity(Entity):
    ATTR_NAME = "Name"
    def __init__(self, name=None, pos=None):
        super(MobEntity, self).__init__(EntityType.Mob, pos)
        super_ = super(MobEntity, self)
        super_.Set(MobEntity.ATTR_NAME, name)

    def __str__(self):
        return "Mob %s at %s" % (self.Get(MobEntity.ATTR_NAME), self.Position)

class DummyTileEntity(Entity):
    ATTR_TYPE = "Type"
    ATTR_ID = "ID"
    ATTR_NPC = "NPC"
    def __init__(self, type=None, id=None, pos=None, npc=None):
        super(DummyTileEntity, self).__init__(EntityType.TileEntity_Dummy, pos)
        super_ = super(DummyTileEntity, self)
        super_.Set(DummyTileEntity.ATTR_TYPE, type)
        super_.Set(DummyTileEntity.ATTR_ID, id)
        super_.Set(DummyTileEntity.ATTR_NPC, npc)

    def __str__(self):
        return "Dummy at %s: ID %s, NPC %s" % (self.Position,
                self.Get(DummyTileEntity.ATTR_ID),
                self.Get(DummyTileEntity.ATTR_NPC))

class ItemFrameTileEntity(Entity):
    ATTR_TYPE = "Type"
    ATTR_ID = "ID"
    ATTR_ITEM = "ItemNetID"
    ATTR_PREFIX = "Prefix"
    ATTR_STACK = "Stack"
    def __init__(self, type=None, id=None, pos=None, item=None, prefix=None,
                 stack=None):
        super(ItemFrameTileEntity, self).__init__(
                EntityType.TileEntity_ItemFrame, pos)
        super_ = super(ItemFrameTileEntity, self)
        super_.Set(ItemFrameTileEntity.ATTR_TYPE, type)
        super_.Set(ItemFrameTileEntity.ATTR_ID, id)
        super_.Set(ItemFrameTileEntity.ATTR_ITEM, item)
        super_.Set(ItemFrameTileEntity.ATTR_PREFIX, prefix)
        super_.Set(ItemFrameTileEntity.ATTR_STACK, stack)

    def __str__(self):
        return "ItemFrame at %s: ID %s, Item %s, Prefix %s, Stack %s" % (
                self.Position, self.Get(ItemFrameTileEntity.ATTR_ID),
                self.Get(ItemFrameTileEntity.ATTR_ITEM),
                self.Get(ItemFrameTileEntity.ATTR_PREFIX),
                self.Get(ItemFrameTileEntity.ATTR_STACK))

