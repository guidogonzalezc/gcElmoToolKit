import maya.cmds as cmds
import maya.OpenMayaUI as omui
import maya.api.OpenMaya as om
from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance

# Import the provided adnx library
try:
    import adn.api.adnx as adnx
except ImportError:
    om.MGlobal.displayWarning("Could not import 'adnx'. Please ensure the library is in your scripts path.")

DEFAULT_LOCATORS = [
    # LEFT SIDE
    {
        "name": "L_LegUpper_adnLocatorRotation_Thigh",
        "inputs": ["L_clavicle_ENV", "L_backLegUpperBendy00_ENV", "L_backLegMiddleBendy00_ENV"]
    },
    {
        "name": "L_LegMiddle_adnLocatorRotation_Knee",
        "inputs": ["L_backLegUpperBendy00_ENV", "L_backLegMiddleBendy00_ENV", "L_backLegLowerBendy00_ENV"]
    },
    {
        "name": "L_LegLower_adnLocatorRotation_Ankle",
        "inputs": ["L_backLegMiddleBendy00_ENV", "L_backLegLowerBendy00_ENV", "L_backLegLowerBendy05_ENV"]
    },
    {
        "name": "L_shoulderFront_adnLocatorRotation_Shoulder",
        "inputs": ["L_clavicle_ENV", "L_armUpperBendy00_ENV", "L_shoulderFrontDistance_JNT"]
    },
    {
        "name": "L_shoulderUp_adnLocatorRotation_Shoulder",
        "inputs": ["L_clavicle_ENV", "L_armUpperBendy00_ENV", "L_shoulderUpDistance_JNT"]
    },
    {
        "name": "L_armMiddle_adnLocatorRotation_Elbow",
        "inputs": ["L_armUpperBendy00_ENV", "L_armLowerBendy00_ENV", "L_armLowerBendy05_ENV"]
    },
    {
        "name": "L_clavicle_frontDistance_adnLocatorDistance",
        "inputs": ["C_leftHeadDistance_JNT", "L_clavicle_ENV"]
    },
    {
        "name": "L_clavicle_backDistance_adnLocatorDistance",
        "inputs": ["L_clavicle_ENV", "C_spine00_ENV"]
    },
    {
        "name": "L_tail_leftDistance_adnLocatorDistance",
        "inputs": ["C_leftTailDistance_JNT", "C_tail020_ENV"]
    },
    # {
    #     "name": "L_neck_frontDistance_adnLocatorDistance",
    #     "inputs": ["C_neck00_ENV", "C_leftHeadDistance_JNT"]
    # },

    # RIGHT SIDE
    {
        "name": "R_LegUpper_adnLocatorRotation_Thigh",
        "inputs": ["R_clavicle_ENV", "R_backLegUpperBendy00_ENV", "R_backLegMiddleBendy00_ENV"]
    },
    {
        "name": "R_LegMiddle_adnLocatorRotation_Knee",
        "inputs": ["R_backLegUpperBendy00_ENV", "R_backLegMiddleBendy00_ENV", "R_backLegLowerBendy00_ENV"]
    },
    {
        "name": "R_LegLower_adnLocatorRotation_Ankle",
        "inputs": ["R_backLegMiddleBendy00_ENV", "R_backLegLowerBendy00_ENV", "R_backLegLowerBendy05_ENV"]
    },
    {
        "name": "R_shoulderUp_adnLocatorRotation_Shoulder",
        "inputs": ["R_clavicle_ENV", "R_armUpperBendy00_ENV", "R_shoulderUpDistance_JNT"]
    },
    {
        "name": "R_armMiddle_adnLocatorRotation_Elbow",
        "inputs": ["R_armUpperBendy00_ENV", "R_armLowerBendy00_ENV", "R_armLowerBendy05_ENV"]
    },
    {
        "name": "R_armMiddle_adnLocatorRotation_Elbow",
        "inputs": ["R_armUpperBendy00_ENV", "R_armLowerBendy00_ENV", "R_armLowerBendy05_ENV"]
    },
    {
        "name": "R_clavicle_frontDistance_adnLocatorDistance",
        "inputs": ["C_rightHeadDistance_JNT", "R_clavicle_ENV"]
    },
    {
        "name": "R_clavicle_backDistance_adnLocatorDistance",
        "inputs": ["R_clavicle_ENV", "C_spine00_ENV"]
    },
    {
        "name": "R_tail_rightDistance_adnLocatorDistance",
        "inputs": ["C_rightTailDistance_JNT", "C_tail020_ENV"]
    },
    {
        "name": "R_shoulderFront_adnLocatorRotation_Shoulder",
        "inputs": ["R_clavicle_ENV", "R_armUpperBendy00_ENV", "R_shoulderFrontDistance_JNT"]
    },
    # {
    #     "name": "R_neck_frontDistance_adnLocatorDistance",
    #     "inputs": ["C_neck00_ENV", "C_rightHeadDistance_JNT"]
    # },

    # CENTER
    {
        "name": "C_neck_backDistance_adnLocatorDistance",
        "inputs": ["C_neck00_ENV", "C_localChest_ENV"]
    },
    {
        "name": "C_neck_upperDistance_adnLocatorDistance",
        "inputs": ["C_neck00_ENV", "C_centerUpHeadDistance_JNT"]
    },
    {
        "name": "C_neck_downDistance_adnLocatorDistance",
        "inputs": ["C_neck00_ENV", "C_centerDownHeadDistance_JNT"]
    },
    {
        "name": "C_tail_downDistance_adnLocatorDistance",
        "inputs": ["C_centerDownTailDistance_JNT", "C_tail020_ENV"]
    },
    {
        "name": "C_tail_upDistance_adnLocatorDistance",
        "inputs": ["C_centerUpTailDistance_JNT", "C_tail020_ENV"]
    }
]

