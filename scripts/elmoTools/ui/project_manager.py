# Python libraries import
import os
import json
from importlib import reload
from functools import partial

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        from shiboken2 import wrapInstance
    except ImportError:
        cmds.error("Could not import PySide2 or PySide6. Check your Maya installation.")

# Maya commands import
from maya.api import OpenMaya as om
import maya.OpenMayaUI as omui
import maya.cmds as cmds

# elmoTools imports
from elmoTools.utils import core
import re


reload(core)

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)).split("\scripts")[0]

def asset_structure_creation(asset_name, model_path = False, guides_path = False, curves_path = False, skinning_path = False, asset_type = "CHAR"):
    """
    Function to create the basic asset folder structure.

    This function creates the necessary folder structure for a new asset
    """
    
    # Create main asset folder
    asset_path = os.path.join(SCRIPT_PATH, "assets", asset_name)
    if not os.path.exists(asset_path):
        os.makedirs(asset_path)
    else:
        # Asset folder already exists
        om.MGlobal.displayInfo(f"The asset folder already exists at: {asset_path}")
        return

    core.DataManager.clear_data()
    core.DataManager.set_project_path(asset_path)
    core.DataManager.set_asset_name(asset_name)
    
    configurations = {"asset_type": asset_type}
    # Create subfolders and handle custom paths
    extensions = [".guides", ".json", ".skn"]
    for i, (folder_names, path) in enumerate([("models", model_path), ("guides", guides_path), ("curves", curves_path), ("skinning", skinning_path)]):
        
        folder_path = os.path.join(asset_path, folder_names)
        
        if not os.path.exists(folder_path) and not path:
            os.makedirs(folder_path)
            configurations[folder_names] = "relative"

        elif path:
            if os.path.exists(path):
                folder_path = path
                configurations[folder_names] = folder_path
            else:
                om.MGlobal.displayError(f"The provided path for {folder_names} directory does not exist: {path}")
                return
        else:
            om.MGlobal.displayInfo(f"The {folder_names} directory already exists at: {folder_path}")
            configurations[folder_names] = "relative"
            return
        om.MGlobal.displayInfo(f"Asset folder structure created at: {asset_path}")

        # Create initial files in each subfolder
        if not folder_names == "models":
            initial_file = os.path.join(folder_path, f"{asset_type.upper()}_{asset_name}_001{extensions[i-1]}")
            if not os.path.exists(initial_file):
                with open(initial_file, 'w') as config_file:
                    json.dump(configurations, config_file, indent=4)
                om.MGlobal.displayInfo(f"Configuration file created at: {initial_file}")
            else:
                om.MGlobal.displayInfo(f"Configuration file already exists at: {initial_file}")
        else:
            cmds.file(new=True, force=True)
            cmds.file(rename=os.path.join(folder_path, f"{asset_type.upper()}_{asset_name}_0001.ma"))
            cmds.createNode("transform", name="skelMesh")
            cmds.createNode("transform", name="proxyMesh")
            cmds.createNode("transform", name="model")
            cmds.file(save=True, type="mayaAscii")



        # Store paths in DataManager
        if folder_names == "guides":
            core.DataManager.set_guide_data(folder_path)
        elif folder_names == "curves":
            core.DataManager.set_ctls_data(folder_path)
        elif folder_names == "skinning":
            core.DataManager.set_skinning_data(folder_path)

    # Create configuration file for setting relative or absolute paths
    config_file_path = os.path.join(asset_path, f"{asset_type.upper()}_{asset_name}_Paths.config")
    if not os.path.exists(config_file_path):
        with open(config_file_path, 'w') as config_file:
            json.dump(configurations, config_file, indent=4)
        om.MGlobal.displayInfo(f"Configuration file created at: {config_file_path}")
    else:
        om.MGlobal.displayInfo(f"Configuration file already exists at: {config_file_path}")

    extra_attrs_file_path = os.path.join(asset_path, f"{asset_type.upper()}_{asset_name}_extraAttrs.settings")
    if not os.path.exists(extra_attrs_file_path):
        with open(extra_attrs_file_path, 'w') as config_file:
            json.dump(configurations, config_file, indent=4)
        om.MGlobal.displayInfo(f"Extra Attrs file created at: {extra_attrs_file_path}")
    else:
        om.MGlobal.displayInfo(f"Extra Attrs file already exists at: {extra_attrs_file_path}")

