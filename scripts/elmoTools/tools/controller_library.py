import sys
import os

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import Signal
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import Signal

import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# --- MAYA COLORS ---
def get_maya_index_color(index):
    if index == 0:
        return (60, 60, 60) # Grey soft for 0
    rgb_float = cmds.colorIndex(index, q=True)
    return (int(rgb_float[0]*255), int(rgb_float[1]*255), int(rgb_float[2]*255))

# --- CUSTOM FLOW LAYOUT ---
class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, hSpacing=-1, vSpacing=-1):
        super(FlowLayout, self).__init__(parent)
        self._hSpace = hSpacing
        self._vSpace = vSpacing
        self.setContentsMargins(margin, margin, margin, margin)
        self._itemList = []

    def addItem(self, item):
        self._itemList.append(item)

    def horizontalSpacing(self):
        if self._hSpace >= 0: return self._hSpace
        return self.spacing()

    def verticalSpacing(self):
        if self._vSpace >= 0: return self._vSpace
        return self.spacing()

    def count(self):
        return len(self._itemList)

    def itemAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList.pop(index)
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._itemList:
            size = size.expandedTo(item.minimumSize())
        size += QtCore.QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().bottom())
        return size

    def _doLayout(self, rect, testOnly):
        x, y = rect.x(), rect.y()
        lineHeight = 0
        spacingX = self.horizontalSpacing()
        spacingY = self.verticalSpacing()

        for item in self._itemList:
            wid = item.widget()
            spaceX = spacingX + wid.style().layoutSpacing(QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal)
            spaceY = spacingY + wid.style().layoutSpacing(QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical)
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

# --- WIDGETS ---

