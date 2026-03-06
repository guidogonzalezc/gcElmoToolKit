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
from elmoTools.utils import de_boor_core_002 as de_boors_002
from elmoTools.utils import export_settings

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
                                     "settings_transform": self.transform_settings,
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


    def local_parent_second_layer(self, grp, parent):
        name = grp.replace("_GRP", "")
        local_mult_matrix = cmds.createNode("multMatrix", name=f"{name}SecondLayer_MMX", ss=True)

        cmds.setAttr(f"{name}_OFF.inheritsTransform", 0)
        
        parent_matrix = cmds.getAttr(f"{parent}")
        head_matrix = cmds.getAttr(f"{self.head_ctl}.worldInverseMatrix[0]")


        # cmds.setAttr(f"{grp}.offsetParentMatrix", parent_matrix, type="matrix")

        cmds.connectAttr(f"{parent}", f"{local_mult_matrix}.matrixIn[0]")
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{local_mult_matrix}.matrixIn[1]")
        cmds.setAttr(f"{local_mult_matrix}.matrixIn[2]", head_matrix, type="matrix")

        cmds.connectAttr(f"{local_mult_matrix}.matrixSum", f"{name}_OFF.offsetParentMatrix", force=True)

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

        self.local_jaw = self.local_setup(self.jaw_ctl_grp[0], self.jaw_ctl)

        cmds.addAttr(self.jaw_ctl, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.jaw_ctl+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.jaw_ctl, shortName="collision", niceName="Collision", maxValue=1, minValue=0,defaultValue=1, keyable=True)
        cmds.addAttr(self.jaw_ctl, shortName="mouthHeight", niceName="Mouth Height", maxValue=1, minValue=0,defaultValue=0.5, keyable=True)
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
        self.local_upper_jaw = self.local_setup(self.upper_jaw_ctl_grp[0], self.upper_jaw_ctl)

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
        cmds.connectAttr(self.local_jaw, f"{self.jaw_local_joint}.offsetParentMatrix")

        self.upper_jaw_local_joint = cmds.createNode("joint", name=f"{self.side}_upperJaw_JNT", ss=True, parent=self.skinning_trn)
        cmds.connectAttr(self.local_upper_jaw, f"{self.upper_jaw_local_joint}.offsetParentMatrix")

        self.jaw_surface = None
        for guides in self.guides:
            if cmds.listRelatives(guides, shapes=True, type="nurbsSurface"):
                    self.jaw_surface = guides

        if self.jaw_surface:

            bbox = cmds.xform(self.jaw_surface, q=True, bb=True, ws=True)
            
            cx = (bbox[0] + bbox[3]) / 2
            cy = (bbox[1] + bbox[4]) / 2
            cz = (bbox[2] + bbox[5]) / 2
            
            self.center_locator = cmds.spaceLocator(name=f"{self.jaw_surface}_bbox_LOC")[0]
            cmds.parent(self.center_locator, self.module_trn)
            cmds.move(cx, cy, cz, self.center_locator)

        corner_joints = []
        for obj in self.guides[1:]:
            if "corner" in obj.lower():
                corner_joints.append(obj)

        if corner_joints:
            for obj in corner_joints:
                name = obj.replace("_GUIDE", "")
                jaw_corner_ctl, jaw_corner_ctl_grp = controller_creator(
                name=name,
                suffixes=["GRP", "OFF","ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
                )

                cmds.connectAttr(f"{obj}.worldMatrix[0]", f"{jaw_corner_ctl_grp[0]}.offsetParentMatrix")

                parent_matrix = cmds.createNode("parentMatrix", name=f"{name}_PMX", ss=True)
                cmds.connectAttr(f"{jaw_corner_ctl_grp[0]}.worldMatrix[0]", f"{parent_matrix}.inputMatrix", force=True)
                cmds.connectAttr(f"{self.jaw_ctl}.worldMatrix[0]", f"{parent_matrix}.target[0].targetMatrix", force=True)
                offset = core.get_offset_matrix(f"{jaw_corner_ctl_grp[0]}.worldMatrix", f"{self.jaw_ctl}.worldMatrix[0]")
                cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", offset, type="matrix")

                multMatrix = cmds.createNode("multMatrix", name=f"{name}Offset_MMX", ss=True)
                cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{multMatrix}.matrixIn[0]")
                cmds.connectAttr(f"{jaw_corner_ctl_grp[0]}.worldInverseMatrix[0]", f"{multMatrix}.matrixIn[1]")

                cmds.connectAttr(f"{multMatrix}.matrixSum", f"{jaw_corner_ctl_grp[1]}.offsetParentMatrix", force=True)

                local_corner = self.local_setup(ctl = jaw_corner_ctl, grp = jaw_corner_ctl_grp[0])

                joint = cmds.createNode("joint", name=f"{name}_JNT", ss=True, parent=self.skinning_trn)
                cmds.connectAttr(f"{local_corner}", f"{joint}.offsetParentMatrix", force=True)

                self.guides.remove(obj)

        if len(self.guides) > 2:

            self.lips_setup()

    def lips_setup(self):

        self.projected_locators_trn = cmds.createNode("transform", name=f"{self.side}_jawProjectedLocators_GRP", ss=True, parent=self.module_trn)


        self.linear_curves = []
        for guides in self.guides:
            if cmds.listRelatives(guides, shapes=True, type="nurbsCurve"):
                cv_pos = cmds.xform(f"{guides}.cv[0]", q=True, ws=True, t=True)
                if cv_pos[0] > 0:
                    cmds.reverseCurve(guides, ch=False, rpo=True)
                self.linear_curves.append(guides)

        self.bezier_curves = []

        self.transform_settings = cmds.createNode("transform", name=f"C_lipSettings_TRN", ss=True, parent=self.module_trn)
        for attr in ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "visibility"]:
            cmds.setAttr(f"{self.transform_settings}.{attr}", lock=True, keyable=False, channelBox=False)

        cmds.addAttr(self.transform_settings, longName="lipsSep", niceName="LIPS ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(f"{self.transform_settings}.lipsSep", channelBox=True, lock=True)
        cmds.addAttr(self.transform_settings, longName="horizontalFollow02", niceName="horizontalFollow02", defaultValue=0.77, minValue=0,maxValue = 1, keyable=True)
        cmds.addAttr(self.transform_settings, longName="verticalFollow02", niceName="verticalFollow02", defaultValue=0.58, minValue=0,maxValue = 1, keyable=True)
        cmds.addAttr(self.transform_settings, longName="horizontalFollow03", niceName="horizontalFollow03", defaultValue=0.5, minValue=0,maxValue = 1, keyable=True)
        cmds.addAttr(self.transform_settings, longName="verticalFollow03", niceName="verticalFollow03", defaultValue=0.25, minValue=0,maxValue = 1, keyable=True)

        cmds.addAttr(self.transform_settings, longName="jawSep", niceName="JAW WEIGHTS ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(f"{self.transform_settings}.jawSep", channelBox=True, lock=True)
        cmds.addAttr(self.transform_settings, longName="jawUpperWeight02", niceName="jawUpperWeight02", defaultValue=0.3, minValue=0,maxValue = 1, keyable=True)
        cmds.addAttr(self.transform_settings, longName="jawUpperWeight03", niceName="jawUpperWeight03", defaultValue=0.1, minValue=0,maxValue = 1, keyable=True)
        cmds.addAttr(self.transform_settings, longName="jawLowerWeight02", niceName="jawLowerWeight02", defaultValue=0.6, minValue=0,maxValue = 1, keyable=True)
        cmds.addAttr(self.transform_settings, longName="jawLowerWeight03", niceName="jawLowerWeight03", defaultValue=0.77, minValue=0,maxValue = 1, keyable=True)

        cmds.addAttr(self.transform_settings, longName="poutSep", niceName="POUT WEIGHTS ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(f"{self.transform_settings}.poutSep", channelBox=True, lock=True)
        cmds.addAttr(self.transform_settings, longName="poutLowerTranslate", niceName="poutLowerTranslate", defaultValue=-0.02, keyable=True)
        cmds.addAttr(self.transform_settings, longName="poutLowerRotate", niceName="poutLowerRotate", defaultValue=-0.2, keyable=True)
        cmds.addAttr(self.transform_settings, longName="poutUpperTranslate", niceName="poutUpperTranslate", defaultValue=-0.05, keyable=True)
        cmds.addAttr(self.transform_settings, longName="poutUpperRotate", niceName="poutUpperRotate", defaultValue=2.0, keyable=True)

        export_settings.import_settings()


        self.average_curve_node = cmds.createNode("avgCurves", name=f"{self.side}_lipsAverage_ACV", ss=True)
        cmds.setAttr(f"{self.average_curve_node}.automaticWeight", 0)
        reverse = cmds.createNode("reverse", name=f"{self.side}_lipsAverageReverse_REV", ss=True)
        cmds.connectAttr(f"{reverse}.outputX", f"{self.average_curve_node}.weight1")
        cmds.connectAttr(f"{self.jaw_ctl}.mouthHeight", f"{reverse}.inputX")
        cmds.connectAttr(f"{self.jaw_ctl}.mouthHeight", f"{self.average_curve_node}.weight2")

        mouth_sliding_shape = cmds.listRelatives(self.jaw_surface, shapes=True, noIntermediate=True)[0]

        corner_locals = []

        uv_pin_corners = cmds.createNode("uvPin", name=f"C_lipCorners_UVP", ss=True)
        cmds.connectAttr(f"{mouth_sliding_shape}.worldSpace[0]", f"{uv_pin_corners}.deformedGeometry")

        cmds.setAttr(f"{uv_pin_corners}.normalAxis", 2)
        cmds.setAttr(f"{uv_pin_corners}.tangentAxis", 0)

        closest_points_corners = []
        local_lips_corner_projected = []
        corner_projected_ctls = []

        cvs= cmds.ls(f"{self.linear_curves[0]}.cv[*]", fl=True)
        for i, (side, index) in enumerate(zip(["L", "R"], [len(cvs)-1, 0])):
            corner_jaw_ctl, corner_jaw_ctl_grp = controller_creator(
                name=f"{side}_lipCorner",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["rx","ry","rz","scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
            )

            lip_corner_pos = cmds.createNode("fourByFourMatrix", name=f"{side}_lipCorner_4B4", ss=True)
            pos = cmds.pointPosition(f"{self.linear_curves[0]}.cv[{index}]", w=True)
            cmds.setAttr(f"{lip_corner_pos}.in30", pos[0])
            cmds.setAttr(f"{lip_corner_pos}.in31", pos[1])
            cmds.setAttr(f"{lip_corner_pos}.in32", pos[2])
         
            aimMatrix_corner = cmds.createNode("aimMatrix", name=f"{side}_lipCorner_AMX", ss=True)
            cmds.connectAttr(f"{lip_corner_pos}.output", f"{aimMatrix_corner}.inputMatrix")
            cmds.connectAttr(f"{self.center_locator}.worldMatrix[0]", f"{aimMatrix_corner}.primaryTargetMatrix")
            cmds.setAttr(f"{aimMatrix_corner}.primaryInputAxis", 0,0,-1)
            if side == "R":
                multmatrix_corner = core.mirror_behaviour(type=0, name=f"{side}_lipCornerMirror", input_matrix=f"{aimMatrix_corner}.outputMatrix")

            else:
                multmatrix_corner = f"{aimMatrix_corner}.outputMatrix"


            cmds.addAttr(corner_jaw_ctl, longName="jawSep", niceName = "Jaw Separator  ———", attributeType="enum", enumName="———", keyable=True)
            cmds.setAttr(f"{corner_jaw_ctl}.jawSep", channelBox=True, lock=True)   

            cmds.addAttr(corner_jaw_ctl, longName="upperJawLowerJaw", niceName= "Upper Jaw --> Lower Jaw", attributeType="float", min=0, max=1, defaultValue=0.5, keyable=True)
            parent_matrix = cmds.createNode("parentMatrix", name=f"{side}_lipCornerJaw_PMX", ss=True)
    
            cmds.connectAttr(f"{multmatrix_corner}", f"{parent_matrix}.inputMatrix", force=True)
            cmds.connectAttr(f"{self.local_jaw}", f"{parent_matrix}.target[0].targetMatrix", force=True)
            offset = core.get_offset_matrix(multmatrix_corner, self.local_jaw)
            cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", offset, type="matrix")

            cmds.connectAttr(f"{self.local_upper_jaw}", f"{parent_matrix}.target[1].targetMatrix", force=True)
            offset = core.get_offset_matrix(multmatrix_corner, self.local_upper_jaw)
            cmds.setAttr(f"{parent_matrix}.target[1].offsetMatrix", offset, type="matrix")

            self.jaw_reverse = cmds.createNode("reverse", name=f"{side}_lipCornerUpperLower_REV", ss=True)
            cmds.connectAttr(f"{corner_jaw_ctl}.upperJawLowerJaw", f"{self.jaw_reverse}.inputX")
            cmds.connectAttr(f"{self.jaw_reverse}.outputX", f"{parent_matrix}.target[1].weight", force=True)
            cmds.connectAttr(f"{corner_jaw_ctl}.upperJawLowerJaw", f"{parent_matrix}.target[0].weight", force=True)

            cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{corner_jaw_ctl_grp[0]}.offsetParentMatrix", force=True)
    
            corner_local = self.local_setup(ctl = corner_jaw_ctl, grp = corner_jaw_ctl_grp[0])
            corner_locals.append(corner_local)

            row = cmds.createNode("rowFromMatrix", name=f"{side}_lipCorner01_RFM", ss=True)
            cmds.connectAttr(f"{corner_local}", f"{row}.matrix")
            cmds.setAttr(f"{row}.input", 3) 
            closest_point = cmds.createNode("closestPointOnSurface", name=f"{side}_lipCorner01_CPS", ss=True)
            for attr in ["X", "Y", "Z"]:
                cmds.connectAttr(f"{row}.output{attr}", f"{closest_point}.inPosition{attr}")

            cmds.connectAttr(f"{closest_point}.parameterU", f"{uv_pin_corners}.coordinate[{i}].coordinateU")
            cmds.connectAttr(f"{closest_point}.parameterV", f"{uv_pin_corners}.coordinate[{i}].coordinateV")

            closest_points_corners.append(closest_point)

            cmds.connectAttr(f"{mouth_sliding_shape}.worldSpace[0]", f"{closest_point}.inputSurface")

            projected_locator = cmds.spaceLocator(name=f"{side}_lipCorner01_LOC")[0]

            if side == "R":
                multmatrix_corner = core.mirror_behaviour(type=0, name=f"{side}_lipCorner01Mirror", input_matrix=f"{uv_pin_corners}.outputMatrix[{i}]")
                connected_attr = multmatrix_corner
            else:
                connected_attr = f"{uv_pin_corners}.outputMatrix[{i}]"

            multmatrix = cmds.createNode("multMatrix", name=f"C_lipCorner01Jaw_MMX", ss=True)
            cmds.connectAttr(connected_attr, f"{multmatrix}.matrixIn[0]")

            matrix = cmds.getAttr(self.local_jaw)
            matrix_inverse = om.MMatrix(matrix).inverse()
            cmds.setAttr(f"{multmatrix}.matrixIn[1]", matrix_inverse, type="matrix")
            
            wtadd = cmds.createNode("wtAddMatrix", name=f"{side}_lipCorner01Jaw_WTM", ss=True)
            cmds.connectAttr(self.local_jaw, f"{wtadd}.wtMatrix[0].matrixIn")
            cmds.connectAttr(self.local_upper_jaw, f"{wtadd}.wtMatrix[1].matrixIn")
            cmds.connectAttr(f"{corner_jaw_ctl}.upperJawLowerJaw", f"{wtadd}.wtMatrix[0].weightIn")
            cmds.connectAttr(f"{self.jaw_reverse}.outputX", f"{wtadd}.wtMatrix[1].weightIn")

            cmds.connectAttr(f"{wtadd}.matrixSum", f"{multmatrix}.matrixIn[2]")

            cmds.connectAttr(f"{multmatrix}.matrixSum", f"{projected_locator}.offsetParentMatrix", force=True)


            cmds.parent(projected_locator, self.projected_locators_trn)

            ctl, ctl_grp = controller_creator(
                name=f"{side}_lipCorner01",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn,
            )

            corner_projected_ctls.append(ctl)
            
            cmds.connectAttr(f"{projected_locator}.worldMatrix[0]", f"{ctl_grp[0]}.offsetParentMatrix", force=True)

            local_lip_corner_projected = self.local_setup(ctl = ctl, grp = ctl_grp[0])
            local_lips_corner_projected.append(local_lip_corner_projected)


        matrix_ends = []
        temp_matrix_ends = []
        self.center_mid_ctl = []
        for curve_index, curve in enumerate(self.linear_curves):
            
            main_mid_name = "upper" if "upper" in curve else "lower"
            jaw_controller = self.jaw_ctl if "lower" in curve else self.upper_jaw_ctl

            rebuilded_curve_4 = cmds.rebuildCurve(
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
                    name=curve.replace("Curve_GUIDE", "RebuildFourSpans_CRV")
                )[0]
            

            rebuilded_curve_8 = cmds.rebuildCurve(
                    curve,
                    ch=0,
                    rpo=0,
                    rt=0,
                    end=1,
                    kr=0,
                    kcp=0,
                    kep=1,
                    kt=0,
                    s=9,
                    d=2,
                    tol=0.01,
                    name=curve.replace("Curve_GUIDE", "RebuildEightSpans_CRV")
                )[0]
            
            cmds.parent(rebuilded_curve_4, rebuilded_curve_8, self.module_trn)


            self.main_mid_ctl, self.main_mid_ctl_grp = controller_creator(
                    name=f"C_{main_mid_name}Lip",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn,
                )
            

            self.center_mid_ctl.append(self.main_mid_ctl)

            last_cv = int((len(cmds.ls(f"{curve}.cv[*]", flatten=True))-1)//2)
            mid_pos_4b4 = cmds.createNode("fourByFourMatrix", name=f"C_{main_mid_name}MidLip_4B4", ss=True)
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].xValueEp", f"{mid_pos_4b4}.in30")
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].yValueEp", f"{mid_pos_4b4}.in31")
            cmds.connectAttr(f"{curve}.editPoints[{last_cv}].zValueEp", f"{mid_pos_4b4}.in32")

            if main_mid_name == "lower":
                multmatrix_corner = cmds.createNode("multMatrix", name=f"C_{main_mid_name}MidLipMirror_MMX", ss=True)
                cmds.setAttr(f"{multmatrix_corner}.matrixIn[0]", 1, 0, 0, 0,
                                                    0, -1, 0, 0,
                                                    0, 0, 1, 0,
                                                    0, 0, 0, 1, type="matrix")
                cmds.connectAttr(f"{mid_pos_4b4}.output", f"{multmatrix_corner}.matrixIn[1]")
                current_attr = f"{multmatrix_corner}.matrixSum"
            else:
                current_attr = f"{mid_pos_4b4}.output"

            multmatrix = cmds.createNode("multMatrix", name=f"C_{main_mid_name}MidLipJaw_MMX", ss=True)
            offset = core.get_offset_matrix(f"{current_attr}", f"{self.jaw_ctl}.worldMatrix")
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", offset, type="matrix")
            cmds.connectAttr(f"{self.local_jaw if main_mid_name == 'lower' else self.local_upper_jaw}", f"{multmatrix}.matrixIn[1]")
            cmds.connectAttr(f"{multmatrix}.matrixSum", f"{self.main_mid_ctl_grp[0]}.offsetParentMatrix", force=True)



            self.mid_local = self.local_setup(ctl = self.main_mid_ctl, grp = self.main_mid_ctl_grp[0])
            
            uv_pin = cmds.createNode("uvPin", name=f"C_{main_mid_name}Lip_UVP", ss=True)
            cmds.connectAttr(f"{mouth_sliding_shape}.worldSpace[0]", f"{uv_pin}.deformedGeometry")
            cmds.setAttr(f"{uv_pin}.normalAxis", 2)
            cmds.setAttr(f"{uv_pin}.tangentAxis", 0)

            cvs_deboors = []
            closest_points = []

            # ---- BTA PROJECTIONS ---- #

            center_row = cmds.createNode("rowFromMatrix", name=f"C_{main_mid_name}Lip01_RFM", ss=True)
            cmds.connectAttr(f"{self.mid_local}", f"{center_row}.matrix")
            cmds.setAttr(f"{center_row}.input", 3) 
            c_closest_point = cmds.createNode("closestPointOnSurface", name=f"C_{main_mid_name}lip01_CPS", ss=True)
            closest_points.append(c_closest_point)
            for attr in ["X", "Y", "Z"]:
                cmds.connectAttr(f"{center_row}.output{attr}", f"{c_closest_point}.inPosition{attr}")

            cmds.connectAttr(f"{c_closest_point}.parameterU", f"{uv_pin}.coordinate[0].coordinateU")
            cmds.connectAttr(f"{c_closest_point}.parameterV", f"{uv_pin}.coordinate[0].coordinateV")

            cmds.connectAttr(f"{mouth_sliding_shape}.worldSpace[0]", f"{c_closest_point}.inputSurface")


            projected_locator_mid = cmds.spaceLocator(name=f"C_{main_mid_name}Lip01_LOC")[0]

            if main_mid_name == "lower":
                multmatrix_corner = core.mirror_behaviour(type=2, name=f"C_{main_mid_name}Lip01Mirror", input_matrix=f"{uv_pin}.outputMatrix[0]")

                connected_attr = multmatrix_corner
            else:

                connected_attr = f"{uv_pin}.outputMatrix[0]"

            multmatrix = cmds.createNode("multMatrix", name=f"C_{main_mid_name}MidLipJaw_MMX", ss=True)
            cmds.connectAttr(connected_attr, f"{multmatrix}.matrixIn[0]")

            matrix = cmds.getAttr(self.local_jaw)
            matrix_inverse = om.MMatrix(matrix).inverse()
            cmds.setAttr(f"{multmatrix}.matrixIn[1]", matrix_inverse, type="matrix")
            
            if main_mid_name == "lower":
                cmds.connectAttr(f"{self.local_jaw}", f"{multmatrix}.matrixIn[2]")
            else:
                cmds.connectAttr(f"{self.local_upper_jaw}", f"{multmatrix}.matrixIn[2]")

            cmds.connectAttr(f"{multmatrix}.matrixSum", f"{projected_locator_mid}.offsetParentMatrix", force=True)


            cmds.parent(projected_locator_mid, self.projected_locators_trn)

            for i, local in enumerate(corner_locals):

                side = local.split("_")[0] 
                i_range = i*3+1
            
                for num_zero, j in enumerate(range(i_range+1, i_range+3)):
                    u_bta = cmds.createNode("blendTwoAttr", name=f"{side}_{main_mid_name}LipUFollow0{num_zero+2}_BTA", ss=True)
                    v_bta = cmds.createNode("blendTwoAttr", name=f"{side}_{main_mid_name}LipVFollow0{num_zero+2}_BTA", ss=True)
                    cmds.connectAttr(f"{self.transform_settings}.horizontalFollow0{num_zero+2}", f"{u_bta}.attributesBlender")
                    cmds.connectAttr(f"{self.transform_settings}.verticalFollow0{num_zero+2}", f"{v_bta}.attributesBlender")

                    cmds.connectAttr(f"{c_closest_point}.parameterU", f"{u_bta}.input[0]")
                    cmds.connectAttr(f"{c_closest_point}.parameterV", f"{v_bta}.input[0]")
                    cmds.connectAttr(f"{closest_points_corners[i]}.parameterU", f"{u_bta}.input[1]")
                    cmds.connectAttr(f"{closest_points_corners[i]}.parameterV", f"{v_bta}.input[1]")

                    cmds.connectAttr(f"{u_bta}.output", f"{uv_pin}.coordinate[{j}].coordinateU")
                    cmds.connectAttr(f"{v_bta}.output", f"{uv_pin}.coordinate[{j}].coordinateV")

                    projected_locator = cmds.spaceLocator(name=f"{side}_{main_mid_name}Lip0{num_zero+2}_LOC")[0]
                    cvs_deboors.append(projected_locator)
                    cmds.parent(projected_locator, self.projected_locators_trn)

                    if j-1 == i_range+1:
                        aim = f"{uv_pin}.outputMatrix[{j-1}]"
                    else:
                        aim = f"{uv_pin_corners}.outputMatrix[{i}]"

                    aimMatrix = cmds.createNode("aimMatrix", name=f"{side}_{main_mid_name}Lip0{num_zero+2}_AMX", ss=True)
                    cmds.connectAttr(f"{uv_pin}.outputMatrix[{j}]", f"{aimMatrix}.inputMatrix")
                    cmds.connectAttr(aim, f"{aimMatrix}.primaryTargetMatrix")
                    cmds.connectAttr(f"{self.center_locator}.worldMatrix[0]", f"{aimMatrix}.secondaryTargetMatrix")

                    if side == "L":
                        axis = (1,0,0)
                    else:
                        axis = (-1,0,0)

                    cmds.setAttr(f"{aimMatrix}.primaryInputAxis", *axis)
                    cmds.setAttr(f"{aimMatrix}.secondaryInputAxis", 0,0,-1)
                    cmds.setAttr(f"{aimMatrix}.secondaryMode", 1)

                    if side == "R" or main_mid_name == "lower":
                        if side == "R" and main_mid_name == "lower":
                            multmatrix = core.mirror_behaviour(type=1, name=f"{side}_{main_mid_name}Lip0{num_zero+2}Mirror", input_matrix=f"{aimMatrix}.outputMatrix")
                        
                        elif side == "R":
                            multmatrix = core.mirror_behaviour(type=0, name=f"{side}_{main_mid_name}Lip0{num_zero+2}Mirror", input_matrix=f"{aimMatrix}.outputMatrix")

                        else:
                            multmatrix = core.mirror_behaviour(type=2, name=f"{side}_{main_mid_name}Lip0{num_zero+2}Mirror", input_matrix=f"{aimMatrix}.outputMatrix")

                        connected_attr = multmatrix
                    else:
                        connected_attr = f"{aimMatrix}.outputMatrix"

                    multmatrix = cmds.createNode("multMatrix", name=f"{side}_{main_mid_name}Lip0{num_zero+2}Jaw_MMX", ss=True)
                    cmds.connectAttr(connected_attr, f"{multmatrix}.matrixIn[0]")

                    matrix = cmds.getAttr(self.local_jaw)
                    matrix_inverse = om.MMatrix(matrix).inverse()
                    cmds.setAttr(f"{multmatrix}.matrixIn[1]", matrix_inverse, type="matrix")
                    
                    wtadd = cmds.createNode("wtAddMatrix", name=f"{side}_{main_mid_name}Lip0{num_zero+2}Jaw_WTM", ss=True)
                    cmds.connectAttr(self.local_jaw, f"{wtadd}.wtMatrix[0].matrixIn")
                    cmds.connectAttr(self.local_upper_jaw, f"{wtadd}.wtMatrix[1].matrixIn")

                    reverse = cmds.createNode("reverse", name=f"{side}_{main_mid_name}Lip0{num_zero+2}Jaw_REV", ss=True)

                    cmds.connectAttr(f"{self.transform_settings}.jaw{main_mid_name.capitalize()}Weight0{num_zero+2}", f"{wtadd}.wtMatrix[0].weightIn")
                    cmds.connectAttr(f"{self.transform_settings}.jaw{main_mid_name.capitalize()}Weight0{num_zero+2}", f"{reverse}.inputX")
                    cmds.connectAttr(f"{reverse}.outputX", f"{wtadd}.wtMatrix[1].weightIn")

                    cmds.connectAttr(f"{wtadd}.matrixSum", f"{multmatrix}.matrixIn[2]")

                    cmds.connectAttr(f"{multmatrix}.matrixSum", f"{projected_locator}.offsetParentMatrix", force=True)

            cv_deboors = [corner_projected_ctls[1], cvs_deboors[2], cvs_deboors[3], projected_locator_mid, cvs_deboors[1], cvs_deboors[0], corner_projected_ctls[0]]

            for cv in cv_deboors:
                name_split = cv.split("_")
                name = name_split[0] + "_" + name_split[1]

                temp_decompose = cmds.createNode("decomposeMatrix", name=f"{name}Temp_DCM", ss=True)
                cmds.connectAttr(f"{cv}.worldMatrix[0]", f"{temp_decompose}.inputMatrix", force=True)
                cmds.connectAttr(f"{temp_decompose}.outputTranslate", f"{rebuilded_curve_4}.cv[{cv_deboors.index(cv)}]", force=True)




            ctls = []

            for i, locator in enumerate(cv_deboors):
                if "_LOC" in locator:
                    name = locator.replace("_LOC", "")
                    
                    ctl, ctl_grp = controller_creator(
                        name=f"{name}",
                        suffixes=["GRP", "OFF", "ANM"],
                        lock=["rz","ry","rx","scaleX", "scaleY", "scaleZ", "visibility"],
                        ro=True,
                        parent=self.controllers_trn,
                    )

                    
                    pos_cv = cmds.xform(f"{rebuilded_curve_4}.cv[{i}]", query=True, worldSpace=True, translation=True)
                    locator_wm = cmds.getAttr(f"{locator}.worldMatrix[0]")
                    pos = cmds.xform(locator, query=True, worldSpace=True, translation=True)

                    closest_position, closest_parm = core.getClosestParamToWorldMatrixCurve(rebuilded_curve_4, pos, both = True)
                    # closest_position = core.getPositionFromParmCurve(rebuilded_curve_4, closest_parm)

                    m_matrix = om.MMatrix(locator_wm)
                    m_matrix_inverse = om.MMatrix(locator_wm).inverse()

                    om.MMatrix.setElement(m_matrix, 3, 0, closest_position[0]) # Translate X
                    om.MMatrix.setElement(m_matrix, 3, 1, closest_position[1]) # Translate Y
                    om.MMatrix.setElement(m_matrix, 3, 2, closest_position[2]) # Translate Z

                    offset_matrix = om.MMatrix(m_matrix) * om.MMatrix(m_matrix_inverse)
                   
                    mmx_offset = cmds.createNode("multMatrix", name=f"{name}Offset_MMX", ss=True)

                    cmds.setAttr(f"{mmx_offset}.matrixIn[0]", offset_matrix, type="matrix")
                    cmds.connectAttr(f"{locator}.worldMatrix[0]", f"{mmx_offset}.matrixIn[1]")
                    cmds.connectAttr(f"{mmx_offset}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix", force=True)


                    # cmds.connectAttr(f"{locator}.worldMatrix[0]", f"{ctl_grp[0]}.offsetParentMatrix", force=True)



                else:
                    name = f"{locator.split('_')[0]}{locator.split('_')[1]}"
                    local = locator
                    ctl = locator

                ctls.append(ctl)

            # Convert nurbsCurve into nurbsSurface
            lips_surface = core.create_surface_from_curve(rebuilded_curve_8, clean_name=f"C_{main_mid_name}FineTune_NBS", parent=self.module_trn)
            
            kv = de_boors_002.get_open_uniform_kv(len(ctls), 3)

            pick_matrix_ctls = []
            for z, ctl in enumerate(ctls):
                if z == len(ctls)-1 or z == 0:
                    name = f"{ctl.split('_')[0]}_{main_mid_name}FineTune00"
                else:
                    name = ctl.replace("_CTL", "")
                pickmatrix = cmds.createNode("pickMatrix", name=f"{name}_PMX", ss=True)
                cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{pickmatrix}.inputMatrix")
                pick_matrix_ctls.append(f"{pickmatrix}.outputMatrix")
                cmds.setAttr(f"{pickmatrix}.useShear", 0)
                cmds.setAttr(f"{pickmatrix}.useScale", 0)
                # if z == len(ctls)-1 or z == 0:

                cmds.setAttr(f"{pickmatrix}.useRotate", 1)
                # else:   
                #     cmds.setAttr(f"{pickmatrix}.useRotate", 0)


            count = 0

            initial_fine_tune = []

            for side_corner, index in zip(["R", "L"], [0, -1]):
                if index == 0:
                    initial_fine_tune.append(pick_matrix_ctls[index])
                else:
                    corner_fine_tune = pick_matrix_ctls[index]

            aim_matrix = []
            wt_adds = []

            for i in range(1, 10):
                if i < 5:
                    fine_tune_side = "R"
                    count = count + 1
                elif i == 5:
                    fine_tune_side = "C"
                    count = 0
                else:
                    fine_tune_side = "L"
                    count = count - 1


                position = cmds.pointPosition(f"{rebuilded_curve_8}.cv[{i}]", w=True)
                paramU = self.getClosestParamToPosition(rebuilded_curve_4, position)
 
                wts = de_boors_002.de_boor(len(ctls), 3, paramU, kv)

                wt_add = cmds.createNode("wtAddMatrix", name=f"{fine_tune_side}_{main_mid_name}FineTune0{count}_WTA", ss=True)
                # wt_add_rot = cmds.createNode("wtAddMatrix", name=f"{fine_tune_side}_{main_mid_name}FineTune0{count}Rot_WTA", ss=True)

                for matrix_attr, wt, i in zip(pick_matrix_ctls, wts, range(len(pick_matrix_ctls))):
                    if wt < 0.000001:
                        continue
                    
                    node = matrix_attr.split(".")[0]

                    input_connection = cmds.listConnections(f"{node}.inputMatrix", source=True, destination=False, plugs=True)[0]
                    # cmds.connectAttr(f"{input_connection}", f'{wt_add_rot}.wtMatrix[{i}].matrixIn', force=True)

                    cmds.connectAttr(f"{matrix_attr}", f'{wt_add}.wtMatrix[{i}].matrixIn')
                    cmds.setAttr(f'{wt_add}.wtMatrix[{i}].weightIn', wt)
                    # cmds.setAttr(f'{wt_add_rot}.wtMatrix[{i}].weightIn', wt)

                # aimMatrix_fine = cmds.createNode("aimMatrix", name=f"{fine_tune_side}_{main_mid_name}FineTune0{count}Rotation_AMX", ss=True)
                # cmds.connectAttr(f"{wt_add}.matrixSum", f"{aimMatrix_fine}.inputMatrix")
                # cmds.connectAttr(f"{wt_add}.matrixSum", f"{aimMatrix_fine}.primaryTargetMatrix")
                # cmds.connectAttr(f"{wt_add_rot}.matrixSum", f"{aimMatrix_fine}.primaryTargetMatrix")
                # cmds.connectAttr(f"{wt_add_rot}.matrixSum", f"{aimMatrix_fine}.secondaryTargetMatrix")

                # cmds.setAttr(f"{aimMatrix_fine}.primaryInputAxis", 1,0,0, type="double3")
                # cmds.setAttr(f"{aimMatrix_fine}.primaryTargetVector", 1,0,0, type="double3")
                # cmds.setAttr(f"{aimMatrix_fine}.primaryMode", 1)

                # cmds.setAttr(f"{aimMatrix_fine}.secondaryInputAxis", 0,1,0, type="double3")
                # cmds.setAttr(f"{aimMatrix_fine}.secondaryTargetVector", 0,1,0, type="double3")
                # cmds.setAttr(f"{aimMatrix_fine}.secondaryMode", 2)

                # print(f"{fine_tune_side}_{main_mid_name}FineTune0{count}Rotation_AMX")
                # if aim_matrix:
                #     print(i)
                #     if fine_tune_side == "L" and count:   
                #         print("dentro", f"{fine_tune_side}_{main_mid_name}FineTune0{count}Rotation_AMX") 
                #         cmds.connectAttr(f"{wt_adds[-1]}.matrixSum", f"{aimMatrix_fine}.primaryTargetMatrix")
                #         cmds.setAttr(f"{aimMatrix_fine}.primaryInputAxis", -1,0,0, type="double3")

                    
                    
                #     cmds.connectAttr(f"{wt_add}.matrixSum", f"{aim_matrix[-1]}.primaryTargetMatrix")

                # initial_fine_tune.append(f"{wt_add}.matrixSum")
                initial_fine_tune.append(f"{wt_add}.matrixSum")

                if fine_tune_side == "C":
                    count = 5

                # aim_matrix.append(aimMatrix_fine)
                wt_adds.append(wt_add)


            initial_fine_tune.append(corner_fine_tune)

            surface_joints = []

            fine_tune_trn = cmds.createNode("transform", name=f"C_{main_mid_name}FineTune_GRP", ss=True, parent=self.module_trn)

            for i, fine_tune in enumerate(initial_fine_tune):
                split = fine_tune.split("_")
                name = f"{split[0]}_{split[1]}"
                name = name.replace("Rotation", "")
                side = split[0]

                joint = cmds.createNode("joint", name=f"{name}_JNT", ss=True, parent=fine_tune_trn)
                ctl, ctl_grp = controller_creator(
                        name=f"{name}",
                        suffixes=["GRP", "OFF", "ANM"],
                        lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                        ro=True,
                        parent=self.controllers_trn,
                    )
                
                cmds.setAttr(f"{ctl_grp[1]}.inheritsTransform", 0)

                # if side != "C":
                #     aimMatrix_fine = cmds.createNode("aimMatrix", name=f"{name.replace('Rotation', '_AMX')}", ss=True)
                #     cmds.connectAttr(fine_tune, f"{aimMatrix_fine}.inputMatrix")
                #     cmds.connectAttr(fine_tune, f"{aimMatrix_fine}.secondaryTargetMatrix")
                #     cmds.setAttr(f"{aimMatrix_fine}.secondaryInputAxis", 0,1,0, type="double3")
                #     cmds.setAttr(f"{aimMatrix_fine}.secondaryMode", 2)
                #     cmds.setAttr(f"{aimMatrix_fine}.secondaryTargetVector", 0,1,0, type="double3")

                #     if i != len(initial_fine_tune)-1:
                #         cmds.connectAttr(f"{initial_fine_tune[i+1]}", f"{aimMatrix_fine}.primaryTargetMatrix")
                #     else:
                #         cmds.connectAttr(f"{initial_fine_tune[i-1]}", f"{aimMatrix_fine}.primaryTargetMatrix")
                #         cmds.setAttr(f"{aimMatrix_fine}.primaryInputAxis", -1,0,0, type="double3")

                #     connect_attr_fineTune = f"{aimMatrix_fine}.outputMatrix"

                # else:
                connect_attr_fineTune = fine_tune

                # if fine_tune_side == "R" or main_mid_name == "lower":
                #         if fine_tune_side == "R" and main_mid_name == "lower":
                #             multmatrix = core.mirror_behaviour(type=1, name=f"{name}Mirror", input_matrix=connect_attr_fineTune)
                        
                #         elif fine_tune_side == "R":
                #             multmatrix = core.mirror_behaviour(type=0, name=f"{name}Mirror", input_matrix=connect_attr_fineTune)

                #         else:
                #             multmatrix = core.mirror_behaviour(type=2, name=f"{name}Mirror", input_matrix=connect_attr_fineTune )

                #         cmds.connectAttr(f"{multmatrix}", f"{ctl_grp[1]}.offsetParentMatrix")


                # else:

                cmds.connectAttr(connect_attr_fineTune, f"{ctl_grp[1]}.offsetParentMatrix", force=True)

                cmds.matchTransform(ctl_grp[0], ctl_grp[1])

                local_jaw = self.local_setup(ctl_grp[0], ctl)

                # blend_matrix = cmds.createNode("blendMatrix", name=f"{name}_BMX", ss=True)
                # cmds.connectAttr(f"{local_jaw}", f"{blend_matrix}.inputMatrix")
                # cmds.connectAttr(f"{ctl}.matrix", f"{blend_matrix}.target[0].targetMatrix")
                # cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
                # cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 0)
                # cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)
                # cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", force=True)
                cmds.connectAttr(f"{local_jaw}", f"{joint}.offsetParentMatrix", force=True)
                surface_joints.append(joint)

            offset_nodes = cmds.offsetCurve(
                rebuilded_curve_8,
                ch=True, rn=False, cb=2, st=True, cl=True,
                cr=0, d=0.1, tol=0.01, sd=0, ugn=False
            )

            cmds.setAttr(f"{offset_nodes[-1]}.useGivenNormal", 1)
            cmds.setAttr(f"{offset_nodes[-1]}.normal", 0,0,1, type="double3")

            renamed_offset_curve = cmds.rename(offset_nodes[0], f"C_{main_mid_name}FineTuneOffset_CRV")

            cmds.delete(renamed_offset_curve, ch=True)
            cmds.parent(renamed_offset_curve, self.module_trn)

            lip_skincluster_up = cmds.skinCluster(
                renamed_offset_curve,
                surface_joints,
                n=f"C_{main_mid_name}FineTuneUp_SKC",
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=2,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]


            lip_skincluster = cmds.skinCluster(
                lips_surface,
                surface_joints,
                n=f"C_{main_mid_name}FineTune_SKC",
                toSelectedBones=True,
                bindMethod=0,
                normalizeWeights=1,
                weightDistribution=0,
                maximumInfluences=2,
                dropoffRate=4,
                removeUnusedInfluence=False
            )[0]

            for u in range(len(cmds.ls(f"{lips_surface}.cv[*][1]", flatten=True))):
                curve_cv = f"{renamed_offset_curve}.cv[{u}]"
                cmds.skinPercent(lip_skincluster_up, curve_cv, transformValue=[
                        (surface_joints[u], 1)])
                
                for v in range(len(cmds.ls(f"{lips_surface}.cv[0][*]", flatten=True))):
                    cv = f"{lips_surface}.cv[{u}][{v}]"
                    cmds.skinPercent(lip_skincluster, cv, transformValue=[
                        (surface_joints[u], 1)])

            curve_original_cvs = cmds.ls(f"{curve}.cv[*]", fl=True)

            uv_pin_cvs = cmds.createNode("uvPin", name=f"C_{main_mid_name}LipOriginalCvs_UVP", ss=True)
            uv_pin_cvs_up = cmds.createNode("uvPin", name=f"C_{main_mid_name}LipOriginalCvsUp_UVP", ss=True)

            cmds.setAttr(f"{uv_pin_cvs}.normalAxis", 1)
            cmds.setAttr(f"{uv_pin_cvs}.tangentAxis", 0)

            cmds.connectAttr(f"{lips_surface}.worldSpace[0]", f"{uv_pin_cvs}.deformedGeometry")
            cmds.connectAttr(f"{renamed_offset_curve}.worldSpace[0]", f"{uv_pin_cvs_up}.deformedGeometry")

            count = 0

            mid_index = len(curve_original_cvs)

            for z, cv in enumerate(curve_original_cvs):

                total_len = len(curve_original_cvs) 
                mid_index = (total_len - 1) / 2.0
                
                dist_from_center = abs(count - mid_index)
                t_val = 1.0 - (dist_from_center / mid_index)
                t_val = max(0.0, min(1.0, t_val)) 

         
                pout_remap = cmds.createNode("remapValue", n=f"{side}_{main_mid_name}LipPoutFalloff0{count}_RMV")
                cmds.setAttr(f"{pout_remap}.inputValue", t_val)

                cmds.setAttr(f"{pout_remap}.value[0].value_FloatValue", 0.0)
                cmds.setAttr(f"{pout_remap}.value[0].value_Position", 0.0)
                cmds.setAttr(f"{pout_remap}.value[0].value_Interp", 3)
                
                cmds.setAttr(f"{pout_remap}.value[1].value_FloatValue", 1.0)
                cmds.setAttr(f"{pout_remap}.value[1].value_Position", 1.0)
                cmds.setAttr(f"{pout_remap}.value[1].value_Interp", 3)


                pout_driver = cmds.createNode("multiply", n=f"{side}_{main_mid_name}LipPoutDriver_{count}_MUL")
                cmds.connectAttr(f"{self.main_mid_ctl}.rotateX", f"{pout_driver}.input[0]")
                cmds.connectAttr(f"{pout_remap}.outValue", f"{pout_driver}.input[1]")

                pout_compose = cmds.createNode("composeMatrix", n=f"{side}_{main_mid_name}LipPoutOffset_{count}_CM")

                tz_mult = cmds.createNode("multiply", n=f"{side}_{main_mid_name}LipPoutTZ_{count}_MUL")
                cmds.connectAttr(f"{pout_driver}.output", f"{tz_mult}.input[0]")
                if main_mid_name == "upper":
                    cmds.connectAttr(f"{self.transform_settings}.poutUpperTranslate", f"{tz_mult}.input[1]")
                else:
                    cmds.connectAttr(f"{self.transform_settings}.poutLowerTranslate", f"{tz_mult}.input[1]")


                cmds.connectAttr(f"{tz_mult}.output", f"{pout_compose}.inputTranslateZ")

                rx_mult = cmds.createNode("multiply", n=f"{side}_{main_mid_name}LipPoutRX_{count}_MUL")
                cmds.connectAttr(f"{pout_driver}.output", f"{rx_mult}.input[0]")
                # value_rotate = 2.0 if main_mid_name == "upper" else -0.2
                # cmds.setAttr(f"{rx_mult}.input[1]", value_rotate)
                if main_mid_name == "upper":
                    cmds.connectAttr(f"{self.transform_settings}.poutUpperRotate", f"{rx_mult}.input[1]")
                else:
                    cmds.connectAttr(f"{self.transform_settings}.poutLowerRotate", f"{rx_mult}.input[1]")
                cmds.connectAttr(f"{rx_mult}.output", f"{pout_compose}.inputRotateX")


                if z == len(curve_original_cvs)//2:
                    side = "C"
                    count = 0
                elif z < len(curve_original_cvs)//2:
                    side = "R"
                    count = count + 1
                else:
                    side = "L"
                    count = count - 1

                pos = cmds.pointPosition(cv, w=True)
                u, v = core.getClosestParamsToPositionSurface(lips_surface, pos)

                cmds.setAttr(f"{uv_pin_cvs}.coordinate[{z}].coordinateU", u)
                cmds.setAttr(f"{uv_pin_cvs}.coordinate[{z}].coordinateV", v)

                cmds.setAttr(f"{uv_pin_cvs_up}.coordinate[{z}].coordinateU", u)
                cmds.setAttr(f"{uv_pin_cvs_up}.coordinate[{z}].coordinateV", v)

                aimmatrix = cmds.createNode("aimMatrix", name=f"{side}_{main_mid_name}LipProjected0{count}_AMX", ss=True)
                cmds.connectAttr(f"{uv_pin_cvs}.outputMatrix[{z}]", f"{aimmatrix}.inputMatrix")
                cmds.connectAttr(f"{uv_pin_cvs}.outputMatrix[{z}]", f"{aimmatrix}.primaryTargetMatrix")
                cmds.setAttr(f"{aimmatrix}.primaryInputAxis", 0,0,1)
                cmds.setAttr(f"{aimmatrix}.primaryTargetVector", 0,0,1)
                cmds.setAttr(f"{aimmatrix}.primaryMode", 2)

                cmds.connectAttr(f"{uv_pin_cvs_up}.outputMatrix[{z}]", f"{aimmatrix}.secondaryTargetMatrix")
                cmds.setAttr(f"{aimmatrix}.secondaryInputAxis", 0,1,0)
                cmds.setAttr(f"{aimmatrix}.secondaryMode", 1)

                multmatrix = cmds.createNode("multMatrix", name=f"{side}_{main_mid_name}Lip0{count}_MMX", ss=True)
                point_pos = cmds.pointPosition(cv, w=True)

                point_matrix = (1, 0, 0, 0,
                                0, 1, 0, 0,
                                0, 0, 1, 0,
                                point_pos[0], point_pos[1], point_pos[2], 1)
                point_mmatrix = om.MMatrix(point_matrix)
                
                raw_matrix = cmds.getAttr(f"{aimmatrix}.outputMatrix")
                m_matrix = om.MMatrix(raw_matrix)
                offset = point_mmatrix * m_matrix.inverse()

                cmds.setAttr(f"{multmatrix}.matrixIn[0]", list(offset), type="matrix")

                # if compose:
                cmds.connectAttr(f"{pout_compose}.outputMatrix", f"{multmatrix}.matrixIn[1]")
                cmds.connectAttr(f"{aimmatrix}.outputMatrix", f"{multmatrix}.matrixIn[2]")
                # else:
                #     cmds.connectAttr(f"{aimmatrix}.outputMatrix", f"{multmatrix}.matrixIn[1]")




                joint = cmds.createNode("joint", name=f"{side}_{main_mid_name}Lip0{count}_JNT", ss=True, parent=self.skinning_trn)

                cmds.connectAttr(f"{multmatrix}.matrixSum", f"{joint}.offsetParentMatrix", force=True)
                temp_matrix_ends.append(f"{joint}")


                if side == "C":
                    count = z+1

            if temp_matrix_ends:
                matrix_ends.insert(curve_index, temp_matrix_ends)
                temp_matrix_ends = []


        
        lower_joints = matrix_ends[0]
        upper_joints = matrix_ends[1]


        sticky_driver = f"{self.jaw_ctl}.stickyLips"
        
        num_joints = len(upper_joints)
        mid_index = (num_joints - 1) / 2.0

        height_rev = cmds.createNode("reverse", n=f"C_jawMouthHeight_REV")
        cmds.connectAttr(f"{self.jaw_ctl}.mouthHeight", f"{height_rev}.inputX")
        
        for i, (up_jnt, low_jnt) in enumerate(zip(upper_joints, lower_joints)):
            
            name = up_jnt.replace("_JNT", "").replace("upper", "sticky").replace("lower", "sticky")

            input_connection_up = cmds.listConnections(f"{up_jnt}.offsetParentMatrix", source=True, destination=False, plugs=True)[0]
            input_connection_down = cmds.listConnections(f"{low_jnt}.offsetParentMatrix", source=True, destination=False, plugs=True)[0]
           
            wt_add = cmds.createNode("wtAddMatrix", n=f"{name}_WAM")
            cmds.connectAttr(f"{input_connection_up}", f"{wt_add}.wtMatrix[0].matrixIn")
            cmds.connectAttr(f"{input_connection_down}", f"{wt_add}.wtMatrix[1].matrixIn")

            cmds.connectAttr(f"{self.jaw_ctl}.mouthHeight", f"{wt_add}.wtMatrix[0].weightIn")
            cmds.connectAttr(f"{height_rev}.outputX", f"{wt_add}.wtMatrix[1].weightIn")

            dist_from_center = abs(i - mid_index)
            t = 1.0 - (dist_from_center / mid_index)
            t = max(0.0, min(1.0, t))
      
            start_threshold = t * 0.7

            for attr, joint in zip([up_jnt, low_jnt], [input_connection_up, input_connection_down]):

                name_joint = joint.split(".")[0].replace("_MMX", "")

                blend_node_up = cmds.createNode("blendMatrix", n=f"{name_joint}_BM")
                
                cmds.connectAttr(f"{joint}", f"{blend_node_up}.inputMatrix", force=True)
                cmds.connectAttr(f"{wt_add}.matrixSum", f"{blend_node_up}.target[0].targetMatrix")
                
                                
                remap = cmds.createNode("remapValue", n=f"{name_joint}StickyFalloff__RMV")
                cmds.connectAttr(sticky_driver, f"{remap}.inputValue")
                
                sum = cmds.createNode("sum", n=f"{name_joint}Falloff_SUM")
                cmds.setAttr(f"{sum}.input[0]", start_threshold)
                cmds.connectAttr(f"{self.jaw_ctl}.stickyFalloff", f"{sum}.input[1]")
                
                cmds.connectAttr(f"{sum}.output", f"{remap}.inputMax")
                
                cmds.setAttr(f"{remap}.outputMin", 0)
                cmds.setAttr(f"{remap}.outputMax", 1)
   
                
                cmds.connectAttr(f"{remap}.outValue", f"{blend_node_up}.target[0].weight")

                cmds.connectAttr(f"{blend_node_up}.outputMatrix", f"{attr}.offsetParentMatrix", force=True)

                
            
