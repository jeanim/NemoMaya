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

from nemo.filter import scene_collect
from nemo import utils


def get_io(controllers, shapes):
    inputs = []
    outputs = []
    for ctrl in controllers:
        attributes = set([attr for attr in utils.list_channel_box(ctrl) if not cmds.listConnections("{}.{}".format(ctrl, attr), d=False)])

        for attr in [x for x in attributes if x not in utils.default_attributes(ctrl)]:
            inputs.append("{}.{}".format(ctrl, attr))

        for attr in {'translate', 'rotate', 'scale'}:
            components = []
            driven_components = []
            for comp in {'X', 'Y', 'Z'}:
                x = attr + comp
                sources = cmds.listConnections("{}.{}".format(ctrl, x), s=True, d=False) or cmds.listConnections("{}.{}".format(ctrl, attr), s=True, d=False)
                if sources:
                    if sources != [ctrl]:
                        driven_components.append(x)
                elif x in attributes:
                    components.append(x)

            if len(components) == 1:
                inputs.append("{}.{}".format(ctrl, components[0]))
            elif len(components) > 1:
                if not driven_components:
                    inputs.append("{}.{}".format(ctrl, attr))
                else:
                    for x in components:
                        inputs.append("{}.{}".format(ctrl, x))

            if driven_components:
                if len(driven_components) == 3:
                    outputs.append("{}.{}".format(ctrl, attr))
                else:
                    for x in driven_components:
                        outputs.append("{}.{}".format(ctrl, x))

        if utils.is_shape_visibility_driven(ctrl):
            outputs.append("{}.lodVisibility".format(cmds.listRelatives(ctrl, shapes=True)[0]))
        else:
            outputs.append("{}.lodVisibility".format(ctrl))
        extra = scene_collect.get_extra(ctrl)
        if extra:
            inputs.append('{}.matrix'.format(extra))

        if extra:
            outputs.append('{}.parentMatrix[0]'.format(extra))
        else:
            outputs.append('{}.parentMatrix[0]'.format(ctrl))

    for shape in shapes:
        if 'mesh' == cmds.nodeType(shape):
            outputs.append('{}.worldMesh[0]'.format(shape))
        elif 'nurbsCurve' == cmds.nodeType(shape):
            outputs.append('{}.worldSpace[0]'.format(shape))
        outputs.append('{}.lodVisibility'.format(shape))

    return list(set(inputs)), list(set(outputs))
