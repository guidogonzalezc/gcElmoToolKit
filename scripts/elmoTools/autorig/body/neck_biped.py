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


class NeckModule():
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

    def make(self, guide_name, num_joints = 5):
        """
        Creates the neck module, including the neck chain, controllers, and various systems.

        Args:
            self: Instance of the NeckModule class.
        """

        self.guide_name = guide_name
        self.num_joints = int(num_joints)

        self.primary_aim = "y"
        self.primary_aim_vector = AXIS_VECTOR[self.primary_aim]
        self.secondary_aim = "z"
        self.secondary_aim_vector = AXIS_VECTOR[self.secondary_aim]

        self.side = self.guide_name.split("_")[0]

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_neckModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_neckControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_neckSkinning_GRP", ss=True, p=self.skel_grp)

        pick_matrix = cmds.createNode("pickMatrix", name=f"{self.side}_neckPickMatrix_PMX", ss=True)
        cmds.connectAttr(f"{self.masterWalk_ctl}.worldMatrix[0]", f"{pick_matrix}.inputMatrix")
        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{self.module_trn}.offsetParentMatrix")

        self.create_chain()

        self.data_exporter.append_data(f"{self.side}_neckModule", 
                                    {"skinning_transform": self.skinning_trn,
                                    "neck_ctl": self.main_controllers[0],
                                    "head_ctl": self.main_controllers[-1],

                                    }
                                  )

    def create_chain(self):
        """
        Creates the neck joint chain by importing guides and parenting the first joint to the module transform.

        Args:
            self: Instance of the neckModule class.
        """
        
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)


        aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_neck01Guide_AMX", ss=True)
        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.guides[1]}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix")
        cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

        blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_headGuide_BMX", ss=True)
        cmds.connectAttr(f"{self.guides[1]}.worldMatrix[0]", f"{blend_matrix}.inputMatrix")
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)
        
        self.blend_head = blend_matrix


        self.main_controllers = []
        self.main_controllers_grp = []

        self.guide_matrix = [aim_matrix, blend_matrix]

        for i, matrix in enumerate(self.guide_matrix ):
            pre_name = "neck" if i != len(self.guide_matrix ) - 1 else "head"
            name = f"Tan0{i}" if i == 1 else f"0{i+1}"
            name = name if pre_name == "neck" else ""
            ctl, ctl_grp = controller_creator(
                name=f"{self.side}_{pre_name}{name}",
                suffixes=["GRP", "ANM"],
                lock=["visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.controllers_trn)

            cmds.connectAttr(f"{matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix")

            self.main_controllers.append(ctl)
            self.main_controllers_grp.append(ctl_grp)

        fk_switch(target= self.main_controllers[-1], sources= [self.main_controllers[0]], default_rotate=0, sources_names= ["Neck"])

        cmds.addAttr(self.main_controllers[-1], shortName="STRETCH", niceName="Stretch ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.main_controllers[-1]+".STRETCH", channelBox=True, lock=True)
        cmds.addAttr(self.main_controllers[-1], shortName="stretch", niceName="Stretch", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        cmds.addAttr(self.main_controllers[-1], shortName="attachedFk", niceName="Fk ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.main_controllers[-1]+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(self.main_controllers[-1], shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(self.main_controllers[-1]+".attachedFKVis", channelBox=True)

        

        clamped_distance = cmds.createNode("distanceBetween", name=f"{self.side}_neckToHeadClamped_DIB", ss=True)
        real_distance = cmds.createNode("distanceBetween", name=f"{self.side}_neckToHead_DIB", ss=True)
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{real_distance}.inMatrix1")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{real_distance}.inMatrix2")

        real_dis_global = cmds.createNode("divide", name=f"{self.side}_realDistanceGlobal_DIV", ss=True)
        cmds.connectAttr(f"{real_distance}.distance", f"{real_dis_global}.input1")
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{real_dis_global}.input2")

        cmds.connectAttr(f"{self.guide_matrix[0]}.outputMatrix", f"{clamped_distance}.inMatrix1")
        cmds.connectAttr(f"{self.guide_matrix[1]}.outputMatrix", f"{clamped_distance}.inMatrix2")

        neck_to_head_blendTwo = cmds.createNode("blendTwoAttr", name=f"{self.side}_neckToHead_B2A", ss=True)
        cmds.connectAttr(f"{clamped_distance}.distance", f"{neck_to_head_blendTwo}.input[0]")
        cmds.connectAttr(f"{real_dis_global}.output", f"{neck_to_head_blendTwo}.input[1]")
        cmds.connectAttr(f"{self.main_controllers[-1]}.stretch", f"{neck_to_head_blendTwo}.attributesBlender")

        neck01_world_matrix_aim = cmds.createNode("aimMatrix", name=f"{self.side}_neckWM_AIM", ss=True)
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{neck01_world_matrix_aim}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{neck01_world_matrix_aim}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{neck01_world_matrix_aim}.secondaryTargetMatrix")
        cmds.setAttr(f"{neck01_world_matrix_aim}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{neck01_world_matrix_aim }.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{neck01_world_matrix_aim}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{neck01_world_matrix_aim}.secondaryMode", 2)

        neck01_world_matrix = cmds.createNode("multMatrix", name=f"{self.side}_neck01_MMX", ss=True)
        decompose_wm = cmds.createNode("decomposeMatrix", name=f"{self.side}_neck01_DCM", ss=True)
        decompose_ctl = cmds.createNode("decomposeMatrix", name=f"{self.side}_neck01CTL_DCM", ss=True)
        negate = cmds.createNode("negate", name=f"{self.side}_neck01Negate_NEG", ss=True)
        sum = cmds.createNode("sum", name=f"{self.side}_neck01_SUM", ss=True)
        compose = cmds.createNode("composeMatrix", name=f"{self.side}_neck01_CMP", ss=True)

        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{decompose_ctl}.inputMatrix")
        cmds.connectAttr(f"{decompose_wm}.outputRotateY", f"{negate}.input")
        cmds.connectAttr(f"{negate}.output", f"{sum}.input[1]")
        cmds.connectAttr(f"{neck01_world_matrix_aim}.outputMatrix", f"{decompose_wm}.inputMatrix")
        cmds.connectAttr(f"{decompose_ctl}.outputRotateY", f"{sum}.input[0]")
        cmds.connectAttr(f"{sum}.output", f"{compose}.inputRotateY")
        cmds.connectAttr(f"{compose}.outputMatrix", f"{neck01_world_matrix}.matrixIn[0]")

        cmds.connectAttr(f"{neck01_world_matrix_aim}.outputMatrix", f"{neck01_world_matrix}.matrixIn[1]")






        tan01_translate_offset = cmds.createNode("fourByFourMatrix", name=f"{self.side}_headTranslateOffset_FBM", ss=True)
        cmds.connectAttr(f"{neck_to_head_blendTwo}.output", f"{tan01_translate_offset}.in31")

        tan01_end_pos = cmds.createNode("multMatrix", name=f"{self.side}_headNoScale_MMT", ss=True)
        cmds.connectAttr(f"{tan01_translate_offset}.output", f"{tan01_end_pos}.matrixIn[0]")
        cmds.connectAttr(f"{neck01_world_matrix}.matrixSum", f"{tan01_end_pos}.matrixIn[1]")
        
        head_scale = cmds.createNode("blendMatrix", name=f"{self.side}_headScale_BMX", ss=True)
        cmds.connectAttr(f"{tan01_end_pos}.matrixSum", f"{head_scale}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{head_scale}.target[0].targetMatrix")
        cmds.setAttr(f"{head_scale}.target[0].translateWeight", 0)
        # cmds.setAttr(f"{head_scale}.target[0].rotateWeight", 0)

        head_with_local_rotation = cmds.createNode("blendMatrix", name=f"{self.side}_headLocalRotation_BMX", ss=True)
        cmds.connectAttr(f"{tan01_end_pos}.matrixSum", f"{head_with_local_rotation}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{head_with_local_rotation}.target[0].targetMatrix")
        cmds.setAttr(f"{head_with_local_rotation}.target[0].translateWeight", 0)

        cvs = [f"{neck01_world_matrix}.matrixSum", f"{head_scale}.outputMatrix"]

        t_values = []
        for i in range(self.num_joints):
            t = i / (float(self.num_joints) - 1)    
            t_values.append(t)

        t_values.pop(-1)
        
        self.old_joints = de_boor_core_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs=cvs, num_joints=self.num_joints-1, name=f"{self.side}_neck", parent=self.skinning_trn, custom_parm=t_values, use_position=True, use_tangent=True, use_up=True, negate_secundary=True, align=True)

        self.input_connections = []
        head_temp_joint = cmds.createNode("joint", n=f"{self.side}_head_JNT", parent=self.skinning_trn, ss=True)
        cmds.connectAttr(f"{head_with_local_rotation}.outputMatrix", f"{head_temp_joint}.offsetParentMatrix")
        self.old_joints.append(head_temp_joint)
        for joint in self.old_joints:
            input_connection = cmds.listConnections(f"{joint}.offsetParentMatrix", source=True, destination=False, plugs=True)[0]
            self.input_connections.append(input_connection)


        self.attached_fk()

    def attached_fk(self):
        """
        Creates the attached FK controllers for the neck module, including sub-neck controllers and joints.

        Args:
            self: Instance of the neckModule class.
        Returns:
            list: A list of sub-neck joint names created for the attached FK system.
        """
        
        ctls_sub_neck = []
        sub_neck_ctl_trn = cmds.createNode("transform", n=f"{self.side}_subNeckControllers_GRP", parent=self.controllers_trn, ss=True)
        cmds.setAttr(f"{sub_neck_ctl_trn}.inheritsTransform", 0)
        cmds.connectAttr(f"{self.main_controllers[-1]}.attachedFKVis", f"{sub_neck_ctl_trn}.visibility")

        for i, joint in enumerate(self.input_connections):
            name = joint.split(".")[0].split("_")[1]
            if "Scale" in name or "End" in name:
                name = name.replace("Scale", "").replace("End", "")
                if i == len(self.input_connections)-1:
                    name = name.replace("neck", "head")

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}AttachedFk",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=ctls_sub_neck[-1] if ctls_sub_neck else sub_neck_ctl_trn
            )

            if i == 0:
                cmds.connectAttr(f"{joint}", f"{controller_grp[0]}.offsetParentMatrix")

            else:
                mmt = cmds.createNode("multMatrix", n=f"{self.side}_neckSubAttachedFk0{i+1}_MMT")

                inverse = cmds.createNode("inverseMatrix", n=f"{self.side}_neckSubAttachedFk0{i+1}_IMX")
                cmds.connectAttr(f"{self.input_connections[i-1]}", f"{inverse}.inputMatrix")
                cmds.connectAttr(f"{joint}", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{inverse}.outputMatrix", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")

                for attr in ["translateX","translateY","translateZ", "rotateX", "rotateY", "rotateZ"]:
                    cmds.setAttr(f"{controller_grp[0]}.{attr}", 0)

            ctls_sub_neck.append(ctl)

        cmds.delete(self.old_joints)

        skinning_joints = []

        for ctl in ctls_sub_neck:
            name = ctl.replace("AttachedFk_CTL", "_JNT")
            joint_skin = cmds.createNode("joint", n=name, parent=self.skinning_trn, ss=True)
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint_skin}.offsetParentMatrix")
            skinning_joints.append(joint_skin)

        for name in ["center", "left", "right"]:
            try:
                self.distance = guide_import(f"{self.side}_{name}HeadDistance_GUIDE", all_descendents=False)[0]

                pos_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{name}HeadFrontDistance_MMX", ss=True)
                cmds.connectAttr(f"{self.distance}.worldMatrix[0]", f"{pos_multMatrix}.matrixIn[0]")

                inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_{name}HeadDistanceInverse_MTX", ss=True)
                cmds.connectAttr(f"{self.blend_head}.outputMatrix", f"{inverse}.inputMatrix")
                cmds.connectAttr(f"{inverse}.outputMatrix", f"{pos_multMatrix}.matrixIn[1]")
                cmds.connectAttr(f"{skinning_joints[-1]}.worldMatrix[0]", f"{pos_multMatrix}.matrixIn[2]")
                distance_joints = cmds.createNode("joint", name=f"{self.side}_{name}HeadDistance_JNT", ss=True, parent = self.muscle_locators)
                cmds.connectAttr(f"{pos_multMatrix}.matrixSum", f"{distance_joints}.offsetParentMatrix")
            except:
                pass
            
