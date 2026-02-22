#Python libraries import
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math

# Local imports
from elmoTools.utils.curve_tool import controller_creator
from elmoTools.utils.guide_creation import guide_import
from elmoTools.utils import data_export
from elmoTools.utils import core
from elmoTools.utils.core import get_offset_matrix

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class CheekModule():
    """
    Class to create a neck module in a Maya rigging setup.
    This module handles the creation of neck joints, controllers, and various systems such as stretch, reverse, offset, squash, and volume preservation.
    """
    def __init__(self):
        """
        Initializes the NeckModule class, setting up paths and data exporters.
        
        Args:
            self: Instance of the NeckModule class.
        """
        
        self.data_exporter = data_export.DataExport()


        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")
        self.muscle_locators = self.data_exporter.get_data("basic_structure", "muscleLocators_GRP")
        self.head_ctl = self.data_exporter.get_data("C_neckModule", "skinning_transform")
        relatives = cmds.listRelatives(self.head_ctl, ad=True)
        self.head_ctl = relatives[-1]
        self.head_controller = self.data_exporter.get_data("C_neckModule", "head_ctl")



    def make(self, guide_name):
        """
        Creates the neck module, including the neck chain, controllers, and various systems.

        Args:
            self: Instance of the NeckModule class.
        """
        self.side = guide_name.split("_")[0]
        self.guide_name = guide_name

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_cheekModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_cheekControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)

        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_cheekFacialSkinning_GRP", ss=True, p=self.skel_grp)
        try:
            parentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_cheekModule_PM", ss=True)
            cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
            offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
            cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
            cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)
        except:
            pass

        self.create_chain()

        self.data_exporter.append_data(f"{self.side}_cheekModule", 
                            {"skinning_transform": self.skinning_trn,

                            }
                            )


    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, useGuideRotation=True)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        name = self.guides[0].replace("_GUIDE", "")

        ctl, controller_grp = controller_creator(
            name= name,
            suffixes=["GRP", "OFF", "ANM"],
            lock=["visibility"],
            ro=True,
            parent=self.controllers_trn
        )

        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix", force=True)

        mmx = core.local_mmx(ctl, controller_grp[0])

        joint = cmds.createNode("joint", name=f"{name}_JNT", parent=self.skinning_trn)
        cmds.connectAttr(mmx, f"{joint}.offsetParentMatrix", force=True)

