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

import json
import import_controllers
from maya import cmds


def inv_var_name(text):
    return text.replace("__DOT__", '.')


def connect_matrix_to_transform(src, obj):
    node_decompose = cmds.createNode('decomposeMatrix')
    cmds.connectAttr(src, '%s.inputMatrix' % node_decompose)

    for attr in {'translate', 'rotate', 'scale'}:
        cmds.connectAttr('{}.output{}'.format(node_decompose, attr.capitalize()), '{}.{}'.format(obj, attr))


def assemble(path_config, path_scene, path_bin, path_resource, identifier, dll_mode):
    with open(path_scene) as f:
        import_controllers.import_from(json.load(f))

    with open(path_config) as f:
        config = json.load(f)

    if dll_mode:
        config['bin'] = path_bin
        config['resource'] = path_resource
        with open(path_config, 'w') as f:
            json.dump(config, f)
        cmds.loadPlugin('NemoMayaNodes', quiet=True)
    else:
        cmds.loadPlugin(path_bin)
    cmds.loadPlugin('matrixNodes', quiet=True)

    if dll_mode:
        node = cmds.createNode('Nemo')
        cmds.createNode('transform', name='Dummy')
        cmds.createNode('mesh', name='DummyShape', parent='Dummy')
        cmds.connectAttr('{}.dummy'.format(node), 'DummyShape.inMesh')
    else:
        node = cmds.createNode(identifier)

    ## import rig
    for x in config["inputs"] + config["outputs"]:
        name = x["name"]
        typename = x["type"]
        obj, attr = inv_var_name(name).split('.')
        if dll_mode:
            if "Float" == typename:
                cmds.addAttr(node, ln=name, at="float")
            elif "Angle" == typename:
                cmds.addAttr(node, ln=name, at="doubleAngle")
            elif "Vec3" == typename:
                cmds.addAttr(node, ln=name, at="float3")
                cmds.addAttr(node, ln=name + 'X', at="float", parent=name)
                cmds.addAttr(node, ln=name + 'Y', at="float", parent=name)
                cmds.addAttr(node, ln=name + 'Z', at="float", parent=name)
            elif "Euler" == typename:
                cmds.addAttr(node, ln=name, at="double3")
                cmds.addAttr(node, ln=name + 'X', at="doubleAngle", parent=name)
                cmds.addAttr(node, ln=name + 'Y', at="doubleAngle", parent=name)
                cmds.addAttr(node, ln=name + 'Z', at="doubleAngle", parent=name)
            elif "Mat4" == typename:
                cmds.addAttr(node, ln=name, at="fltMatrix")
            elif "Bool" == typename:
                cmds.addAttr(node, ln=name, at="bool")
            elif "Int" == typename:
                cmds.addAttr(node, ln=name, at="long")
            elif "Mesh" == typename:
                cmds.addAttr(node, ln=name, dt="mesh")
            else:
                assert False, typename

        is_output = "affectings" in x
        if is_output:
            if attr == 'worldMesh0':
                dest = '{}.inMesh'.format(obj)
            elif attr == 'parentMatrix0':
                dest = cmds.listRelatives(obj, p=True)[0]
            elif attr == 'lodVisibility':
                dest = 'NEMO_{}.visibility'.format(obj)
                if not cmds.objExists(dest):
                    dest = '{}.visibility'.format(obj)
            else:
                dest = '{}.{}'.format(obj, attr)
            if typename == 'Mat4':
                connect_matrix_to_transform('{}.{}'.format(node, name), dest)
            else:
                cmds.connectAttr('{}.{}'.format(node, name), dest)
        else:
            cmds.connectAttr('{}.{}'.format(obj, attr), '{}.{}'.format(node, name))

    if dll_mode:
        cmds.setAttr('{}.nemo'.format(node), path_config, type="string")
        cmds.polyEvaluate('DummyShape', v=True)
    else:
        cmds.setAttr('{}.resource'.format(node), path_resource, type="string")