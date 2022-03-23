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

from maya import cmds


def default_attributes(obj):
    node_type = cmds.nodeType(obj)
    attributes = ['visibility', 'translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ', 'scaleX', 'scaleY', 'scaleZ']
    if node_type == 'transform':
        return attributes
    elif node_type == 'joint':
        return attributes + ['radius']
    else:
        return False


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


def is_matrix_identity(mat):
    for i in range(16):
        if i in {0, 5, 10, 15}:
            if abs(mat[i] - 1) > 1E-5:
                return False
        else:
            if abs(mat[i]) > 1E-5:
                return False
    return True


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


def pack_enum_field(field):
    field = {value: name for name, value in field}
    enumName = ''
    cursor = -1
    for value in sorted(field.iterkeys()):
        if cursor + 1 == value:
            enumName += field[value] + ':'
        else:
            enumName += field[value] + '=' + str(value)
        cursor = value
    if enumName.endswith('.'):
        enumName = enumName[:-1]
    return enumName


def is_shape_visibility_driven(ctrl):
    ctrl_shapes = cmds.listRelatives(ctrl, shapes=True, ni=True) or []
    if len(ctrl_shapes) != 1:
        return False
    src = cmds.listConnections('{}.visibility'.format(ctrl_shapes[0]), p=True, s=True, d=False)
    return bool(src)


def var_name(name):
    return name.replace('.', '__DOT__').replace('|', '__SPL__')


def create_from_path(path, t):
    segments = path.split('|')[1:]
    for i in range(len(segments)):
        transform = '|' + '|'.join(segments[:i + 1])
        if cmds.objExists(transform):
            continue
        name = segments[i]

        is_final = i + 1 == len(segments)

        node_type = t if is_final else 'transform'
        if i:
            real_name = cmds.createNode(node_type, name=name, parent='|'.join(segments[:i]))
        else:
            real_name = cmds.createNode(node_type, name=name)
        if is_final:
            return name
