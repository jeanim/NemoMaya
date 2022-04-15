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
from PySide2 import QtWidgets, QtCore
from PySide2.QtWidgets import QMessageBox
import maya.OpenMayaUI as omui
from maya import cmds

import os
import json


def get_nemo_root():
    if 'NEMO_ROOT' in os.environ:
        return os.environ['NEMO_ROOT']
    raise RuntimeError("Env NEMO_ROOT must be set first")


import sys

sys.path.insert(0, "{}/extern".format(get_nemo_root()))
sys.path.insert(0, "{}".format(get_nemo_root()))

import Qt
import dayu_widgets


def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return Qt.QtCompat.wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


class WidgetNemoExporter(QtWidgets.QWidget):

    def __init__(self, parent=maya_main_window()):
        super(WidgetNemoExporter, self).__init__()
        self.setParent(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Nemo Exporter")
        self.layout = self.create_ui()
        self.controllers = []
        self.setLayout(self.layout)
        cmds.select(cl=True)

        if cmds.optionVar(exists='NEMO_EXPORT_CONFIG'):
            self.load_config(json.loads(cmds.optionVar(q='NEMO_EXPORT_CONFIG')))
        else:
            self.load_config(dict())

    def create_ui(self):
        main_layout = QtWidgets.QVBoxLayout()

        main_layout.addWidget(self.create_version())
        main_layout.addLayout(self.create_controllers())
        main_layout.addLayout(self.create_shapes())
        main_layout.addLayout(self.create_export())
        main_layout.addStretch()
        return main_layout

    def create_version(self):
        timestamp = "<unknown>"
        try:
            import NemoMaya
            timestamp = NemoMaya.get_timestamp()
        except:
            pass
        return dayu_widgets.MLabel("Timestamp: {}".format(timestamp))

    def create_controllers(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dayu_widgets.MDivider("Controllers"))

        label_readme = dayu_widgets.MLabel("Nemo need to know all controllers in this rig. It could be configured by GLOB and filters.").secondary()
        label_readme.setWordWrap(True)
        layout.addWidget(label_readme)

        self.list_glob = QtWidgets.QListWidget()
        self.list_glob.setFixedHeight(60)
        layout.addWidget(self.list_glob)

        self.text_controller_patterns = dayu_widgets.MLineEdit("<GLOB>")
        label_head = dayu_widgets.MLabel(text="Pattern").mark().secondary()
        label_head.setAlignment(QtCore.Qt.AlignCenter)
        label_head.setFixedWidth(60)
        self.text_controller_patterns.set_prefix_widget(label_head)
        layout.addWidget(self.text_controller_patterns)

        layout_list = QtWidgets.QHBoxLayout()
        btn_remove_current = dayu_widgets.MPushButton("Remove")
        btn_remove_current.clicked.connect(lambda: self.list_glob.takeItem(self.list_glob.currentRow()
                                                                           if self.list_glob.hasFocus() else self.list_prefix.count() - 1))
        btn_remove_current.clicked.connect(self.on_change_controller_pattern)
        layout_list.addWidget(btn_remove_current)
        btn_add_pattern = dayu_widgets.MPushButton("Add")
        btn_add_pattern.clicked.connect(lambda: self.list_glob.addItem(self.text_controller_patterns.text()))
        btn_add_pattern.clicked.connect(self.on_change_controller_pattern)
        layout_list.addWidget(btn_add_pattern)
        layout.addLayout(layout_list)

        self.tags_controllers = dayu_widgets.MCheckBoxGroup()
        self.tags_controllers.set_button_list(["Curve", "Surface", "Free", "Visible"])
        self.tags_controllers.sig_checked_changed.connect(self.on_change_controller_pattern)
        layout.addWidget(self.tags_controllers)

        btn_controllers = dayu_widgets.MPushButton("Select Controllers")
        btn_controllers.clicked.connect(self.on_select_controllers)
        layout.addWidget(btn_controllers)

        layout_list = QtWidgets.QHBoxLayout()
        btn_append = dayu_widgets.MPushButton("Append")
        btn_append.clicked.connect(self.append_select_controllers)
        layout_list.addWidget(btn_append)
        btn_deslect = dayu_widgets.MPushButton("Deselect")
        btn_deslect.clicked.connect(self.deselect_controllers)
        layout_list.addWidget(btn_deslect)
        layout.addLayout(layout_list)

        return layout

    def get_controllers(self):
        if self.controllers:
            return self.controllers

        patterns = [self.list_glob.item(row).text() for row in range(self.list_glob.count())]
        args = {'patterns': patterns}
        for x in self.tags_controllers.get_dayu_checked():
            args[str(x).lower()] = True

        from nemo.filter import scene_collect
        return scene_collect.get_controllers(**args)

    def append_select_controllers(self):
        selection = cmds.ls(sl=True)
        for x in selection:
            if cmds.nodeType(x) not in {'transform', 'joint'}:
                QMessageBox.critical(self, "Controller can only be transform or joint",
                                     '{}({}) is not allowed for controller. Please make sure not selecting any shapes.'.format(x, cmds.nodeType(x)))
                return

        if not self.controllers:
            self.controllers = self.get_controllers()
        self.controllers.extend(selection)
        self.on_select_controllers()

    def deselect_controllers(self):
        selection = cmds.ls(sl=True)
        if not selection:
            return

        if not self.controllers:
            self.controllers = self.get_controllers()
        print("deselect: ", selection)
        print("controllers before select:", len(self.controllers))
        self.controllers = [x for x in self.controllers if x not in selection]
        print("controllers after select:", len(self.controllers))
        self.on_select_controllers()

    def on_change_controller_pattern(self):
        if self.controllers:
            QMessageBox.information(self, "Attention", 'change controller patern will clear your manual selection')
            self.controllers = []

    def on_select_controllers(self):
        cmds.select(self.get_controllers())
        cmds.warning('{} controllers are selected. use `ls -sl` to list them.'.format(len(cmds.ls(sl=True))))

    def create_shapes(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dayu_widgets.MDivider("Shapes"))

        label_readme = dayu_widgets.MLabel("Mehses under any group list here would be passed to animators.").secondary()
        label_readme.setWordWrap(True)
        layout.addWidget(label_readme)

        self.list_prefix = QtWidgets.QListWidget()
        self.list_prefix.setFixedHeight(60)
        layout.addWidget(self.list_prefix)

        self.text_shape_groups = dayu_widgets.MLineEdit("<keyword>")
        label_head = dayu_widgets.MLabel(text="Group").mark().secondary()
        label_head.setAlignment(QtCore.Qt.AlignCenter)
        label_head.setFixedWidth(60)
        self.text_shape_groups.set_prefix_widget(label_head)
        layout.addWidget(self.text_shape_groups)

        layout_list = QtWidgets.QHBoxLayout()
        btn_remove_current = dayu_widgets.MPushButton("Remove")
        btn_remove_current.clicked.connect(lambda: self.list_prefix.takeItem(self.list_prefix.currentRow()
                                                                             if self.list_prefix.hasFocus() else self.list_prefix.count() - 1))
        layout_list.addWidget(btn_remove_current)
        btn_add_pattern = dayu_widgets.MPushButton("Add")
        btn_add_pattern.clicked.connect(lambda: self.list_prefix.addItem(self.text_shape_groups.text()))
        layout_list.addWidget(btn_add_pattern)
        layout.addLayout(layout_list)

        self.btn_shapes = dayu_widgets.MPushButton("Select Shapes")
        self.btn_shapes.clicked.connect(self.on_select_shapes)
        layout.addWidget(self.btn_shapes)
        return layout

    def get_shapes(self):
        from nemo.filter import scene_collect
        patterns = [self.list_prefix.item(row).text() for row in range(self.list_prefix.count())]
        return scene_collect.get_meshes(patterns)

    def on_select_shapes(self):
        cmds.select(self.get_shapes())
        print('{} meshes are selected'.format(len(cmds.ls(sl=True))))

    def create_export(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(dayu_widgets.MDivider("Export"))

        label_readme = dayu_widgets.MLabel(
            "All buttons above are merely for double check and can be skipped as long as the configuration is correct.").secondary()
        label_readme.setWordWrap(True)
        layout.addWidget(label_readme)

        self.text_name = dayu_widgets.MLineEdit("Dummy")
        label_head = dayu_widgets.MLabel(text="Name").mark().secondary()
        label_head.setAlignment(QtCore.Qt.AlignCenter)
        label_head.setFixedWidth(60)
        self.text_name.set_prefix_widget(label_head)
        layout.addWidget(self.text_name)

        layout_dir = QtWidgets.QHBoxLayout()
        self.browser_dir_export = dayu_widgets.MClickBrowserFolderToolButton()
        layout_dir.addWidget(self.browser_dir_export)
        label_dir = dayu_widgets.MLabel("<Select Output Folder>")
        label_dir.set_elide_mode(QtCore.Qt.ElideLeft)
        layout_dir.addWidget(label_dir)
        self.browser_dir_export.sig_folder_changed.connect(label_dir.setText)
        layout.addLayout(layout_dir)

        label_readme = dayu_widgets.MLabel(
            "Nemo could be extended to support in-house plug-ins by adding specifications under <NEMO_ROOT>/modules.").secondary()
        label_readme.setWordWrap(True)
        layout.addWidget(label_readme)
        import glob
        addons = [os.path.splitext(os.path.basename(x))[0] for x in glob.glob("{}/modules/*.json".format(get_nemo_root()))]
        addons = [x for x in addons if x not in {"builtin", "matrixNodes"}]
        self.tags_addons = dayu_widgets.MCheckBoxGroup()
        self.tags_addons.set_button_list(addons)
        layout.addWidget(self.tags_addons)

        self.btn_export = dayu_widgets.MPushButton("Parse")
        self.btn_export.clicked.connect(self.on_export)
        layout.addWidget(self.btn_export)

        self.progress_parse = dayu_widgets.MProgressBar().auto_color()
        layout.addWidget(self.progress_parse)
        return layout

    def on_export(self):
        from nemo.m2n import m2n
        path = self.browser_dir_export.dayu_path
        if path is None:
            QMessageBox.critical(self, "Error", "Must Select Output Folder First")
            return
        if os.listdir(path):
            if QMessageBox.StandardButton.No == QMessageBox.question(self, "Export folder not empty", "Do you really want to overwrite {}?".format(path)):
                return

        name = self.text_name.text()
        if "Dummy" == name:
            if QMessageBox.StandardButton.No == QMessageBox.question(self, "Name", "Is Dummy the correct name?"):
                return
        try:
            cmds.optionVar(sv=('NEMO_EXPORT_CONFIG', self.save_config()))

            m2n._process(name,
                         self.get_controllers(),
                         self.get_shapes(),
                         str(path),
                         addons=self.tags_addons.get_dayu_checked(),
                         debug=True,
                         callback=lambda percent: self.progress_parse.setValue(percent))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        else:
            QMessageBox.information(self, "Success", '{} has been exported to {}'.format(name, path))

    def save_config(self):
        config = dict()
        config['ctrl_pattern'] = [self.list_glob.item(row).text() for row in range(self.list_glob.count())]
        config['ctrl_tags'] = [str(x) for x in self.tags_controllers.get_dayu_checked()]
        config['shapes_keyword'] = [self.list_prefix.item(row).text() for row in range(self.list_prefix.count())]
        config['export_dir'] = str(self.browser_dir_export.dayu_path)
        config['addons'] = [str(x) for x in self.tags_addons.get_dayu_checked()]
        return json.dumps(config)

    def load_config(self, config):
        try:
            for pattern in config.get('ctrl_pattern', ['*']):
                self.list_glob.addItem(pattern)
            self.tags_controllers.set_dayu_checked(config.get('ctrl_tags', ["Curve", "Free", "Visible"]))
            for keyword in config.get('shapes_keyword', ['Geometry|high|', 'Geometry|temp|']):
                self.list_prefix.addItem(keyword)
            if 'export_dir' in config:
                self.browser_dir_export.set_dayu_path(config['export_dir'])
                self.browser_dir_export.sig_folder_changed.emit(self.browser_dir_export.get_dayu_path())
            self.tags_addons.set_dayu_checked(config.get('addons', ["quatNodes"]))
        except Exception:
            pass


def show():
    widget = WidgetNemoExporter()
    from dayu_widgets import dayu_theme
    dayu_theme.apply(widget)
    widget.show()


if __name__ == "__main__":
    show()
