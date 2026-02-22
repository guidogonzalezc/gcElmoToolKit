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

    def make(self, guide_name):
        """
        Creates the neck module, including the neck chain, controllers, and various systems.

        Args:
            self: Instance of the NeckModule class.
        """

        self.guide_name = guide_name

        self.primary_aim = "z"
        self.primary_aim_vector = AXIS_VECTOR[self.primary_aim]
        self.secondary_aim = "y"
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

        blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_neck03Guide_BMX", ss=True)
        cmds.connectAttr(f"{self.guides[1]}.worldMatrix[0]", f"{blend_matrix}.inputMatrix")
        # cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.target[0].targetMatrix")
        # cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        # cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 0)
        # cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)
        
        self.blend_head = blend_matrix

        self.blend_matrix02 = cmds.createNode("blendMatrix", name=f"{self.side}_neck02Guide_BMX", ss=True)
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{self.blend_matrix02}.inputMatrix")
        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{self.blend_matrix02}.target[0].targetMatrix")
        cmds.setAttr(f"{self.blend_matrix02}.target[0].weight", 0.5)
        cmds.setAttr(f"{self.blend_matrix02}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{self.blend_matrix02}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{self.blend_matrix02}.target[0].shearWeight", 0)


        self.main_controllers = []
        self.main_controllers_grp = []

        self.guide_matrix = [aim_matrix, self.blend_matrix02, blend_matrix]

        for i, matrix in enumerate(self.guide_matrix ):
            pre_name = "neck" if i != len(self.guide_matrix ) - 1 else "head"
            name = f"Tan0{i}" if i == 1 else f"0{i+1}"
            name = name if pre_name == "neck" else ""
            ctl, ctl_grp = controller_creator(
                name=f"{self.side}_{pre_name}{name}",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.controllers_trn)

            cmds.connectAttr(f"{matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix")

            self.main_controllers.append(ctl)
            self.main_controllers_grp.append(ctl_grp)

        cmds.addAttr(self.main_controllers[1], shortName="tangents", niceName="Tangents ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.main_controllers[1]+".tangents", channelBox=True, lock=True)
        cmds.addAttr(self.main_controllers[1], shortName="tangentVisibility", niceName="Tangent Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(self.main_controllers[1]+".tangentVisibility", channelBox=True)


        fk_switch(target= self.main_controllers[1], sources= [self.main_controllers[2], self.main_controllers[0]], sources_names=["Head", "Neck Base"])
        fk_switch(target= self.main_controllers[2], sources= [self.main_controllers[0]])
        # cmds.setAttr(f"{self.main_controllers[1]}.RotateValue", lock=True, keyable=False)

        cmds.addAttr(self.main_controllers[-1], shortName="STRETCH", niceName="Stretch ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.main_controllers[-1]+".STRETCH", channelBox=True, lock=True)
        cmds.addAttr(self.main_controllers[-1], shortName="stretch", niceName="Stretch", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        cmds.addAttr(self.main_controllers[-1], shortName="attachedFk", niceName="Fk ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.main_controllers[-1]+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(self.main_controllers[-1], shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(self.main_controllers[-1]+".attachedFKVis", channelBox=True)

        

        clamped_distance = cmds.createNode("distanceBetween", name=f"{self.side}_neckToTan01_DIB", ss=True)
        real_distance = cmds.createNode("distanceBetween", name=f"{self.side}_neckToTan01_DIB", ss=True)
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{real_distance}.inMatrix1")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{real_distance}.inMatrix2")

        real_dis_global = cmds.createNode("divide", name=f"{self.side}_realDistanceGlobalNeck_DIV", ss=True)
        cmds.connectAttr(f"{real_distance}.distance", f"{real_dis_global}.input1")
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{real_dis_global}.input2")

        cmds.connectAttr(f"{self.guide_matrix[0]}.outputMatrix", f"{clamped_distance}.inMatrix1")
        cmds.connectAttr(f"{self.guide_matrix[1]}.outputMatrix", f"{clamped_distance}.inMatrix2")

        neck_to_tan01_blendTwo = cmds.createNode("blendTwoAttr", name=f"{self.side}_neckToTan01_B2A", ss=True)
        cmds.connectAttr(f"{clamped_distance}.distance", f"{neck_to_tan01_blendTwo}.input[0]")
        cmds.connectAttr(f"{real_dis_global}.output", f"{neck_to_tan01_blendTwo}.input[1]")
        cmds.connectAttr(f"{self.main_controllers[-1]}.stretch", f"{neck_to_tan01_blendTwo}.attributesBlender")

        neck01_world_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_neck01WM_AIM", ss=True)
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{neck01_world_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{neck01_world_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{neck01_world_matrix}.secondaryTargetMatrix")
        cmds.setAttr(f"{neck01_world_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{neck01_world_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{neck01_world_matrix}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{neck01_world_matrix}.secondaryMode", 1)
        tan01_translate_offset = cmds.createNode("fourByFourMatrix", name=f"{self.side}_tan01TranslateOffset_FBM", ss=True)
        cmds.connectAttr(f"{neck_to_tan01_blendTwo}.output", f"{tan01_translate_offset}.in32")

        tan01_end_pos = cmds.createNode("multMatrix", name=f"{self.side}_tan01EndPos_MMT", ss=True)
        cmds.connectAttr(f"{tan01_translate_offset}.output", f"{tan01_end_pos}.matrixIn[0]")
        cmds.connectAttr(f"{neck01_world_matrix}.outputMatrix", f"{tan01_end_pos}.matrixIn[1]")

        tan01_wm_no_rot = cmds.createNode("blendMatrix", name=f"{self.side}_tan01EndWMNoRot_BMX", ss=True)
        cmds.connectAttr(f"{tan01_end_pos}.matrixSum", f"{tan01_wm_no_rot}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[1]}.worldMatrix[0]", f"{tan01_wm_no_rot}.target[0].targetMatrix")
        cmds.setAttr(f"{tan01_wm_no_rot}.target[0].translateWeight", 0)

        clamped_distance_tan_neck = cmds.createNode("distanceBetween", name=f"{self.side}_tan01Toneck_DIB", ss=True)
        real_distance_tan_neck = cmds.createNode("distanceBetween", name=f"{self.side}_tan01Toneck_DIB", ss=True)
        cmds.connectAttr(f"{tan01_wm_no_rot}.outputMatrix", f"{real_distance_tan_neck}.inMatrix1")
        cmds.connectAttr(f"{self.main_controllers[2]}.worldMatrix[0]", f"{real_distance_tan_neck}.inMatrix2")

        real_dis_global_tanToHead = cmds.createNode("divide", name=f"{self.side}_realDistanceGlobalNeckTanToHead_DIV", ss=True)
        cmds.connectAttr(f"{real_distance_tan_neck}.distance", f"{real_dis_global_tanToHead}.input1")
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{real_dis_global_tanToHead}.input2")

        cmds.connectAttr(f"{self.guide_matrix[1]}.outputMatrix", f"{clamped_distance_tan_neck}.inMatrix1")
        cmds.connectAttr(f"{self.guide_matrix[2]}.outputMatrix", f"{clamped_distance_tan_neck}.inMatrix2")

        tan01_to_neck01_blendTwo = cmds.createNode("blendTwoAttr", name=f"{self.side}_tan01Toneck01_B2A", ss=True)
        cmds.connectAttr(f"{clamped_distance_tan_neck}.distance", f"{tan01_to_neck01_blendTwo}.input[0]")
        cmds.connectAttr(f"{real_dis_global_tanToHead}.output", f"{tan01_to_neck01_blendTwo}.input[1]")
        cmds.connectAttr(f"{self.main_controllers[-1]}.stretch", f"{tan01_to_neck01_blendTwo}.attributesBlender")

        tan01_world_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_neckTan01WM_AIM", ss=True)
        cmds.connectAttr(f"{tan01_wm_no_rot}.outputMatrix", f"{tan01_world_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[2]}.worldMatrix[0]", f"{tan01_world_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{self.masterWalk_ctl}.worldMatrix[0]", f"{tan01_world_matrix}.secondaryTargetMatrix")

        cmds.setAttr(f"{tan01_world_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{tan01_world_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{tan01_world_matrix}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{tan01_world_matrix}.secondaryMode", 2)
        neck02_translate_offset = cmds.createNode("fourByFourMatrix", name=f"{self.side}_neck02TranslateOffset_FBM", ss=True)
        cmds.connectAttr(f"{tan01_to_neck01_blendTwo}.output", f"{neck02_translate_offset}.in32")

        neck02_end_pos = cmds.createNode("multMatrix", name=f"{self.side}_neck02EndPos_MMT", ss=True)
        cmds.connectAttr(f"{neck02_translate_offset}.output", f"{neck02_end_pos}.matrixIn[0]")
        cmds.connectAttr(f"{tan01_world_matrix}.outputMatrix", f"{neck02_end_pos}.matrixIn[1]")

        neck_wm = cmds.createNode("blendMatrix", name=f"{self.side}_head_BMX", ss=True)
        cmds.connectAttr(f"{neck02_end_pos}.matrixSum", f"{neck_wm}.inputMatrix")
        cmds.connectAttr(f"{self.main_controllers[2]}.worldMatrix[0]", f"{neck_wm}.target[0].targetMatrix")
        cmds.setAttr(f"{neck_wm}.target[0].translateWeight", 0)

        neck01_to_head_tan_1 = cmds.createNode("blendMatrix", name=f"{self.side}_neck01ToHeadTan01StartPos_BMX", ss=True)
        cmds.connectAttr(f"{self.guide_matrix[-1]}.outputMatrix", f"{neck01_to_head_tan_1}.inputMatrix")
        cmds.connectAttr(f"{self.guide_matrix[0]}.outputMatrix", f"{neck01_to_head_tan_1}.target[0].targetMatrix")
        cmds.setAttr(f"{neck01_to_head_tan_1}.target[0].translateWeight", 0.2)
        neck01_tan = cmds.createNode("multMatrix", name=f"{self.side}_neck01Tan_MMT", ss=True)
        inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_neck01Guide_INV", ss=True)
        cmds.connectAttr(f"{self.guide_matrix[-1]}.outputMatrix", f"{inverse}.inputMatrix")
        cmds.connectAttr(f"{neck01_to_head_tan_1}.outputMatrix", f"{neck01_tan}.matrixIn[0]")
        cmds.connectAttr(f"{inverse}.outputMatrix", f"{neck01_tan}.matrixIn[1]")
        cmds.connectAttr(f"{neck_wm}.outputMatrix", f"{neck01_tan}.matrixIn[2]")

        neck02_to_neck01_tan_2 = cmds.createNode("blendMatrix", name=f"{self.side}_neck02ToNeck01Tan02StartPos_BMX", ss=True)
        cmds.connectAttr(f"{self.guide_matrix[-1]}.outputMatrix", f"{neck02_to_neck01_tan_2}.inputMatrix")
        cmds.connectAttr(f"{self.guide_matrix[0]}.outputMatrix", f"{neck02_to_neck01_tan_2}.target[0].targetMatrix")
        cmds.setAttr(f"{neck02_to_neck01_tan_2}.target[0].translateWeight", 0.8)
        neck02_tan = cmds.createNode("multMatrix", name=f"{self.side}_neck02Tan_MMT", ss=True)
        inverse_matrix_02 = cmds.createNode("inverseMatrix", name=f"{self.side}_neck02Guide_INV", ss=True)
        cmds.connectAttr(f"{self.guide_matrix[0]}.outputMatrix", f"{inverse_matrix_02}.inputMatrix")
        cmds.connectAttr(f"{neck02_to_neck01_tan_2}.outputMatrix", f"{neck02_tan}.matrixIn[0]")
        cmds.connectAttr(f"{inverse_matrix_02}.outputMatrix", f"{neck02_tan}.matrixIn[1]")
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{neck02_tan}.matrixIn[2]")

        ctls = []
        for node, name in zip([neck02_tan, neck01_tan], ["neckTangent", "headTangent"]):

            ctl, controller_grp = controller_creator(
                    name=f"{self.side}_{name}",
                    suffixes=["GRP", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )
        
            cmds.setAttr(f"{controller_grp[0]}.inheritsTransform", 0)

            cmds.connectAttr(f"{node}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")
            cmds.connectAttr(f"{self.main_controllers[1]}.tangentVisibility", f"{controller_grp[0]}.visibility")
            ctls.append(ctl)


        cvs = [f"{neck01_world_matrix}.outputMatrix", f"{ctls[0]}.worldMatrix[0]", f"{tan01_world_matrix}.outputMatrix",f"{ctls[1]}.worldMatrix[0]", f"{neck_wm}.outputMatrix"]

        self.num_joints = 10

        t_values = []
        for i in range(self.num_joints):
            t = i / (float(self.num_joints) - 1)
            t_values.append(t)

        t_values.pop(-1)
        

        self.old_joints = de_boor_core_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs=cvs, num_joints=self.num_joints-1, name=f"{self.side}_neck", parent=self.skinning_trn, custom_parm=t_values)

        self.input_connections = []
        head_temp_joint = cmds.createNode("joint", n=f"{self.side}_head_JNT", parent=self.skinning_trn, ss=True)
        cmds.connectAttr(f"{neck_wm}.outputMatrix", f"{head_temp_joint}.offsetParentMatrix")
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

        # movable_ctl = controller_creator(f"{self.side}_movablePivotHead", 
        #                                                   suffixes=[], 
        #                                                   lock=["scaleX", "scaleY", "scaleZ", "visibility"], 
        #                                                   ro=True, 
        #                                                   parent=self.main_controllers[-1])
        
        # for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
        #     cmds.setAttr(f"{movable_ctl}.{attr}", 0)
        

        # cmds.connectAttr(f"{movable_ctl}.translate", f"{self.main_controllers[-1]}.rotatePivot") 
        # cmds.connectAttr(f"{movable_ctl}.translate", f"{self.main_controllers[-1]}.scalePivot") 

        # dummy_body = cmds.createNode("transform", n=f"{self.side}_dummyBody_TRN", p=self.body_ctl) 




        # ctl, controller_grp = controller_creator(
        #         name=f"{self.side}_localHead",
        #         suffixes=["GRP", "ANM"],
        #         lock=["scaleX", "scaleY", "scaleZ", "visibility"],
        #         ro=True,
        #         parent=self.controllers_trn
        #     )
        # cmds.connectAttr(f"{self.guide_matrix[-1]}.outputMatrix", f"{controller_grp[0]}.offsetParentMatrix")
        # fk_switch(target = ctl, sources= [ctls_sub_neck[-1], self.main_controllers[-1]], sources_names=["Neck", "Main Head"])
        # joint_skin = cmds.createNode("joint", n=f"{self.side}_localHead_JNT", parent=self.skinning_trn, ss=True)
        # cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint_skin}.offsetParentMatrix")
        
        if core.DataManager.get_adonis_data():

            for name in ["centerUp", "centerDown", "left", "right"]:
                self.distance = guide_import(f"{self.side}_{name}HeadDistance_GUIDE", all_descendents=False)[0]

                pos_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{name}HeadFrontDistance_MMX", ss=True)
                cmds.connectAttr(f"{self.distance}.worldMatrix[0]", f"{pos_multMatrix}.matrixIn[0]")

                inverse = cmds.createNode("inverseMatrix", name=f"{self.side}_{name}HeadDistanceInverse_MTX", ss=True)
                cmds.connectAttr(f"{self.blend_head}.outputMatrix", f"{inverse}.inputMatrix")
                cmds.connectAttr(f"{inverse}.outputMatrix", f"{pos_multMatrix}.matrixIn[1]")
                cmds.connectAttr(f"{skinning_joints[-1]}.worldMatrix[0]", f"{pos_multMatrix}.matrixIn[2]")
                distance_joints = cmds.createNode("joint", name=f"{self.side}_{name}HeadDistance_JNT", ss=True, parent = self.muscle_locators)
                cmds.connectAttr(f"{pos_multMatrix}.matrixSum", f"{distance_joints}.offsetParentMatrix")
            
