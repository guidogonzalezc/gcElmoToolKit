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
from elmoTools.utils import basic_structure
from elmoTools.utils import de_boor_core_002
from elmoTools.utils.space_switch import fk_switch

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}


class TongueModule():
    """
    Class to create a spine module in a Maya rigging setup.
    This module handles the creation of spine joints, controllers, and various systems such as stretch, reverse, offset, squash, and volume preservation.
    """
    def __init__(self):
        """
        Initializes the SpineModule class, setting up paths and data exporters.
        
        Args:
            self: Instance of the SpineModule class.
        """
        
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")
        self.head_ctl = self.data_exporter.get_data("C_neckModule", "head_ctl")
        self.jaw_ctl = self.data_exporter.get_data("C_jawModule", "jaw_ctl")


    def make(self, guide_name):
        """
        Creates the spine module, including the spine chain, controllers, and various systems.

        Args:
            self: Instance of the SpineModule class.
        """

        self.guide_name = guide_name

        self.primary_aim = "z"
        self.primary_aim_vector = AXIS_VECTOR[self.primary_aim]
        self.secondary_aim = "y"
        self.secondary_aim_vector = AXIS_VECTOR[self.secondary_aim]

        self.side = self.guide_name.split("_")[0]

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_tongueModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_tongueControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_tongueFacialSkinning_GRP", ss=True, p=self.skel_grp)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0) # Avoid double transformations

        if self.jaw_ctl:
            parent = self.jaw_ctl
        else:
            parent = self.head_ctl

        parentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_tongueModule_PM", ss=True)
        cmds.connectAttr(f"{parent}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
        offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{parent}.worldMatrix")
        cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)


        self.create_chain()
        self.create_controllers()

        self.data_exporter.append_data(f"{self.side}_tongueModule", 
                            {"skinning_transform": self.skinning_trn,
                            }
                            )
    
    def create_chain(self):

        """
        pass
        """

        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        else:
            self.enum_str = "———"

        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

    def create_controllers(self):

        """
        Create the controllers setup FK for the ribbon. Must create 7 controllers
        """

        aim_matrix = cmds.createNode("aimMatrix", name=self.guides[0].replace("_GUIDE", "_AMX"), ss=True)
        cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *self.primary_aim_vector)
        cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector)
        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix")
        

        self.ctls = []
        self.nodes = []
        self.bendy_ctls = []
        self.bendy_nodes = []
        
        clts_numbers = 5

        for i in range(clts_numbers):

            ctl, ctl_grp = controller_creator(name=f"{self.side}_tongue0{i}",suffixes=["GRP", "ANM"],lock=["scaleX", "scaleY", "scaleZ", "visibility"], ro=True) # Create controller

            if self.ctls:
                cmds.parent(ctl_grp[0], self.ctls[-1]) # Parent the group to the last controller for FK behavior
                blend_matrix = cmds.createNode("blendMatrix", name=self.guides[0].replace("_GUIDE", "_BMX"), ss=True)
                cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
                cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.inputMatrix")
                cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix")
                translate_weight = i / (clts_numbers)
                cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", translate_weight) # Set weight based on controller index to place it along the guides
                cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix") # Connect the controller to the blended matrix

            else:
                cmds.parent(ctl_grp[0], self.controllers_trn)
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix") # Connect the first controller to the guide

    

            self.ctls.append(ctl)
            self.nodes.append(ctl_grp)

        blend_matrix = cmds.createNode("blendMatrix", name=self.guides[0].replace("_GUIDE", "End_BMX"), ss=True)
        cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 1) # Set weight based on controller index to place it along the guides

        parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_tongueEnd_PM", ss=True)
        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{parent_matrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.ctls[-1]}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix", force=True)
        offset = core.get_offset_matrix(f"{blend_matrix}.outputMatrix", f"{self.ctls[-1]}.worldMatrix")
        cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", offset, type="matrix")

        self.ctls.append(f"{parent_matrix}.outputMatrix")

        self.num_joints = len(self.ctls) * 5
        self.old_joints = de_boor_core_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs=self.ctls, num_joints=self.num_joints, name=f"{self.side}_tongue", parent=self.skinning_trn, negate_secundary=True)


