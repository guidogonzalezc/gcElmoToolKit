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
from elmoTools.utils import de_boor_core_002
from elmoTools.utils.space_switch import fk_switch

reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class EyeModule():
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
        self.head_ctl = self.data_exporter.get_data("C_neckModule", "head_ctl")




    def make(self, guide_name):
        """
        Creates the neck module, including the neck chain, controllers, and various systems.

        Args:
            self: Instance of the NeckModule class.
        """

        self.guide_name = guide_name

        self.side = self.guide_name.split("_")[0]

        if self.side == "L":
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["z"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-x"])
        else:
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["-z"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-x"])

        self.eye_centered = True # Change if you dont want a centered eye controller

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_eyeModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyeControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.tangent_controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyeTangentControllers_GRP", ss=True, parent=self.controllers_trn)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_eyeFacialSkinning_GRP", ss=True, p=self.skel_grp)

        parentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_eyeModule_PM", ss=True)
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
        offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
        cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)

        self.create_chain()

        self.data_exporter.append_data(f"{self.side}_eyeModule", 
                                    {"skinning_transform": self.skinning_trn,
                                    "eyeMain": self.eye_main_ctl,

                                    }
                                  )
            
    def curve_attachment(self, name, curve_shape, u_value):

        point_on_surface = cmds.createNode("pointOnCurveInfo", name=f"{name}_POCI", ss=True)
        cmds.setAttr(f"{point_on_surface}.parameter", u_value)

        cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{point_on_surface}.inputCurve", force=True)

        matrix_node = cmds.createNode('fourByFourMatrix', name=f"{name}_FBF", ss=True)

        self.eye_rotation_4b4(matrix_node)

        cmds.connectAttr(f"{point_on_surface}.positionX", f"{matrix_node}.in30", force=True)
        cmds.connectAttr(f"{point_on_surface}.positionY", f"{matrix_node}.in31", force=True)
        cmds.connectAttr(f"{point_on_surface}.positionZ", f"{matrix_node}.in32", force=True)

        pickMatrix = cmds.createNode("pickMatrix", name=f"{name}_PMX", ss=True)
        cmds.connectAttr(f"{matrix_node}.output", f"{pickMatrix}.inputMatrix", force=True)
        cmds.setAttr(f"{pickMatrix}.useScale", 0)
        cmds.setAttr(f"{pickMatrix}.useShear", 0)

        return pickMatrix

    def eye_rotation_4b4(self, four_by_four):
        reshaped_matrix = [self.eyelid_rotation_matrix[i:i+4] for i in range(0, len(self.eyelid_rotation_matrix), 4)]
        for row in range(4):
            for col in range(4):
                cmds.setAttr(f"{four_by_four}.in{row}{col}", reshaped_matrix[row][col])

    def socket_local(self, grp, off, multmatrix_name):
        parentMatrix = cmds.createNode("parentMatrix", name=f"{multmatrix_name.replace('_MMX', '')}_PMX", ss=True)
        cmds.connectAttr(f"{grp}.worldMatrix[0]", f"{parentMatrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{multmatrix_name}.matrixSum", f"{parentMatrix}.target[0].targetMatrix", force=True)
        
        cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", get_offset_matrix(grp, f"{multmatrix_name}.matrixSum"), type="matrix")

        multmatrix = cmds.createNode("multMatrix", name=f"{multmatrix_name.replace('_MMX', 'Offset_MMX')}", ss=True)
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{multmatrix}.matrixIn[0]", force=True)
        cmds.connectAttr(f"{grp}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{off}.offsetParentMatrix", force=True)

    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.curve_guides = []
        self.guides_transforms = []
        for guides in self.guides:
            shape = cmds.listRelatives(guides, shapes=True)[0] if cmds.listRelatives(guides, shapes=True) else None
            if shape and cmds.objectType(shape) == "nurbsCurve":
                self.curve_guides.append(guides)
            else:
                self.guides_transforms.append(guides)

        self.eyelid_rotation = cmds.createNode("aimMatrix", name=f"{self.side}_eyelidRotation_AMX", ss=True)

        temp_curves = ["", ""]
        for item in self.curve_guides:
            if "upper" in item.lower():
                temp_curves[1] = item
            elif "lower" in item.lower():
                temp_curves[0] = item
        self.curve_guides = temp_curves

        self.eye_direct_ctl, self.eye_direct_ctl_grp = controller_creator(
                    name=f"{self.side}_eyeDirect",
                    suffixes=["GRP", "OFF", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )

        cmds.connectAttr(f"{self.guides_transforms[0]}.worldMatrix[0]", f"{self.eyelid_rotation}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.guides_transforms[1]}.worldMatrix[0]", f"{self.eyelid_rotation}.primaryTargetMatrix", force=True)
        cmds.setAttr(f"{self.eyelid_rotation}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryTargetVector", 0, 0, 1, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryMode", 2)

        if self.side == "R":

            multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyelidRotation_MMX", ss=True)
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, type="matrix")
            cmds.connectAttr(f"{self.eyelid_rotation}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)

            self.eyelid_rotation = f"{multmatrix}.matrixSum"
        else:
            self.eyelid_rotation = f"{self.eyelid_rotation}.outputMatrix"
            


        self.eyelid_rotation_matrix = cmds.getAttr(self.eyelid_rotation)
        cmds.connectAttr(self.eyelid_rotation, f"{self.eye_direct_ctl_grp[0]}.offsetParentMatrix", force=True)

        cmds.addAttr(self.eye_direct_ctl, shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.eye_direct_ctl+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="blinkHeight", niceName="Blink Height",minValue=0,defaultValue=0.2, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="upperBlink", niceName="Upper Blink",minValue=-1,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="lowerBlink", niceName="Lower Blink",minValue=-1,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="fleshy", niceName="Fleshy",minValue=0,defaultValue=0.1, maxValue = 1, keyable=True)
        cmds.addAttr(self.eye_direct_ctl, shortName="fleshyCorners", niceName="Fleshy Corners",minValue=0,defaultValue=0, maxValue = 1, keyable=True)

        four_by_fours_in_out = []
        blend_matrix_in_out = []
        self.main_ctls = []
        self.main_ctls_grps = []
        for name, item in zip(["Inner", "Outer"], [0, len(cmds.ls(f"{self.curve_guides[0]}.cv[*]", fl=True)) - 1]):

            four_by_four = cmds.createNode("fourByFourMatrix", name=f"{self.side}_eyelid{name}Pos_F4X", ss=True)
            self.eye_rotation_4b4(four_by_four)
            cmds.setAttr(f"{four_by_four}.in30", cmds.pointPosition(f"{self.curve_guides[0]}.cv[{item}]")[0])
            cmds.setAttr(f"{four_by_four}.in31", cmds.pointPosition(f"{self.curve_guides[0]}.cv[{item}]")[1])
            cmds.setAttr(f"{four_by_four}.in32", cmds.pointPosition(f"{self.curve_guides[0]}.cv[{item}]")[2])
            four_by_fours_in_out.append(four_by_four)

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}EyelidCorner",
                suffixes=["GRP", "OFF", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn
            )
            self.main_ctls.append(ctl)
            self.main_ctls_grps.append(controller_grp)

            cmds.connectAttr(f"{four_by_four}.output", f"{controller_grp[0]}.offsetParentMatrix", force=True)

        corner_joints = []
        for ctl, grp in zip(self.main_ctls, self.main_ctls_grps):
            curve_skinning_joint = cmds.createNode("joint", name=ctl.replace("_CTL", "_JNT"), ss=True, p=self.module_trn)

            local_mmx = core.local_mmx(ctl, grp[0])

            cmds.connectAttr(f"{local_mmx}", f"{curve_skinning_joint}.offsetParentMatrix", force=True)
            corner_joints.append(curve_skinning_joint)

        rebuilded_curves = []

        for curve in self.curve_guides:
            rebuild_curve = cmds.rebuildCurve(curve, name=curve.replace("Curve_GUIDE", "_CRV") ,ch=False, rpo=False, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=4, d=3)[0]
            cmds.parent(rebuild_curve, self.module_trn)
            rebuilded_curves.append(rebuild_curve)
        
        blink_ref = cmds.duplicate(rebuilded_curves[0], n=f"{self.side}_blinkRef_CRV") # Tabula esto para Oswald

        blink_ref_bls = cmds.blendShape(rebuilded_curves[1], blink_ref, n=f"{self.side}_blinkHeight_BLS")[0]

        cmds.connectAttr(self.eye_direct_ctl+".blinkHeight", f"{blink_ref_bls}.weight[0]")

        negative_curves = []
        for i, curve in enumerate(rebuilded_curves):
            negative_blink_curve = cmds.duplicate(curve, n=curve.replace("_CRV", f"NegativeBlinkRef_CRV"))
            value = 0 if i != 0 else 1
            bls_tmp = cmds.blendShape(rebuilded_curves[value], negative_blink_curve, n=curve.replace("_CRV", f"NegativeBlinkRef_BLS"))[0]
            cmds.setAttr(f"{bls_tmp}.weight[0]", -1)
            cmds.delete(negative_blink_curve, constructionHistory=True)
            negative_curves.append(negative_blink_curve)

        blink_end_curves = []
        bls_name = []

        for i, curves in enumerate(rebuilded_curves):
            name = curves.replace("_CRV", f"Blink")
            blink_curve = cmds.duplicate(curves, n=curves.replace("_CRV", f"Blink_CRV"))[0]

            blink_bls = cmds.blendShape(blink_ref, curves, negative_curves[i], blink_curve, n=f"{name}_BLS")[0]

            attr = "upperBlink" if "upper" in curves.lower() else "lowerBlink"

            clamp = cmds.createNode("clamp", n=f"{name}_CLP")
            rev = cmds.createNode("reverse", n=f"{name}_REV")
            flm = cmds.createNode("floatMath", n=f"{name}_FLM")
            cmds.connectAttr(f"{self.eye_direct_ctl}.{attr}", clamp+".inputR")
            cmds.connectAttr(f"{self.eye_direct_ctl}.{attr}", clamp+".inputG")
            cmds.setAttr(clamp+".minG", -1)
            cmds.setAttr(clamp+".maxR", 1)
            cmds.connectAttr(clamp+".outputR", f"{blink_bls}.weight[0]")
            cmds.connectAttr(clamp+".outputR", f"{rev}.inputX")
            cmds.connectAttr(rev+".outputX", f"{blink_bls}.weight[1]")
            cmds.connectAttr(clamp+".outputG", f"{flm}.floatA")
            cmds.setAttr(flm+".operation", 2)
            cmds.setAttr(flm+".floatB", -1)
            cmds.connectAttr(flm+".outFloat", f"{blink_bls}.weight[2]")

            blink_end_curves.append(blink_curve)
            bls_name.append(blink_bls)

        # Fleshy Sockets

        mmtx = cmds.createNode("multMatrix", n=f"{self.side}_fleshySockets_MMT", ss=True)
        cmds.connectAttr(self.eye_direct_ctl + ".worldMatrix[0]", mmtx + ".matrixIn[0]")
        cmds.connectAttr(self.eye_direct_ctl_grp[0] + ".worldInverseMatrix[0]", mmtx + ".matrixIn[1]")

        dcmp = cmds.createNode("decomposeMatrix", n=f"{self.side}_fleshySockets_DMP", ss=True)
        cmds.connectAttr(mmtx + ".matrixSum", dcmp + ".inputMatrix")

        mult = cmds.createNode("multiply", n=f"{self.side}_fleshySockets_MLT", ss=True)
        cmds.connectAttr(self.eye_direct_ctl + ".fleshy", mult + ".input[0]")
        cmds.connectAttr(self.eye_direct_ctl + ".fleshyCorners", mult + ".input[1]")

        blc01 = cmds.createNode("blendColors", n=f"{self.side}_fleshySockets01_BLC", ss=True)
        cmds.connectAttr(mult + ".output", blc01 + ".blender")
        cmds.connectAttr(dcmp + ".outputRotateX", blc01 + ".color1R")
        cmds.connectAttr(dcmp + ".outputRotateY", blc01 + ".color1G")

        blc02 = cmds.createNode("blendColors", n=f"{self.side}_fleshySockets02_BLC", ss=True)
        cmds.connectAttr(self.eye_direct_ctl + ".fleshy", blc02 + ".blender")
        cmds.connectAttr(dcmp + ".outputRotateX", blc02 + ".color1R")
        cmds.connectAttr(dcmp + ".outputRotateY", blc02 + ".color1G")

        for attr in ["color1B", "color2B", "color2R", "color2G"]:
            cmds.setAttr(blc01 + "." + attr, 0)
            cmds.setAttr(blc02 + "." + attr, 0)

        compose01 = cmds.createNode("composeMatrix", n=f"{self.side}_fleshySockets01_CMP", ss=True) # Corners
        cmds.connectAttr(blc01 + ".output", compose01 + ".inputRotate")

        compose02 = cmds.createNode("composeMatrix", n=f"{self.side}_fleshySockets02_CMP", ss=True) # Mid
        cmds.connectAttr(blc02 + ".output", compose02 + ".inputRotate")

        multMatrix01 = cmds.createNode("multMatrix", n=f"{self.side}_fleshySocketsIniPos_MMX", ss=True)
        cmds.connectAttr(f"{compose01}.outputMatrix", f"{multMatrix01}.matrixIn[0]", force=True)
        cmds.connectAttr(self.eyelid_rotation, f"{multMatrix01}.matrixIn[1]", force=True)

        multMatrix02 = cmds.createNode("multMatrix", n=f"{self.side}_fleshySocketsMidPos_MMX", ss=True)
        cmds.connectAttr(f"{compose02}.outputMatrix", f"{multMatrix02}.matrixIn[0]", force=True)
        cmds.connectAttr(self.eyelid_rotation, f"{multMatrix02}.matrixIn[1]", force=True)

        self.socket_local(self.main_ctls_grps[0][0], self.main_ctls_grps[0][1], multMatrix01)
        self.socket_local(self.main_ctls_grps[1][0], self.main_ctls_grps[1][1], multMatrix01)

        # cmds.connectAttr(compose02 + ".outputMatrix", self.main_ctls_grps[0][1] + ".offsetParentMatrix", force=True)
        # cmds.connectAttr(compose02 + ".outputMatrix", self.main_ctls_grps[1][1] + ".offsetParentMatrix", force=True)
        self.eye_main()

        for index_main, curve in enumerate(rebuilded_curves):
         
            four_by_four_mid = cmds.createNode("fourByFourMatrix", name=curve.replace("_CRV", f"Middle_F4X"), ss=True)

            pos = core.getClosestParamToWorldMatrixCurve(curve = curve, pos = cmds.pointPosition(f"{curve}.cv[{3}]"), point=True)

            self.eye_rotation_4b4(four_by_four_mid)

            cmds.setAttr(f"{four_by_four_mid}.in30", pos[0])
            cmds.setAttr(f"{four_by_four_mid}.in31", pos[1])
            cmds.setAttr(f"{four_by_four_mid}.in32", pos[2])

            mid_ctl, mid_controller_grp = controller_creator(
                    name=f"{curve.replace('_CRV', 'Mid')}",
                    suffixes=["GRP", "OFF","ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )
            cmds.connectAttr(f"{four_by_four_mid}.output", f"{mid_controller_grp[0]}.offsetParentMatrix", force=True)

            # cmds.connectAttr(compose01 + ".outputMatrix", mid_controller_grp[1] + ".offsetParentMatrix", force=True)
            self.socket_local(mid_controller_grp[0], mid_controller_grp[1], multMatrix02)


           
            joint_skinning_joints = []

            for i, cv_index in enumerate([2, 3, 4]): # 3 6 9
                ctl, controller_grp = controller_creator(
                    name=f"{curve.replace('_CRV', f'Secondary0{i+1}')}",
                    suffixes=["GRP", "OFF","ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.controllers_trn
                )

                four_by_four_mid = cmds.createNode("fourByFourMatrix", name=curve.replace("_CRV", f"Middle_F4X"), ss=True)

                pos = core.getClosestParamToWorldMatrixCurve(curve = curve, pos = cmds.pointPosition(f"{curve}.cv[{cv_index}]"), point=True)

                self.eye_rotation_4b4(four_by_four_mid)

                cmds.setAttr(f"{four_by_four_mid}.in30", pos[0])
                cmds.setAttr(f"{four_by_four_mid}.in31", pos[1])
                cmds.setAttr(f"{four_by_four_mid}.in32", pos[2])

                cmds.connectAttr(f"{four_by_four_mid}.output", f"{controller_grp[0]}.offsetParentMatrix", force=True)

                if cv_index == 2: # 3
                    multmatrix = core.local_space_parent(ctl, parents=[self.main_ctls[0], mid_ctl], default_weights=0.8)
                elif cv_index == 4: # 9
                    multmatrix = core.local_space_parent(ctl, parents=[self.main_ctls[1], mid_ctl], default_weights=0.8)
                else:
                    multmatrix = cmds.createNode("multMatrix", name=f"{curve.replace('_CRV', f'Secondary0{i+1}')}localSpaceParent_MMX", ss=True)
                    cmds.connectAttr(f"{mid_ctl}.worldMatrix[0]", f"{multmatrix}.matrixIn[0]", force=True)
                    cmds.connectAttr(f"{controller_grp[0]}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
                    cmds.connectAttr(f"{multmatrix}.matrixSum", f"{controller_grp[1]}.offsetParentMatrix", force=True)

                curve_skinning_joint = cmds.createNode("joint", name=ctl.replace("_CTL", f"CurveSkinning_JNT"), ss=True, parent=self.module_trn)

                local_mmx = core.local_mmx(ctl, controller_grp[0])

                cmds.connectAttr(f"{local_mmx}", f"{curve_skinning_joint}.offsetParentMatrix", force=True)

                joint_skinning_joints.append(curve_skinning_joint)

                if i == 2:
                    skinCluster = cmds.skinCluster(joint_skinning_joints, corner_joints, curve, n=curve.replace("_CRV", "_SKC"), toSelectedBones=True, maximumInfluences=1, normalizeWeights=1)[0]
                    cmds.skinPercent(skinCluster, f"{curve}.cv[1]", transformValue=(joint_skinning_joints[0], 0.5))
                    cmds.skinPercent(skinCluster, f"{curve}.cv[5]", transformValue=(joint_skinning_joints[-1], 0.5))

            for i, cv in enumerate(cmds.ls(f"{self.curve_guides[index_main]}.cv[*]", fl=True)):
                name = f"{cv.split('.')[0].replace('Curve_GUIDE', 'Aim')}0{i+1}"
                pick = self.curve_attachment(name=name, curve_shape=blink_end_curves[index_main], u_value=core.getClosestParamToWorldMatrixCurve(curve=blink_end_curves[index_main], pos=cmds.pointPosition(cv)))
                aim_matrix = cmds.createNode("aimMatrix", name=f"{name}_AMX", ss=True)
                cmds.connectAttr(f"{self.guides_transforms[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix", force=True)
                cmds.connectAttr(f"{pick}.outputMatrix", f"{aim_matrix}.primaryTargetMatrix", force=True)
                cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")
                cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")

                value = (0, 0, 1) if self.side == "L" else (0, 0, -1)

                cmds.setAttr(f"{aim_matrix}.secondaryTargetVector", *value, type="double3")
                cmds.setAttr(f"{aim_matrix}.secondaryMode", 0)

                multmatrix = cmds.createNode("multMatrix", name=f"{name}_MMX", ss=True)
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)

                fourbyfour = cmds.createNode("fourByFourMatrix", name=f"{name}_F4X", ss=True)
                dist = (om.MVector(*cmds.xform(self.guides_transforms[0], q=1, ws=1, t=1)) - om.MVector(*cmds.xform(cv, q=1, ws=1, t=1))).length()
                cmds.setAttr(f"{fourbyfour}.in32", dist if self.side == "L" else -dist)
                cmds.connectAttr(f"{fourbyfour}.output", f"{multmatrix}.matrixIn[0]", force=True)
                name_joint = name.replace("Aim","")
                joint = cmds.createNode("joint", name=f"{name_joint}_JNT", ss=True, parent=self.skinning_trn)

                cmds.connectAttr(f"{multmatrix}.matrixSum", f"{joint}.offsetParentMatrix", force=True)
        

    def eye_main(self):

        reverse_side = "R" if self.side == "L" else "L"

        self.eye_main_ctl = self.data_exporter.get_data(f"{reverse_side}_eyeModule", "eyeMain")

        if not self.eye_main_ctl and self.eye_centered:
            self.eye_main_ctl, self.eye_main_ctl_grp = controller_creator(
                name=f"C_eyeMain",
                suffixes=["GRP", "OFF","ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.masterWalk_ctl
            )

            cmds.matchTransform(self.eye_main_ctl_grp[0], self.guides_transforms[0])
            cmds.setAttr(f"{self.eye_main_ctl_grp[0]}.tx", 0)
            cmds.move(0, 0, 20, self.eye_main_ctl_grp[0], r=True, ws=False)

        ctl, controller_grp = controller_creator(
            name=f"{self.side}_eye",
            suffixes=["GRP", "OFF","ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            # parent=self.controllers_trn
        )

        cmds.connectAttr(f"{self.guides_transforms[0]}.worldMatrix[0]", f"{controller_grp[0]}.offsetParentMatrix", force=True)
        
        if not core.DataManager.get_asset_name() == "moana":
            cmds.move(20, 0, 0, controller_grp[0], r=True, ws=False)
        else:
            cmds.move(0, 0, 20, controller_grp[0], r=True, ws=False)
        
        cmds.parent(controller_grp[0], self.eye_main_ctl if self.eye_main_ctl else self.masterWalk_ctl)

        aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_eyeMain_AMX", ss=True)
        cmds.connectAttr(self.eyelid_rotation, f"{aim_matrix}.inputMatrix", force=True)

        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix", force=True)
        if self.side == "L":
            primary_vector = self.primary_aim_vector
        else:
            primary_vector = (-self.primary_aim_vector.x, -self.primary_aim_vector.y, -self.primary_aim_vector.z)

        cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *primary_vector, type="double3")
        cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")

        multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyeMain_MMX", ss=True)
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{multmatrix}.matrixIn[0]", force=True)
        cmds.connectAttr(f"{self.eye_direct_ctl_grp[0]}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)

        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{self.eye_direct_ctl_grp[1]}.offsetParentMatrix", force=True)

        eye_joint = cmds.createNode("joint", name=f"{self.side}_eye_JNT", ss=True, parent=self.skinning_trn)

        local_mmx = core.local_mmx(self.eye_direct_ctl, self.eye_direct_ctl_grp[0])

        cmds.connectAttr(f"{local_mmx}", f"{eye_joint}.offsetParentMatrix", force=True)

        cmds.reorder(eye_joint, front=True)
