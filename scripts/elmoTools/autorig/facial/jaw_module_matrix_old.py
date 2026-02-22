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
from elmoTools.utils import basic_structure
from elmoTools.utils import guide_creation
import maya.api.OpenMaya as om

from elmoTools.utils.space_switch import fk_switch

reload(data_export)
reload(guide_creation)
reload(core)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}


class JawModule():
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

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_jawModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_jawControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_jawFacialSkinning_GRP", ss=True, p=self.skel_grp)

        self.controllersParentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_jawModule_PM", ss=True)
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{self.controllersParentMatrix}.target[0].targetMatrix", force=True)
        offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
        cmds.setAttr(f"{self.controllersParentMatrix}.target[0].offsetMatrix", offset, type="matrix")
        cmds.connectAttr(f"{self.controllersParentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)


        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.jaw_module()

        self.data_exporter.append_data(f"{self.side}_jawModule", 
                                    {"skinning_transform": self.skinning_trn,
                                    "jaw_ctl": self.jaw_ctl,
                                     
                                    # "neck_ctl": self.main_controllers[0],

                                    }
                                  )

    def local_setup(self, grp, ctl):

        local_mult_matrix = cmds.createNode("multMatrix", name=ctl.replace("_CTL", "_MMX"), ss=True)
        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{local_mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{local_mult_matrix}.matrixIn[1]")
        grp_world_matrix = cmds.getAttr(f"{grp}.worldMatrix[0]")
        cmds.setAttr(f"{local_mult_matrix}.matrixIn[2]", grp_world_matrix, type="matrix")

        return f"{local_mult_matrix}.matrixSum"
    
    def getClosestParamToPosition(self, curve, position):
        """
        Returns the closest parameter (u) on the given NURBS curve to a world-space position.
        
        Args:
            curve (str or MObject or MDagPath): The curve to evaluate.
            position (list or tuple): A 3D world-space position [x, y, z].

        Returns:
            float: The parameter (u) value on the curve closest to the given position.
        """
        if isinstance(curve, str):
            sel = om.MSelectionList()
            sel.add(curve)
            curve_dag_path = sel.getDagPath(0)
        elif isinstance(curve, om.MObject):
            curve_dag_path = om.MDagPath.getAPathTo(curve)
        elif isinstance(curve, om.MDagPath):
            curve_dag_path = curve
        else:
            raise TypeError("Curve must be a string name, MObject, or MDagPath.")

        curve_fn = om.MFnNurbsCurve(curve_dag_path)

        point = om.MPoint(*position)

        closest_point, paramU = curve_fn.closestPoint(point, space=om.MSpace.kWorld)

        return paramU

    def jaw_module(self):
        """
        Creates the neck joint chain by importing guides and parenting the first joint to the module transform.

        Args:
            self: Instance of the neckModule class.
        """
        jaw_guide = self.guides[0]

        self.jaw_ctl, self.jaw_ctl_grp = controller_creator(
                name=f"{self.side}_jaw",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
            )
        
        cmds.connectAttr(f"{jaw_guide}.worldMatrix[0]", f"{self.jaw_ctl_grp[0]}.offsetParentMatrix")

        local_jaw = self.local_setup(self.jaw_ctl_grp[0], self.jaw_ctl)
        self.local_jaw = local_jaw

        cmds.addAttr(self.jaw_ctl, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.jaw_ctl+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.jaw_ctl, shortName="collision", niceName="Collision", maxValue=1, minValue=0,defaultValue=1, keyable=True)
        cmds.addAttr(self.jaw_ctl, shortName="mouthHeight", niceName="Mouth Height", maxValue=1, minValue=0,defaultValue=0.5, keyable=True)
        cmds.addAttr(self.jaw_ctl, shortName="zip", niceName="Zip", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.jaw_ctl, shortName="stickyLips", niceName="Sticky Lips", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.jaw_ctl, shortName="stickyFalloff", niceName="Sticky Falloff", maxValue=1, minValue=0.001, defaultValue=0.2, keyable=True)

        self.upper_jaw_ctl, self.upper_jaw_ctl_grp = controller_creator(
                name=f"{self.side}_upperJaw",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
            )
        
        cmds.connectAttr(f"{jaw_guide}.worldMatrix[0]", f"{self.upper_jaw_ctl_grp[0]}.offsetParentMatrix")
        local_upper_jaw = self.local_setup(self.upper_jaw_ctl_grp[0], self.upper_jaw_ctl)
        self.local_upper_jaw = local_upper_jaw

        jaws_rotation_sum = cmds.createNode("sum", name=f"{self.side}_jawsRotation_SUM", ss=True)
        cmds.connectAttr(f"{self.jaw_ctl}.rotateX", f"{jaws_rotation_sum}.input[0]")
        cmds.connectAttr(f"{self.upper_jaw_ctl}.rotateX", f"{jaws_rotation_sum}.input[1]")

        collision_clamp = cmds.createNode("clamp", name=f"{self.side}_collision_CLAMP", ss=True)
        cmds.connectAttr(f"{jaws_rotation_sum}.output", f"{collision_clamp}.inputR")
        cmds.setAttr(f"{collision_clamp}.minR", -360)
        cmds.connectAttr(f"{self.upper_jaw_ctl}.rotateX", f"{collision_clamp}.maxR")

        collision_bta = cmds.createNode("blendTwoAttr", name=f"{self.side}_collision_BTA", ss=True)
        cmds.connectAttr(f"{collision_clamp}.outputR", f"{collision_bta}.input[1]")
        cmds.connectAttr(f"{self.jaw_ctl}.collision", f"{collision_bta}.attributesBlender")
        cmds.setAttr(f"{collision_bta}.input[0]", 0)

        collision_compose = cmds.createNode("composeMatrix", name=f"{self.side}_collision_CPM", ss=True)
        cmds.connectAttr(f"{collision_bta}.output", f"{collision_compose}.inputRotateX")

        cmds.connectAttr(f"{collision_compose}.outputMatrix", f"{self.upper_jaw_ctl}.offsetParentMatrix")

        self.jaw_local_joint = cmds.createNode("joint", name=f"{self.side}_jaw_JNT", ss=True, parent=self.skinning_trn)
        cmds.connectAttr(local_jaw, f"{self.jaw_local_joint}.offsetParentMatrix")

        self.upper_jaw_local_joint = cmds.createNode("joint", name=f"{self.side}_upperJaw_JNT", ss=True, parent=self.skinning_trn)
        cmds.connectAttr(local_upper_jaw, f"{self.upper_jaw_local_joint}.offsetParentMatrix")

        self.jaw_surface = None
        for guides in self.guides:
            if cmds.listRelatives(guides, shapes=True, type="nurbsSurface"):
                    self.jaw_surface = guides

        if self.jaw_surface:
            self.jaw_skin_cluster = cmds.skinCluster(
                self.jaw_surface,
                self.jaw_local_joint,
                self.upper_jaw_local_joint,
                n=f"{self.jaw_surface}_SKC",
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=2,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]

            u_spans = cmds.getAttr(f"{self.jaw_surface}.spansU")
            v_spans = cmds.getAttr(f"{self.jaw_surface}.spansV")
            degU = cmds.getAttr(f"{self.jaw_surface}.degreeU")
            degV = cmds.getAttr(f"{self.jaw_surface}.degreeV")

            u_count = u_spans + degU
            v_count = v_spans + degV

            for u in range(u_count):
                for v in range(v_count):
                    t = float(v) / (v_count - 1)
                    jaw_w = 1.0 - t
                    upper_w = t
                    
                    cv = f"{self.jaw_surface}.cv[{u}][{v}]"
                    
                    cmds.skinPercent(self.jaw_skin_cluster, cv, transformValue=[
                        (self.jaw_local_joint, jaw_w),
                        (self.upper_jaw_local_joint, upper_w)
                    ])

        if len(self.guides) > 2:

            self.lips_setup()

    def lips_setup(self):

        self.linear_curves = []
        for guides in self.guides:
            if cmds.listRelatives(guides, shapes=True, type="nurbsCurve"):
                cv_pos = cmds.xform(f"{guides}.cv[0]", q=True, ws=True, t=True)
                if cv_pos[0] > 0:
                    cmds.reverseCurve(guides, ch=False, rpo=True)
                self.linear_curves.append(guides)

        self.bezier_curves = []

        self.average_curve_node = cmds.createNode("avgCurves", name=f"{self.side}_lipsAverage_ACV", ss=True)
        cmds.setAttr(f"{self.average_curve_node}.automaticWeight", 0)
        reverse = cmds.createNode("reverse", name=f"{self.side}_lipsAverageReverse_REV", ss=True)
        cmds.connectAttr(f"{reverse}.outputX", f"{self.average_curve_node}.weight1")
        cmds.connectAttr(f"{self.jaw_ctl}.mouthHeight", f"{reverse}.inputX")
        cmds.connectAttr(f"{self.jaw_ctl}.mouthHeight", f"{self.average_curve_node}.weight2")

        offset_calculation = []


        for index, curve in enumerate(self.linear_curves):
            rebuilded_curve = cmds.rebuildCurve(
                    curve,
                    ch=0,
                    rpo=0,
                    rt=0,
                    end=1,
                    kr=0,
                    kcp=0,
                    kep=1,
                    kt=0,
                    s=4,
                    d=3,
                    tol=0.01,
                    name=curve.replace("Curve_GUIDE", "Rebuild_CRV")
                )[0]
            
            cmds.parent(rebuilded_curve, self.module_trn)

            # Create lip corner controllers

            if index == 0:

                self.r_side_jaw_ctl, self.r_side_jaw_ctl_grp = controller_creator(
                    name=f"R_lipCorner",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["rx","ry","rz","scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )

                r_lip_corner_4b4 = cmds.createNode("fourByFourMatrix", name="R_lipCorner_4B4", ss=True)
                pos = cmds.pointPosition(f"{curve}.cv[0]", w=True)
                cmds.setAttr(f"{r_lip_corner_4b4}.in30", pos[0])
                cmds.setAttr(f"{r_lip_corner_4b4}.in31", pos[1])
                cmds.setAttr(f"{r_lip_corner_4b4}.in32", pos[2])
                front_corner_4b4 = cmds.createNode("fourByFourMatrix", name="R_lipCornerFront_4B4", ss=True)
                pos_front = cmds.pointPosition(f"{curve}.cv[5]", w=True)
                cmds.setAttr(f"{front_corner_4b4}.in30", pos_front[0])
                cmds.setAttr(f"{front_corner_4b4}.in31", pos[1])
                cmds.setAttr(f"{front_corner_4b4}.in32", pos_front[2])

                aimMatrix_corner = cmds.createNode("aimMatrix", name="R_lipCorner_AMX", ss=True)
                cmds.connectAttr(f"{r_lip_corner_4b4}.output", f"{aimMatrix_corner}.inputMatrix")
                cmds.connectAttr(f"{front_corner_4b4}.output", f"{aimMatrix_corner}.primaryTargetMatrix")
                cmds.setAttr(f"{aimMatrix_corner}.primaryInputAxis", 1,0,0)

                multmatrix_corner = cmds.createNode("multMatrix", name="R_lipCorner_MMX", ss=True)
                cmds.setAttr(f"{multmatrix_corner}.matrixIn[0]", -1, 0, 0, 0,
                                                    0, 1, 0, 0,
                                                    0, 0, 1, 0,
                                                    0, 0, 0, 1, type="matrix")
                cmds.connectAttr(f"{aimMatrix_corner}.outputMatrix", f"{multmatrix_corner}.matrixIn[1]")


                cmds.connectAttr(f"{multmatrix_corner}.matrixSum", f"{self.r_side_jaw_ctl_grp[0]}.offsetParentMatrix")

                parent_mouth_pos = core.local_space_parent(self.r_side_jaw_ctl, parents=[f"{self.jaw_ctl}", f"{self.upper_jaw_ctl}"], default_weights=0.5)


                self.l_side_jaw_ctl, self.l_side_jaw_ctl_grp = controller_creator(
                    name=f"L_lipCorner",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["rx","ry","rz","scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )

                last_cv = len(cmds.ls(f"{curve}.cv[*]", flatten=True))-1
                l_lip_corner_4b4 = cmds.createNode("fourByFourMatrix", name="L_lipCorner_4B4", ss=True)
                cmds.connectAttr(f"{curve}.editPoints[{last_cv}].xValueEp", f"{l_lip_corner_4b4}.in30")
                cmds.connectAttr(f"{curve}.editPoints[{last_cv}].yValueEp", f"{l_lip_corner_4b4}.in31")
                cmds.connectAttr(f"{curve}.editPoints[{last_cv}].zValueEp", f"{l_lip_corner_4b4}.in32")

                l_lip_corner_4b4 = cmds.createNode("fourByFourMatrix", name="L_lipCorner_4B4", ss=True)
                pos = cmds.pointPosition(f"{curve}.cv[{last_cv}]", w=True)
                cmds.setAttr(f"{l_lip_corner_4b4}.in30", pos[0])
                cmds.setAttr(f"{l_lip_corner_4b4}.in31", pos[1])
                cmds.setAttr(f"{l_lip_corner_4b4}.in32", pos[2])
                front_corner_4b4 = cmds.createNode("fourByFourMatrix", name="L_lipCornerFront_4B4", ss=True)
                pos_front = cmds.pointPosition(f"{curve}.cv[{last_cv-5}]", w=True)
                cmds.setAttr(f"{front_corner_4b4}.in30", pos_front[0])
                cmds.setAttr(f"{front_corner_4b4}.in31", pos[1])
                cmds.setAttr(f"{front_corner_4b4}.in32", pos_front[2])

                aimMatrix_corner = cmds.createNode("aimMatrix", name="L_lipCorner_AMX", ss=True)
                cmds.connectAttr(f"{l_lip_corner_4b4}.output", f"{aimMatrix_corner}.inputMatrix")
                cmds.connectAttr(f"{front_corner_4b4}.output", f"{aimMatrix_corner}.primaryTargetMatrix")
                cmds.setAttr(f"{aimMatrix_corner}.primaryInputAxis", -1,0,0)

                cmds.connectAttr(f"{aimMatrix_corner}.outputMatrix", f"{self.l_side_jaw_ctl_grp[0]}.offsetParentMatrix")

             
                parent_mouth_pos = core.local_space_parent(self.l_side_jaw_ctl, parents=[f"{self.jaw_ctl}", f"{self.upper_jaw_ctl}"], default_weights=0.5)


                self.r_corner_local = self.local_setup(ctl = self.r_side_jaw_ctl, grp = self.r_side_jaw_ctl_grp[0])
                self.l_corner_local = self.local_setup(ctl = self.l_side_jaw_ctl, grp = self.l_side_jaw_ctl_grp[0])

                mouth_sliding_shape = cmds.listRelatives(self.jaw_surface, shapes=True, noIntermediate=True)[0]

                self.corner_projected_joints = []

                for local in [self.r_corner_local, self.l_corner_local]:
                    local_side = local.split("_")[0]
                    row_projection = cmds.createNode("rowFromMatrix", name=f"{local_side}_mouthSlidingProjection_ROW", ss=True)
                    cmds.connectAttr(local, f"{row_projection}.matrix")
                    cmds.setAttr(f"{row_projection}.input", 3)
                    closes_point_on_surface = cmds.createNode("closestPointOnSurface", name=f"{local_side}_mouthSlidingProjection_CPOS", ss=True)
                    cmds.connectAttr(f"{mouth_sliding_shape}.worldSpace[0]", f"{closes_point_on_surface}.inputSurface")
                    cmds.connectAttr(f"{row_projection}.outputX", f"{closes_point_on_surface}.inPositionX")
                    cmds.connectAttr(f"{row_projection}.outputY", f"{closes_point_on_surface}.inPositionY")
                    cmds.connectAttr(f"{row_projection}.outputZ", f"{closes_point_on_surface}.inPositionZ")
                    joint = cmds.createNode("joint", name=f"{local_side}_lipCorner_JNT", ss=True, parent=self.module_trn)
                    cmds.connectAttr(f"{closes_point_on_surface}.position", f"{joint}.translate")

                    decompose_matrix = cmds.createNode("decomposeMatrix", name=f"{local_side}_lipCorner_DM", ss=True)
                    cmds.connectAttr(local, f"{decompose_matrix}.inputMatrix")
                    cmds.connectAttr(f"{decompose_matrix}.outputRotate", f"{joint}.rotate")

                    self.corner_projected_joints.append(joint)


            main_mid_name = "upper" if "upper" in curve else "lower"
            jaw_controller = self.jaw_ctl if "lower" in curve else self.upper_jaw_ctl

            self.main_mid_ctl, self.main_mid_ctl_grp = controller_creator(
                    name=f"C_{main_mid_name}Lip",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )
            last_cv = int((len(cmds.ls(f"{curve}.cv[*]", flatten=True))-1)//2)
            mid_pos_4b4 = cmds.createNode("fourByFourMatrix", name=f"C_{main_mid_name}MidLip_4B4", ss=True)
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].xValueEp", f"{mid_pos_4b4}.in30")
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].yValueEp", f"{mid_pos_4b4}.in31")
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].zValueEp", f"{mid_pos_4b4}.in32")
            cmds.connectAttr(f"{mid_pos_4b4}.output", f"{self.main_mid_ctl_grp[0]}.offsetParentMatrix")

            parent_mouth_pos = core.local_space_parent(self.main_mid_ctl, parents=[f"{jaw_controller}"])


            self.mid_local = self.local_setup(ctl = self.main_mid_ctl, grp = self.main_mid_ctl_grp[0])
            
            mid_local_joint = cmds.createNode("joint", name=f"C_{main_mid_name}Lip_JNT", ss=True, parent=self.module_trn)
            cmds.connectAttr(self.mid_local, f"{mid_local_joint}.offsetParentMatrix")

            joint_list = [self.corner_projected_joints[0], self.corner_projected_joints[1] , mid_local_joint]

            rebuilded_skinned_curve = cmds.skinCluster(
                joint_list,
                rebuilded_curve,
                n=f"{rebuilded_curve}_SKC",
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=2,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]

            cv_names = cmds.ls(f"{rebuilded_curve}.cv[*]", flatten=True)

            cmds.skinPercent(rebuilded_skinned_curve, cv_names[0], transformValue=[(self.corner_projected_joints[0], 1)])
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[-1], transformValue=[(self.corner_projected_joints[1], 1)])

            mid_index = int(len(cv_names) // 2)
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[mid_index], transformValue=[(mid_local_joint, 1)])

            cmds.skinPercent(rebuilded_skinned_curve, cv_names[1], transformValue=[(self.corner_projected_joints[0], 0.5), (mid_local_joint, 0.5)])
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[-2], transformValue=[(self.corner_projected_joints[1], 0.5), (mid_local_joint, 0.5)])

            cmds.skinPercent(rebuilded_skinned_curve, cv_names[2], transformValue=[(self.corner_projected_joints[0], 0.2), (mid_local_joint, 0.8)])
            cmds.skinPercent(rebuilded_skinned_curve, cv_names[-3], transformValue=[(self.corner_projected_joints[1], 0.2), (mid_local_joint, 0.8)])

            bezierCurve = cmds.duplicate(rebuilded_curve, name=rebuilded_curve.replace("Rebuild", "Bezier"), renameChildren=True)[0]
            cmds.select(bezierCurve, r=True)
            cmds.nurbsCurveToBezier()
            cmds.select(clear=True)

            cmds.connectAttr(f"{bezierCurve}.worldSpace[0]", f"{self.average_curve_node}.inputCurve{index+1}", f=True)

            self.bezier_curves.append(bezierCurve)

            rebuilded_curve_shape = cmds.listRelatives(rebuilded_curve, shapes=True)[0]

            path_joints = []
            ctls = []
            clts_grps = []

            controllers_parenting = []
            local_matrices = []
            parent_mouth_positions = []
            local_matrices_offset = []
            number = 1
            for i, cv in enumerate(cmds.ls(f"{bezierCurve}.cv[*]", flatten=True)):
                total_cvs = len(cmds.ls(f"{bezierCurve}.cv[*]", flatten=True))
                mid_index = total_cvs // 2
                if i < mid_index:
                    cv_side = "R"
                elif i == mid_index:
                    cv_side = "C"
                else:
                    cv_side = "L"

                base = (i // 3) + 1
                mod = i % 3
                position = cmds.xform(cv, q=True, ws=True, t=True)
                parameter = self.getClosestParamToPosition(rebuilded_curve, position)

                if mod == 0:


                    name = f"{cv_side}_{main_mid_name}Lips0{number}"
                    lock=["sz", "sy", "visibility"]
                    tan_vis = True

                    parent = self.controllers_trn
                    
                elif mod == 1:
                    name = f"{cv_side}_{main_mid_name}Lips0{number}Tan02"
                    lock=["rz","ry","rx", "sz", "sy","sx", "visibility"]
                    tan_vis=False

                    parent = self.controllers_trn
                    
                    if cv_side == "R":
                        number = number + 1

                    elif cv_side == "C":
                        number = "Center"
                    
                    else:
                        number = number - 1

                        
                else:
                    name = f"{cv_side}_{main_mid_name}Lips0{number}Tan01"
                    lock=["rz","ry","rx", "sz", "sy","sx", "visibility"]
                    tan_vis=False
                    parent = self.controllers_trn

                ctl, ctl_grp = controller_creator(
                    name=name,
                    suffixes=["GRP", "OFF","ANM"],
                    lock=lock,
                    ro=False,
                    parent= parent
                )
                controllers_parenting.append(ctl)
                ctls.append(ctl)
                clts_grps.append(ctl_grp)
                # cmds.setAttr(f"{ctl_grp[0]}.inheritsTransform", 0)

                if tan_vis:
                    cmds.addAttr(ctl, shortName="tangents", niceName="Tangents ———", enumName="———",attributeType="enum", keyable=True)
                    cmds.setAttr(ctl+".tangents", channelBox=True, lock=True)
                    cmds.addAttr(ctl, shortName="tangentVisibility", niceName="Tangent Visibility", attributeType="bool", keyable=False)
                    cmds.setAttr(ctl+".tangentVisibility", channelBox=True)


                motionPath = cmds.createNode("motionPath", n=f"{name}_MPA", ss=True)
                joint = cmds.createNode("joint", n=f"{name}_JNT", ss=True, p=self.module_trn)
                fourByFourMatrix = cmds.createNode("fourByFourMatrix", n=f"{name}_4B4", ss=True)


                cmds.connectAttr(f"{rebuilded_curve_shape}.worldSpace[0]", f"{motionPath}.geometryPath", f=True)
                
                cmds.setAttr(f"{motionPath}.uValue", parameter)
                
                cmds.connectAttr(f"{motionPath}.allCoordinates.xCoordinate", f"{fourByFourMatrix}.in30", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.yCoordinate", f"{fourByFourMatrix}.in31", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.zCoordinate", f"{fourByFourMatrix}.in32", f=True)

                front_motionPath = cmds.createNode("motionPath", n=f"{name}Front_MPA", ss=True)
                cmds.connectAttr(f"{rebuilded_curve_shape}.worldSpace[0]", f"{front_motionPath}.geometryPath", f=True)
                cmds.setAttr(f"{front_motionPath}.uValue", parameter + 0.05 if parameter + 0.05 <= 1 else parameter - 0.05)

                aimMatrix_pos = cmds.createNode("aimMatrix", name=f"{name}_AMX", ss=True)
                cmds.connectAttr(f"{fourByFourMatrix}.output", f"{aimMatrix_pos}.inputMatrix", f=True)
                cmds.connectAttr(f"{front_motionPath}.allCoordinates.xCoordinate", f"{aimMatrix_pos}.primaryTargetVectorX", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.yCoordinate", f"{aimMatrix_pos}.primaryTargetVectorY", f=True)
                cmds.connectAttr(f"{front_motionPath}.allCoordinates.zCoordinate", f"{aimMatrix_pos}.primaryTargetVectorZ", f=True)
                aimVector = (1,0,0) if parameter + 0.05 <= 1 else (-1,0,0)
                cmds.setAttr(f"{aimMatrix_pos}.primaryInputAxis", *aimVector)

                if cv_side == "L" or cv_side == "C":
                    output_matrix = f"{aimMatrix_pos}.outputMatrix"
                else:
                    multmatrix_corner = cmds.createNode("multMatrix", name=f"{name}Mirror_MMX", ss=True)
                    cmds.setAttr(f"{multmatrix_corner}.matrixIn[0]", -1, 0, 0, 0,
                                                        0, 1, 0, 0,
                                                        0, 0, 1, 0,
                                                        0, 0, 0, 1, type="matrix")
                    cmds.connectAttr(f"{aimMatrix_pos}.outputMatrix", f"{multmatrix_corner}.matrixIn[1]")
                    output_matrix = f"{multmatrix_corner}.matrixSum"


                ctl_rotation = cmds.getAttr(f"{output_matrix}")

                reshaped_matrix = [ctl_rotation[i:i+4] for i in range(0, len(ctl_rotation), 4)]
                for row in range(4):
                    for col in range(4):
                        try:
                            cmds.setAttr(f"{fourByFourMatrix}.in{row}{col}", reshaped_matrix[row][col])
                        except:
                            pass
                    


                # cmds.connectAttr(f"{fourByFourMatrix}.output", f"{ctl_grp[0]}.offsetParentMatrix", f=True)

                multmatrix = cmds.createNode("multMatrix", name=f"{name}InitPos_MMX", ss=True)
                cmds.setAttr(f"{multmatrix}.matrixIn[0]", cmds.getAttr(f"{fourByFourMatrix}.output"), type="matrix")
                cmds.connectAttr(f"{multmatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix", f=True)

                parent_mouth_pos = core.local_space_parent(ctl, parents=[f"{fourByFourMatrix}.output"], local_parent=f"{self.controllersParentMatrix}.outputMatrix")
                parent_mouth_positions.append(parent_mouth_pos)


                local_ctl = self.local_setup(ctl=ctl, grp=ctl_grp[0])
                local_ctl_off = self.local_setup(ctl=ctl, grp=ctl_grp[1])
                local_matrices_offset.append(local_ctl_off)
                local_matrices.append(local_ctl)

                row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{name}_ROW", ss=True)
                cmds.connectAttr(local_ctl, f"{row_from_matrix}.matrix")
                cmds.setAttr(f"{row_from_matrix}.input", 3)

                cmds.connectAttr(f"{row_from_matrix}.outputX", f"{bezierCurve}.controlPoints[{i}].xValue", f=True)
                cmds.connectAttr(f"{row_from_matrix}.outputY", f"{bezierCurve}.controlPoints[{i}].yValue", f=True)
                cmds.connectAttr(f"{row_from_matrix}.outputZ", f"{bezierCurve}.controlPoints[{i}].zValue", f=True)

                # cmds.connectAttr(f"{local_ctl}", f"{joint}.offsetParentMatrix", f=True)

                
                path_joints.append(joint)

            for i, ctl in enumerate(controllers_parenting):
                base = (i // 3) + 1
                mod = i % 3

                name = ctl.split("_CTL")[0] + ctl.split("_CTL")[1]  


                if mod == 0:
                    pass


                elif mod == 1:
                    multmatrix = cmds.createNode("multMatrix", name=f"{name}DoubleParent_MMX", ss=True)
                    cmds.connectAttr(f"{parent_mouth_positions[i]}.matrixSum", f"{multmatrix}.matrixIn[1]")
                    secondary_parent = core.local_space_parent(ctl, parents=[local_matrices_offset[(base - 1) * 3]], local_parent=f"{self.controllersParentMatrix}.outputMatrix")
                    cmds.connectAttr(f"{secondary_parent}.matrixSum", f"{multmatrix}.matrixIn[0]")
                    cmds.connectAttr(f"{multmatrix}.matrixSum", f"{name}_OFF.offsetParentMatrix", f=True)
                    try:
                        cmds.setAttr(f"{ctl}.visibility", lock=False)
                        cmds.connectAttr(f"{controllers_parenting[(base - 1) * 3]}.tangentVisibility", f"{ctl}.visibility", force=True)
                        cmds.setAttr(f"{ctl}.visibility", lock=True)

                    except:
                        pass
                else:
                    multmatrix = cmds.createNode("multMatrix", name=f"{name}DoubleParent_MMX", ss=True)
                    cmds.connectAttr(f"{parent_mouth_positions[i]}.matrixSum", f"{multmatrix}.matrixIn[1]")
                    secondary_parent = core.local_space_parent(ctl, parents=[local_matrices_offset[base * 3]], local_parent=f"{self.controllersParentMatrix}.outputMatrix")
                    cmds.connectAttr(f"{secondary_parent}.matrixSum", f"{multmatrix}.matrixIn[0]")
                    cmds.connectAttr(f"{multmatrix}.matrixSum", f"{name}_OFF.offsetParentMatrix", f=True)
                
                    try:
                        cmds.setAttr(f"{ctl}.visibility", lock=False)

                        cmds.connectAttr(f"{controllers_parenting[base * 3]}.tangentVisibility", f"{ctl}.visibility", force=True)
                        cmds.setAttr(f"{ctl}.visibility", lock=True)

                    except:
                        pass


            bezier_shape = cmds.listRelatives(bezierCurve, shapes=True, type="bezierCurve")[0]
            
            cv_list = cmds.ls(f"{curve}.cv[*]", flatten=True)
            total_cvs = len(cv_list)
            mid_index_calc = int(total_cvs // 2)

            number = 1

            parent_node = []

            for i, cv in enumerate(cv_list):
                mid_index = int(len(cmds.ls(f"{curve}.cv[*]", flatten=True)) // 2)
                if i < mid_index:
                    cv_side = "R"
                elif i == mid_index:
                    cv_side = "C"
                else:
                    cv_side = "L"

                if core.DataManager().get_asset_name() == "varyndor" or core.DataManager().get_asset_name() == "aychedral" or core.DataManager().get_asset_name() == "oto":
                    number = 1

                else:
                    if cv_side == "R":
                        number = number + 1

                    elif cv_side == "C":
                        number = number + 1
                    
                    else:
                        number = number - 1

                name = f"{cv_side}_{main_mid_name}Lips0{number}End"

                cv_pos = cmds.xform(cv, q=True, ws=True, t=True)
                parameter = self.getClosestParamToPosition(bezierCurve, cv_pos)

                motionPath = cmds.createNode("motionPath", n=f"{name}0{i}_MPA", ss=True)
                motionPath_closed = cmds.createNode("motionPath", n=f"{name}0{i}Closed_MPA", ss=True)
                
                fourByFourMatrix = cmds.createNode("fourByFourMatrix", n=f"{name}0{i}_4B4", ss=True)
                fourByFourMatrix_closed = cmds.createNode("fourByFourMatrix", n=f"{name}0{i}Closed_4B4", ss=True)

                cmds.connectAttr(f"{bezier_shape}.worldSpace[0]", f"{motionPath}.geometryPath", f=True)
                cmds.connectAttr(f"{self.average_curve_node}.outputCurve", f"{motionPath_closed}.geometryPath", f=True)
                
                cmds.setAttr(f"{motionPath}.uValue", parameter)
                cmds.setAttr(f"{motionPath_closed}.uValue", parameter)
                
                cmds.connectAttr(f"{motionPath}.allCoordinates.xCoordinate", f"{fourByFourMatrix}.in30", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.yCoordinate", f"{fourByFourMatrix}.in31", f=True)
                cmds.connectAttr(f"{motionPath}.allCoordinates.zCoordinate", f"{fourByFourMatrix}.in32", f=True)
                if cv_side == "R":
                    cmds.setAttr(f"{fourByFourMatrix}.in00", -1)

                cmds.connectAttr(f"{motionPath_closed}.allCoordinates.xCoordinate", f"{fourByFourMatrix_closed}.in30", f=True)
                cmds.connectAttr(f"{motionPath_closed}.allCoordinates.yCoordinate", f"{fourByFourMatrix_closed}.in31", f=True)
                cmds.connectAttr(f"{motionPath_closed}.allCoordinates.zCoordinate", f"{fourByFourMatrix_closed}.in32", f=True)
                if cv_side == "R":
                    cmds.setAttr(f"{fourByFourMatrix_closed}.in00", -1)

                fourOrigPos = cmds.createNode("fourByFourMatrix", name=f"{name}0{i}Orig_4B4", ss=True)
                parent_matrix = cmds.createNode("parentMatrix", name=f"{name}0{i}_PMX", ss=True)
                
                cv_pos = cmds.pointPosition(f"{curve}.cv[{i}]", w=True)
                cmds.setAttr(f"{fourOrigPos}.in30", cv_pos[0])
                cmds.setAttr(f"{fourOrigPos}.in31", cv_pos[1])
                cmds.setAttr(f"{fourOrigPos}.in32", cv_pos[2])

                # cmds.connectAttr(f"{curve}Shape.editPoints[{i}].xValueEp", f"{fourOrigPos}.in30", f=True)
                # cmds.connectAttr(f"{curve}Shape.editPoints[{i}].yValueEp", f"{fourOrigPos}.in31", f=True)
                # cmds.connectAttr(f"{curve}Shape.editPoints[{i}].zValueEp", f"{fourOrigPos}.in32", f=True)

                cmds.connectAttr(f"{fourOrigPos}.output", f"{parent_matrix}.inputMatrix", f=True)
                cmds.connectAttr(f"{fourByFourMatrix}.output", f"{parent_matrix}.target[0].targetMatrix", f=True)
                cmds.connectAttr(f"{fourByFourMatrix_closed}.output", f"{parent_matrix}.target[1].targetMatrix", f=True)

            
                dist_from_center = abs(i - mid_index_calc)
                normalized_pos = 1.0 - (float(dist_from_center) / float(mid_index_calc)) if mid_index_calc > 0 else 1.0

                sticky_remap = cmds.createNode("remapValue", name=f"{name}0{i}Sticky_RMV", ss=True)
                cmds.connectAttr(f"{self.jaw_ctl}.stickyLips", f"{sticky_remap}.inputValue", force=True)

                threshold_start = normalized_pos * 0.8
                
                cmds.setAttr(f"{sticky_remap}.inputMin", threshold_start)
                
                float_constant = cmds.createNode("floatConstant", name=f"{name}0{i}Falloff_FC", ss=True)
                cmds.setAttr(f"{float_constant}.inFloat", threshold_start)

                falloff_sum = cmds.createNode("sum", name=f"{name}0{i}Falloff_SUM", ss=True)
                cmds.connectAttr(f"{self.jaw_ctl}.stickyFalloff", f"{falloff_sum}.input[1]", force=True)
                cmds.connectAttr(f"{float_constant}.outFloat", f"{falloff_sum}.input[0]", force=True)
                cmds.connectAttr(f"{falloff_sum}.output", f"{sticky_remap}.inputMax", force=True)

                # falloff_add = cmds.createNode("addDoubleLinear", name=f"{name}0{i}Falloff_ADL", ss=True)
                # print(falloff_add)
                # cmds.setAttr(f"{falloff_add}.input1", threshold_start)
                # cmds.connectAttr(f"{self.jaw_ctl}.stickyFalloff", f"{falloff_add}.input2", force=True)

                # cmds.connectAttr(f"{falloff_add}.output", f"{sticky_remap}.inputMax", force=True)

                cmds.setAttr(f"{sticky_remap}.outputMin", 0)
                cmds.setAttr(f"{sticky_remap}.outputMax", 1)

                weight_sum = cmds.createNode("plusMinusAverage", name=f"{name}0{i}Weight_PMA", ss=True)
                cmds.setAttr(f"{weight_sum}.operation", 1)
                cmds.connectAttr(f"{self.jaw_ctl}.zip", f"{weight_sum}.input1D[0]", force=True)
                cmds.connectAttr(f"{sticky_remap}.outValue", f"{weight_sum}.input1D[1]", force=True)

                weight_clamp = cmds.createNode("clamp", name=f"{name}0{i}Weight_CLP", ss=True)
                cmds.connectAttr(f"{weight_sum}.output1D", f"{weight_clamp}.inputR", force=True)
                cmds.setAttr(f"{weight_clamp}.minR", 0)
                cmds.setAttr(f"{weight_clamp}.maxR", 1)

                cmds.connectAttr(f"{weight_clamp}.outputR", f"{parent_matrix}.target[1].weight", force=True)

                reverse_node = cmds.createNode("reverse", name=f"{name}0{i}Weight_REV", ss=True)
                cmds.connectAttr(f"{weight_clamp}.outputR", f"{reverse_node}.inputX", force=True)
                cmds.connectAttr(f"{reverse_node}.outputX", f"{parent_matrix}.target[0].weight", force=True)

                # cmds.connectAttr(f"{fourByFourMatrix}.output", f"{joint}.offsetParentMatrix", f=True)

                offset_calculation.append([parent_matrix, fourOrigPos, fourByFourMatrix, fourByFourMatrix_closed])
                joint = cmds.createNode("joint", n=f"{name}0{i}_JNT", ss=True, parent=self.skinning_trn)
                cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", f=True)

                parent_node.append(parent_matrix)

            # for i, node in enumerate(parent_node):
            #     joint = cmds.createNode("joint", n=node.replace("_PMX", "_JNT"), ss=True, parent=self.skinning_trn)
            #     aim_matrix = cmds.createNode("aimMatrix", name=f"{node}Aim_AMX", ss=True)
            #     cmds.connectAttr(f"{node}.outputMatrix", f"{aim_matrix}.inputMatrix", f=True)
            #     # cmds.setAttr(f"{aim_matrix}.secondaryMode", 1)
            #     controller = self.local_jaw  if "lower" in node.lower() else self.local_upper_jaw
            #     cmds.connectAttr(f"{controller}", f"{aim_matrix}.primaryTargetMatrix", f=True)
            #     cmds.setAttr(f"{aim_matrix}.primaryInputAxis", 1,0,0)
            #     # cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", 0,0,-1)
            #     cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", f=True)

                # if i != len(parent_node) -1:
                #     cmds.connectAttr(f"{parent_node[i+1]}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix", f=True)
                # else:
                #     cmds.connectAttr(f"{parent_node[i-1]}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix", f=True)
                #     cmds.setAttr(f"{aim_matrix}.primaryInputAxis", -1,0,0)


        for offset in offset_calculation:
            parent = offset[0]
            orig = offset[1]
            open_mat = offset[2]
            closed_mat = offset[3]

            cmds.setAttr(f"{parent}.target[0].offsetMatrix", get_offset_matrix(f"{orig}.output", f"{open_mat}.output"), type="matrix")
            cmds.setAttr(f"{parent}.target[1].offsetMatrix", get_offset_matrix(f"{orig}.output", f"{closed_mat}.output"), type="matrix")




        
