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


class Exporter:

    def __init__(self, parser_ctor, debug):
        self.parser = parser_ctor()
        self.modules = []
        self.dir_modules = None
        self.dir_proj = None
        self.identifier = None
        self.debug = debug

    def init(self):
        self.parser.init(self.dir_proj, self.debug)

    def set_modules_dir(self, dir):
        self.dir_modules = dir
        self.append_module("builtin")

    def set_project_dir(self, dir):
        self.dir_proj = dir

    def set_identifier(self, identifier):
        self.identifier = identifier

    def append_module(self, name):
        self.check_header()
        self.modules.append(name)
        self.parser.append_module_path('{}/{}.json'.format(self.dir_modules, name))

    def parse(self, inputs, outputs, callback=None):
        self.parser.set_inputs(inputs)
        succeed = True
        for i, x in enumerate(outputs):
            if not self.parser.parse(x):
                succeed = False
            if callback:
                callback(int(100 * float(i+1) / float(len(outputs))))
        self.parser.clean()
        if not succeed:
            return False

        self.parser.dump_graph(self.path_graph())
        self.parser.dump_resource(self.path_resource())
        if self.debug:
            self.parser.dump_debug(self.path_debug())
        return True

    def check_header(self):
        if not self.dir_proj:
            raise RuntimeError("[Nemo]project dir not set.")
        if not self.identifier:
            raise RuntimeError("[Nemo]identifier not set.")
        if not self.dir_modules:
            raise RuntimeError("[Nemo]modules dir not set.")
        return True

    def path_graph(self):
        self.check_header()
        return '{}/{}__GRAPH.json'.format(self.dir_proj, self.identifier)

    def path_resource(self):
        self.check_header()
        return '{}/{}__RESOURCE.nemodata'.format(self.dir_proj, self.identifier)

    def path_debug(self):
        self.check_header()
        return '{}/{}__DEBUG.json'.format(self.dir_proj, self.identifier)