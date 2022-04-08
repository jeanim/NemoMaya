"""
 Copyright (c) 2022 OctMedia

 Permission is hereby granted, free of charge, to any person obtaining a copy of
 this software and associated documentation files (the "Software"), to deal in
 the Software without restriction, including without limitation the rights to
 use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 the Software, and to permit persons to whom the Software is furnished to do so,
 subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 """

from __future__ import print_function
from maya import cmds
from nemo import utils


def get_enum_field(plug):
    from maya import cmds
    result = []
    cursor = -1
    for name_value in cmds.addAttr(plug, q=True, enumName=True).split(':'):
        if '=' in name_value:
            name, value = name_value.rsplit('=', 1)
        else:
            name, value = name_value, cursor + 1
        result.append((name, int(value)))
        cursor = int(value)
    return result


def list_channel_box(obj):
    _attributes = (cmds.listAttr(obj, k=True) or []) + \
        (cmds.listAttr(obj, cb=True) or [])
    attributes = []
    for attr in _attributes:
        plug = '{}.{}'.format(obj, attr)
        if cmds.getAttr(plug, lock=True):
            continue
        attr_type = cmds.getAttr(plug, type=True)
        if attr_type in {'string', 'double3'}:
            continue
        if attr_type == 'enum' and attr != 'rotateOrder' and len(get_enum_field(plug)) == 1:
            continue
        attributes.append(attr)
    return attributes


def is_visibility_always_off(obj):
    return not cmds.getAttr('{}.visibility'.format(obj)) and not cmds.listConnections("{}.visibility".format(obj), s=True, d=False)


def is_world_visibility_always_off(obj):
    shapes = cmds.listRelatives(obj, shapes=True, ni=True)
    if shapes and all(is_visibility_always_off(x) for x in shapes):
        return True
    
    segments = cmds.ls(obj, long=True)[0].split('|')[1:]
    transforms = ['|'.join(segments[:i]) for i in range(1, 1 + len(segments))]
    for x in transforms:
        if is_visibility_always_off(x):
            return True
    return False


def is_channel_box_locked(ctrl):
    for x in list_channel_box(ctrl):
        if not cmds.getAttr("{}.{}".format(ctrl, x), lock=True) and x != "visibility":
            return False
    return True


def is_channel_box_driven(ctrl):
    for x in list_channel_box(ctrl) + ['translate', 'rotate', 'scale']:
        if cmds.listConnections("{}.{}".format(ctrl, x), s=True, d=False):
            return True
    return False


def get_extra(ctrl):
    parent = cmds.listRelatives(ctrl, p=True)
    if not parent:
        return None
    parent = parent[0]
    if not cmds.listRelatives(parent, p=True):
        return None
    if cmds.listRelatives(parent, shapes=True) or not utils.is_matrix_identity(cmds.xform(parent, q=True, m=True, os=True)):
        return None
    return None if is_channel_box_driven(parent) else parent


def get_controllers(pattern, curve=True, surface=False, free=True, visible=True):
    objects = cmds.ls(pattern, transforms=True)
    controllers = []
    for obj in objects:
        shapes = cmds.listRelatives(obj, shapes=True, ni=True) or []
        pass_test = False
        for s in shapes:
            if cmds.getAttr('{}.overrideEnabled'.format(s)) and cmds.getAttr('{}.overrideDisplayType'.format(s)):
                continue
            if curve and cmds.nodeType(s) == 'nurbsCurve':
                pass_test = True
            if surface and cmds.nodeType(obj) == "nurbsSurface":
                pass_test = True
            if not curve and not surface:
                pass_test = True
        if pass_test:
            controllers.append(obj)

    if free:
        controllers = [ctrl for ctrl in controllers if not is_channel_box_locked(ctrl)]
    if visible:
        controllers = [ctrl for ctrl in controllers if not is_world_visibility_always_off(ctrl)]

    return controllers


def get_meshes(patterns):
    shapes = []
    for shape in cmds.ls(type='mesh', long=True, ni=True):
        if any(x in shape for x in patterns):
            shapes.append(shape)
    return shapes