"""
The preferences menu handles:
 - Font Size
 - Background Color
 - Text Color
 - Annotation Color
 - Annotation Size
 - Clipping Min
 - Clipping Max
"""
from __future__ import print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QLabel, QPushButton, QGridLayout, QApplication, QHBoxLayout, QVBoxLayout,
    QColorDialog, QLineEdit, QCheckBox, QComboBox)

from pyNastran.gui.utils.qt.pydialog import PyDialog, check_float
from pyNastran.gui.utils.qt.qpush_button_color import QPushButtonColor


class CuttingPlaneWindow(PyDialog):
    """
    +--------------------+
    | CuttingPlaneWindow |
    +------------------------+
    | Origin/P1   cid  x y z |
    | P2          cid  x y z |
    | z-axis      cid  x y z |
    | tol         cid  x y z |
    |                        |
    |    Apply OK Cancel     |
    +------------------------+
    """
    def __init__(self, data, win_parent=None):
        """
        Saves the data members from data and
        performs type checks
        """
        PyDialog.__init__(self, data, win_parent)

        self._updated_preference = False

        self._default_font_size = data['font_size']

        #self.dim_max = data['dim_max']
        self.cids = data['cids']
        #self._origin = data['origin']
        #self._p1 = data['origin']
        #self._p2 = data['origin']

        #self.out_data = data

        self.plane_color_float, self.plane_color_int = _check_color(
            data['plane_color'])
        self.methods = ['Z-Axis Projection', 'CORD2R']
        self.zaxis_methods = ['Global Z', 'Camera Normal', 'Manual']
        self._zaxis_method = 0  # Global Z

        self.setWindowTitle('Cutting Plane')
        self.create_widgets()
        self.create_layout()
        self.set_connections()
        self.on_font(self._default_font_size)
        #self.on_gradient_scale()
        #self.show()

    def create_widgets(self):
        """creates the display window"""
        # CORD2R
        #self.origin_label = QLabel("Origin:")
        #self.zaxis_label = QLabel("Z Axis:")
        #self.xz_plane_label = QLabel("XZ Plane:")

        # Z-Axis Projection
        self.p1_label = QLabel("Origin/P1:")
        self.p2_label = QLabel("P2:")
        self.zaxis_label = QLabel("Z Axis:")

        self.method_pulldown = QComboBox()
        for method in self.methods:
            self.method_pulldown.addItem(method)

        self.zaxis_method_pulldown = QComboBox()
        for method in self.zaxis_methods:
            self.zaxis_method_pulldown.addItem(method)

        self.cid_label = QLabel("Coordinate System:")
        self.p1_cid_pulldown = QComboBox()
        self.p2_cid_pulldown = QComboBox()
        self.zaxis_cid_pulldown = QComboBox()

        cid_global_str = '0/Global'
        for cid in sorted(self.cids):
            if cid == 0:
                cid_str = cid_global_str
            else:
                cid_str = str(cid)
            #print('cid_str = %r' % cid_str)
            self.p1_cid_pulldown.addItem(cid_str)
            self.p2_cid_pulldown.addItem(cid_str)
            self.zaxis_cid_pulldown.addItem(cid_str)

        self.p1_cid_pulldown.setCurrentIndex(0)
        self.p2_cid_pulldown.setCurrentIndex(0)
        self.zaxis_cid_pulldown.setCurrentIndex(0)
        if len(self.cids) == 1:
            self.p1_cid_pulldown.setEnabled(False)
            self.p2_cid_pulldown.setEnabled(False)
            self.zaxis_cid_pulldown.setEnabled(False)

        #self.p1_cid_pulldown.setItemText(0, cid_str)
        #self.p2_cid_pulldown.setItemText(0, cid_str)
        #self.zaxis_cid_pulldown.setItemText(0, cid_str)

        self.p1_cid_pulldown.setToolTip('Defines the coordinate system for the Point P1')
        self.p2_cid_pulldown.setToolTip('Defines the coordinate system for the Point P2')
        self.zaxis_cid_pulldown.setToolTip('Defines the coordinate system for the Z Axis')

        self.p1_x_edit = QLineEdit('')
        self.p1_y_edit = QLineEdit('')
        self.p1_z_edit = QLineEdit('')

        self.p2_x_edit = QLineEdit('')
        self.p2_y_edit = QLineEdit('')
        self.p2_z_edit = QLineEdit('')

        self.zaxis_x_edit = QLineEdit('')
        self.zaxis_y_edit = QLineEdit('')
        self.zaxis_z_edit = QLineEdit('')

        self.ytol_edit = QLineEdit('10.0')
        self.zero_tol_edit = QLineEdit('1e-5')

        self.p2_label = QLabel("P2:")

        # Plane Color
        self.plane_color_label = QLabel("Plane Color:")
        self.plane_color_edit = QPushButtonColor(self.plane_color_int)

        self.corner_coord_label = QLabel("Show Corner Coordinate System:")
        self.corner_coord_checkbox = QCheckBox()
        #self.corner_coord_checkbox.setChecked(self._show_corner_coord)

        #-----------------------------------------------------------------------
        # closing
        self.apply_button = QPushButton("Apply")
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

    def create_layout(self):
        grid = QGridLayout()
        self.method_label = QLabel('Method:')
        self.location_method_label = QLabel('Method:')

        self.location_label = QLabel('Location:')
        self.zaxis_method_label = QLabel('Z-Axis Method:')
        self.method_projected_label1 = QLabel('Projected')
        self.method_projected_label2 = QLabel('Projected')
        self.cid_label = QLabel('Coordinate System:')
        self.x_label = QLabel('X')
        self.y_label = QLabel('Y')
        self.z_label = QLabel('Z')
        self.ytol_label = QLabel('Y Tolerance:')
        self.zero_tol_label = QLabel('Zero Tolerance:')

        self.location_label.setAlignment(Qt.AlignCenter)
        self.cid_label.setAlignment(Qt.AlignCenter)
        self.method_label.setAlignment(Qt.AlignCenter)
        self.location_method_label.setAlignment(Qt.AlignCenter)

        self.method_projected_label1.setAlignment(Qt.AlignCenter)
        self.method_projected_label2.setAlignment(Qt.AlignCenter)

        self.x_label.setAlignment(Qt.AlignCenter)
        self.y_label.setAlignment(Qt.AlignCenter)
        self.z_label.setAlignment(Qt.AlignCenter)
        irow = 0
        grid.addWidget(self.method_label, irow, 0)
        grid.addWidget(self.method_pulldown, irow, 1)
        irow += 1
        self._add_grid_layout(grid, irow, is_cord2r=True)

        #----------------------------------------------
        grid2 = QGridLayout()
        irow = 0
        grid2.addWidget(self.method_label, irow, 0)
        grid2.addWidget(self.method_pulldown, irow, 1)
        irow += 1
        self._add_grid_layout(grid2, irow, is_cord2r=False)
        #----------------------------------------------

        ok_cancel_box = QHBoxLayout()
        ok_cancel_box.addWidget(self.apply_button)
        ok_cancel_box.addWidget(self.ok_button)
        ok_cancel_box.addWidget(self.cancel_button)

        vbox = QVBoxLayout()

        #if 0:
            #button_frame = QFrame()
            ##button_frame.setFrameStyle(QFrame.Plain | QFrame.Box)
            #button_frame.setFrameStyle(QFrame.Box)
            #button_frame.setLayout(grid)
        #else:
            #button_frame = QGroupBox()
            #button_frame.setLayout(grid)
            #vbox.addWidget(button_frame)

        vbox.addLayout(grid)
        #vbox.addStretch()
        #vbox.addLayout(grid2)
        vbox.addStretch()

        #-----------------------
        vbox.addLayout(ok_cancel_box)
        self.on_method(0)
        self.on_zaxis_method(0)
        self.setLayout(vbox)

    def _add_grid_layout(self, grid, irow, is_cord2r=True):
        j = -1
        grid.addWidget(self.location_label, irow, 0)
        if is_cord2r:
            grid.addWidget(self.location_method_label, irow, 1)
            j = 0
        grid.addWidget(self.cid_label, irow, j+2)
        grid.addWidget(self.x_label, irow, j+3)
        grid.addWidget(self.y_label, irow, j+4)
        grid.addWidget(self.z_label, irow, j+5)
        irow += 1

        j = -1
        grid.addWidget(self.p1_label, irow, 0)
        if is_cord2r:
            grid.addWidget(self.method_projected_label1, irow, 1)
            j = 0
        grid.addWidget(self.p1_cid_pulldown, irow, j+2)
        grid.addWidget(self.p1_x_edit, irow, j+3)
        grid.addWidget(self.p1_y_edit, irow, j+4)
        grid.addWidget(self.p1_z_edit, irow, j+5)
        irow += 1

        j = -1
        grid.addWidget(self.p2_label, irow, 0)
        if is_cord2r:
            grid.addWidget(self.method_projected_label2, irow, 1)
            j = 0
        grid.addWidget(self.p2_cid_pulldown, irow, j+2)
        grid.addWidget(self.p2_x_edit, irow, j+3)
        grid.addWidget(self.p2_y_edit, irow, j+4)
        grid.addWidget(self.p2_z_edit, irow, j+5)
        irow += 1

        j = -1
        grid.addWidget(self.zaxis_label, irow, 0)
        if is_cord2r:
            grid.addWidget(self.zaxis_method_pulldown, irow, 1)
            j = 0
        grid.addWidget(self.zaxis_cid_pulldown, irow, j+2)
        grid.addWidget(self.zaxis_x_edit, irow, j+3)
        grid.addWidget(self.zaxis_y_edit, irow, j+4)
        grid.addWidget(self.zaxis_z_edit, irow, j+5)
        irow += 1

        #-----------------------------------------
        #spacer_item = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        grid.addWidget(self.ytol_label, irow, 0)
        grid.addWidget(self.ytol_edit, irow, 1)
        #grid.addItem(spacer_item, irow, 2)
        irow += 1

        grid.addWidget(self.zero_tol_label, irow, 0)
        grid.addWidget(self.zero_tol_edit, irow, 1)
        irow += 1

        grid.addWidget(self.plane_color_label, irow, 0)
        grid.addWidget(self.plane_color_edit, irow, 1)
        irow += 1

        #grid.addWidget(self.corner_coord_label, irow, 0)
        #grid.addWidget(self.corner_coord_checkbox, irow, 1)
        #irow += 1

    def set_connections(self):
        self.method_pulldown.currentIndexChanged.connect(self.on_method)
        self.zaxis_method_pulldown.currentIndexChanged.connect(self.on_zaxis_method)
        self.plane_color_edit.clicked.connect(self.on_plane_color)

        self.apply_button.clicked.connect(self.on_apply)
        self.ok_button.clicked.connect(self.on_ok)
        self.cancel_button.clicked.connect(self.on_cancel)
        # closeEvent
        return

    def on_method(self, method_int=None):
        method = get_pulldown_text(method_int, self.methods, self.method_pulldown)
        if method == 'Z-Axis Projection':
            is_cord2r = False
        elif method == 'CORD2R':
            is_cord2r = True
        else:
            raise NotImplementedError(method)
        if is_cord2r:
            p1_label_text = 'Origin:'
            p2_label_text = 'Z Axis:'
            p3_label_text = 'XZ Plane:'
        else:
            p1_label_text = 'Origin/P1:'
            p2_label_text = 'P1:'
            p3_label_text = 'Z-Axis:'

        self.p1_label.setText(p1_label_text)
        self.p2_label.setText(p2_label_text)
        self.zaxis_label.setText(p3_label_text)

        if is_cord2r:
            self._zaxis_method = self.zaxis_method_pulldown.currentIndex()
            # set to manual
            #self.on_zaxis_method(method_int=2)  # manual

            self.zaxis_method_pulldown.setCurrentIndex(2)
            self.on_zaxis_method()  # update
        else:
            self.zaxis_method_pulldown.setCurrentIndex(self._zaxis_method)
            self.on_zaxis_method()  # update

        # works
        self.zaxis_method_pulldown.setEnabled(not is_cord2r)
        #self.cid_label.setVisible(not is_cord2r)
        self.method_projected_label1.setVisible(not is_cord2r)
        self.method_projected_label2.setVisible(not is_cord2r)
        self.location_method_label.setVisible(not is_cord2r)
        self.zaxis_method_pulldown.setVisible(not is_cord2r)

    def on_zaxis_method(self, method_int=None):
        method = get_pulldown_text(method_int, self.zaxis_methods, self.zaxis_method_pulldown)

        if method == 'Global Z':
            is_visible = False
        elif method == 'Camera Normal':
            is_visible = False
        elif method == 'Manual':
            is_visible = True
        else:
            raise NotImplementedError(method)

        self.zaxis_cid_pulldown.setVisible(is_visible)
        self.zaxis_x_edit.setVisible(is_visible)
        self.zaxis_y_edit.setVisible(is_visible)
        self.zaxis_z_edit.setVisible(is_visible)

    def on_font(self, value=None):
        """update the font for the current window"""
        if value is None:
            value = self.font_size_edit.value()
        font = QtGui.QFont()
        font.setPointSize(value)
        self.setFont(font)

    #def on_corner_coord(self):
        #is_checked = self.corner_coord_checkbox.isChecked()
        #if self.win_parent is not None:
            #self.win_parent.set_corner_axis_visiblity(is_checked, render=True)

    def on_plane_color(self):
        """ Choose a plane color"""
        title = "Choose a cutting plane color"
        rgb_color_ints = self.plane_color_int
        color_edit = self.plane_color_edit
        func_name = 'set_plane_color'
        passed, rgb_color_ints, rgb_color_floats = self._background_color(
            title, color_edit, rgb_color_ints, func_name)
        if passed:
            self.plane_color_int = rgb_color_ints
            self.plane_color_float = rgb_color_floats

    def _background_color(self, title, color_edit, rgb_color_ints, func_name):
        """helper method for ``on_background_color`` and ``on_background_color2``"""
        passed, rgb_color_ints, rgb_color_floats = self.on_color(
            color_edit, rgb_color_ints, title)
        if passed and 0:
            if self.win_parent is not None:
                settings = self.win_parent.settings
                func_background_color = getattr(settings, func_name)
                func_background_color(rgb_color_floats)
        return passed, rgb_color_ints, rgb_color_floats

    def on_color(self, color_edit, rgb_color_ints, title):
        """pops a color dialog"""
        col = QColorDialog.getColor(QtGui.QColor(*rgb_color_ints), self,
                                    title)
        if not col.isValid():
            return False, rgb_color_ints, None

        color_float = col.getRgbF()[:3]  # floats
        color_int = [int(colori * 255) for colori in color_float]

        assert isinstance(color_float[0], float), color_float
        assert isinstance(color_int[0], int), color_int

        color_edit.setStyleSheet(
            "QPushButton {"
            "background-color: rgb(%s, %s, %s);" % tuple(color_int) +
            #"border:1px solid rgb(255, 170, 255); "
            "}")
        return True, color_int, color_float


    #---------------------------------------------------------------------------

    def on_validate(self):
        p1_cidi = self.p1_cid_pulldown.currentText()
        p2_cidi = self.p2_cid_pulldown.currentText()
        zaxis_cidi = self.zaxis_cid_pulldown.currentText()
        p1_cid = int(p1_cidi) if 'Global' not in p1_cidi else 0
        p2_cid = int(p2_cidi) if 'Global' not in p2_cidi else 0
        zaxis_cid = int(zaxis_cidi) if 'Global' not in zaxis_cidi else 0
        #print('p1_cidi=%r p2_cidi=%r p3_cidi=%r' % (p1_cidi, p2_cidi, zaxis_cidi))
        #print('p2_cid=%r p2_cid=%r p3_cidi=%r' % (p2_cid, p2_cid, zaxis_cid))

        p1_x, flag0 = check_float(self.p1_x_edit)
        p1_y, flag1 = check_float(self.p1_y_edit)
        p1_z, flag2 = check_float(self.p1_z_edit)

        p2_x, flag3 = check_float(self.p2_x_edit)
        p2_y, flag4 = check_float(self.p2_y_edit)
        p2_z, flag5 = check_float(self.p2_z_edit)
        p1 = [p1_x, p1_y, p1_z]
        p2 = [p2_x, p2_y, p2_z]

        zaxis_method = str(self.zaxis_method_pulldown.currentText())
        flag6, flag7, flag8 = True, True, True
        if zaxis_method == 'Global Z':
            zaxis = [0., 0., 1.]
            zaxis_cid = 0
        elif zaxis_method == 'Manual':
            zaxis_x, flag6 = check_float(self.zaxis_x_edit)
            zaxis_y, flag7 = check_float(self.zaxis_y_edit)
            zaxis_z, flag8 = check_float(self.zaxis_z_edit)
            zaxis = [zaxis_x, zaxis_y, zaxis_z]
        elif zaxis_method == 'Camera Normal':
            if self.win_parent is not None:
                camera = self.win_parent.GetCamera()
                zaxis = camera.GetViewPlaneNormal()
            else:
                zaxis = [1., 1., 1.]
            zaxis_cid = 0
        else:
            raise NotImplementedError(zaxis_method)
        #print('zaxis =', zaxis)

        method = self.method_pulldown.currentText()
        assert method in self.methods, 'method=%r' % method
        flag9 = True

        ytol, flag10 = check_float(self.ytol_edit)
        zero_tol, flag11 = check_float(self.zero_tol_edit)

        flags = [flag0, flag1, flag2, flag3, flag4, flag5,
                 flag6, flag7, flag8,
                 flag9, flag10, flag11]
        if all(flags):
            self.out_data['method'] = method
            self.out_data['p1'] = [p1_cid, p1]
            self.out_data['p2'] = [p2_cid, p2]
            self.out_data['zaxis'] = [zaxis_method, zaxis_cid, zaxis]
            self.out_data['ytol'] = ytol
            self.out_data['zero_tol'] = zero_tol
            self.out_data['plane_color'] = self.plane_color_float
            self.out_data['plane_opacity'] = 0.6
            self.out_data['clicked_ok'] = True
            return True
        return False

    def on_apply(self, force=False):
        passed = self.on_validate()

        if (passed or force) and self.win_parent is not None:
            self.win_parent.make_cutting_plane_from_data(self.out_data)
        return passed

    def on_ok(self):
        passed = self.on_apply()
        if passed:
            self.close()
            #self.destroy()

    def on_cancel(self):
        self.out_data['close'] = True
        self.close()

def _check_color(color_float):
    assert len(color_float) == 3, color_float
    assert isinstance(color_float[0], float), color_float
    color_int = [int(colori * 255) for colori in color_float]
    return color_float, color_int

def get_pulldown_text(method_int, methods, pulldown):
    if method_int is None:
        #method = pulldown.getText()
        method = pulldown.currentText()
    else:
        method = methods[method_int]
    return method

def main():
    # kills the program when you hit Cntl+C from the command line
    # doesn't save the current state as presumably there's been an error
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)


    import sys
    # Someone is launching this directly
    # Create the QApplication
    app = QApplication(sys.argv)
    #The Main window
    data = {
        'font_size' : 8,
        #'cids' : [0, 1, 2, 3],
        'cids' : [0],
        'plane_color' : (1., 0., 1.), # purple
        'name' : 'main',

    }
    main_window = CuttingPlaneWindow(data)
    main_window.show()
    # Enter the main loop
    app.exec_()

if __name__ == "__main__":
    main()
