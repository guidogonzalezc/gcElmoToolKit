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
        self.import_guides(guide_name)

        leg_skinning = data_exporter.get_data(f"{self.side}_{self.finger_front_name.lower()}LegModule", "skinning_transform")
        self.leg_ball_blm = cmds.listRelatives(leg_skinning, children=True)[-1]
        self.foot_rotation = data_exporter.get_data(f"{self.side}_{self.finger_front_name.lower()}LegModule", "frontRoll")
        self.ikSwitch_ctl = data_exporter.get_data(f"{self.side}_{self.finger_front_name.lower()}LegModule", "ikFkSwitch")
        

        parent_matrix = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
        cmds.connectAttr(self.leg_ball_blm + ".worldMatrix[0]", parent_matrix + ".target[0].targetMatrix")
        cmds.connectAttr(self.foot_rotation + ".worldMatrix[0]", parent_matrix + ".target[1].targetMatrix")
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", parent_matrix + ".target[0].weight")
        reverse = cmds.createNode("reverse", name=f"{self.side}_legFingers_IKFK_REV", ss=True)
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", reverse + ".inputX")
        cmds.connectAttr(reverse + ".outputX", parent_matrix + ".target[1].weight")

        offset_matrix = get_offset_matrix(self.controllers_grp, self.leg_ball_blm)

        offset_matrix02 = get_offset_matrix(self.controllers_grp, self.foot_rotation + ".worldMatrix[0]")

        cmds.setAttr(parent_matrix + ".target[0].offsetMatrix", *offset_matrix, type="matrix")
        cmds.setAttr(parent_matrix + ".target[1].offsetMatrix", *offset_matrix02, type="matrix")

        cmds.connectAttr(parent_matrix + ".outputMatrix", self.controllers_grp + ".offsetParentMatrix")

        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "-y"

        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "y"

        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])
        self.create_controller()

        self.data_exporter.append_data(
            f"{self.side}_foot{self.finger_front_name}FingersModule",
            {
                "skinning_transform": self.skinning_grp,
                "ik_controllers": self.ik_controllers,
            }
        )
    
    def import_guides(self, guide_name):

        """
        Import the guides for the fingers module
        :param guide_name: name of the guide to import
        """

        self.fingers = guide_import(guide_name, all_descendents=True, path=None)
        self.side = self.fingers[0].split("_")[0]
        if "front" in self.fingers[0].lower():
            self.finger_front_name = "Front" 

        elif  "back" in self.fingers[0].lower():
            self.finger_front_name = "Back"
        else:
            self.finger_front_name = "Back"

        self.controllers_grp = cmds.createNode("transform", name=f"{self.side}_legFingers{self.finger_front_name}Controllers_GRP", parent=self.masterWalk_ctl)
        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_footFinger{self.finger_front_name}Module_GRP", parent=self.modules_grp, ss=True)
        self.skinning_grp = cmds.createNode("transform", name=f"{self.side}_footFinger{self.finger_front_name}SkinningJoints_GRP", parent=self.skel_grp, ss=True)
        self.controllers_grp_ik = cmds.createNode("transform", name=f"{self.side}_legFingers{self.finger_front_name}IkControllers_GRP", parent=self.masterWalk_ctl)

        self.attached_fk_ctls = []
        self.attached_fk_sdks = []


        cmds.setAttr(self.controllers_grp + ".inheritsTransform", 0)
        
    def create_controller(self):

        """"
        Create controllers for each guide
        :param guide_name: name of the guide to import
        """

        self.finger_attributes_ctl, self.finger_attributes_nodes = controller_creator(name=f"{self.side}_fingers{self.finger_front_name}Attributes", suffixes=["GRP"], parent=self.controllers_grp, lock=["tx", "ty", "tz" ,"rx", "ry", "rz", "sx", "sy", "sz", "visibility"], ro=False)
        # self.finger_attributes_ctl = self.foot_rotation

        self.finger_plane, self.finger_plane_grp = controller_creator(
                    name=f"{self.side}_fingers{self.finger_front_name}PlaneIk",
                    suffixes=["GRP", "ANM"],
                    lock=["sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= self.controllers_grp_ik
                )
        

        self.leg_ik_main_controller = self.data_exporter.get_data(f"{self.side}_{self.finger_front_name.lower()}LegModule", "end_ik")


        finger_plane_guide = cmds.createNode("transform", name = f"{self.side}_fingerPlaneIk_GUIDE", parent=self.guides_grp, ss=True)
        cmds.matchTransform(finger_plane_guide, self.leg_ball_blm, pos=True)

        cmds.setAttr(f"{finger_plane_guide}.ty", 0)

        cmds.connectAttr(f"{finger_plane_guide}.worldMatrix[0]", f"{self.finger_plane_grp[0]}.offsetParentMatrix")

        ss.fk_switch(target = self.finger_plane, sources= [self.leg_ik_main_controller, self.leg_ball_blm], sources_names=["Leg IK Controller", "Foot"])




        cmds.addAttr(self.finger_attributes_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.finger_attributes_ctl+".extraAttr", channelBox=True, lock=True)
        cmds.addAttr(self.finger_attributes_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="FingerAttributes", attributeType="enum", enumName="———")
        cmds.setAttr(f"{self.finger_attributes_ctl}.FingerAttributes", lock=True, keyable=False, channelBox=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Curl", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Spread", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Twist", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)
        cmds.addAttr(self.finger_attributes_ctl, longName="Fan", attributeType="float", defaultValue=0, max=10, min=-10, keyable=True)


        final_path = core.DataManager.get_guide_data()
        self.controller_number = 5
        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")
        for template_name, guides in guides_data.items():
            if not isinstance(guides, dict):
                continue  
            for guide_name, guide_info in guides.items():
                if guide_name == self.fingers[0]:
                    self.controller_number = int(guide_info.get("controllerNumber", 0))

        thumb_guides = [finger for finger in self.fingers if "thumb" in finger.lower()]
        index_guides = [finger for finger in self.fingers if "index" in finger.lower()]
        middle_guides = [finger for finger in self.fingers if "middle" in finger.lower()]
        pinky_guides = [finger for finger in self.fingers if "pinky" in finger.lower()]
        ring_guides = [finger for finger in self.fingers if "ring" in finger.lower()]

        self.controllers = []

        self.ik_controllers = []
        finger_list = [thumb_guides, index_guides, middle_guides, pinky_guides, ring_guides]
        for i in range (self.controller_number):
            finger = finger_list[i]
            finger_name = ''.join([c for c in finger[0].split('_')[1] if not c.isdigit()])
            
            controllers = []
            aim_matrix_guides = []
            self.sdk_thumb_nodes = []
            self.sdk_index_nodes = []
            self.sdk_middle_nodes = []
            self.sdk_pinky_nodes = []

            for index in range(0, 2):
                aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{finger_name}Guide0{index+1}_AMX", ss=True)

                cmds.setAttr(aim_matrix + ".primaryInputAxis", *self.primary_aim_vector, type="double3")
                cmds.setAttr(aim_matrix + ".secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                cmds.setAttr(aim_matrix + ".secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                
                cmds.setAttr(aim_matrix + ".primaryMode", 1)
                cmds.setAttr(aim_matrix + ".secondaryMode", 1)

                next_index = index + 2 if (index + 2) < len(finger) else 0

                cmds.connectAttr(finger[index] + ".worldMatrix[0]", aim_matrix + ".inputMatrix")
                cmds.connectAttr(finger[index+1] + ".worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
                cmds.connectAttr(finger[next_index] + ".worldMatrix[0]", aim_matrix + ".secondaryTargetMatrix")

                aim_matrix_guides.append(aim_matrix)

            aim_matrix_guides.append(cmds.createNode("blendMatrix", name=f"{self.side}_{finger_name}Guide0{index+2}_BLM", ss=True))
            cmds.connectAttr(finger[-1] + ".worldMatrix[0]", aim_matrix_guides[-1] + ".inputMatrix")
            cmds.connectAttr(aim_matrix_guides[1] + ".outputMatrix", aim_matrix_guides[-1] + ".target[0].targetMatrix")
            cmds.setAttr(aim_matrix_guides[-1] + ".target[0].translateWeight", 0)

            controller_matrices = []
            fk_grps = []
            for j, guide in enumerate(aim_matrix_guides):


                finger_name = guide.split('_')[1].replace('Guide', '')

                ctl, grp = controller_creator(
                    name=f"{self.side}_{finger_name}",
                    suffixes=["GRP", "SDK", "ANM"],
                    lock=["tx", "ty", "tz" ,"sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= controllers[-1] if controllers else self.controllers_grp
                )


                # cmds.setDrivenKeyframe(at="ry", dv=0, cd=f"{self.finger_attributes_ctl}.Spread", v=0)
                # cmds.setDrivenKeyframe(at="ry", dv=10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[2])
                # cmds.setDrivenKeyframe(at="ry", dv=-10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[3])

                # cmds.setDrivenKeyframe(at="rx", dv=0, cd=f"{self.finger_attributes_ctl}.Twist", v=0)
                # cmds.setDrivenKeyframe(at="rx", dv=10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[4])
                # cmds.setDrivenKeyframe(at="rx", dv=-10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[5])

                # cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Fan", v=0)
                # cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[6])
                # cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[7])


                if i == 0:
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, -25, 15, 20, -20, 30, -30], thumb_values=[0,0,0,0,0,0, 0,0])
                        
                    elif j == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    # elif j == 2:
                    #     self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                if i == 1:
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, 0, 0, 20, -20, 30, -30], thumb_values=[0,0,0,0,0,0, 0,0])   
                    elif j == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    # elif j == 2:
                        # self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                if i == 2: 
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, 25, -15, 20, -20, -2, 2], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif j == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    # elif j == 2:
                    #     self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                if i == 3:
                    if j == 0:
                        self.fingers_attributes_callback(grp[1], finger_values=[-90, 20, 30, -15, 20, -20, -50, 50], thumb_values=[0,0,0,0,0,0, 0,0])
                    elif j == 1:
                        self.fingers_attributes_callback(grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                    # elif j == 2:
                    #     self.fingers_attributes_callback(grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])

                if controllers:
                    offset_matrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}_MLT", ss=True)
                    inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_{finger_name}_INV", ss=True)
                    cmds.connectAttr(aim_matrix_guides[j-1] + ".outputMatrix", inverse + ".inputMatrix")
                    cmds.connectAttr(guide + ".outputMatrix", offset_matrix + ".matrixIn[0]")
                    cmds.connectAttr(controllers[-1] + ".worldInverseMatrix[0]", offset_matrix + ".matrixIn[1]")
                    cmds.connectAttr(controllers[-1] + ".worldMatrix[0]", offset_matrix + ".matrixIn[2]")
                    cmds.connectAttr(inverse + ".outputMatrix", offset_matrix + ".matrixIn[3]")
                    cmds.connectAttr(offset_matrix + ".matrixSum", grp[0] + ".offsetParentMatrix")
                else:
                    cmds.connectAttr(guide + ".outputMatrix", grp[0] + ".offsetParentMatrix")                

                cmds.setAttr(f"{grp[0]}.rotate", 0,0,0, type="double3")
                cmds.setAttr(f"{grp[0]}.translate", 0,0,0, type="double3")

                controller_matrices.append(ctl + ".worldMatrix[0]")
                fk_grps.append(grp)
                controllers.append(ctl)
                self.controllers.append(ctl)

            ik_matrices, grp_ik = self.ik_setup(aim_matrix_guides, finger_name)

            self.pairblends(ik_matrices, controller_matrices, fk_grps, finger_name, grp_ik)

        parent = self.controllers[::3]

        cmds.delete(cmds.pointConstraint(parent, self.finger_attributes_nodes[0], mo=False)) # Position the main attr grp

    def pairblends(self, ik, fk, fk_grp, finger_name, ctl_ik):

        finger_name_chain = re.sub(r'\d+', '', finger_name)
        finger_name_chain = finger_name_chain.replace('Guide', '').strip('_')

        finger_name = finger_name_chain

        cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{fk_grp[0][0]}.visibility", force=True)
        self.ik_visibility_rev = cmds.createNode("reverse", name=f"{self.side}_FkVisibility_REV", ss=True)
        cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{self.ik_visibility_rev}.inputX")
        cmds.connectAttr(f"{self.ik_visibility_rev}.outputX", f"{self.controllers_grp_ik}.visibility", force=True)


        self.blend_wm = []
        end_joints = []
        for i, (fk, ik) in enumerate(zip(fk, ik)):

            blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{finger_name.replace('Guide', '')}0{i+1}_BLM", ss=True)
            cmds.connectAttr(ik, f"{blendMatrix}.inputMatrix")
            cmds.connectAttr(fk, f"{blendMatrix}.target[0].targetMatrix")
            cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{blendMatrix}.target[0].weight")

            self.blend_wm.append(f"{blendMatrix}.outputMatrix")

            joint = cmds.createNode("joint", name=f"{self.side}_{finger_name.replace('Guide', '')}0{i+1}_JNT", parent=self.skinning_grp, ss=True)
            cmds.connectAttr(blendMatrix + ".outputMatrix", joint + ".offsetParentMatrix")
            end_joints.append(joint)


        core.pv_locator(name=f"{self.side}_{finger_name.replace('Guide', '')}PVLocator", parents=[self.pv, end_joints[1]], parent_append=self.controllers_grp_ik)
        
        
    def ik_setup(self, guides_list, finger_name):
        self.side = guides_list[0].split("_")[0]

        root_wm = cmds.createNode("parentMatrix", name=f"{self.side}_legFingersParent_PMX", ss=True)
        cmds.connectAttr(guides_list[0] + ".outputMatrix", root_wm + ".inputMatrix")
        cmds.connectAttr(self.leg_ball_blm + ".worldMatrix[0]", root_wm + ".target[0].targetMatrix")
        cmds.connectAttr(self.foot_rotation + ".worldMatrix[0]", root_wm + ".target[1].targetMatrix")
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", root_wm + ".target[0].weight")
        reverse = cmds.createNode("reverse", name=f"{self.side}_legFingers_IKFK_REV", ss=True)
        cmds.connectAttr(self.ikSwitch_ctl + ".switchIkFk", reverse + ".inputX")
        cmds.connectAttr(reverse + ".outputX", root_wm + ".target[1].weight")

        offset_matrix = get_offset_matrix(guides_list[0] + ".outputMatrix", self.leg_ball_blm)
        offset_matrix02 = get_offset_matrix(guides_list[0] + ".outputMatrix", self.foot_rotation)

        cmds.setAttr(root_wm + ".target[0].offsetMatrix", *offset_matrix, type="matrix")
        cmds.setAttr(root_wm + ".target[1].offsetMatrix", *offset_matrix02, type="matrix")

        ctl, grp = controller_creator(
                    name=f"{self.side}_{finger_name}Ik",
                    suffixes=["GRP", "SDK", "ANM"],
                    lock=["sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= self.controllers_grp_ik
                )
        
        self.pv, pv_grp = controller_creator(
                    name=f"{self.side}_{finger_name}Pv",
                    suffixes=["GRP", "SDK", "ANM"],
                    lock=["sx", "sy", "sz", "visibility"],
                    ro=False,
                    parent= self.controllers_grp_ik
                )
        
        cmds.addAttr(ctl, shortName="attachedFk", niceName="Fk ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(ctl+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(ctl, shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(ctl+".attachedFKVis", channelBox=True)

        self.attached_fk_vis = cmds.createNode("condition", name=f"{self.side}_{finger_name}AttachedFk_VIS", ss=True)
        cmds.setAttr(f"{self.attached_fk_vis}.operation", 0)
        cmds.setAttr(f"{self.attached_fk_vis}.colorIfFalseR", 0)
        cmds.setAttr(f"{self.attached_fk_vis}.secondTerm", 0)
        cmds.connectAttr(f"{ctl}.attachedFKVis", f"{self.attached_fk_vis}.colorIfTrueR")
        cmds.connectAttr(f"{self.finger_attributes_ctl}.switchIkFk", f"{self.attached_fk_vis}.firstTerm")

        pv_pos_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}PVPosition_MMX", ss=True)
        cmds.connectAttr(f"{guides_list[1]}.outputMatrix", f"{pv_pos_multMatrix}.matrixIn[1]")
        cmds.connectAttr(f"{pv_pos_multMatrix}.matrixSum", f"{pv_grp[0]}.offsetParentMatrix")

        pv_pos_4b4 = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}PVPosition_F4X", ss=True)
        cmds.connectAttr(f"{pv_pos_4b4}.output", f"{pv_pos_multMatrix}.matrixIn[0]")

        # temp_pos01 = cmds.createNode("transform",n = "temp01", ss=True)
        # temp_pos02 = cmds.createNode("transform",n = "temp02", ss=True)
        # temp_pos03 = cmds.createNode("transform",n = "temp03", ss=True)

        # cmds.connectAttr(f"{guides_list[0]}.outputMatrix", f"{temp_pos01}.offsetParentMatrix")
        # cmds.connectAttr(f"{guides_list[1]}.outputMatrix", f"{temp_pos02}.offsetParentMatrix")
        # cmds.connectAttr(f"{guides_list[2]}.outputMatrix", f"{temp_pos03}.offsetParentMatrix")

        # pos1 = cmds.xform(temp_pos01, q=True, ws=True, t=True)
        # pos2 = cmds.xform(temp_pos02, q=True, ws=True, t=True)

        # distance01 = math.sqrt(sum([(a - b) ** 2 for a, b in zip(pos1, pos2)]))

        # pos3 = cmds.xform(temp_pos02, q=True, ws=True, t=True)
        # pos4 = cmds.xform(temp_pos03, q=True, ws=True, t=True)

        # distance02 = math.sqrt(sum([(a - b) ** 2 for a, b in zip(pos3, pos4)]))

        if core.DataManager.get_asset_name() == "cheetah":
            if self.side == "R":
                cmds.setAttr(f"{pv_pos_4b4}.in31", -5)#(distance01+distance02)*-1)
            else:
                cmds.setAttr(f"{pv_pos_4b4}.in31", 5)#(distance01+distance02))

        else:
            if self.side == "R":
                cmds.setAttr(f"{pv_pos_4b4}.in31", -50)#(distance01+distance02)*-1)
            else:
                cmds.setAttr(f"{pv_pos_4b4}.in31", 50)#(distance01+distance02))
        

        
        self.ik_controllers.append(ctl)
        
        cmds.connectAttr(guides_list[-1] + ".outputMatrix", grp[0] + ".offsetParentMatrix")

        ss.fk_switch(target = ctl, sources= [self.finger_plane, self.leg_ball_blm], sources_names=["Finger Plane", "Foot"])


        ss.fk_switch(target = self.pv, sources= [self.leg_ball_blm, ctl, self.finger_plane], sources_names=["Foot", "Ik Controller", "Finger Plane"])


        self.ikHandleManager = f"{ctl}.worldMatrix[0]"

        self.distance_between_output = []
        for i, (first, second) in enumerate(zip([f"{guides_list[0]}.outputMatrix", f"{guides_list[1]}.outputMatrix", f"{root_wm}.outputMatrix"], [f"{guides_list[1]}.outputMatrix", f"{guides_list[2]}.outputMatrix", f"{self.ikHandleManager}"])):
            distance = cmds.createNode("distanceBetween", name=f"{finger_name}_DB", ss=True)
            cmds.connectAttr(f"{first}", f"{distance}.inMatrix1")
            cmds.connectAttr(f"{second}", f"{distance}.inMatrix2")

            if i == 2:
                global_scale_divide = cmds.createNode("divide", name=f"{self.side}_{finger_name}GlobalScaleFactor_DIV", ss=True)
                cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{global_scale_divide}.input2")
                cmds.connectAttr(f"{distance}.distance", f"{global_scale_divide}.input1")
                self.distance_between_output.append(f"{global_scale_divide}.output")
            else:
                self.distance_between_output.append(f"{distance}.distance")
            

        # --- STRETCH --- #

        arm_length = cmds.createNode("sum", name=f"{self.side}_{finger_name}Length_SUM", ss=True)
        cmds.connectAttr(f"{self.distance_between_output[0]}", f"{arm_length}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[1]}", f"{arm_length}.input[1]")

        arm_length_min = cmds.createNode("min", name=f"{self.side}_{finger_name}ClampedLength_MIN", ss=True)
        cmds.connectAttr(f"{arm_length}.output", f"{arm_length_min}.input[0]")
        cmds.connectAttr(f"{self.distance_between_output[2]}", f"{arm_length_min}.input[1]")



        # --- CUSTOM SOLVER --- #

        upper_divide, upper_arm_acos, power_mults = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{self.distance_between_output[1]}", f"{arm_length_min}.output"], name = f"{self.side}_{finger_name}Upper", acos=True)
        lower_divide, lower_power_mults, negate_cos_value = core.law_of_cosine(sides = [f"{self.distance_between_output[0]}", f"{arm_length_min}.output", f"{self.distance_between_output[1]}"],
                                                                             power = [power_mults[0], power_mults[2], power_mults[1]],
                                                                             name = f"{self.side}_{finger_name}Lower", 
                                                                             negate=True)

        # --- Aligns --- #
 
        upper_arm_ik_aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{finger_name}UpperIk_AIM", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{upper_arm_ik_aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.pv}.worldMatrix", f"{upper_arm_ik_aim_matrix}.secondaryTargetMatrix")
        cmds.connectAttr(f"{root_wm}.outputMatrix", f"{upper_arm_ik_aim_matrix}.inputMatrix")
        cmds.setAttr(f"{upper_arm_ik_aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

        self.upperArmIkWM = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}01_MMX", ss=True)
        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}UpperIkLocal_F4X", ss=True)
        sin = cmds.createNode("sin", name=f"{self.side}_{finger_name}UpperIkWM_SIN", ss=True)
        negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}UpperIkWM_NEGATE", ss=True)

        cmds.connectAttr(f"{upper_arm_ik_aim_matrix}.outputMatrix", f"{self.upperArmIkWM}.matrixIn[1]")
        cmds.connectAttr(f"{fourByfour}.output", f"{self.upperArmIkWM}.matrixIn[0]")

        cmds.connectAttr(f"{upper_divide}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{upper_divide}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{sin}.output", f"{fourByfour}.in01")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in10")

        cmds.connectAttr(f"{upper_arm_acos}.output", f"{sin}.input")
        cmds.connectAttr(f"{sin}.output", f"{negate}.input")

        cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryMode", 1)
            
        # Lower

        cosValueSquared = cmds.createNode("multiply", name=f"{self.side}_{finger_name}LowerCosValueSquared_MUL", ss=True)
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[0]")
        cmds.connectAttr(f"{lower_divide}.output", f"{cosValueSquared}.input[1]")

        lower_sin_value_squared = cmds.createNode("subtract", name=f"{self.side}_{finger_name}LowerSinValueSquared_SUB", ss=True)
        cmds.connectAttr(f"{cosValueSquared}.output", f"{lower_sin_value_squared}.input2")
        cmds.setAttr(f"{lower_sin_value_squared}.input1", 1)
        self.floatConstant_zero = cmds.createNode("floatConstant", name=f"{self.side}_zero{finger_name}_FLC", ss=True)
        cmds.setAttr(f"{self.floatConstant_zero}.inFloat", 0)
        lower_sin_value_squared_clamped = cmds.createNode("max", name=f"{self.side}_{finger_name}LowerSinValueSquared_MAX", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared}.output", f"{lower_sin_value_squared_clamped}.input[1]")
        cmds.connectAttr(f"{self.floatConstant_zero}.outFloat", f"{lower_sin_value_squared_clamped}.input[0]")


        lower_sin = cmds.createNode("power", name=f"{self.side}_{finger_name}LowerSin_POW", ss=True)
        cmds.connectAttr(f"{lower_sin_value_squared_clamped}.output", f"{lower_sin}.input")
        cmds.setAttr(f"{lower_sin}.exponent", 0.5)

        negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}LowerSin_NEGATE", ss=True)
        cmds.connectAttr(f"{lower_sin}.output", f"{negate}.input")

        fourByfour = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}LowerIkLocal_F4X", ss=True)
      
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in11")
        cmds.connectAttr(f"{negate_cos_value}.output", f"{fourByfour}.in00")
        cmds.connectAttr(f"{lower_sin}.output", f"{fourByfour}.in10")
        cmds.connectAttr(f"{negate}.output", f"{fourByfour}.in01")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}UpperTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, -1, 0, type="double3") ########################## CAMBIO QUIZAS

        else:
            cmds.connectAttr(f"{self.distance_between_output[0]}", f"{fourByfour}.in30")
            cmds.setAttr(upper_arm_ik_aim_matrix + ".secondaryInputAxis", 0, 1, 0, type="double3") ########################## CAMBIO QUIZAS


        lower_wm_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}02_MMX", ss=True)
        cmds.connectAttr(f"{fourByfour}.output", f"{lower_wm_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixIn[1]")

        # Hand
        lower_inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{finger_name}LowerIkInverse_MTX", ss=True)
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{lower_inverse_matrix}.inputMatrix")

        hand_local_matrix_multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}EndBaseLocal_MMX", ss=True)
        cmds.connectAttr(f"{self.ikHandleManager}", f"{hand_local_matrix_multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{lower_inverse_matrix}.outputMatrix", f"{hand_local_matrix_multmatrix}.matrixIn[1]")

        hand_local_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{finger_name}EndLocal_F4X", ss=True)


        # Depen de si alex es subnormal o no necessitas el blend matrix
        hand_wm_multmatrix_end_own_rotation = cmds.createNode("multMatrix", name=f"{self.side}_{finger_name}03_MMX", ss=True)
        cmds.connectAttr(f"{hand_local_matrix}.output", f"{hand_wm_multmatrix_end_own_rotation}.matrixIn[0]")
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{hand_wm_multmatrix_end_own_rotation}.matrixIn[1]")

        hand_wm_multmatrix_end = cmds.createNode("blendMatrix", name=f"{self.side}_{finger_name}End_BLM", ss=True)
        cmds.connectAttr(f"{hand_wm_multmatrix_end_own_rotation}.matrixSum", f"{hand_wm_multmatrix_end}.inputMatrix")
        cmds.connectAttr(f"{lower_wm_multmatrix}.matrixSum", f"{hand_wm_multmatrix_end}.target[0].targetMatrix")
        cmds.setAttr(f"{hand_wm_multmatrix_end}.target[0].translateWeight", 0)
        cmds.setAttr(f"{hand_wm_multmatrix_end}.target[0].rotateWeight", 1)
        cmds.setAttr(f"{hand_wm_multmatrix_end}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{hand_wm_multmatrix_end}.target[0].shearWeight", 0)


        for i in range(0, 3):
            row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{self.side}_{finger_name}EndLocalAxis{i}_RFM", ss=True)
            cmds.connectAttr(f"{hand_local_matrix_multmatrix}.matrixSum", f"{row_from_matrix}.matrix")
            cmds.setAttr(f"{row_from_matrix}.input", i)
            for z, attr in enumerate(["X", "Y", "Z", "W"]):
                cmds.connectAttr(f"{row_from_matrix}.output{attr}", f"{hand_local_matrix}.in{i}{z}")

        if self.side == "R":
            translate_negate = cmds.createNode("negate", name=f"{self.side}_{finger_name}LowerTranslate_NEGATE", ss=True)
            cmds.connectAttr(f"{self.distance_between_output[1]}", f"{translate_negate}.input")
            cmds.connectAttr(f"{translate_negate}.output", f"{hand_local_matrix}.in30")
        else:
            cmds.connectAttr(f"{self.distance_between_output[1]}", f"{hand_local_matrix}.in30")    

        self.ik_wm = [ f"{self.upperArmIkWM}.matrixSum", f"{lower_wm_multmatrix}.matrixSum",f"{hand_wm_multmatrix_end}.outputMatrix"]

        self.attached_fk()

        return self.ik_wm, grp[0]

    def attached_fk(self):
        """
        Creates the attached FK controllers for the neck module, including sub-neck controllers and joints.

        Args:
            self: Instance of the SpineModule class.
        Returns:
            list: A list of sub-neck joint names created for the attached FK system.
        """
        
        ctls_sub = []
        ctls_sdk = []
        for i, joint in enumerate(self.ik_wm):
            name = joint.split(".")[0].split("_")[1]

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}AttachedFk",
                suffixes=["GRP", "SDK", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=ctls_sub[-1] if ctls_sub else self.controllers_grp_ik
            )
            if "thumb" in name.lower():
                if i == 0:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-90, 20, -25, 15, 20, -20, 30, -30], thumb_values=[0,0,0,0,0,0, 0,0])
                    
                elif i == 1:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                # elif i == 2:
                #     self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
            if "index" in name.lower():
                if i == 0:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-90, 20, 0, 0, 20, -20, 30, -30], thumb_values=[0,0,0,0,0,0, 0,0])   
                elif i == 1:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                # elif i == 2:
                #     self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
            if "middle" in name.lower(): 
                if i == 0:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-90, 20, 25, -15, 20, -20, -2, 2], thumb_values=[0,0,0,0,0,0, 0,0])
                elif i == 1:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                # elif i == 2:
                #     self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
            if "ring" in name.lower():
                if i == 0:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-90, 20, 30, -15, 20, -20, -50, 50], thumb_values=[0,0,0,0,0,0, 0,0])
                elif i == 1:
                    self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 18, 0, 0, 10, -10, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])
                # elif i == 2:
                #     self.fingers_attributes_callback(controller_grp[1], finger_values=[-80, 15, 0, 0, 5, -5, 0, 0], thumb_values=[0,0,0,0,0,0, 0,0])

            if i == 0:  
                cmds.setAttr(f"{controller_grp[0]}.inheritsTransform", 0)
                # cmds.connectAttr(f"{self.hand_ik_ctl}.attachedFKVis", f"{controller_grp[0]}.visibility")
                cmds.connectAttr(f"{self.attached_fk_vis}.outColorR", f"{controller_grp[0]}.visibility")
                cmds.connectAttr(f"{joint}", f"{controller_grp[0]}.offsetParentMatrix")

            else:
                mmt = cmds.createNode("multMatrix", n=f"{self.side}_{name}AttachedFk0{i+1}_MMT")

                inverse = cmds.createNode("inverseMatrix", n=f"{self.side}_{name}AttachedFk0{i+1}_IMX")
                cmds.connectAttr(f"{self.ik_wm[i-1]}", f"{inverse}.inputMatrix")
                cmds.connectAttr(f"{joint}", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{inverse}.outputMatrix", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")

                for attr in ["translateX","translateY","translateZ", "rotateX", "rotateY", "rotateZ"]:  
                    cmds.setAttr(f"{controller_grp[0]}.{attr}", 0)

            ctls_sub.append(ctl)
            ctls_sdk.append(controller_grp[1])

        self.attached_fk_ctls.append(ctls_sub)
        self.attached_fk_sdks.append(ctls_sdk)

        self.ik_wm = [f"{ctl}.worldMatrix[0]" for ctl in ctls_sub]     

    def fingers_attributes_callback(self, ctl, finger_values=[None], thumb_values=[None]):

        cmds.select(ctl)
        
        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Curl", v=0, inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Curl", v=finger_values[0], inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Curl", v=finger_values[1], inTangentType="linear", outTangentType="linear")

        cmds.setDrivenKeyframe(at="ry", dv=0, cd=f"{self.finger_attributes_ctl}.Spread", v=0, inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="ry", dv=10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[2], inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="ry", dv=-10, cd=f"{self.finger_attributes_ctl}.Spread", v=finger_values[3], inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rx", dv=0, cd=f"{self.finger_attributes_ctl}.Twist", v=0, inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rx", dv=10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[4], inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rx", dv=-10, cd=f"{self.finger_attributes_ctl}.Twist", v=finger_values[5], inTangentType="linear", outTangentType="linear")

        cmds.setDrivenKeyframe(at="rz", dv=0, cd=f"{self.finger_attributes_ctl}.Fan", v=0, inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rz", dv=10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[6], inTangentType="linear", outTangentType="linear")
        cmds.setDrivenKeyframe(at="rz", dv=-10, cd=f"{self.finger_attributes_ctl}.Fan", v=finger_values[7], inTangentType="linear", outTangentType="linear")
        
    