def _highest_version_file_in_directory(folder_path, extension):
    """
    Function to load the highest versioned model file from a directory.
    Args:
        folder_path (str): The directory path to search for model files.
        extension (str): The file extension to look for (e.g., ".ma").
    """
    file_path = None
    candidates = []
    for fname in os.listdir(folder_path):
        if not fname.lower().endswith(extension):
            continue
        candidates.append((os.path.join(folder_path, fname)))
    if candidates:
        candidates.sort()
        file_path = candidates[-1]
    return file_path

def load_asset_configuration(asset_name):
    """
    Function to load asset configuration from the configuration file.

    This function reads the configuration file for the specified asset
    and sets the paths in the DataManager accordingly.
    """
    asset_path = os.path.join(SCRIPT_PATH, "assets", asset_name)
    
    # List files ending with .config on asset_path
    config_files = []
    if os.path.exists(asset_path):
        for fname in os.listdir(asset_path):
            full_path = os.path.join(asset_path, fname)
            if os.path.isfile(full_path) and fname.lower().endswith('.config') and asset_name in fname:
                config_files.append(full_path)


    # If multiple .config files are found, use the first one
    if config_files:
        config_file_path = config_files[0]  # use the first .config found
    else:
        om.MGlobal.displayInfo(f"No .config files found in: {asset_path}")
        return

    with open(config_file_path, 'r') as config_file:
        configurations = json.load(config_file)


    for folder_names, path in configurations.items():
        if path == "relative":
            folder_path = os.path.join(asset_path, folder_names)
        else:
            folder_path = path

        if folder_names == "guides":
            highest_version_file = _highest_version_file_in_directory(folder_path, ".guides")
            if highest_version_file:
                core.DataManager.set_guide_data(highest_version_file)
                om.MGlobal.displayInfo(f"Guides file loaded from: {highest_version_file}")
            else:
                om.MGlobal.displayInfo(f"No matching .guides files found in: {folder_path}")
                return

        elif folder_names == "curves":
            highest_version_file = _highest_version_file_in_directory(folder_path, ".json")
            if highest_version_file:
                core.DataManager.set_ctls_data(highest_version_file)
                om.MGlobal.displayInfo(f"Controllers file loaded from: {highest_version_file}")
            else:
                om.MGlobal.displayInfo(f"No matching .curves files found in: {folder_path}")
                return

        elif folder_names == "skinning":
            highest_version_file = _highest_version_file_in_directory(folder_path, ".skn")
            if highest_version_file:
                core.DataManager.set_skinning_data(highest_version_file)
                om.MGlobal.displayInfo(f"Skinning file loaded from: {highest_version_file}")
            else:
                om.MGlobal.displayInfo(f"No matching .skn files found in: {folder_path}")
                return
            
        elif folder_names == "models":
            if os.path.exists(folder_path):
                highest_version_file = _highest_version_file_in_directory(folder_path, ".ma")

                if highest_version_file:
                    core.DataManager.set_model_path(highest_version_file)
                    om.MGlobal.displayInfo(f"Model loaded from: {highest_version_file}")
                else:
                    om.MGlobal.displayInfo(f"No matching .ma files found in: {folder_path}")
            else:
                folder_path = os.path.join(asset_path, "models")
                highest_version_file = _highest_version_file_in_directory(folder_path, ".ma")

                if highest_version_file:
                    core.DataManager.set_model_path(highest_version_file)
                    om.MGlobal.displayInfo(f"Model loaded from: {highest_version_file}")
                else:
                    om.MGlobal.displayInfo(f"No matching .ma files found in: {folder_path}")
                om.MGlobal.displayError(f"Models folder does not exist repathed to: {folder_path}")
                return

    if os.path.exists(asset_path):
        for fname in os.listdir(asset_path):
            full_path = os.path.join(asset_path, fname)
            if os.path.isfile(full_path) and fname.lower().endswith('.settings') and asset_name in fname:
                core.DataManager.set_extra_data_path(full_path)
                om.MGlobal.displayInfo(f"Extra Attrs file loaded from: {full_path}")
                break

    

    core.DataManager.set_asset_name(asset_name)
    core.DataManager.set_project_path(asset_path)
    om.MGlobal.displayInfo(f"Asset configuration loaded for {asset_name} Completed.")

