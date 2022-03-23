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

import os
import json
import shutil
import imp

from maya import cmds

import exporter
from get_io import get_io
from nemo.filter.scene_collect import get_controllers, get_meshes
from nemo.filter.expressions_destructor import convert_all_expressions
import export_controllers


def preprocess():
    convert_all_expressions()


def _process(identifier, controllers, shapes, project_dir, addons=[], debug=False):
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
    os.mkdir(project_dir)

    inputs, outputs = get_io(controllers, shapes)

    if debug:
        bak_file_path = cmds.file(q=True, sn=True)
        filename = cmds.file(q=True, sn=True, shn=True)
        base, ext = os.path.splitext(filename)
        cmds.file(rename="{}/{}.nemo.preprocessed{}".format(project_dir, base, ext))
        cmds.file(save=True, type="mayaAscii")
        cmds.file(rename=bak_file_path)

    scene_data = export_controllers.export(identifier, controllers, shapes)
    path_scene = '{}/{}__SCENE.json'.format(project_dir, identifier)
    with open(path_scene, 'w') as f:
        json.dump(scene_data, f)

    import NemoMaya
    nemo = exporter.Exporter(NemoMaya.Parser)
    nemo.set_project_dir(project_dir)
    nemo.set_identifier(identifier)

    nemo.set_modules_dir(os.path.realpath('{}/modules'.format(os.environ['NEMO_ROOT'])))
    for plugin in ['matrixNodes'] + addons:
        cmds.loadPlugin(plugin, quiet=True)
        nemo.append_module(plugin)

    nemo.parser.init()

    addons_data = []
    for x in addons:
        spec_path = '{}/modules/{}.py'.format(os.environ['NEMO_ROOT'], x)
        if not os.path.exists(spec_path):
            continue
        mod = imp.load_source(x, spec_path)
        addons_data += mod.add_custom_parameters(nemo.parser)

    nemo.parse(inputs, outputs, debug)
    # WARNING: addons_data can only be dropped after this moment as parsing done.
    del addons_data

    return nemo.path_graph(), nemo.path_resource(), path_scene, nemo.path_debug() if debug else None


def process(identifier, mayafile, project_dir, debug=True):
    cmds.file(mayafile, o=True, f=True)
    preprocess()

    controllers = get_controllers("*")
    shapes = get_meshes(["Geometry|high|", "Geometry|temp|"])
    return _process(identifier, controllers, shapes, project_dir, addons=["quatNodes", "weightDriver"], debug=debug)
