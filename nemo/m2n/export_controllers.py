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

import maya.api.OpenMaya as om2
from maya import cmds

from nemo import utils
from nemo.filter import scene_collect


def export(rig_name, controllers, shapes, init_data=None):
    data = init_data or dict()
    data['name'] = rig_name

    controllers_data = dict()
    for x in controllers:
        controllers_data[x] = dict()
        export_single_controller(rig_name, x, controllers_data[x])
    data['controllers'] = controllers_data

    mesh_data = dict()
    for x in shapes:
        mesh_data[x] = {'type': cmds.nodeType(x), 'path': cmds.ls(x, l=True)[0]}
    data['shapes'] = mesh_data
    return data


def export_single_controller(rig_name, ctrl, data):
    node_type = cmds.nodeType(ctrl)
    assert node_type in {'transform', 'joint'}
    data['type'] = node_type

    extra = scene_collect.get_extra(ctrl)
    if extra:
        path = '|{0}|NEMO_{1}|{1}'.format(rig_name, extra)
        data['extra_ctrl_name'] = extra
        data['extra_ctrl_matrix'] = cmds.xform(extra, q=True, m=True, os=True)
        data['extra_ctrl_rotateOrder'] = cmds.getAttr(extra + '.rotateOrder')
        data['rootMatrix'] = cmds.getAttr('{}.parentMatrix'.format(extra))
    else:
        path = '|{0}|NEMO_{1}'.format(rig_name, ctrl)
        data['rootMatrix'] = cmds.getAttr('{}.parentMatrix'.format(ctrl))
    data['path'] = path + '|' + ctrl

    if node_type == 'joint':
        data['jointDrawStyle'] = cmds.getAttr(ctrl + '.drawStyle')
        data['jointOrient'] = cmds.getAttr(ctrl + '.jointOrient')[0]

    data['attributes'] = []
    attributes = utils.list_channel_box(ctrl)
    for attr in ['translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ', 'scaleX', 'scaleY', 'scaleZ', 'visibility', 'rotateOrder']:
        if attr not in attributes and cmds.listConnections('{}.{}'.format(ctrl, attr), s=True, d=False) == [ctrl]:
            attributes.append(attr)
    for attr in attributes:
        attr_data = dict()
        attr_data['name'] = attr
        plug = '{}.{}'.format(ctrl, attr)

        attr_data['value'] = cmds.getAttr(plug)
        attr_data['type'] = cmds.getAttr(plug, type=True)
        if attr_data['type'] == 'enum' and attr not in {'rotateOrder'}:
            attr_data['enumField'] = utils.get_enum_field(plug)
        if cmds.getAttr(plug, lock=True):
            attr_data['lock'] = True
        if not cmds.getAttr(plug, keyable=True):
            attr_data['keyable'] = False
        if cmds.attributeQuery(attr, node=ctrl, minExists=True):
            attr_data['min'] = cmds.attributeQuery(attr, node=ctrl, min=True)[0]
        if cmds.attributeQuery(attr, node=ctrl, maxExists=True):
            attr_data['max'] = cmds.attributeQuery(attr, node=ctrl, max=True)[0]
        if cmds.listConnections(plug, s=True, d=False) == [ctrl]:
            attr_data['source'] = cmds.listConnections(plug, s=True, d=False, p=True)[0]
        data['attributes'].append(attr_data)

    if 'rotateOrder' not in attributes and cmds.getAttr('{}.rotateOrder'.format(ctrl)) != 0:
        data['rotateOrder'] = cmds.getAttr('{}.rotateOrder'.format(ctrl))

    if cmds.getAttr('{}.overrideEnabled'.format(ctrl)):
        data['overrideEnabled'] = True
        data['overrideRGBColors'] = cmds.getAttr('{}.overrideRGBColors'.format(ctrl))
        if not cmds.getAttr('{}.overrideVisibility'.format(ctrl)):
            data['overrideVisibility'] = False
        if data['overrideRGBColors']:
            data['overrideColorRGB'] = cmds.getAttr('{}.overrideColorRGB'.format(ctrl))[0]
        else:
            data['overrideColor'] = cmds.getAttr('{}.overrideColor'.format(ctrl))

    data['shapes'] = []
    shapes = cmds.listRelatives(ctrl, shapes=True, ni=True) or []
    if not utils.is_shape_visibility_driven(ctrl):
        shapes = [x for x in shapes if cmds.getAttr('{}.visibility'.format(x))]
    for shape_name in shapes:
        unique_name = '{}|{}'.format(ctrl, shape_name)
        shape_data = {'name': shape_name, 'type': cmds.nodeType(unique_name)}
        if not export_shape_value(unique_name, shape_data):
            continue
        data['shapes'].append(shape_data)

    data['matrix'] = cmds.xform(ctrl, q=True, m=True, os=True)
    for attr in {'rotatePivot', 'rotatePivotTranslate', 'scalePivot', 'scalePivotTranslate'}:
        v = cmds.getAttr('{}.{}'.format(ctrl, attr))[0]
        if any(abs(x) > 1E-5 for x in v):
            data['attributes'].append({'name': attr, 'value': v})


def export_shape_value(shape, data):
    if data['type'] == 'nurbsCurve':
        valid = export_shape_nurbs_curve(shape, data)
    elif data['type'] == 'locator':
        valid = export_shape_locator(shape, data)
    elif data['type'] in {'clusterHandle', 'softModHandle'}:
        return False
    else:
        assert False, (shape, data['type'])

    if not valid:
        return False

    if cmds.getAttr('{}.overrideEnabled'.format(shape)):
        data['overrideEnabled'] = True
        data['overrideRGBColors'] = cmds.getAttr(shape + '.overrideRGBColors')
        if not cmds.getAttr('{}.overrideVisibility'.format(shape)):
            data['overrideVisibility'] = False
        if data['overrideRGBColors']:
            data['overrideColorRGB'] = cmds.getAttr('{}.overrideColorRGB'.format(shape))[0]
        else:
            data['overrideColor'] = cmds.getAttr('{}.overrideColor'.format(shape))

    return True


def export_shape_nurbs_curve(shape, data):
    curve = om2.MFnNurbsCurve(om2.MGlobal.getSelectionListByName(shape).getDagPath(0))
    if curve.object().isNull():
        return False
    data['degree'] = curve.degree
    data['form'] = cmds.getAttr('{}.form'.format(shape), asString=True)
    data['knots'] = list(curve.knots())
    data['cvs'] = [[x.x, x.y, x.z] for x in curve.cvPositions()]
    return True


def export_shape_locator(shape, data):
    data['localPosition'] = cmds.getAttr('{}.localPosition'.format(shape))[0]
    data['localScale'] = cmds.getAttr('{}.localScale'.format(shape))[0]
    return True