# asset_structure_creation("rigoberta", asset_type="CHAR")

class AssetManagerWindow(QtWidgets.QDialog):
    
    WINDOW_NAME = "AssetManagerToolUI"
    WINDOW_TITLE = "Asset Manager"
    
    def __init__(self, parent=None):
        super(AssetManagerWindow, self).__init__(wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QMainWindow))
        
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(400, 500)
        self.setSizeGripEnabled(True) 
        
        core.load_data()

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.update_preview_image()
        
    def create_widgets(self):
        self.tabs = QtWidgets.QTabWidget()
        
        names = self.load_assets_names()

        self.tab_load = QtWidgets.QWidget()
        
        self.lbl_preview = QtWidgets.QLabel()
        self.lbl_preview.setMinimumSize(300, 200)
        self.lbl_preview.setMaximumSize(300, 200)
        self.lbl_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("border: 1px solid #444; background-color: #222; color: #888;")
        self.lbl_preview.setText("No Preview Available")

        first_name = core.DataManager.get_asset_name()

        if first_name in names:
            names.remove(first_name)
            names.insert(0, first_name)
        
        self.combo_items = QtWidgets.QComboBox()
        self.combo_items.addItems(names)
        
        self.btn_capture = QtWidgets.QPushButton("Capture Persp Thumbnail")
        self.btn_capture.setToolTip("Switches to Perspective view, frames selection, and saves a thumbnail.")
        
        self.btn_ok_t1 = QtWidgets.QPushButton("Load Asset")
        
        # --- Tab 2: Create Widgets ---
        self.tab_create = QtWidgets.QWidget()
        self.asset_type = QtWidgets.QComboBox()
        self.asset_type.addItems(["CHAR", "PROP", "ENV"])

        self.input_name = QtWidgets.QLineEdit()
        self.input_name.setPlaceholderText("Enter Asset Name...")
        
        self.btn_ok_t2 = QtWidgets.QPushButton("Create Asset")

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        
        layout_t1 = QtWidgets.QVBoxLayout(self.tab_load)
        
        layout_t1.addWidget(self.lbl_preview, alignment=QtCore.Qt.AlignCenter)
        layout_t1.addSpacing(10)
        
        layout_t1.addWidget(QtWidgets.QLabel("Select Asset:"))
        layout_t1.addWidget(self.combo_items)
        layout_t1.addWidget(self.btn_capture)
        layout_t1.addStretch()
        
        buttons_layout_t1 = QtWidgets.QHBoxLayout()
        buttons_layout_t1.addStretch()
        buttons_layout_t1.addWidget(self.btn_ok_t1)
        layout_t1.addLayout(buttons_layout_t1)
        
        h_layout_big = QtWidgets.QHBoxLayout()

        v_layout_type = QtWidgets.QVBoxLayout()
        v_layout_type.addWidget(QtWidgets.QLabel("Asset Type:"))
        v_layout_type.addWidget(self.asset_type)
        h_layout_big.addLayout(v_layout_type)

        v_layout_name = QtWidgets.QVBoxLayout()
        v_layout_name.addWidget(QtWidgets.QLabel("Asset Name:"))
        v_layout_name.addWidget(self.input_name)
        h_layout_big.addLayout(v_layout_name)

        layout_t2 = QtWidgets.QVBoxLayout(self.tab_create)
        layout_t2.addStretch()
        layout_t2.addLayout(h_layout_big)
        layout_t2.addStretch()
        
        buttons_layout_t2 = QtWidgets.QHBoxLayout()
        buttons_layout_t2.addStretch()
        buttons_layout_t2.addWidget(self.btn_ok_t2)
        layout_t2.addLayout(buttons_layout_t2)
        
        self.tabs.addTab(self.tab_load, "Load Asset")
        self.tabs.addTab(self.tab_create, "Create Asset")

    def create_connections(self):
        self.btn_ok_t1.clicked.connect(self.load_selected_asset)
        self.btn_ok_t2.clicked.connect(self.create_asset)
        self.combo_items.currentIndexChanged.connect(self.update_preview_image)
        self.btn_capture.clicked.connect(self.capture_thumbnail)

    def load_assets_names(self):
        asset_path = os.path.join(SCRIPT_PATH, "assets")
        assets_names = []
        if os.path.exists(asset_path):
            for name in os.listdir(asset_path):
                full_path = os.path.join(asset_path, name)
                if os.path.isdir(full_path):
                    assets_names.append(name)
        return assets_names
    
    def update_preview_image(self):
        """Updates the label with the image found in the asset directory."""
        asset_name = self.combo_items.currentText()
        if not asset_name:
            return

        image_path = os.path.join(SCRIPT_PATH, "assets", asset_name, "asset_image.png")
        
        if os.path.exists(image_path):
            pixmap = QtGui.QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                self.lbl_preview.size(), 
                QtCore.Qt.KeepAspectRatio, 
                QtCore.Qt.SmoothTransformation
            )
            self.lbl_preview.setPixmap(scaled_pixmap)
            self.lbl_preview.setText("") # Clear text
        else:
            self.lbl_preview.clear()
            self.lbl_preview.setText("No Preview Available")

    def capture_thumbnail(self):
        """Captures a front view playblast of the viewport."""
        asset_name = self.combo_items.currentText()
        if not asset_name:
            om.MGlobal.displayWarning("No asset selected to capture.")
            return

        asset_path = os.path.join(SCRIPT_PATH, "assets", asset_name)
        if not os.path.exists(asset_path):
            om.MGlobal.displayError(f"Asset path does not exist: {asset_path}")
            return
            
        image_path = os.path.join(asset_path, "asset_image.png")

        current_panel = cmds.getPanel(withFocus=True)
        if "modelPanel" not in current_panel:
            visible_panels = cmds.getPanel(visiblePanels=True)
            model_panels = [p for p in visible_panels if "modelPanel" in p]
            if model_panels:
                current_panel = model_panels[0]
            else:
                om.MGlobal.displayError("No model panel found to capture from.")
                return

        original_cam = cmds.modelPanel(current_panel, query=True, camera=True)

        try:
            cmds.lookThru(current_panel, original_cam)
            # cmds.setFocus(current_panel)
            
            # cmds.viewFit(animate=False)
            
            cmds.playblast(
                completeFilename=image_path,
                forceOverwrite=True,
                format='image',
                compression='png',
                showOrnaments=False,
                startTime=cmds.currentTime(query=True),
                endTime=cmds.currentTime(query=True),
                viewer=False,
                percent=100,
                quality=100,
                width=600, 
                height=400,
                offScreen=True 
            )
            
            om.MGlobal.displayInfo(f"Thumbnail captured: {image_path}")
            
        except Exception as e:
            om.MGlobal.displayError(f"Failed to capture thumbnail: {e}")
            
        finally:
            cmds.lookThru(current_panel, original_cam)
            pass

        self.update_preview_image()
    
    def load_selected_asset(self):
        asset_name = self.combo_items.currentText()
        try:
            load_asset_configuration(asset_name)
            if cmds.window(AssetManagerWindow.WINDOW_NAME, exists=True):
                cmds.deleteUI(AssetManagerWindow.WINDOW_NAME)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading asset configuration: {e}")
            return
        
    def create_asset(self):
        asset_name = self.input_name.text().strip()
        asset_type = self.asset_type.currentText()
        if not asset_name:
            om.MGlobal.displayError("Please enter a valid asset name.")
            return
        try:
            asset_structure_creation(asset_name, asset_type=asset_type)
            if cmds.window(AssetManagerWindow.WINDOW_NAME, exists=True):
                cmds.deleteUI(AssetManagerWindow.WINDOW_NAME)
        except Exception as e:
            om.MGlobal.displayError(f"Error creating asset structure: {e}")
            return
        
        names = self.load_assets_names()
        self.combo_items.clear()
        self.combo_items.addItems(names)
        

def show():
    if cmds.window(AssetManagerWindow.WINDOW_NAME, exists=True):
        cmds.deleteUI(AssetManagerWindow.WINDOW_NAME)
        
    # 3. Create and show
    ui = AssetManagerWindow()
    ui.show()
    return ui

    