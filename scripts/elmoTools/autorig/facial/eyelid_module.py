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


reload(data_export)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class EyelidModule():
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

        self.guide_name = guide_name

        self.side = self.guide_name.split("_")[0]

        if self.side == "L":
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["x"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["y"])
        else:
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["-x"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-y"])


        self.module_trn = cmds.createNode("transform", name=f"{self.side}_eyelidModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyelidControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)
        self.tangent_controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyelidTangentControllers_GRP", ss=True, parent=self.controllers_trn)

        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_eyelidFacialSkinning_GRP", ss=True, p=self.skel_grp)

        try:
            parentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_eyelidModule_PM", ss=True)
            cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
            offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
            cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
            cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)
        except:
            pass

        self.create_chain()

        self.data_exporter.append_data(f"{self.side}_eyeModule", 
                            {"skinning_transform": self.skinning_trn,
                            "eyeMain": self.eye_main_ctl,

                            }
                            )

        # cmds.setAttr(f"C_preferences_CTL.showModules", 1)

    def socket_local(self, grp, off, multmatrix_name):
        parentMatrix = cmds.createNode("parentMatrix", name=f"{multmatrix_name.replace('_MMX', '')}_PMX", ss=True)
        cmds.connectAttr(f"{grp}.worldMatrix[0]", f"{parentMatrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{multmatrix_name}.matrixSum", f"{parentMatrix}.target[0].targetMatrix", force=True)
        
        cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", get_offset_matrix(grp, f"{multmatrix_name}.matrixSum"), type="matrix")

        multmatrix = cmds.createNode("multMatrix", name=f"{multmatrix_name.replace('_MMX', 'Offset_MMX')}", ss=True)
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{multmatrix}.matrixIn[0]", force=True)
        cmds.setAttr(f"{multmatrix}.matrixIn[1]", cmds.getAttr(f"{grp}.worldInverseMatrix[0]"), type="matrix")
        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{off}.offsetParentMatrix", force=True)

        return parentMatrix

    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.eye = self.guides[0]

        self.eyeEnd = None
        self.curves = [None, None]

        for guide in self.guides:
            shape = cmds.listRelatives(guide, shapes=True)
            if shape:
                if cmds.objectType(shape[0]) == "nurbsCurve":
                    if "upper" in guide.lower():
                        self.curves[0] = guide
                    elif "lower" in guide.lower():
                        self.curves[1] = guide
            else:
                self.eyeEnd = guide

        self.eyelid_rotation = cmds.createNode("aimMatrix", name=f"{self.side}_eyelidRotation_AMX", ss=True)

        cvs = cmds.ls(f"{self.curves[0]}.cv[*]", fl=True)

        pos = cmds.pointPosition(cvs[0], world=True)

        corner_01_fbf = cmds.createNode("fourByFourMatrix", name=f"{self.side}_eyelid01CornerGuide_F4X", ss=True)
        cmds.setAttr(f"{corner_01_fbf}.in30", pos[0])
        cmds.setAttr(f"{corner_01_fbf}.in31", pos[1])
        cmds.setAttr(f"{corner_01_fbf}.in32", pos[2])

        pos = cmds.pointPosition(cvs[-1], world=True)

        corner_02_fbf = cmds.createNode("fourByFourMatrix", name=f"{self.side}_eyelid02CornerGuide_F4X", ss=True)
        cmds.setAttr(f"{corner_02_fbf}.in30", pos[0])
        cmds.setAttr(f"{corner_02_fbf}.in31", pos[1])
        cmds.setAttr(f"{corner_02_fbf}.in32", pos[2])


        cmds.connectAttr(f"{corner_01_fbf}.output", f"{self.eyelid_rotation}.inputMatrix", force=True)
        cmds.connectAttr(f"{corner_02_fbf}.output", f"{self.eyelid_rotation}.primaryTargetMatrix", force=True)
        cmds.setAttr(f"{self.eyelid_rotation}.primaryInputAxis", *self.primary_aim_vector, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryTargetVector", 0, 1, 0, type="double3")
        cmds.setAttr(f"{self.eyelid_rotation}.secondaryMode", 2)

        if self.side == "R":

            multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyelidRotation_MMX", ss=True)
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1, type="matrix")
            cmds.connectAttr(f"{self.eyelid_rotation}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)

            self.eyelid_rotation = f"{multmatrix}.matrixSum"
        else:
            self.eyelid_rotation = f"{self.eyelid_rotation}.outputMatrix"   
            


        self.eyelid_rotation_matrix = cmds.getAttr(self.eyelid_rotation)

        self.main_ctl, self.main_ctl_grp = controller_creator(
                name=f"{self.side}_eyeDirect",
                suffixes=["GRP", "OFF","ANM"],
                lock=["sz", "sy", "sx", "visibility"],
                ro=False,
                parent= self.controllers_trn
            )
        
        
        
        cmds.addAttr(self.main_ctl, shortName="extraSep", niceName="EXTRA_____", enumName="_____",attributeType="enum", keyable=True)
        cmds.setAttr(self.main_ctl+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(self.main_ctl, shortName="blinkHeight", niceName="Blink Height",minValue=0,defaultValue=0.2, maxValue = 1, keyable=True)
        cmds.addAttr(self.main_ctl, shortName="upperBlink", niceName="Upper Blink",minValue=-1,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.main_ctl, shortName="lowerBlink", niceName="Lower Blink",minValue=-1,defaultValue=0, maxValue = 1, keyable=True)
        cmds.addAttr(self.main_ctl, shortName="fleshy", niceName="Fleshy",minValue=0,defaultValue=0.1, maxValue = 1, keyable=True)
        cmds.addAttr(self.main_ctl, shortName="fleshyCorners", niceName="Fleshy Corners",minValue=0,defaultValue=0, maxValue = 1, keyable=True)
        
        self.eyeDirect_blm = cmds.createNode("blendMatrix", n=f"{self.side}_eyeDirect_BLM")
        cmds.connectAttr(f"{self.eye}.worldMatrix[0]", f"{self.eyeDirect_blm}.inputMatrix")

        # cmds.connectAttr(f"{self.eyelid_rotation}", f"{self.eyeDirect_blm}.target[0].targetMatrix", force=True)
        # cmds.setAttr(f"{self.eyeDirect_blm}.target[0].translateWeight", 0)
        # cmds.connectAttr(f"{self.eyeDirect_blm}.outputMatrix", f"{self.main_ctl_grp[0]}.offsetParentMatrix", force=True)

        if self.side == "L":
            cmds.connectAttr(f"{self.eye}.worldMatrix[0]", f"{self.main_ctl_grp[0]}.offsetParentMatrix", force=True)


        else:
            multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyeDirect_MMX", ss=True)
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", -1, 0, 0, 0,
                                            0, 1, 0, 0,
                                            0, 0, 1, 0,
                                            0, 0, 0, 1, type="matrix")
            cmds.connectAttr(f"{self.eye}.worldMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
            cmds.connectAttr( f"{multmatrix}.matrixSum", f"{self.main_ctl_grp[0]}.offsetParentMatrix", force=True)


        corner_aim = []
        corner_ctls = []
        corner_grps = []

        for name, item in zip(["Inner", "Outer"], [0, len(cmds.ls(f"{self.curves[0]}.cv[*]", fl=True)) - 1]):

            four_by_four = cmds.createNode("fourByFourMatrix", name=f"{self.side}_eyelid{name}Pos_F4X", ss=True)
            cmds.setAttr(f"{four_by_four}.in30", cmds.pointPosition(f"{self.curves[0]}.cv[{item}]")[0])
            cmds.setAttr(f"{four_by_four}.in31", cmds.pointPosition(f"{self.curves[0]}.cv[{item}]")[1])
            cmds.setAttr(f"{four_by_four}.in32", cmds.pointPosition(f"{self.curves[0]}.cv[{item}]")[2])

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}EyelidCorner",
                suffixes=["GRP", "OFF", "ANM"],
                lock=[ "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn
            )

            cmds.addAttr(ctl, shortName="tangents", niceName="Tangents ———", enumName="———",attributeType="enum", keyable=True)
            cmds.setAttr(ctl+".tangents", channelBox=True, lock=True)
            cmds.addAttr(ctl, shortName="tangentVisibility", niceName="Tangent Visibility", attributeType="bool", keyable=False)
            cmds.setAttr(ctl+".tangentVisibility", channelBox=True)

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{name}EyelidCorner_AMX", ss=True)
            cmds.connectAttr(f"{four_by_four}.output", f"{aim_matrix}.inputMatrix", force=True)
            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *self.primary_aim_vector, type="double3")

            if self.side == "L":
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{controller_grp[0]}.offsetParentMatrix", force=True)



            else:
                multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_{name}EyelidCorner_MMX", ss=True)
                cmds.setAttr(f"{multmatrix}.matrixIn[0]", -1, 0, 0, 0,
                                                0, 1, 0, 0,
                                                0, 0, 1, 0,
                                                0, 0, 0, 1, type="matrix")
                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)
                cmds.connectAttr( f"{multmatrix}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix", force=True)



            corner_aim.append(aim_matrix)
            corner_ctls.append(ctl)
            corner_grps.append(controller_grp)

        mid_pos_4b4 = []
        rebuilded_curves = []
        controllers = []
        for curve in self.curves:
            
            rebuilded = cmds.rebuildCurve(curve, ch=0, rpo=0, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=2, d=3, tol=0.01)[0]
            rebuilded = cmds.rename(rebuilded, curve.replace("Curve_GUIDE", "Bezier_CRV"))
            cmds.parent(rebuilded, self.module_trn)
            cmds.select(rebuilded, r=True)
            cmds.nurbsCurveToBezier()
            rebuilded_curves.append(rebuilded)

        blink_ref = cmds.duplicate(rebuilded_curves[1], n=f"{self.side}_blinkRef_CRV") # Tabula esto para Oswald

        # blink_ref_bls = cmds.blendShape(rebuilded_curves[0], rebuilded_curves[1], blink_ref, n=f"{self.side}_blinkHeight_BLS")[0]

        # cmds.connectAttr(self.main_ctl+".blinkHeight", f"{blink_ref_bls}.weight[0]")

        avg_curve = cmds.createNode("avgCurves", name=f"{self.side}_eyelidAvgCurve_AVC", ss=True)
        cmds.connectAttr(f"{rebuilded_curves[0]}.worldSpace[0]", f"{avg_curve}.inputCurve1", force=True)
        cmds.connectAttr(f"{rebuilded_curves[1]}.worldSpace[0]", f"{avg_curve}.inputCurve2", force=True)
        cmds.connectAttr(f"{avg_curve}.outputCurve", f"{blink_ref[0]}.create", force=True)
        cmds.connectAttr(self.main_ctl+".blinkHeight", f"{avg_curve}.weight1", force=True)
        reverse_blink_height = cmds.createNode("reverse", name=f"{self.side}_blinkHeight_REV", ss=True)
        cmds.connectAttr(self.main_ctl+".blinkHeight", f"{reverse_blink_height}.inputX", force=True)
        cmds.connectAttr(f"{reverse_blink_height}.outputX", f"{avg_curve}.weight2", force=True)
        cmds.setAttr(f"{avg_curve}.automaticWeight", 0)

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
        clamps = []

        for i, curves in enumerate(rebuilded_curves):
            name = curves.replace("_CRV", f"Blink")
            blink_curve = cmds.duplicate(curves, n=curves.replace("_CRV", f"Blink_CRV"))[0]

            blink_bls = cmds.blendShape(blink_ref, curves, negative_curves[i], blink_curve, n=f"{name}_BLS")[0]
            # blink_bls = cmds.blendShape(curves, negative_curves[i], blink_curve, n=f"{name}_BLS")[0]

            attr = "upperBlink" if "upper" in curves.lower() else "lowerBlink"

            clamp = cmds.createNode("clamp", n=f"{name}_CLP")
            rev = cmds.createNode("reverse", n=f"{name}_REV")
            flm = cmds.createNode("floatMath", n=f"{name}_FLM")
            cmds.connectAttr(f"{self.main_ctl}.{attr}", clamp+".inputR")
            cmds.connectAttr(f"{self.main_ctl}.{attr}", clamp+".inputG")
            cmds.setAttr(clamp+".minG", -1)
            cmds.setAttr(clamp+".maxR", 1)
            cmds.connectAttr(clamp+".outputR", f"{blink_bls}.weight[0]")
            cmds.connectAttr(clamp+".outputR", f"{rev}.inputX")
            cmds.connectAttr(rev+".outputX", f"{blink_bls}.weight[1]")
            cmds.connectAttr(clamp+".outputG", f"{flm}.floatA")
            cmds.setAttr(flm+".operation", 2)
            cmds.setAttr(flm+".floatB", -1)
            cmds.connectAttr(flm+".outFloat", f"{blink_bls}.weight[2]")
            clamps.append(clamp)
            blink_end_curves.append(blink_curve)
            bls_name.append(blink_bls)

        # Fleshy Sockets

        mmtx = cmds.createNode("multMatrix", n=f"{self.side}_fleshySockets_MMT", ss=True)
        cmds.connectAttr(self.main_ctl + ".worldMatrix[0]", mmtx + ".matrixIn[0]")
        cmds.connectAttr(self.main_ctl_grp[0] + ".worldInverseMatrix[0]", mmtx + ".matrixIn[1]")

        dcmp = cmds.createNode("decomposeMatrix", n=f"{self.side}_fleshySockets_DMP", ss=True)
        cmds.connectAttr(mmtx + ".matrixSum", dcmp + ".inputMatrix")

        mult = cmds.createNode("multiply", n=f"{self.side}_fleshySockets_MLT", ss=True)
        cmds.connectAttr(self.main_ctl + ".fleshy", mult + ".input[0]")
        cmds.connectAttr(self.main_ctl + ".fleshyCorners", mult + ".input[1]")

        blc01 = cmds.createNode("blendColors", n=f"{self.side}_fleshySockets01_BLC", ss=True)
        cmds.connectAttr(mult + ".output", blc01 + ".blender")
        cmds.connectAttr(dcmp + ".outputRotateX", blc01 + ".color1R")
        cmds.connectAttr(dcmp + ".outputRotateY", blc01 + ".color1G")

        blc02 = cmds.createNode("blendColors", n=f"{self.side}_fleshySockets02_BLC", ss=True)
        cmds.connectAttr(self.main_ctl + ".fleshy", blc02 + ".blender")
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
        self.fleshySocketMMX = multMatrix01

        self.fleshySocketMMXOuter = cmds.createNode("multMatrix", n=f"{self.side}_fleshySocketsIniPosOuter_MMX", ss=True)
        cmds.connectAttr(f"{compose01}.outputMatrix", f"{self.fleshySocketMMXOuter}.matrixIn[0]", force=True)


        self.middle_fleshy = compose02


        main_ctls = []
        main_ctls_grps = []
        controllers_parenting = []
        for index_curve, curve in enumerate(rebuilded_curves):
            clts = [corner_ctls[0]]
            ctls_grps = [corner_grps[0]]

            for i, cv in enumerate(cmds.ls(f"{self.curves[index_curve]}.cv[*]", fl=True)):
                suffix = "upper" if "upper" in self.curves[index_curve].lower() else "lower"
                name = f"{self.side}_{suffix}Eyelid0{i:01d}"
                pos = cmds.pointPosition(cv, world=True)

                linear_guide_4b4 = cmds.createNode("fourByFourMatrix", name=f"{name}InitPos_FBF", ss=True)
                

                parm_on_rebuilded = core.getClosestParamToWorldMatrixCurve(curve = curve, pos=pos)  

                pos_eye = cmds.xform(self.eye, q=True, ws=True, t=True)

                distance_eye_to_guide = math.sqrt((pos_eye[0]-pos[0])**2 + (pos_eye[1]-pos[1])**2 + (pos_eye[2]-pos[2])**2) 

                eyelid_aim = cmds.createNode("aimMatrix", name=f"{name}_AMX", ss=True)
                cmds.connectAttr(f"{self.eye}.worldMatrix[0]", f"{eyelid_aim}.inputMatrix", force=True)

                uv_pin = cmds.createNode("uvPin", name=f"{name}_UVP", ss=True)
                cmds.connectAttr(f"{blink_end_curves[index_curve]}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)
                cmds.setAttr(f"{uv_pin}.coordinate[0].coordinateU", parm_on_rebuilded)
                cmds.connectAttr(f"{uv_pin}.outputMatrix[0]", f"{eyelid_aim}.primaryTargetMatrix", force=True)
                cmds.setAttr(f"{eyelid_aim}.primaryInputAxis", 0,0,1, type="double3")

                fbf_distance = cmds.createNode("fourByFourMatrix", name=f"{name}Distance_FBF", ss=True)
                cmds.setAttr(f"{fbf_distance}.in32", distance_eye_to_guide)

                multmatrix_end_pox = cmds.createNode("multMatrix", name=f"{name}EndPos_MMX", ss=True)
                cmds.connectAttr(f"{eyelid_aim}.outputMatrix", f"{multmatrix_end_pox}.matrixIn[1]", force=True)
                cmds.connectAttr(f"{fbf_distance}.output", f"{multmatrix_end_pox}.matrixIn[0]", force=True)

                eye_matrix = cmds.getAttr(f"{multmatrix_end_pox}.matrixSum")

                reshaped_matrix = [eye_matrix[i:i+4] for i in range(0, len(eye_matrix), 4)]
                for row in range(4):
                    for col in range(4):
                        cmds.setAttr(f"{linear_guide_4b4}.in{row}{col}", reshaped_matrix[row][col])

                cmds.setAttr(f"{linear_guide_4b4}.in30", pos[0])
                cmds.setAttr(f"{linear_guide_4b4}.in31", pos[1])
                cmds.setAttr(f"{linear_guide_4b4}.in32", pos[2])

                parent_matrix = cmds.createNode("parentMatrix", name=f"{name}_PMX", ss=True)
                cmds.connectAttr(f"{linear_guide_4b4}.output", f"{parent_matrix}.inputMatrix", force=True)
                cmds.connectAttr(f"{multmatrix_end_pox}.matrixSum", f"{parent_matrix}.target[0].targetMatrix", force=True)
                cmds.setAttr(f"{parent_matrix}.target[0].offsetMatrix", get_offset_matrix(f"{linear_guide_4b4}.output", f"{multmatrix_end_pox}.matrixSum"), type="matrix")

                blink_blend_matrix = cmds.createNode("blendMatrix", name=f"{name}Blink_BMX", ss=True)

                cmds.connectAttr(f"{parent_matrix}.outputMatrix", f"{blink_blend_matrix}.inputMatrix", force=True)
                cmds.connectAttr(f"{multmatrix_end_pox}.matrixSum", f"{blink_blend_matrix}.target[0].targetMatrix", force=True)

                blink_attr = "lowerBlink" if "lower" in name.lower() else "upperBlink"
                cmds.connectAttr(f"{self.main_ctl}.{blink_attr}", f"{blink_blend_matrix}.target[0].weight", force=True)




                joint = cmds.createNode("joint", name=f"{name}_JNT", ss=True, parent=self.skinning_trn)
                cmds.connectAttr(f"{blink_blend_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", force=True) # CAMBIAR PARENT MATRIX O MULTMATRIX DEPENDIENDO SI QUIERES OFFSET O NO

            main_4b4 = []
            tan_4b4 = []
            all_4b4 = []

            if "upper" in curve.lower():
                suffix_name = "Upper"
            elif "lower" in curve.lower():
                suffix_name = "Lower"

            controllers = []
            curve_especific_main = []

            for i, cv in enumerate(cmds.ls(f"{curve}.cv[*]", fl=True)):
                if i != 0 and i != len(cmds.ls(f"{curve}.cv[*]", fl=True))-1:
                    base = (i // 3) + 1
                    mod = i % 3
                    if mod == 0:
                        name = f"{self.side}_eyelids{suffix_name}{base:02d}"
                        lock=["sz", "sy", "visibility"]
                        if i == 0 or i == len(cmds.ls(f"{curve}.cv[*]", fl=True))-1:
                            tan_vis = False
                        else:
                            tan_vis = True

                        parent = self.controllers_trn
                        
                    elif mod == 1:
                        name = f"{self.side}_eyelids{suffix_name}{base:02d}Tan02"
                        lock=["rz","ry","rx", "sz", "sy","sx", "visibility"]
                        tan_vis=False

                        parent = self.tangent_controllers_trn
                    else:
                        name = f"{self.side}_eyelids{suffix_name}{base+1:02d}Tan01"
                        lock=["rz","ry","rx", "sz", "sy","sx", "visibility"]
                        tan_vis=False
                        parent = self.tangent_controllers_trn

                    ctl, ctl_grp = controller_creator(
                        name=name,
                        suffixes=["GRP", "OFF","ANM"],
                        lock=lock,
                        ro=False,
                        parent= parent
                    )

                    if mod == 0:
                        main_ctls.append(ctl)
                        main_ctls_grps.append(ctl_grp)
                        curve_especific_main.append(ctl)
                        

                    if tan_vis:
                        cmds.addAttr(ctl, shortName="tangents", niceName="Tangents ———", enumName="———",attributeType="enum", keyable=True)
                        cmds.setAttr(ctl+".tangents", channelBox=True, lock=True)
                        cmds.addAttr(ctl, shortName="tangentVisibility", niceName="Tangent Visibility", attributeType="bool", keyable=False)
                        cmds.setAttr(ctl+".tangentVisibility", channelBox=True)

                    pos = cmds.pointPosition(cv, world=True)

                    pos_init, parm = core.getClosestParamToWorldMatrixCurve(curve = curve, pos=pos, both=True)  

                    parm_sum = parm + 0.05 if parm+0.05 <= 1 else parm - 0.05

                    pos_aim = core.getPositionFromParmCurve(curve = curve, u_value=parm_sum)
                    four_by_four_aim = cmds.createNode("fourByFourMatrix", name=f"{name}Aim_FBF", ss=True)
                    cmds.setAttr(f"{four_by_four_aim}.in30", pos_aim[0])
                    cmds.setAttr(f"{four_by_four_aim}.in31", pos_aim[1])
                    cmds.setAttr(f"{four_by_four_aim}.in32", pos_aim[2])

                    four_by_four_aim_init = cmds.createNode("fourByFourMatrix", name=f"{name}AimInit_FBF", ss=True)
                    cmds.setAttr(f"{four_by_four_aim_init}.in30", pos_init[0])
                    cmds.setAttr(f"{four_by_four_aim_init}.in31", pos_init[1])
                    cmds.setAttr(f"{four_by_four_aim_init}.in32", pos_init[2])

                    fourByFour = cmds.createNode("fourByFourMatrix", name=f"{name}_FBF", ss=True)

                    if mod == 0:
                        main_4b4.append(fourByFour)
                    else:
                        tan_4b4.append(fourByFour)
                    all_4b4.append(fourByFour)
                    ctls_grps.append(ctl_grp)
                    clts.append(ctl)

                    for j in pos:
                        cmds.setAttr(f"{fourByFour}.in3{pos.index(j)}", j)

                    aim_matrix = cmds.createNode("aimMatrix", name=f"{name}Controller_AMX", ss=True)
                    cmds.connectAttr(f"{four_by_four_aim_init}.output", f"{aim_matrix}.inputMatrix", force=True)
                    cmds.connectAttr(f"{four_by_four_aim}.output", f"{aim_matrix}.primaryTargetMatrix", force=True)
                    
                    aimVector = (1,0,0) if parm+0.05 <= 1 else (-1,0,0)
                    secondaryVector = (0,1,0)
                    secondaryTargetVector = (0,1,0)

                    cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *aimVector, type="double3")
                    cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *secondaryVector, type="double3")
                    cmds.setAttr(f"{aim_matrix}.secondaryTargetVector", *secondaryTargetVector, type="double3")
                    cmds.setAttr(f"{aim_matrix}.secondaryMode", 2)  

                    blend_matrix = cmds.createNode("blendMatrix", name=f"{name}_BMX", ss=True)
                    cmds.connectAttr(f"{fourByFour}.output", f"{blend_matrix}.inputMatrix", force=True)
                    cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{blend_matrix}.target[0].targetMatrix", force=True)
                    cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 0)

                    if self.side == "L":
                        cmds.connectAttr( f"{blend_matrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix", force=True)
                        
                    else:
                        multmatrix = cmds.createNode("multMatrix", name=f"{name}_MMX", ss=True)
                        cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0,
                                                        0, 1, 0, 0,
                                                        0, 0, -1, 0,
                                                        0, 0, 0, 1, type="matrix")
                        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)

                        cmds.connectAttr( f"{multmatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix", force=True)

                    if i == int(len(cmds.ls(f"{curve}.cv[*]", fl=True)) //2): 
                        mid_pos = cmds.createNode("fourByFourMatrix", name=f"{name}MidPos_F4X", ss=True)
                        cmds.setAttr(f"{mid_pos}.in30", pos[0])
                        cmds.setAttr(f"{mid_pos}.in31", pos[1])
                        cmds.setAttr(f"{mid_pos}.in32", pos[2])

                        mid_pos_4b4.append(mid_pos)

                    mmx = core.local_mmx(ctl, ctl_grp[0])
                    row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{name}_RFM", ss=True)
                    cmds.connectAttr(f"{mmx}", f"{row_from_matrix}.matrix", force=True)
                    for axis in ["X", "Y", "Z"]:
                        cmds.connectAttr(f"{row_from_matrix}.output{axis}", f"{curve}.controlPoints[{i}].{axis.lower()}Value", force=True)
    
                    cmds.setAttr(f"{row_from_matrix}.input", 3)

            clts.append(corner_ctls[1])
            ctls_grps.append(corner_grps[1])
            parenting = [clts, curve_especific_main]
            controllers_parenting.append(parenting)
  
        for ctl , grp in zip(main_ctls, main_ctls_grps):
            name = ctl.split("_ANM")[0]
            fleshySocketsUpperMid = cmds.createNode("multMatrix", n=f"{self.side}_{name}fleshySocketsMidPosUpper_MMX", ss=True)
            cmds.connectAttr(f"{self.middle_fleshy}.outputMatrix", f"{fleshySocketsUpperMid}.matrixIn[0]", force=True)

            parentMatrix_fleshy = self.socket_local(grp[0], grp[1], fleshySocketsUpperMid)

            cmds.setAttr(f"{fleshySocketsUpperMid}.matrixIn[1]", cmds.getAttr(f"{ctl}.worldMatrix[0]"), type="matrix")
            cmds.setAttr(f"{parentMatrix_fleshy}.target[0].offsetMatrix", get_offset_matrix(grp[0], f"{fleshySocketsUpperMid}.matrixSum"), type="matrix")

        blend_mid_pos = cmds.createNode("blendMatrix", name=f"{self.side}_eyelidMidPos_BLM", ss=True)
        cmds.connectAttr(f"{mid_pos_4b4[0]}.output", f"{blend_mid_pos}.inputMatrix")
        cmds.connectAttr(f"{mid_pos_4b4[1]}.output", f"{blend_mid_pos}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{blend_mid_pos}.target[0].translateWeight", 0.5)


        # values = [(1,0,0), (-1,0,0)]
        mmx_fleshy = [self.fleshySocketMMX, self.fleshySocketMMXOuter]
        for i, aim in enumerate(corner_aim):
            cmds.connectAttr(f"{blend_mid_pos}.outputMatrix", f"{aim}.primaryTargetMatrix", force=True)
            # cmds.setAttr(f"{aim}.primaryInputAxis", *values[i], type="double3")

            parentMatrix_fleshy = self.socket_local(corner_grps[i][0], corner_grps[i][1], mmx_fleshy[i])

            cmds.setAttr(f"{mmx_fleshy[i]}.matrixIn[1]", cmds.getAttr(f"{aim}.outputMatrix"), type="matrix")
            cmds.setAttr(f"{parentMatrix_fleshy}.target[0].offsetMatrix", get_offset_matrix(corner_grps[i][0], f"{mmx_fleshy[i]}.matrixSum"), type="matrix")

            for rebuilded in rebuilded_curves:
                name = aim.split("_AMX")[0] + "Upper" if "upper" in rebuilded.lower() else aim.split("_AMX")[0] + "Lower"
                value = 0 if i == 0 else len(cmds.ls(f"{rebuilded}.cv[*]", fl=True)) -1

                mmx = core.local_mmx(corner_ctls[i], corner_grps[i][0])
                        
                row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{name}_RFM", ss=True)
                cmds.connectAttr(f"{mmx}", f"{row_from_matrix}.matrix", force=True)
                for axis in ["X", "Y", "Z"]:
                    cmds.connectAttr(f"{row_from_matrix}.output{axis}", f"{rebuilded}.controlPoints[{value}].{axis.lower()}Value", force=True)

                cmds.setAttr(f"{row_from_matrix}.input", 3)


        for parenting in controllers_parenting:
            clts = parenting[0]
            curve_especific_main = parenting[1]
            for i, ctl in enumerate(clts):
                base = (i // 3) + 1
                mod = i % 3
                if mod == 0:
                    pass

                elif mod == 1:
                    if ctl == clts[1]:
                        core.local_space_parent(ctl, parents=[curve_especific_main[0], clts[(base - 1) * 3]], default_weights=0.5)
                    else:
                        core.local_space_parent(ctl, parents=[clts[(base - 1) * 3]], default_weights=0.5)
                    try:
                        cmds.setAttr(f"{ctl}.visibility", lock=False)
                        cmds.connectAttr(f"{clts[(base - 1) * 3]}.tangentVisibility", f"{ctl}.visibility", force=True)
                        cmds.setAttr(f"{ctl}.visibility", lock=True)

                    except:
                        pass
                else:
                    if ctl == clts[-2]:
                        core.local_space_parent(ctl, parents=[clts[(base - 1) * 3], clts[-1]], default_weights=0.5)
                    else:
                        core.local_space_parent(ctl, parents=[clts[base * 3]], default_weights=0.5)
                    try:
                        cmds.setAttr(f"{ctl}.visibility", lock=False)

                        cmds.connectAttr(f"{clts[base * 3]}.tangentVisibility", f"{ctl}.visibility", force=True)
                        cmds.setAttr(f"{ctl}.visibility", lock=True)

                    except:
                        pass
                    
        self.eye_main_creation()
        
    def eye_main_creation(self):

        self.eye_centered = True

        reverse_side = "R" if self.side == "L" else "L"

        self.eye_main_ctl = self.data_exporter.get_data(f"{reverse_side}_eyeModule", "eyeMain")

        if not self.eye_main_ctl and self.eye_centered:
            self.eye_main_ctl, self.eye_main_ctl_grp = controller_creator(
                name=f"C_eyeMain",
                suffixes=["GRP", "OFF","ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=self.controllers_trn
            )

            eye_main_guide = cmds.createNode("transform", name=f"C_eyeMain_GUIDE", ss=True, parent=self.guides_grp)

            cmds.matchTransform(eye_main_guide, self.eye)
            cmds.setAttr(f"{eye_main_guide}.tx", 0)
            if core.DataManager.get_asset_name() == "varyndor" or core.DataManager.get_asset_name() == "aychedral" or core.DataManager.get_asset_name() == "azhurean":
                value = 400
            else:
                value = 40
            cmds.move(0, 0, value, eye_main_guide,  r=True, ws=False)

            cmds.connectAttr(f"{eye_main_guide}.worldMatrix[0]", f"{self.eye_main_ctl_grp[0]}.offsetParentMatrix", force=True)

        ctl, controller_grp = controller_creator(
            name=f"{self.side}_eye",
            suffixes=["GRP", "OFF","ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            # parent=self.controllers_trn
        )

        
        multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyeInit_MMX", ss=True)

        cmds.connectAttr(f"{self.eye}.worldMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)
        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix", force=True)

        if core.DataManager.get_asset_name() == "varyndor" or core.DataManager.get_asset_name() == "aychedral" or core.DataManager.get_asset_name() == "azhurean":
            value = 40 if self.side == "L" else -40
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0,
                                            0, 1, 0, 0,
                                            0, 0, 1, 0,
                                            value, 0, 0, 1, type="matrix")
        else:
            cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0,
                                            0, 1, 0, 0,
                                            0, 0, 1, 0,
                                            0, 0, 40, 1, type="matrix")

        cmds.parent(controller_grp[0], self.eye_main_ctl if self.eye_main_ctl else self.masterWalk_ctl)

        aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_eyeMain_AMX", ss=True)
        cmds.connectAttr(f"{self.main_ctl_grp[0]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix", force=True)

        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix", force=True)
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{aim_matrix}.secondaryTargetMatrix", force=True)
        cmds.setAttr(f"{aim_matrix}.secondaryMode", 2)

        # if self.side == "L":
        primary_vector = (0, 0, 1)
        secondary_vector = (0, 1, 0)
        # else:
        #     primary_vector = (0, 0, -1)
        #     secondary_vector = (-self.secondary_aim_vector.x, -self.secondary_aim_vector.y, -self.secondary_aim_vector.z)

        cmds.setAttr(f"{aim_matrix}.primaryInputAxis", *primary_vector, type="double3")
        cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *secondary_vector, type="double3")
        cmds.setAttr(f"{aim_matrix}.secondaryTargetVector", 0, 1, 0, type="double3")

        multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_eyeMain_MMX", ss=True)
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{multmatrix}.matrixIn[0]", force=True)
        cmds.connectAttr(f"{self.main_ctl_grp[0]}.worldInverseMatrix[0]", f"{multmatrix}.matrixIn[1]", force=True)

        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{self.main_ctl_grp[1]}.offsetParentMatrix", force=True)

        eye_joint = cmds.createNode("joint", name=f"{self.side}_eye_JNT", ss=True, parent=self.skinning_trn)

        cmds.connectAttr(f"{self.main_ctl}.worldMatrix[0]", f"{eye_joint}.offsetParentMatrix", force=True)

        cmds.reorder(eye_joint, front=True)
