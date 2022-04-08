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

from PySide2 import QtWidgets, QtCore
from PySide2.QtWidgets import QMessageBox
import maya.OpenMayaUI as omui
from maya import cmds

import os
import glob


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


class WidgetNemoAssembler(QtWidgets.QWidget):
    symbol_unknown = "<Unknown>"

    def __init__(self, parent=maya_main_window()):
        super(WidgetNemoAssembler, self).__init__()
        self.setParent(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("Nemo Assembler")
        self.layout = self.create_ui()
        self.setLayout(self.layout)

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self.create_version())

        layout_name = QtWidgets.QHBoxLayout()
        label_head = dayu_widgets.MLabel(text="Name:")
        label_head.setAlignment(QtCore.Qt.ElideLeft)
        label_head.setFixedWidth(60)
        layout_name.addWidget(label_head)
        self.label_name = dayu_widgets.MLabel(text=WidgetNemoAssembler.symbol_unknown)
        self.label_name.setAlignment(QtCore.Qt.AlignCenter)
        layout_name.addWidget(self.label_name)
        layout.addLayout(layout_name)

        layout_receive = QtWidgets.QHBoxLayout()
        layout_receive.addWidget(dayu_widgets.MLabel("Receive:"))
        self.browser_dir_receive = dayu_widgets.MClickBrowserFolderToolButton()
        layout_receive.addWidget(self.browser_dir_receive)
        label_receive = dayu_widgets.MLabel("<Select Folder>")
        label_receive.set_elide_mode(QtCore.Qt.ElideLeft)
        layout_receive.addWidget(label_receive)
        self.browser_dir_receive.sig_folder_changed.connect(label_receive.setText)
        self.browser_dir_receive.sig_folder_changed.connect(self.on_select_receive_folder)
        layout.addLayout(layout_receive)

        layout_upload = QtWidgets.QHBoxLayout()
        layout_upload.addWidget(dayu_widgets.MLabel("Export: "))
        self.browser_dir_upload = dayu_widgets.MClickBrowserFolderToolButton()
        layout_upload.addWidget(self.browser_dir_upload)
        self.label_upload = dayu_widgets.MLabel("<Select Folder>")
        self.label_upload.set_elide_mode(QtCore.Qt.ElideLeft)
        layout_upload.addWidget(self.label_upload)
        self.browser_dir_upload.sig_folder_changed.connect(self.on_select_upload_folder)
        layout.addLayout(layout_upload)

        layout_output = QtWidgets.QHBoxLayout()
        layout_output.addWidget(dayu_widgets.MLabel("Runtime:"))
        self.browser_dir_output = dayu_widgets.MClickBrowserFolderToolButton()
        layout_output.addWidget(self.browser_dir_output)
        self.label_output = dayu_widgets.MLabel("<Select Folder>")
        self.label_output.set_elide_mode(QtCore.Qt.ElideLeft)
        layout_output.addWidget(self.label_output)
        self.browser_dir_output.sig_folder_changed.connect(self.on_select_output_folder)
        layout.addLayout(layout_output)

        btn_assemble = dayu_widgets.MPushButton("Assemble")
        btn_assemble.clicked.connect(self.on_assemble)
        layout.addWidget(btn_assemble)
        return layout

    @staticmethod
    def ext():
        return "mll" if "win32" == sys.platform else "so"

    def on_select_receive_folder(self, path):
        try:
            binary = glob.glob('{}/*.{}'.format(path, WidgetNemoAssembler.ext()))[0]
            self.label_name.setText(os.path.splitext(os.path.basename(binary))[0])
        except Exception as e:
            self.label_name.setText(WidgetNemoAssembler.symbol_unknown)

    def on_select_upload_folder(self, path):
        if path is None:
            return
        if path == self.browser_dir_output.dayu_path:
            QMessageBox.critical(self, "Error", "Export folder cannot be the same with Output folder")
            return
        self.label_upload.setText(path)

    def on_select_output_folder(self, path):
        if path is None:
            return
        if path == self.browser_dir_upload.dayu_path:
            QMessageBox.critical(self, "Error", "Output folder cannot be the same with Export folder")
            return
        self.label_output.setText(path)

    def on_assemble(self):
        name = self.label_name.text()
        if name == WidgetNemoAssembler.symbol_unknown:
            QMessageBox.critical(self, "Error", "Select Receive folder containing correct binary.")
            return

        dir_receive = str(self.browser_dir_receive.dayu_path)
        path_config = "{}/{}__CONFIG.json".format(dir_receive, name)
        path_bin = "{}/{}.{}".format(dir_receive, name, WidgetNemoAssembler.ext())
        dir_upload = str(self.browser_dir_upload.dayu_path)
        path_resource = "{}/{}__RESOURCE.nemodata".format(dir_upload, name)
        path_scene = "{}/{}__SCENE.json".format(dir_upload, name)

        import shutil
        try:
            dir_output = str(self.browser_dir_output.dayu_path)
            if os.listdir(dir_output):
                if QMessageBox.StandardButton.No == QMessageBox.question(self, "Export folder not empty",
                                                                         "Do you really want to overwrite {}?".format(dir_output)):
                    return
            new_path_resource = "{}/{}__RESOURCE.nemodata".format(dir_output, name)
            shutil.copy(path_resource, new_path_resource)
            path_resource = new_path_resource
            new_path_bin = "{}/{}.{}".format(dir_output, name, WidgetNemoAssembler.ext())
            shutil.copy(path_bin, new_path_bin)
            path_bin = new_path_bin

            from nemo.n2m import n2m
            n2m.assemble(path_config, path_scene, path_bin, path_resource, name, False)
            cmds.file(rename='{}/{}.ma'.format(dir_output, name))
            cmds.file(save=True, type="mayaAscii")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def create_version(self):
        timestamp = "<unknown>"
        try:
            import NemoMaya
            timestamp = NemoMaya.get_timestamp()
        except:
            pass
        return dayu_widgets.MLabel("Timestamp: {}".format(timestamp))


def show():
    widget = WidgetNemoAssembler()
    from dayu_widgets import dayu_theme
    dayu_theme.apply(widget)
    widget.show()


if __name__ == "__main__":
    show()
