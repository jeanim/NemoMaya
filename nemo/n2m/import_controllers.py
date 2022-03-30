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

from nemo import utils


def import_from(data):
    cmds.file(new=True, f=True)
    rig_name = data['name']
    for ctrl_name, ctrl_data in data['controllers'].items():
        import_single(rig_name, ctrl_name, ctrl_data)

    for shape_name, shape_data in data['shapes'].items():
        utils.create_from_path(shape_data['path'], shape_data['type'])


def import_single(rig_name, ctrl_name, data):
    utils.create_from_path(data['path'], data['type'])
    if 'extra_ctrl_name' in data:
        extra_ctrl_name = data['extra_ctrl_name']
        cmds.xform('|{}|NEMO_{}'.format(rig_name, extra_ctrl_name), m=data['rootMatrix'])
        cmds.setAttr(extra_ctrl_name + '.rotateOrder', data['extra_ctrl_rotateOrder'])
        cmds.xform(extra_ctrl_name, m=data['extra_ctrl_matrix'], os=True)
    else:
        cmds.xform('|{}|NEMO_{}'.format(rig_name, ctrl_name), m=data['rootMatrix'])
    cmds.xform(ctrl_name, m=data['matrix'], os=True)
    cmds.setAttr('{}.rotateOrder'.format(ctrl_name), data.get('rotateOrder', 0))

    default_attributes = {
        'translateX', 'translateY', 'translateZ', 'rotateX', 'rotateY', 'rotateZ', 'scaleX', 'scaleY', 'scaleZ', 'visibility', 'rotatePivot', 'rotatePivotX',
        'rotatePivotY', 'rotatePivotZ', 'rotatePivotTranslate', 'scalePivot', 'scalePivotX', 'scalePivotY', 'scalePivotZ', 'scalePivotTranslate', 'rotateOrder'
    }
    if data['type'] == 'joint':
        default_attributes.add('radius')
    for attributes in data.get('attributes', []):
        add_attr_args = dict()
        if 'min' in attributes:
            add_attr_args['hasMinValue'] = True
            add_attr_args['min'] = attributes['min']
        if 'max' in attributes:
            add_attr_args['hasMaxValue'] = True
            add_attr_args['max'] = attributes['max']

        name = attributes['name']
        if name in default_attributes:
            default_attributes.discard(name)
        elif 'enum' == attributes['type']:
            cmds.addAttr(ctrl_name, ln=name, enumName=utils.pack_enum_field(attributes['enumField']), at='enum', k=True, **add_attr_args)
        else:
            cmds.addAttr(ctrl_name, ln=name, at=attributes['type'], k=True, **add_attr_args)

        plug_name = '{}.{}'.format(ctrl_name, name)
        if isinstance(attributes['value'], list) or isinstance(attributes['value'], tuple):
            cmds.setAttr(plug_name, *attributes['value'])
        else:
            cmds.setAttr(plug_name, attributes['value'])

        if not attributes.get('keyable', True):
            cmds.setAttr(plug_name, keyable=False, channelBox=True)
        elif name == 'rotateOrder':
            cmds.setAttr(plug_name, keyable=True, channelBox=True)

        if attributes.get('source', ''):
            cmds.connectAttr(attributes['source'], plug_name)
        if attributes.get('lock', False) and name != 'visibility':
            cmds.setAttr(plug_name, lock=True)

    for attr_name in default_attributes:
        cmds.setAttr('{}.{}'.format(ctrl_name, attr_name), keyable=False, channelBox=False, lock=False if attr_name == 'visibility' else True)

    if data['type'] == 'joint':
        cmds.setAttr('{}.drawStyle'.format(ctrl_name), data['jointDrawStyle'])
        cmds.setAttr('{}.jointOrient'.format(ctrl_name), *data['jointOrient'])

    if data.get('overrideEnabled', False):
        cmds.setAttr('{}.overrideEnabled'.format(ctrl_name), True)
        cmds.setAttr('{}.overrideRGBColors'.format(ctrl_name), data['overrideRGBColors'])
        cmds.setAttr('{}.overrideVisibility'.format(ctrl_name), data.get('overrideVisibility', True))
        if data['overrideRGBColors']:
            cmds.setAttr('{}.overrideRGBColors'.format(ctrl_name), *data['overrideColorRGB'])
        else:
            cmds.setAttr('{}.overrideColor'.format(ctrl_name), data['overrideColor'])

    for shape in data.get('shapes', []):
        import_shape(shape, ctrl_name)


def import_shape(data, ctrl_name):
    if data['type'] == 'nurbsCurve':
        unique_name = import_shape_nurbs_curve(data, ctrl_name)
    elif data['type'] == 'locator':
        unique_name = import_shape_locator(data, ctrl_name)
    else:
        assert False, data['type']

    if not data.get('overrideEnabled', False):
        return
    cmds.setAttr('{}.overrideEnabled'.format(unique_name), True)
    cmds.setAttr('{}.overrideRGBColors'.format(unique_name), data['overrideRGBColors'])
    cmds.setAttr('{}.overrideVisibility'.format(unique_name), data.get('overrideVisibility', True))
    if data['overrideRGBColors']:
        cmds.setAttr('{}.overrideColorRGB'.format(unique_name), *data['overrideColorRGB'])
    else:
        cmds.setAttr('{}.overrideColor'.format(unique_name), data['overrideColor'])


def import_shape_nurbs_curve(data, ctrl_name):
    if data['form'] == 'Periodic':
        curve = cmds.curve(degree=data['degree'], p=data['cvs'], k=data['knots'], periodic=True)
    else:
        curve = cmds.curve(degree=data['degree'], p=data['cvs'], k=data['knots'])
    shape_name = cmds.parent(cmds.listRelatives(curve, shapes=True)[0], ctrl_name, s=True, add=True)[0]
    cmds.delete(curve)
    return cmds.rename(shape_name, data['name'])


def import_shape_locator(data, ctrl_name):
    loc = cmds.spaceLocator()[0]
    cmds.setAttr('{}.localPosition'.format(loc), *data['localPosition'])
    cmds.setAttr('{}.localScale'.format(loc), *data['localScale'])
    shape_name = cmds.parent(cmds.listRelatives(loc, shapes=True)[0], ctrl_name, s=True, add=True)[0]
    cmds.delete(loc)
    return cmds.rename(shape_name, data['name'])
