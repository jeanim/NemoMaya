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

import NemoMaya
import maya.OpenMaya as om


class WeightDriverOrientParameter(NemoMaya.Vec3CustomParameter):

    def __init__(self):
        super(WeightDriverOrientParameter, self).__init__()
        self.method_name = "weightDriverDrivers"

    def get(self, plug, _):
        node = om.MFnDependencyNode(plug.node())
        plug_driver_input = node.findPlug("driverList").elementByLogicalIndex(0).child(0)
        driver_obj = plug_driver_input.source().node()
        if driver_obj.apiTypeStr() == 'kJoint':
            plug_orient = om.MFnDependencyNode(driver_obj).findPlug("jointOrient")
            data = plug_orient.asMDataHandle().asDouble3()
            return NemoMaya.vec3(data[0], data[1], data[2])
        else:
            return NemoMaya.vec3(0, 0, 0)


def add_custom_parameters(parser):
    param = WeightDriverOrientParameter()
    parser.add_custom_parameter(param)
    return [param]