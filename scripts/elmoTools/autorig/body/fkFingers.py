#Python libraries import
import json
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math

# Local imports
from elmoTools.utils.curve_tool import controller_creator
from elmoTools.utils.guide_creation import guide_import
from elmoTools.utils import data_export

# Dev only imports
from elmoTools.utils import guide_creation
import elmoTools.utils.de_boor_core_002 as de_boors_002
from elmoTools.utils import space_switch as ss
from elmoTools.utils import core
from elmoTools.utils.core import get_offset_matrix
from elmoTools.utils import basic_structure
import re


reload(de_boors_002)
reload(guide_creation)
reload(ss)
reload(core)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class FingersModule(object):

    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")

    def make(self, guide_name):

        """
        Make the fingers module
        :param guide_name: name of the guide to import
        """

        data_exporter = data_export.DataExport()

        self.guides = guide_import(guide_name, all_descendents=True, useGuideRotation=True)
        self.side = self.guides[0].split("_")[0]

        self.name = guide_name.split("_")[1].replace("Metacarpal", "")
        self.name = re.sub(r"\d+", "", self.name)
        dict = core.DataManager.get_finger_data(self.side) or {}
        self.controllers_grp = None
        if dict:    
            if core.DataManager.get_asset_name() == "varyndor":
                if self.guides[0].lower() == "l_footfinger00_guide":
                    self.controllers_grp = "L_fingersBackAttributes_CTL"
                elif self.guides[0].lower() == "r_footfinger00_guide":
                    self.controllers_grp = "R_fingersBackAttributes_CTL"
            if cmds.objExists(dict.get("controllers")) and not self.controllers_grp:
                self.controllers_grp = dict.get("controllers")
            elif not self.controllers_grp:
                self.controllers_grp = cmds.createNode("transform", name=f"{self.side}_fkFingersControllers_GRP", parent=self.masterWalk_ctl)
                cmds.setAttr(self.controllers_grp + ".inheritsTransform", 0)
                arm_skinning = data_exporter.get_data(f"{self.side}_armModule", "skinning_transform")
                self.arm_last_joints = cmds.listRelatives(arm_skinning, children=True, type="joint", fullPath=True)[-1] or []

                parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
                cmds.connectAttr(self.arm_last_joints + ".worldMatrix[0]", parent_matrix + ".target[0].targetMatrix")

                offset_matrix = get_offset_matrix(self.controllers_grp, self.arm_last_joints)

                cmds.setAttr(parent_matrix + ".target[0].offsetMatrix", *offset_matrix, type="matrix")

                cmds.connectAttr(parent_matrix + ".outputMatrix", self.controllers_grp + ".offsetParentMatrix")

            self.individual_module_grp = None
            if core.DataManager.get_asset_name() == "varyndor":
                if self.guides[0].lower() == "l_footfinger00_guide":
                    self.individual_module_grp = "L_fingersBackAttributes_CTL"
                elif self.guides[0].lower() == "r_footfinger00_guide":
                    self.individual_module_grp = "R_fingersBackAttributes_CTL"
            if cmds.objExists(dict.get("module")) and not self.individual_module_grp:
                self.individual_module_grp = dict.get("module")
            elif not self.individual_module_grp:
                self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_fkFingersModule", parent=self.modules_grp, ss=True)


            if dict.get("skinning_transform") and cmds.objExists(dict.get("skinning_transform")):
                self.skinning_grp = dict.get("skinning_transform")
            else:
                self.skinning_grp = cmds.createNode("transform", name=f"{self.side}_fkFingersSkinningJoints", parent=self.skel_grp, ss=True)


            self.finger_attributes_ctl = None
            if core.DataManager.get_asset_name() == "varyndor":
                if self.guides[0].lower() == "l_footfinger00_guide":
                    self.finger_attributes_ctl = "L_fingersBackAttributes_CTL"
                elif self.guides[0].lower() == "r_footfinger00_guide":
                    self.finger_attributes_ctl = "R_fingersBackAttributes_CTL"

            if cmds.objExists(dict.get("attributes_ctl")) and not self.finger_attributes_ctl:
                self.finger_attributes_ctl = dict.get("attributes_ctl")
                self.finger_attributes_nodes = None
            elif not self.finger_attributes_ctl:
                self.finger_attributes_ctl, self.finger_attributes_nodes = controller_creator(
                    name=f"{self.side}_fkFingersAttributes",
                    suffixes=["GRP"],
                    parent=self.controllers_grp,
                    lock=["tx", "ty", "tz" ,"rx", "ry", "rz", "sx", "sy", "sz", "visibility"],
                    ro=False
                )
                cmds.connectAttr(self.arm_last_joints + ".worldMatrix[0]", self.finger_attributes_nodes[0] + ".offsetParentMatrix")
                cmds.setAttr(self.finger_attributes_nodes[0] + ".inheritsTransform", 0)
                cmds.setAttr(f"{self.finger_attributes_ctl}.FingerAttributes", lock=True, keyable=False, channelBox=True)
                cmds.addAttr(self.finger_attributes_ctl, longName="Curl", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, longName="Spread", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, longName="Twist", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, longName="Fan", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, longName="ThumbAttributes", attributeType="enum", enumName="____")
                cmds.setAttr(f"{self.finger_attributes_ctl}.ThumbAttributes", lock=True, keyable=False, channelBox=True)
                cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Curl", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Spread", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Twist", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
                cmds.addAttr(self.finger_attributes_ctl, ln="Thumb_Fan", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)

        else:
            self.controllers_grp = cmds.createNode("transform", name=f"{self.side}_fkFingersControllers_GRP", parent=self.masterWalk_ctl)
            cmds.setAttr(self.controllers_grp + ".inheritsTransform", 0)

            self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_fkFingersModule", parent=self.modules_grp, ss=True)

            self.skinning_grp = cmds.createNode("transform", name=f"{self.side}_fkFingersSkinningJoints", parent=self.skel_grp, ss=True)

            self.finger_attributes_ctl, self.finger_attributes_nodes = controller_creator(
                name=f"{self.side}_fkFingersAttributes",
                suffixes=["GRP"],
                parent=self.controllers_grp,
                lock=["tx", "ty", "tz" ,"rx", "ry", "rz", "sx", "sy", "sz", "visibility"],
                ro=False
            )

            arm_skinning = data_exporter.get_data(f"{self.side}_armModule", "skinning_transform")
            self.arm_last_joints = cmds.listRelatives(arm_skinning, children=True, type="joint", fullPath=True)[-1] or []

            parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
            cmds.connectAttr(self.arm_last_joints + ".worldMatrix[0]", parent_matrix + ".target[0].targetMatrix")

            offset_matrix = get_offset_matrix(self.controllers_grp, self.arm_last_joints)

            cmds.setAttr(parent_matrix + ".target[0].offsetMatrix", *offset_matrix, type="matrix")

            cmds.connectAttr(parent_matrix + ".outputMatrix", self.controllers_grp + ".offsetParentMatrix")

            cmds.connectAttr(self.arm_last_joints + ".worldMatrix[0]", self.finger_attributes_nodes[0] + ".offsetParentMatrix")
            cmds.setAttr(self.finger_attributes_nodes[0] + ".inheritsTransform", 0)



        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "-y"

        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "y"

        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])
        self.create_controller()
        data={
            "module": self.individual_module_grp,
            "skinning_transform": self.skinning_grp,
            "controllers": self.controllers_grp,
            "attributes_ctl": self.finger_attributes_ctl
        }
        
        core.DataManager.set_finger_data(core.DataManager, side=self.side, data=data)

        self.data_exporter.append_data(
            f"{self.side}_FkFingersModule",
            {
                "skinning_transform": self.skinning_grp,
                "attributes_ctl": self.finger_attributes_ctl,
            }
        )
            
    def create_controller(self):

        """"
        Create controllers for each guide
        :param guide_name: name of the guide to import
        """

        aim_matrix_guides = [f"{guide}.worldMatrix[0]" for guide in self.guides[:-1]]
        try:
            cmds.getAttr(f"{self.finger_attributes_ctl}.FingerAttributes")
        except:
            cmds.addAttr(self.finger_attributes_ctl, longName="FingerAttributes", attributeType="enum", enumName="———")
            cmds.setAttr(f"{self.finger_attributes_ctl}.FingerAttributes", lock=True, keyable=False, channelBox=True)


        for attr in ["Curl", "Spread", "Twist", "Fan"]:
            try:
                cmds.getAttr(f"{self.finger_attributes_ctl}.{attr}")
            except:
                cmds.addAttr(self.finger_attributes_ctl, longName=attr, attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)


        controllers = []
        fk_grps = []
        for j, guide in enumerate(aim_matrix_guides):


            finger_name = guide.split('_')[1]

            ctl, grp = controller_creator(
                name=f"{self.side}_{finger_name}",
                suffixes=["GRP", "SDK", "ANM"],
                lock=["sx", "sy", "sz", "visibility"],
                ro=False,
                parent= controllers[-1] if controllers else self.finger_attributes_ctl
            )

            if controllers:
                offset_matrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}_MLT", ss=True)
                inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_{finger_name}_INV", ss=True)
                cmds.connectAttr(aim_matrix_guides[j-1], inverse + ".inputMatrix")
                cmds.connectAttr(guide, offset_matrix + ".matrixIn[0]")
                cmds.connectAttr(controllers[-1] + ".worldInverseMatrix[0]", offset_matrix + ".matrixIn[1]")
                cmds.connectAttr(controllers[-1] + ".worldMatrix[0]", offset_matrix + ".matrixIn[2]")
                cmds.connectAttr(inverse + ".outputMatrix", offset_matrix + ".matrixIn[3]")
                cmds.connectAttr(offset_matrix + ".matrixSum", grp[0] + ".offsetParentMatrix")
                cmds.setAttr(f"{grp[0]}.rotate", 0,0,0, type="double3")
                cmds.setAttr(f"{grp[0]}.translate", 0,0,0, type="double3")
            else:
                cmds.connectAttr(guide, grp[0] + ".offsetParentMatrix")     
                cmds.matchTransform(grp[0], guide.replace(".worldMatrix[0]", ""))      

            # Add setDrivenKeyframe for Curl and Spread
            if controllers:
                for attr in ["Curl", "Fan"]:
                    if self.side == "L":
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, -25, 15, 20, -20, 30, -30], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif self.side == "R":
                        self.fingers_attributes_callback(grp[1], finger_values=[90, -20, 25, -15, -20, 20, -30, 30], thumb_values=[0,0,0,0,0,0, 0,0])

            joint = cmds.createNode("joint", name=f"{self.side}_{finger_name}_JNT", ss=True, parent=self.skinning_grp)
            cmds.connectAttr(ctl + ".worldMatrix[0]", joint + ".offsetParentMatrix")

            fk_grps.append(grp)
            controllers.append(ctl)


        
    def fingers_attributes_callback(self, ctl, finger_values=[None], thumb_values=[None]):

        cmds.select(ctl)
        
        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Curl", v=0)
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Curl", v=finger_values[0])
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Curl", v=finger_values[1])

        cmds.setDrivenKeyframe(at="ry", dv=0, cd=f"{self.finger_attributes_ctl}.Spread", v=0)
        cmds.setDrivenKeyframe(at="ry", dv=10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[2])
        cmds.setDrivenKeyframe(at="ry", dv=-10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[3])

        cmds.setDrivenKeyframe(at="rx", dv=0, cd=f"{self.finger_attributes_ctl}.Twist", v=0)
        cmds.setDrivenKeyframe(at="rx", dv=10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[4])
        cmds.setDrivenKeyframe(at="rx", dv=-10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[5])

        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Fan", v=0)
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[6])
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[7])