def get_maya_window():
    """ Get the main Maya window as a QWidget. """
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


class LocatorsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(LocatorsTab, self).__init__(parent)
        self.create_widgets()
        self.create_layout()
        self.populate_table()
        self.create_connections()

    def create_widgets(self):
        self.lbl_info = QtWidgets.QLabel("Modify mappings. Name MUST contain 'adnLocatorRotation' or 'adnLocatorDistance'.")
        self.lbl_info.setWordWrap(True)
        
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Locator Name", "Joint Inputs (Comma Separated)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        self.btn_add_row = QtWidgets.QPushButton("+ Add New Row")
        
        self.btn_create = QtWidgets.QPushButton("Create All Locators && Sensors")
        self.btn_create.setStyleSheet("background-color: #44A; color: white; font-weight: bold; padding: 8px;")

    def create_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.lbl_info)
        layout.addWidget(self.table)
        
        layout.addWidget(self.btn_add_row)
        layout.addSpacing(5)
        
        layout.addWidget(self.btn_create)

    def create_connections(self):
        self.btn_create.clicked.connect(self.build_locators)
        self.btn_add_row.clicked.connect(self.add_new_row)

    def populate_table(self):
        self.table.setRowCount(len(DEFAULT_LOCATORS))
        for i, item in enumerate(DEFAULT_LOCATORS):
            name_item = QtWidgets.QTableWidgetItem(item["name"])
            name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable) 
            self.table.setItem(i, 0, name_item)
            
            inputs_str = ", ".join(item["inputs"])
            input_item = QtWidgets.QTableWidgetItem(inputs_str)
            self.table.setItem(i, 1, input_item)

    def add_new_row(self):
        """ Adds an editable row to the table """
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        

        name_item = QtWidgets.QTableWidgetItem("Custom_Name_adnLocatorRotation_Side")
        self.table.setItem(row_idx, 0, name_item)
        
        input_item = QtWidgets.QTableWidgetItem("")
        self.table.setItem(row_idx, 1, input_item)
        
        self.table.scrollToBottom()

    def build_locators(self):
        rig = adnx.AdnRig(host=adnx.AdnHost.kMaya)
        row_count = self.table.rowCount()
        built_count = 0

        for i in range(row_count):
            name_item = self.table.item(i, 0)
            input_item = self.table.item(i, 1)
            
            if not name_item or not input_item:
                continue

            name = name_item.text().strip()
            inputs_text = input_item.text().strip()
            inputs = [x.strip() for x in inputs_text.split(",") if x.strip()]
            
            if not name:
                continue

            if "adnLocatorRotation" in name:
                self.build_rotation_locator(rig, name, inputs)
                built_count += 1
            elif "adnLocatorDistance" in name:
                self.build_distance_locator(rig, name, inputs)
                built_count += 1
            else:
                om.MGlobal.displayWarning(f"Skipping '{name}': Unknown Type. Name must include 'adnLocatorRotation' or 'adnLocatorDistance'.")

        om.MGlobal.displayInfo(f"--- AdonisFX: Processed {built_count} Locators ---")

    def build_rotation_locator(self, rig, name, inputs):
        if len(inputs) != 3:
            om.MGlobal.displayWarning(f"Skipping {name}: Needs 3 inputs. Found {len(inputs)}.")
            return

        start, mid, end = inputs
        for jnt in inputs:
            if not cmds.objExists(jnt):
                om.MGlobal.displayWarning(f"Skipping {name}: Joint '{jnt}' missing.")
                return

        sensor = adnx.AdnSensorRotation(rig)
        
        shape_name = name + "Shape"
        sensor.setName(shape_name)

        sensor_name = name.replace("adnLocatorRotation", "adnSensorRotation")
        sensor.setParameter("sensorName", sensor_name)

        sensor._data["node"] = shape_name 

        sensor.setParameter("sensorStart", start)
        sensor.setParameter("sensorMid", mid)
        sensor.setParameter("sensorEnd", end)
        
        try:
            sensor.build()
            parent_grp = "muscleSystems_GRP"
            if cmds.objExists(parent_grp):
                try:
                    cmds.parent(name, parent_grp)
                except Exception as e:
                    om.MGlobal.displayWarning(f"Could not parent {name} to {parent_grp}: {e}")
            om.MGlobal.displayInfo(f"[SUCCESS] Built {name} -> {sensor_name}")
        except Exception as e:
            om.MGlobal.displayError(f"[FAIL] {name}: {e}")

    def build_distance_locator(self, rig, name, inputs):
        if len(inputs) != 2:
            om.MGlobal.displayWarning(f"Skipping {name}: Needs 2 inputs. Found {len(inputs)}.")
            return

        start, end = inputs
        for jnt in inputs:
            if not cmds.objExists(jnt):
                om.MGlobal.displayWarning(f"Skipping {name}: Joint '{jnt}' missing.")
                return

        sensor = adnx.AdnSensorDistance(rig)
        
        shape_name = name + "Shape"
        sensor.setName(shape_name)
        
        sensor_name = name.replace("adnLocatorDistance", "adnSensorDistance")
        sensor.setParameter("sensorName", sensor_name)

        sensor._data["node"] = shape_name 
        
        sensor.setParameter("sensorStart", start)
        sensor.setParameter("sensorEnd", end)
        
        try:
            sensor.build()
            parent_grp = "muscleSystems_GRP"
            if cmds.objExists(parent_grp):
                try:
                    cmds.parent(name, parent_grp)
                except Exception as e:
                    om.MGlobal.displayWarning(f"Could not parent {name} to {parent_grp}: {e}")
            om.MGlobal.displayInfo(f"[SUCCESS] Built {name} -> {sensor_name}")
        except Exception as e:
            om.MGlobal.displayError(f"[FAIL] {name}: {e}")


class MusclesTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MusclesTab, self).__init__(parent)
        self.targets = []
        self.muscles = []
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.lw_targets = QtWidgets.QListWidget()
        self.lw_targets.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lw_muscles = QtWidgets.QListWidget()
        self.lw_muscles.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        
        self.btn_add_targets = QtWidgets.QPushButton("Add Selected as Targets (Skeleton)")
        self.btn_add_muscles = QtWidgets.QPushButton("Add Selected as Muscles")
        self.btn_clear = QtWidgets.QPushButton("Clear Lists")
        self.btn_build = QtWidgets.QPushButton("Configure Muscles")
        self.btn_build.setStyleSheet("background-color: #5D5; color: black; font-weight: bold; padding: 10px;")

        self.lbl_targets = QtWidgets.QLabel("Skeleton / Targets:")
        self.lbl_muscles = QtWidgets.QLabel("Muscles (Solvers):")

    def create_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.lbl_targets)
        layout.addWidget(self.lw_targets)
        layout.addWidget(self.btn_add_targets)
        layout.addSpacing(10)
        layout.addWidget(self.lbl_muscles)
        layout.addWidget(self.lw_muscles)
        layout.addWidget(self.btn_add_muscles)
        layout.addSpacing(20)
        layout.addWidget(self.btn_clear)
        layout.addWidget(self.btn_build)

    def create_connections(self):
        self.btn_add_targets.clicked.connect(self.add_targets)
        self.btn_add_muscles.clicked.connect(self.add_muscles)
        self.btn_clear.clicked.connect(self.clear_lists)
        self.btn_build.clicked.connect(self.build_setup)

    def add_targets(self):
        sel = cmds.ls(sl=True)
        if sel:
            self.lw_targets.addItems(sel)
            self.targets.extend(sel)

    def add_muscles(self):
        sel = cmds.ls(sl=True)
        if sel:
            self.lw_muscles.addItems(sel)
            self.muscles.extend(sel)

    def clear_lists(self):
        self.lw_targets.clear()
        self.lw_muscles.clear()
        self.targets = []
        self.muscles = []

    def build_setup(self):
        """
        Builds the muscles using complete settings extracted from AdnMuscle1.mel
        AND connects the global Time node.
        """
        if not self.muscles:
            om.MGlobal.displayWarning("No muscles selected.")
            return


        DEFAULT_SETTINGS = {
            "frozen": 0,
            "blockGPU": 0,
            "envelope": 1.0,
            "enable": True,
            "iterations": 10,
            "triangulateMesh": True,
            "material": 1,
            "stiffnessMultiplier": 1.0,
            "pointMassMode": 0,
            "density": 1060.0,
            "activation": 0.0,
            "restActivation": 0.0,
            "anisotropy": 0,
            "anisotropyRatio": 9.0,
            "timeScale": 1.0,
            "spaceScale": 1.0,
            "spaceScaleMode": 2,          
            "gravity": 9.8,
            "gravityDirectionX": 0.0,
            "gravityDirectionY": -1.0,
            "gravityDirectionZ": 0.0,
            "useCustomStiffness": True,
            "stiffness": 15000.0,
            "attachmentToGeometryStiffnessOverride": -1.0,
            "attachmentToTransformStiffnessOverride": -1.0,
            "fiberStiffnessOverride": -1.0,
            "shapeStiffnessOverride": -1.0,
            "hardAttachments": False,
            "slidingConstraintsMode": 1, 
            "maxSlidingDistance": 1.0,
            "globalMassMultiplier": 0.001
        }

        rig = adnx.AdnRig(host=adnx.AdnHost.kMaya)

        for muscle_geo in self.muscles:
            if not cmds.objExists(muscle_geo):
                continue

            muscle = adnx.AdnMuscle(rig)
            muscle_name = f"{muscle_geo}_adnMuscle"
            muscle.setName(muscle_name)
            muscle.setParameter("geometry", muscle_geo)
            
            for param, value in DEFAULT_SETTINGS.items():
                try:
                    muscle.setParameter(param, value)
                except Exception:
                    pass

            if self.targets:
                for target in self.targets:
                    if not cmds.objExists(target):
                        continue
                    
                    if cmds.nodeType(target) == 'transform':
                        shapes = cmds.listRelatives(target, shapes=True)
                        if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                            muscle.addGeometryAttachment(target)
                        else:
                            muscle.addTransformAttachment(target)
                    elif cmds.nodeType(target) == 'joint':
                        muscle.addTransformAttachment(target)

            try:
                muscle.build()
                
                if not cmds.isConnected("time1.outTime", muscle_name + ".currentTime"):
                    cmds.connectAttr("time1.outTime", muscle_name + ".currentTime", force=True)
                    om.MGlobal.displayInfo(f"Connected time1 to {muscle_name}")

                om.MGlobal.displayInfo(f"[SUCCESS] Built Muscle: {muscle_name}")

            except Exception as e:
                om.MGlobal.displayError(f"[FAIL] Failed to build {muscle_name}: {e}")
        
        cmds.select(clear=True)
        om.MGlobal.displayInfo("--- AdonisFX Muscle Setup Complete ---")


class AdonisBuilderUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        if not parent:
            parent = get_maya_window()
        super(AdonisBuilderUI, self).__init__(parent)
        
        self.setWindowTitle("AdonisFX Automator")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.resize(500, 600)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        
        self.tab_locators = LocatorsTab()
        self.tab_muscles = MusclesTab()
        
        self.tabs.addTab(self.tab_locators, "Locators & Sensors")
        self.tabs.addTab(self.tab_muscles, "Muscle Configuration")
        
        self.main_layout.addWidget(self.tabs)

def show_adonis_ui():
    global adonis_tool_window
    try:
        adonis_tool_window.close()
        adonis_tool_window.deleteLater()
    except:
        pass
        
    adonis_tool_window = AdonisBuilderUI()
    adonis_tool_window.show()
    return adonis_tool_window