class ControllerItem(QtWidgets.QWidget):
    clicked = Signal(str)

    def __init__(self, name, icon_path=None, parent=None):
        super(ControllerItem, self).__init__(parent)
        self.name = name
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFixedSize(110, 130)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("""
            ControllerItem {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid transparent;
            }
            ControllerItem:hover {
                background-color: #454545;
                border: 1px solid #5285a6;
            }
        """)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(5)

        self.image_lbl = QtWidgets.QLabel()
        self.image_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.image_lbl.setStyleSheet("background-color: #2b2b2b; border-radius: 4px;")
        self.image_lbl.setFixedHeight(85)
        
        if icon_path and os.path.exists(icon_path):
            pixmap = QtGui.QPixmap(icon_path)
            self.image_lbl.setPixmap(pixmap.scaled(80, 80, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            self.image_lbl.setText("CTL")
        
        self.text_lbl = QtWidgets.QLabel(self.name)
        self.text_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.text_lbl.setStyleSheet("color: #e0e0e0; font-size: 10px;")
        
        font_metrics = QtGui.QFontMetrics(self.text_lbl.font())
        elided_text = font_metrics.elidedText(self.name, QtCore.Qt.ElideRight, 95)
        self.text_lbl.setText(elided_text)

        self.main_layout.addWidget(self.image_lbl)
        self.main_layout.addWidget(self.text_lbl)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.name)
            super(ControllerItem, self).mousePressEvent(event)


class ColorSwatch(QtWidgets.QPushButton):
    color_clicked = Signal(int)

    def __init__(self, index, parent=None):
        super(ColorSwatch, self).__init__(parent)
        self.index = index
        self.setFixedSize(44, 28) 
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Index: {}".format(index))
        
        r, g, b = get_maya_index_color(index)
        
        self.setStyleSheet("""
            QPushButton {{
                background-color: rgb({0}, {1}, {2});
                border: none;
                border-radius: 0px; 
            }}
            QPushButton:hover {{
                border: 1px solid #ffffff; /* Borde blanco al pasar el mouse para resaltar */
            }}
        """.format(r, g, b))
        
        self.clicked.connect(self._emit_index)

    def _emit_index(self):
        self.color_clicked.emit(self.index)


class ColorPickerWidget(QtWidgets.QFrame):
    index_selected = Signal(int)

    def __init__(self, parent=None):
        super(ColorPickerWidget, self).__init__(parent)
        self.setObjectName("ColorPickerFrame")
        
        self.layout = QtWidgets.QGridLayout(self)
        
        self.layout.setContentsMargins(5, 5, 5, 5) 
        self.layout.setSpacing(0)
        
        columns = 8
        for i in range(32):
            swatch = ColorSwatch(i)
            swatch.color_clicked.connect(self.index_selected.emit)
            row = i // columns
            col = i % columns
            self.layout.addWidget(swatch, row, col)


# --- MAIN INTERFACE ---
class ControllerCreatorUI(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    WINDOW_NAME = "ControllerCreatorWin"
    
    def __init__(self, parent=None):
        super(ControllerCreatorUI, self).__init__(parent=parent)
        self.setWindowTitle("Controller Library")
        self.resize(400, 650)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #333333;
                color: #eeeeee;
                font-family: "Segoe UI", sans-serif;
                font-size: 11px;
            }
            #HeaderFrame {
                background-color: #3b3b3b; 
                border-bottom: 1px solid #222;
            }
            #FooterFrame {
                background-color: #2b2b2b;
                border-top: 1px solid #1a1a1a;
            }
            #ColorPickerFrame {
                background-color: #2e2e2e;
                border-top: 1px solid #222;
            }
            QLineEdit {
                background-color: #222222;
                border: 1px solid #444;
                border-radius: 12px;
                padding: 4px 10px;
                color: #ddd;
            }
            QLineEdit:focus { border: 1px solid #5285a6; }
            QScrollArea { border: none; background-color: #252525; }
            QScrollBar:vertical { background: #252525; width: 12px; }
            QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 6px; margin: 2px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

            QPushButton#SaveBtn {
                background-color: #444444;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QPushButton#SaveBtn:hover { background-color: #5285a6; border-color: #6295b6; }
            QPushButton#SaveBtn:pressed { background-color: #3a607a; }
            
            QRadioButton { spacing: 5px; color: #ccc; }
            QRadioButton::indicator { width: 12px; height: 12px; border-radius: 6px; border: 1px solid #555; background-color: #333; }
            QRadioButton::indicator:checked { background-color: #5285a6; border: 1px solid #5285a6; }
            
            #FooterSeparator {
                background-color: #444;
                color: #444;
            }
        """)

        self.setup_ui()
        self.populate_dummy_data()

    def setup_ui(self):
        # Header
        self.header_frame = QtWidgets.QFrame()
        self.header_frame.setObjectName("HeaderFrame")
        header_layout = QtWidgets.QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 10, 10, 10)
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search controllers...")
        self.search_bar.textChanged.connect(self.filter_controllers)

        icon = QtGui.QIcon(":/search.png" )
        self.search_bar.addAction(icon, QtWidgets.QLineEdit.LeadingPosition)

        header_layout.addWidget(self.search_bar)
        self.main_layout.addWidget(self.header_frame)

        # Middle
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.container_widget = QtWidgets.QWidget()
        self.flow_layout = FlowLayout(self.container_widget, margin=15, hSpacing=15, vSpacing=15)
        self.scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(self.scroll_area)

        # COLOR PICKER
        self.color_picker = ColorPickerWidget()
        self.color_picker.index_selected.connect(self.on_color_index_clicked)
        self.main_layout.addWidget(self.color_picker)

        # Footer
        self.footer_frame = QtWidgets.QFrame()
        self.footer_frame.setObjectName("FooterFrame")
        footer_layout = QtWidgets.QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(10, 8, 10, 8)
        footer_layout.setSpacing(10)

        
        separator = QtWidgets.QFrame()
        separator.setObjectName("FooterSeparator")
        separator.setFrameShape(QtWidgets.QFrame.VLine)
        separator.setFrameShadow(QtWidgets.QFrame.Plain)
        separator.setLineWidth(1)
        separator.setFixedHeight(30)

        self.btn_save = QtWidgets.QPushButton("Save Selection")
        self.btn_save.setObjectName("SaveBtn")
        icon = QtGui.QIcon(":/save.png" )

        self.btn_save.setIcon(icon)
        self.btn_save.setFixedHeight(28)
        self.btn_save.clicked.connect(self.on_save_clicked)

        footer_layout.addWidget(separator)
        footer_layout.addWidget(self.btn_save)
        footer_layout.addStretch()

        self.main_layout.addWidget(self.footer_frame)

    def populate_dummy_data(self):
        dummy_names = [
            "arrow", "circle", "square", "triangle", "star", "cross",
        ]
        for name in dummy_names:
            self.add_controller_item(name)

    def add_controller_item(self, name, icon_path=None):
        item = ControllerItem(name, icon_path)
        item.clicked.connect(self.on_controller_clicked)
        self.flow_layout.addWidget(item)
        
    def filter_controllers(self, text):
        text = text.lower()
        for i in range(self.flow_layout.count()):
            widget = self.flow_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(text in widget.name.lower())

    def on_controller_clicked(self, name):
        print(">> Selected Controller: " + str(name))

    def on_color_index_clicked(self, index):
        print(">> Color Index Clicked: " + str(index))

    def on_save_clicked(self):
        print(">> Save Selection clicked.")

def show_ui():
    if cmds.window(ControllerCreatorUI.WINDOW_NAME, exists=True):
        cmds.deleteUI(ControllerCreatorUI.WINDOW_NAME)
    ui = ControllerCreatorUI()
    ui.show(dockable=True)
    return ui

if __name__ == "__main__":
    my_ui = show_ui()