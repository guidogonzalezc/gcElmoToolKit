#Python libraries import
from unicodedata import name
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math
import re

# Local imports
from elmoTools.utils.curve_tool import controller_creator
from elmoTools.utils.guide_creation import guide_import
from elmoTools.utils import data_export
from elmoTools.utils import core
from elmoTools.utils.core import get_offset_matrix

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class CheekBoneModule():
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
        self.def_name = re.sub(r'\d+', '', self.guide_name.replace('_GUIDE', ''))


        self.module_trn = cmds.createNode("transform", name=f"{self.def_name}Module_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.def_name}Controllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)

        self.skinning_trn = cmds.createNode("transform", name=f"{self.def_name}FacialSkinning_GRP", ss=True, p=self.skel_grp)
        try:
            parentMatrix = cmds.createNode("parentMatrix", name=f"{self.def_name}Module_PM", ss=True)
            cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
            offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
            cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
            cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)
        except:
            pass

        self.create_chain()

        self.data_exporter.append_data(f"{self.def_name}Module", 
                            {"skinning_transform": self.skinning_trn,

                            }
                            )


    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, useGuideRotation=True)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        controllers = []
        controllers_grp = []

        ctl_main, controller_grp = controller_creator(
            name= f"{self.def_name}Main",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["visibility"],
                ro=True,
                parent=self.controllers_trn
            )
        
        if self.side == "L":
                cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix", force=True)


        else:
            multmatrix = cmds.createNode("multMatrix", name=f"{self.def_name}_MMX", ss=True)
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", -1, 0, 0, 0,
                                            0, 1, 0, 0,
                                            0, 0, 1, 0,
                                            0, 0, 0, 1, type="matrix")
            cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
            cmds.connectAttr( f"{multmatrix}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix", force=True)

        # main_local = core.local_mmx(ctl_main, controller_grp[0])

        for i, guide in enumerate(self.guides):
            name = re.sub(r'\d+', '', guide.replace("_GUIDE", ""))


            ctl, controller_grp = controller_creator(
                name= f"{name}0{i+1}",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["visibility"],
                ro=True,
                parent=self.controllers_trn
            )

            # cmds.setAttr(f"{controller_grp[0]}.inheritsTransform", 0)

            parent_matrix = cmds.createNode("parentMatrix", name=f"{name}0{i+1}_PM", ss=True)


            if self.side == "L":
                cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix", force=True)
                cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{parent_matrix}.inputMatrix", force=True)

            else:
                multmatrix = cmds.createNode("multMatrix", name=f"{name}0{i+1}_MMX", ss=True)
                cmds.setAttr(f"{multmatrix}.matrixIn[0]", -1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, 0, 1, type="matrix")
                cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
                cmds.connectAttr( f"{multmatrix}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix", force=True)
                cmds.connectAttr(f"{multmatrix}.matrixSum", f"{parent_matrix}.inputMatrix", force=True)

            cmds.connectAttr(f"{ctl_main}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix", force=True)
            offset = core.get_offset_matrix(f"{controller_grp[0]}.worldMatrix[0]", f"{ctl_main}.worldMatrix[0]")
            cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", offset, type="matrix")

            multmatrix_offset = cmds.createNode("multMatrix", name=f"{name}0{i+1}Offset_MMX", ss=True)
            cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{multmatrix_offset}.matrixIn[0]", force=True)
            cmds.connectAttr(f"{controller_grp[0]}.worldInverseMatrix[0]", f"{multmatrix_offset}.matrixIn[1]", force=True)
            cmds.connectAttr(f"{multmatrix_offset}.matrixSum", f"{controller_grp[1]}.offsetParentMatrix", force=True)

            mmx = core.local_mmx(ctl, controller_grp[0])

            joint = cmds.createNode("joint", name=f"{name}0{i+1}_JNT", parent=self.skinning_trn)
            cmds.connectAttr(mmx, f"{joint}.offsetParentMatrix", force=True)


            controllers.append(ctl)
            controllers_grp.append(controller_grp)