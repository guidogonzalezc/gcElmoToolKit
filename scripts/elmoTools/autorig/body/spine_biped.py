#Python libraries import
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math

# Local imports
from elmoTools.utils.curve_tool import controller_creator
from elmoTools.utils.guide_creation import guide_import
from elmoTools.utils import data_export
from elmoTools.utils import basic_structure
from elmoTools.utils import core

reload(data_export)

class SpineModule():
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

    def make(self, guide_name):
        """
        Creates the spine module, including the spine chain, controllers, and various systems.

        Args:
            self: Instance of the SpineModule class.
        """

        self.guide_name = guide_name

        self.module_trn = cmds.createNode("transform", name=f"C_spineModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"C_spineControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"C_spineSkinning_GRP", ss=True, p=self.skel_grp)

        pick_matrix = cmds.createNode("pickMatrix", name="C_spinePickMatrix_PMX", ss=True)
        cmds.connectAttr(f"{self.masterWalk_ctl}.worldMatrix[0]", f"{pick_matrix}.inputMatrix")
        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{self.module_trn}.offsetParentMatrix")

        self.create_chain()

        self.data_exporter.append_data(f"C_spineModule", 
                                    {"skinning_transform": self.skinning_trn,
                                    "body_ctl": self.body_ctl,
                                    "localHip": self.localHip_ctl,
                                    "localChest": self.localChest_ctl,
                                    "main_ctl" : self.localHip,
                                    "end_main_ctl" : self.localChest_ctl
                                    }
                                  )
        
    def create_chain(self):
        """
        Creates the spine joint chain by importing guides and parenting the first joint to the module transform.

        Args:
            self: Instance of the SpineModule class.
        """
        
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)


        aim_matrix = cmds.createNode("aimMatrix", name="C_spine01Guide_AMX", ss=True)
        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
        cmds.connectAttr(f"{self.guides[1]}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix")
        cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 0, 1, 0, type="double3")

        blend_matrix = cmds.createNode("blendMatrix", name="C_spine03Guide_BMX", ss=True)
        cmds.connectAttr(f"{self.guides[1]}.worldMatrix[0]", f"{blend_matrix}.inputMatrix")
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)

        blend_matrix02 = cmds.createNode("blendMatrix", name="C_spine02Guide_BMX", ss=True)
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix02}.inputMatrix")
        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{blend_matrix02}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrix02}.target[0].weight", 0.5)
        cmds.setAttr(f"{blend_matrix02}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix02}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrix02}.target[0].shearWeight", 0)

        blend_matrixTan_01 = cmds.createNode("blendMatrix", name="C_spine01GuideTan_BMX", ss=True)
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrixTan_01}.inputMatrix")
        cmds.connectAttr(f"{blend_matrix02}.outputMatrix", f"{blend_matrixTan_01}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrixTan_01}.target[0].weight", 0.33333)
        cmds.setAttr(f"{blend_matrixTan_01}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrixTan_01}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrixTan_01}.target[0].shearWeight", 0)

        blend_matrixTan_02 = cmds.createNode("blendMatrix", name="C_spine02GuideTan_BMX", ss=True)
        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{blend_matrixTan_02}.inputMatrix")
        cmds.connectAttr(f"{blend_matrix02}.outputMatrix", f"{blend_matrixTan_02}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrixTan_02}.target[0].weight", 0.33333)
        cmds.setAttr(f"{blend_matrixTan_02}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrixTan_02}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrixTan_02}.target[0].shearWeight", 0)

        self.main_controllers = []
        self.main_controllers_grp = []

        self.guide_matrix = [aim_matrix, blend_matrix02, blend_matrix]

        for i, matrix in enumerate(self.guide_matrix ):
            ctl, ctl_grp = controller_creator(
                name=f"C_spine0{i+1}",
                suffixes=["GRP", "OFF","ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.main_controllers[-1] if self.main_controllers else self.controllers_trn)

            if not i == 0:
                offset_multMatrix = cmds.createNode("multMatrix", name=f"C_spineOffset0{i+1}_MMX", ss=True)
                inverse_matrix = cmds.createNode("inverseMatrix", name=f"C_spineOffset0{i+1}_IMX", ss=True)
                cmds.connectAttr(f"{matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[0]")

                cmds.connectAttr(f"{self.guide_matrix[i-1]}.outputMatrix", f"{inverse_matrix}.inputMatrix")

                cmds.connectAttr(f"{inverse_matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[1]")
        

                cmds.connectAttr(f"{offset_multMatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")

                for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                    cmds.setAttr(f"{ctl_grp[0]}.{attr}", 0)

            else:
                cmds.connectAttr(f"{matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix")



            self.main_controllers.append(ctl)
            self.main_controllers_grp.append(ctl_grp)

        self.guide_matrix_tan = [blend_matrixTan_01, blend_matrixTan_02]

        self.tan_controllers = []
        self.tan_controllers_grp = []

        for i, matrix in enumerate(self.guide_matrix_tan):
            ctl, ctl_grp = controller_creator(
                name=f"C_spine0{(i+1)*2-1}Tan",
                suffixes=["GRP", "OFF","ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.main_controllers[i*2])

            offset_multMatrix = cmds.createNode("multMatrix", name=f"C_spineOffset0{(i+1)*2-1}Tan_MMX", ss=True)
            inverse_matrix = cmds.createNode("inverseMatrix", name=f"C_spineOffset0{(i+1)*2-1}Tan_IMX", ss=True)
            cmds.connectAttr(f"{matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[0]")

            cmds.connectAttr(f"{self.guide_matrix[i*2]}.outputMatrix", f"{inverse_matrix}.inputMatrix")

            cmds.connectAttr(f"{inverse_matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[1]")


            cmds.connectAttr(f"{offset_multMatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")

            for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                cmds.setAttr(f"{ctl_grp[0]}.{attr}", 0)

            self.tan_controllers.append(ctl)
            self.tan_controllers_grp.append(ctl_grp[0])

        num_joints = 5

        self.distance_between = cmds.createNode("distanceBetween", name="C_spineDistance_BTW", ss=True)

        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{self.distance_between}.inMatrix1")
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{self.distance_between}.inMatrix2")

        self.twist_division = cmds.createNode("floatMath", name="C_spineTwistDivision_FLM", ss=True)
        cmds.setAttr(f"{self.twist_division}.operation", 3) 
        cmds.connectAttr(f"{self.distance_between}.distance", f"{self.twist_division}.floatA")
        cmds.setAttr(f"{self.twist_division}.floatB", num_joints - 1)

        self.main_chain = []
        for i in range(num_joints):
            cmds.select(clear=True)
            joint = cmds.joint(name=f"C_spine0{i+1}_JNT")
            cmds.parent(joint, self.main_chain[-1] if self.main_chain else self.module_trn)
            cmds.setAttr(f"{joint}.ty", cmds.getAttr(f"{self.twist_division}.outFloat"))

            self.main_chain.append(joint)
# 
        self.ik_handle, self.effector, self.curve = cmds.ikHandle(
            name="C_spineIk_HDL",
            startJoint=self.main_chain[0],
            endEffector=self.main_chain[-1],
            solver="ikSplineSolver",
            numSpans=2,
            createCurve=True,
            parentCurve=False
        )

        self.curve =cmds.rename(self.curve, "C_spineIkCurve_CRV")
        cmds.setAttr(f"{self.curve}.inheritsTransform", 0)

        for i, ctl in enumerate([self.main_controllers[0], self.tan_controllers[0], self.main_controllers[1], self.tan_controllers[1], self.main_controllers[2]]):
            dcp = cmds.createNode("decomposeMatrix", name=ctl.replace("_CTL", "_DCP"), ss=True)
            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{dcp}.inputMatrix")
            cmds.connectAttr(f"{dcp}.outputTranslate", f"{self.curve}.controlPoints[{i}]")

        cmds.select(clear=True)
        self.chest_fix = cmds.joint(name = "C_localChest_JNT")
        cmds.setAttr(f"{self.chest_fix}.inheritsTransform", 0)
        cmds.select(clear=True)
        self.localHip = cmds.joint(name="C_localHip_JNT")
        cmds.setAttr(f"{self.localHip}.inheritsTransform", 0)

        cmds.parent(self.chest_fix, self.ik_handle,self.localHip, self.curve, self.module_trn)
        self.localChest_ctl, localChest_grp = controller_creator(
            name="C_localChest",
            suffixes=["GRP", "ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            parent=self.controllers_trn
        )

        blend_matrix_localChest = cmds.createNode("blendMatrix", name="C_localChest_BMX", ss=True)
        cmds.connectAttr(f"{self.main_controllers[-1]}.worldMatrix[0]", f"{blend_matrix_localChest}.inputMatrix")
        cmds.connectAttr(f"{self.main_chain[-1]}.worldMatrix[0]", f"{blend_matrix_localChest}.target[0].targetMatrix")
        cmds.setAttr(f"{blend_matrix_localChest}.target[0].shearWeight", 0)
        cmds.setAttr(f"{blend_matrix_localChest}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrix_localChest}.target[0].scaleWeight", 0)
        cmds.connectAttr(f"{blend_matrix_localChest}.outputMatrix", f"{localChest_grp[0]}.offsetParentMatrix")
        cmds.connectAttr(f"{self.localChest_ctl}.worldMatrix[0]", f"{self.chest_fix}.offsetParentMatrix")

        self.local_hip_guide = guide_import(f"C_localHip_GUIDE", all_descendents=True, path=None)

        self.localHip_ctl, localHip_grp = controller_creator(
            name="C_localHip",
            suffixes=["GRP", "ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            parent=self.controllers_trn
        )
        cmds.connectAttr(f"{self.localHip_ctl}.worldMatrix[0]", f"{self.localHip}.offsetParentMatrix")
        


        # FALTA CONECTAR PARENT MATRIX CON LA GUIA Y EL BODY CTL
        
        self.body_ctl, body_grp = controller_creator(
            name="C_body",
            suffixes=["GRP", "ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            parent=self.controllers_trn
        )

        for ctl in [localHip_grp[0], localChest_grp[0]]:
            cmds.setAttr(f"{ctl}.inheritsTransform", 0)

        cmds.connectAttr(f"{self.guide_matrix[0]}.outputMatrix", f"{body_grp[0]}.offsetParentMatrix")

        cmds.parent(self.main_controllers_grp[0][0], self.body_ctl)

        movable_ctl = controller_creator(f"C_movablePivot", 
                                                          suffixes=[], 
                                                          lock=["scaleX", "scaleY", "scaleZ"], 
                                                          ro=True, 
                                                          parent=self.body_ctl)
        
        for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
            cmds.setAttr(f"{movable_ctl}.{attr}", 0)

        cmds.addAttr(self.body_ctl, shortName="pivot", niceName="Body Pivot ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".pivot", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="movablePivotVis", niceName="Movable Pivot Visibility", attributeType="bool", keyable=True)
        cmds.setAttr(f"{self.body_ctl}.movablePivotVis", channelBox=True, keyable=False)
        

        cmds.connectAttr(f"{movable_ctl}.translate", f"{self.body_ctl}.rotatePivot") 
        cmds.connectAttr(f"{movable_ctl}.translate", f"{self.body_ctl}.scalePivot") 
        cmds.connectAttr(f"{self.body_ctl}.movablePivotVis", f"{movable_ctl}.visibility", f=True)
        cmds.setAttr(f"{movable_ctl}.visibility", lock=True, k=False)


        dummy_body = cmds.createNode("transform", n="C_dummyBody_TRN", p=self.body_ctl) 

        parent_matrix = cmds.createNode("parentMatrix", name="C_hipPosition_PMX", ss=True)
        cmds.connectAttr(f"{self.local_hip_guide[0]}.worldMatrix[0]", f"{parent_matrix}.inputMatrix")
        cmds.connectAttr(f"{dummy_body}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix")

        child_dag = om.MSelectionList().add(self.local_hip_guide[0]).getDagPath(0)
        parent_dag = om.MSelectionList().add(dummy_body).getDagPath(0)

        child_world_matrix = child_dag.inclusiveMatrix()
        parent_world_matrix = parent_dag.inclusiveMatrix()
        
        offset_matrix = child_world_matrix * parent_world_matrix.inverse()

        cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", offset_matrix, type="matrix")
        cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{localHip_grp[0]}.offsetParentMatrix")

        cmds.setAttr(f"{self.ik_handle}.dTwistControlEnable", 1) 
        cmds.setAttr(f"{self.ik_handle}.dWorldUpType", 4)
        cmds.setAttr(f"{self.ik_handle}.dForwardAxis", 2)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpAxis", 6)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpVectorX", 1)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpVectorY", 0)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpVectorZ", 0)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpVectorEndX", 1)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpVectorEndY", 0)
        cmds.setAttr(f"{self.ik_handle}.dWorldUpVectorEndZ", 0)
        cmds.connectAttr(f"{self.main_controllers[0]}.worldMatrix[0]", f"{self.ik_handle}.dWorldUpMatrix")
        cmds.connectAttr(f"{self.main_controllers[2]}.worldMatrix[0]", f"{self.ik_handle}.dWorldUpMatrixEnd")

        self.stretch_system()

    def stretch_system(self):
        """
        Creates the stretch system for the spine module, including attributes and nodes for stretch and squash functionality.
        
        Args:
            self: Instance of the SpineModule class.
        """
           
        cmds.addAttr(self.body_ctl, shortName="STRETCH", niceName="Stretch ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".STRETCH", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="stretch", niceName="Stretch", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="stretchMin", niceName="Stretch Min", maxValue=1, minValue=0.001,defaultValue=0.8, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="stretchMax", niceName="Stretch Max", minValue=1,defaultValue=1.2, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="offset", niceName="Offset", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        cmds.addAttr(self.body_ctl, shortName="SQUASH", niceName="Squash ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".SQUASH", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="volumePreservation", niceName="Volume Preservation", maxValue=1, minValue=0,defaultValue=1, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="falloff", niceName="Falloff", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.body_ctl, shortName="maxPos", niceName="Max Pos", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)

        cmds.addAttr(self.body_ctl, shortName="attachedFk", niceName="Fk ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.body_ctl+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(self.body_ctl, shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=True)
        cmds.setAttr(f"{self.body_ctl}.attachedFKVis", channelBox=True, keyable=False) # make unkeyable



        nodes_to_create = {
            "C_spine_CIN": ("curveInfo", None), #0
            "C_spineStretchFactor_FLM": ("floatMath", 3), #1
            "C_spineStretchFactor_CLM": ("clamp", None), #2
            "C_spineInitialArcLegth_FLM": ("floatMath", 2), #3
            "C_spineBaseStretch_FLC": ("floatConstant", None), #4
            "C_spineStretch_BTA": ("blendTwoAttr", None), # 5
            "C_spineStretchValue_FLM": ("floatMath", 2),# 6
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(created_nodes[0] + ".arcLength", created_nodes[1]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".inputR")
        cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[1]+".floatB")
        cmds.connectAttr(created_nodes[2] + ".outputR", created_nodes[5]+".input[1]")
        cmds.connectAttr(created_nodes[4] + ".outFloat", created_nodes[5]+".input[0]")
        cmds.connectAttr(created_nodes[5] + ".output", created_nodes[6]+".floatA")
        cmds.setAttr(created_nodes[4]+".inFloat", 1)
        cmds.connectAttr(f"{self.body_ctl}.stretch", created_nodes[5]+".attributesBlender")
        cmds.connectAttr(f"{self.body_ctl}.stretchMax", created_nodes[2]+".maxR")
        cmds.connectAttr(f"{self.body_ctl}.stretchMin", created_nodes[2]+".minR")
        cmds.connectAttr(f"{self.curve}.worldSpace[0]", created_nodes[0]+".inputCurve")
        cmds.connectAttr(f"{self.distance_between}.distance", f"{created_nodes[3]}.floatB")
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", created_nodes[3]+".floatA")
        cmds.connectAttr(f"{self.twist_division}.outFloat", f"{created_nodes[6]}.floatB")
        for joint in self.main_chain[1:]:
            cmds.connectAttr(created_nodes[6]+".outFloat", f"{joint}.translateY")

        self.stretch_float_math = created_nodes[6]

        self.reverse_system()

    def reverse_system(self):
        """
        Creates the reverse system for the spine module, including a reversed curve and an IK spline handle for the reversed chain.

        Args:
            self: Instance of the SpineModule class.
        """

        reversed_curve = cmds.reverseCurve(self.curve, name="C_spineReversed_CRV",  ch=True, rpo=False)
        cmds.setAttr(f"{reversed_curve[0]}.inheritsTransform", 0)
        cmds.parent(reversed_curve[0], self.module_trn ) 
        reversed_joints = cmds.duplicate(self.main_chain[0], renameChildren=True)

        self.reverse_chain = []
        for i, joint in enumerate(reversed(reversed_joints)):
            if "effector" in joint:
                reversed_joints.remove(joint)
                cmds.delete(joint)
                
            else:
                renamed_joint = cmds.rename(joint, f"C_spineReversed0{i}_JNT")
                if i != 5:
                    cmds.parent(renamed_joint, world=True)
                self.reverse_chain.append(renamed_joint) 
        for i, joint in enumerate(self.reverse_chain):
            if i != 0:
                cmds.parent(joint, self.reverse_chain[i-1])


        cmds.parent(self.reverse_chain[0], self.module_trn)
        hdl = cmds.ikHandle(sj=self.reverse_chain[0], ee=self.reverse_chain[-1], sol="ikSplineSolver", n="C_spineReversed_HDL", parentCurve=False, curve=reversed_curve[0], createCurve=False) # Create an IK spline handle
        cmds.parent(hdl[0], self.module_trn) 


        negate_flm = cmds.createNode("floatMath", n="C_spineNegateStretchValue_FLM")
        cmds.setAttr("C_spineNegateStretchValue_FLM.operation", 2)
        cmds.setAttr("C_spineNegateStretchValue_FLM.floatB", -1)
        cmds.connectAttr(self.stretch_float_math+".outFloat", f"{negate_flm}.floatA")

        for joint in self.reverse_chain[1:]:
            cmds.connectAttr(negate_flm+".outFloat", f"{joint}.translateY")

        self.offset_system()

    def offset_system(self):
        """
        Creates the offset system for the spine module, including nodes for decomposing matrices, nearest point on curve, float constants, and blend two attributes.

        Args:
            self: Instance of the SpineModule class.
        """
        nodes_to_create = {
            "C_spineReversed05_DCM": ("decomposeMatrix", None),
            "C_spineOffset_NPC": ("nearestPointOnCurve", None),
            "C_spineOffsetInitialValue_FLC": ("floatConstant", None),
            "C_spineOffset_BTA": ("blendTwoAttr", None),
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(created_nodes[0] + ".outputTranslate", created_nodes[1]+".inPosition")
        cmds.connectAttr(created_nodes[1] + ".parameter", created_nodes[3]+".input[1]")
        cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[3]+".input[0]")
        cmds.connectAttr(f"{self.body_ctl}.offset", created_nodes[3]+".attributesBlender")
        cmds.connectAttr(f"{self.reverse_chain[-1]}.worldMatrix[0]", created_nodes[0]+".inputMatrix")
        cmds.connectAttr(f"{self.curve}.worldSpace[0]", created_nodes[1]+".inputCurve")
        cmds.connectAttr(f"{created_nodes[3]}.output", self.ik_handle +".offset")
        cmds.setAttr(created_nodes[2]+".inFloat", 0)

        self.squash_system()

    def squash_system(self):
        """
        Creates the squash system for the spine module, including a transform node for spine settings, attributes for stretch and squash, and a curve for squash deformation.

        Args:
            self: Instance of the SpineModule class.
        """

        translations = []

        self.spine_settings_trn = cmds.createNode("transform", n="C_spineSettings_TRN", parent=self.module_trn)
        for attribute in ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ","scaleX","scaleY","scaleZ","visibility"]:
            cmds.setAttr(f"{self.spine_settings_trn}.{attribute}", lock=True, keyable=False, channelBox=False)

        cmds.addAttr(self.spine_settings_trn, shortName="maxStretchLength", niceName="Max Stretch Length", minValue=1,defaultValue=2, keyable=True)
        cmds.addAttr(self.spine_settings_trn, shortName="minStretchLength", niceName="Min Stretch Length", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)
        cmds.addAttr(self.spine_settings_trn, shortName="maxStretchEffect", niceName="Max Stretch Effect", minValue=1,defaultValue=2, keyable=True)
        cmds.addAttr(self.spine_settings_trn, shortName="minStretchEffect", niceName="Min Stretch Effect", maxValue=1, minValue=0.001,defaultValue=0.5, keyable=True)
        
        cmds.addAttr(self.spine_settings_trn, shortName="VolumeSep", niceName="Volume_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.spine_settings_trn+".VolumeSep", channelBox=True, lock=True)
        
        for i in range(len(self.main_chain)):
            if i == 0:
                default_value = 0.05
            if i == len(self.main_chain)-1:
                default_value = 0.95
            else:
                default_value = (1/(len(self.main_chain)-1))*i
            cmds.addAttr(self.spine_settings_trn, shortName=f"spine0{i+1}SquashPercentage", niceName="Spine01 Squash Percentage", maxValue=1, minValue=0,defaultValue=default_value, keyable=True)

        for joint in self.main_chain:
            translation = cmds.xform(f"{joint}", query=True, worldSpace=True, translation=True)
            translations.append(translation)
        squash_curve = cmds.curve(p=translations, d=1, n="C_spineSquash_CRV")
        cmds.setAttr(squash_curve+".inheritsTransform", 0)
        cmds.parent(squash_curve, self.module_trn)
        

        for i, joint in enumerate(self.main_chain):
            dcm = cmds.createNode("decomposeMatrix", n=f"C_{joint}Squash_DCM")
            cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{dcm}.inputMatrix")
            cmds.connectAttr(f"{dcm}.outputTranslate", f"{squash_curve}.controlPoints[{i}]")

        nodes_to_create = {
            "C_spineSquash_CIN": ("curveInfo", None),
            "C_spineSquashBaseLength_FLM": ("floatMath", 2),
            "C_spineSquashFactor_FLM": ("floatMath", 3),
        }

        created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            created_nodes.append(node)
            if operation is not None:   
                cmds.setAttr(f'{node}.operation', operation)

        cmds.connectAttr(f"{squash_curve}.worldSpace[0]", created_nodes[0]+".inputCurve")
        cmds.connectAttr(created_nodes[0] + ".arcLength", created_nodes[2]+".floatA")
        cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".floatB") 
        cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", created_nodes[1]+".floatA") 
        cmds.setAttr(created_nodes[1]+".floatB", cmds.getAttr(created_nodes[0]+".arcLength"))

        self.squash_factor_fml = created_nodes[2]

        self.volume_preservation_system()

    def attached_fk(self):
        """
        Creates the attached FK controllers for the spine module, including sub-spine controllers and joints.

        Args:
            self: Instance of the SpineModule class.
        Returns:
            list: A list of sub-spine joint names created for the attached FK system.
        """
        
        main_spine_joint = []
        for joint in self.main_chain:
            if "effector" in joint:
                    self.main_chain.remove(joint)
            else:
                main_spine_joint.append(f"{joint}")
        # AUN FALTA POR APLICAR
        values = []
        x = len(main_spine_joint)
        for i in range(1, 6):
            v = int((i - 1) * (x - 1) / 4)
            values.append(v)

        ctls_sub_spine = []
        sub_spine_ctl_trn = cmds.createNode("transform", n="C_subSpineControllers_GRP", parent=self.masterWalk_ctl)
        cmds.setAttr(f"{sub_spine_ctl_trn}.inheritsTransform", 0)
        cmds.connectAttr(f"{self.body_ctl}.attachedFKVis", f"{sub_spine_ctl_trn}.visibility")
        for i, joint in enumerate(main_spine_joint):
            
            ctl, controller_grp = controller_creator(
                name=f"C_spineSubAttachedFk0{i+1}",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=sub_spine_ctl_trn
            )
                
            if i == 0:
                cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix")
            else:
                mmt = cmds.createNode("multMatrix", n=f"C_spineSubAttachedFk0{i+1}_MMT")
                if i == len(self.main_chain)-1:
                    cmds.connectAttr(f"{self.chest_fix}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
                else:
                    cmds.connectAttr(f"{joint}.worldMatrix[0]", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{main_spine_joint[i-1]}.worldInverseMatrix[0]", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{ctls_sub_spine[i-1]}.worldMatrix[0]", f"{mmt}.matrixIn[2]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")
            ctls_sub_spine.append(ctl)

        self.sub_spine_joints = []
        for i, joint in enumerate(main_spine_joint):
            cmds.select(clear=True)
            new_joint = cmds.joint(joint, name=f"C_subSpineFk0{i+1}_JNT")
            cmds.setAttr(f"{new_joint}.inheritsTransform", 0)

            cmds.parent(new_joint, self.skinning_trn)

            cmds.connectAttr(f"{ctls_sub_spine[i]}.worldMatrix[0]", f"{new_joint}.offsetParentMatrix")
            for attr in ["translateX","translateY","translateZ"]:
                cmds.setAttr(f"{new_joint}.{attr}", 0)
            self.sub_spine_joints.append(new_joint)

        cmds.select(clear=True)
        self.local_hip_joint = cmds.joint(n="C_localHipSkinning_JNT")
        cmds.parent(self.local_hip_joint, self.skinning_trn)
        cmds.connectAttr(f"{self.localHip}.worldMatrix[0]", f"{self.local_hip_joint}.offsetParentMatrix")

        return self.sub_spine_joints

    def volume_preservation_system(self):
        """
        Creates the volume preservation system for the spine module, including remap value nodes, float math nodes, and connections to squash joints.

        Args:
            self: Instance of the SpineModule class.
        """
                
        squash_joints = self.attached_fk()
       
        nodes_to_create = {
            "C_spineVolumeLowBound_RMV": ("remapValue", None),# 0
            "C_spineVolumeHighBound_RMV": ("remapValue", None),# 1
            "C_spineVolumeLowBoundNegative_FLM": ("floatMath", 1),# 2
            "C_spineVolumeHighBoundNegative_FLM": ("floatMath", 1),# 3
            "C_spineVolumeSquashDelta_FLM": ("floatMath", 1), # 4
            "C_spineVolumeStretchDelta_FLM": ("floatMath", 1), # 5
        } 

        main_created_nodes = []
        for node_name, (node_type, operation) in nodes_to_create.items():
            node = cmds.createNode(node_type, name=node_name)
            main_created_nodes.append(node)
            if operation is not None:
                cmds.setAttr(f'{node}.operation', operation)
        values = [0.001, 0.999]
        for i in range(0,2):
            cmds.connectAttr(f"{self.body_ctl}.falloff", f"{main_created_nodes[i]}.inputValue")
            cmds.connectAttr(f"{self.body_ctl}.maxPos", f"{main_created_nodes[i]}.outputMin")
            cmds.setAttr(f"{main_created_nodes[i]}.outputMax", values[i])
            cmds.connectAttr(f"{main_created_nodes[i]}.outValue", f"{main_created_nodes[i+2]}.floatB")

        cmds.setAttr(f"{main_created_nodes[2]}.floatA", 0)
        cmds.setAttr(f"{main_created_nodes[3]}.floatA", 2)
        cmds.setAttr(f"{main_created_nodes[4]}.floatB", 1)
        cmds.setAttr(f"{main_created_nodes[5]}.floatA", 1)
        cmds.connectAttr(f"{self.spine_settings_trn}.maxStretchEffect", f"{main_created_nodes[4]}.floatA")
        cmds.connectAttr(f"{self.spine_settings_trn}.minStretchEffect", f"{main_created_nodes[5]}.floatB")

        for i, joint in enumerate(squash_joints):
            nodes_to_create = {
                f"C_spineVolumeSquashFactor0{i+1}_FLM": ("floatMath", 2), # 0
                f"C_spineVolumeStretchFactor0{i+1}_FLM": ("floatMath", 2), # 1
                f"C_spineVolumeStretchFullValue0{i+1}_FLM": ("floatMath", 1), # 2
                f"C_spineVolumeSquashFullValue0{i+1}_FLM": ("floatMath", 0), # 3
                f"C_spineVolume0{i+1}_RMV": ("remapValue", None), # 4
                f"C_spineVolumeFactor0{i+1}_RMV": ("remapValue", None), # 5
            }

            created_nodes = []
            for node_name, (node_type, operation) in nodes_to_create.items():
                node = cmds.createNode(node_type, name=node_name)
                created_nodes.append(node)
                if operation is not None:
                    cmds.setAttr(f'{node}.operation', operation)

            cmds.connectAttr(f"{self.spine_settings_trn}.spine0{i+1}SquashPercentage", f"{created_nodes[5]}.inputValue")
            cmds.connectAttr(f"{main_created_nodes[2]}.outFloat", f"{created_nodes[5]}.value[0].value_Position")
            cmds.connectAttr(f"{main_created_nodes[0]}.outValue", f"{created_nodes[5]}.value[1].value_Position")
            cmds.connectAttr(f"{main_created_nodes[1]}.outValue", f"{created_nodes[5]}.value[2].value_Position")
            cmds.connectAttr(f"{main_created_nodes[3]}.outFloat", f"{created_nodes[5]}.value[3].value_Position")


            cmds.connectAttr(created_nodes[0] + ".outFloat", created_nodes[3]+".floatA")
            cmds.connectAttr(created_nodes[1] + ".outFloat", created_nodes[2]+".floatB")
            cmds.connectAttr(created_nodes[2] + ".outFloat", created_nodes[4]+".value[2].value_FloatValue")
            cmds.connectAttr(created_nodes[3] + ".outFloat", created_nodes[4]+".value[0].value_FloatValue")
            cmds.connectAttr(self.squash_factor_fml + ".outFloat", created_nodes[4]+".inputValue")
            cmds.setAttr(f"{created_nodes[3]}.floatB", 1)
            cmds.setAttr(f"{created_nodes[2]}.floatA", 1)

            cmds.connectAttr(f"{main_created_nodes[4]}.outFloat", created_nodes[0]+".floatA")
            cmds.connectAttr(f"{main_created_nodes[5]}.outFloat", created_nodes[1]+".floatA")
            cmds.connectAttr(f"{created_nodes[5]}.outValue", created_nodes[0]+".floatB")
            cmds.connectAttr(f"{created_nodes[5]}.outValue", created_nodes[1]+".floatB")

            cmds.connectAttr(f"{self.spine_settings_trn}.maxStretchLength", f"{created_nodes[4]}.value[2].value_Position")
            cmds.connectAttr(f"{self.spine_settings_trn}.minStretchLength", f"{created_nodes[4]}.value[0].value_Position")   

            floatConstant = cmds.createNode("floatConstant", name=f"C_spineVolume0{i+1}_FLC", ss=True)
            blendTwoAttr = cmds.createNode("blendTwoAttr", name=f"C_spineVolume0{i+1}_BTA", ss=True)
            cmds.connectAttr(f"{created_nodes[4]}.outValue", f"{blendTwoAttr}.input[1]")
            cmds.connectAttr(f"{floatConstant}.outFloat", f"{blendTwoAttr}.input[0]")
            cmds.connectAttr(f"{self.body_ctl}.volumePreservation", f"{blendTwoAttr}.attributesBlender")

            cmds.connectAttr(f"{blendTwoAttr}.output",f"{joint}.scaleX")   
            cmds.connectAttr(f"{blendTwoAttr}.output",f"{joint}.scaleZ")   


            values = [-1, 1, 1, -1]
            for i in range(0,4):
                cmds.setAttr(f"{created_nodes[5]}.value[{i}].value_Interp", 2)
                cmds.setAttr(f"{created_nodes[5]}.value[{i}].value_FloatValue", values[i])
