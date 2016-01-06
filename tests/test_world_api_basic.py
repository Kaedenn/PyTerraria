#!/usr/bin/env python


import tests
import World

worlds = World.ListWorlds()
for wfile, wobj, wpath in worlds:
    assert os.path.exists(wpath), "world path %s exists" % (wpath,)
    assert wobj.GetFlag('Title'), "world %s has a title" % (wobj,)
