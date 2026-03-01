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

class EyebrowModule():
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

        self.side = self.guide_name.split("_")[0]

        if self.side == "L":
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["z"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-x"])
        else:
            self.primary_aim_vector = om.MVector(AXIS_VECTOR["-z"])
            self.secondary_aim_vector = om.MVector(AXIS_VECTOR["-x"])


        self.module_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)
        self.tangent_controllers_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowTangentControllers_GRP", ss=True, parent=self.controllers_trn)

        parentMatrix = cmds.createNode("parentMatrix", name=f"{self.side}_eyebrowModule_PM", ss=True)
        cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
        offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
        cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
        cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)

        self.create_chain()
       
            
    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        self.curves = []
        self.nurbsSurface = None

        for item in self.guides:
            try:
                relative = cmds.listRelatives(item, shapes=True)
                if cmds.objectType(relative, isType="nurbsCurve"):
                    self.curves.append(item)
                elif cmds.objectType(relative, isType="nurbsSurface"):
                    self.nurbsSurface = item
            except:
                pass

        if not self.nurbsSurface:
            om.MGlobal.displayError("No NURBS surface found in the eyebrow guide. Please create one to proceed.")
            return
        if not self.curves:
            om.MGlobal.displayError("No NURBS curves found in the eyebrow guide. Please create at least one to proceed.")
            return
        
        self.center_main_ctl, self.center_main_ctl_grp = controller_creator(
                            name=f"C_eyebrowCenter",
                            suffixes=["GRP", "OFF","ANM"],
                            lock=["visibility"],
                            ro=False,
                            parent= self.controllers_trn
                        )
        
        cmds.connectAttr(f"{self.guides[0]}.worldMatrix[0]", f"{self.center_main_ctl_grp[0]}.offsetParentMatrix", force=True)

        mmx = core.local_mmx(self.center_main_ctl, self.center_main_ctl_grp[0]) 
        self.center_joint = cmds.createNode("joint", name=f"C_eyebrowCenter_JNT")
        cmds.connectAttr(mmx, f"{self.center_joint}.offsetParentMatrix", force=True)



        for curve in self.curves:
            
            self.side = curve.split("_")[0]
            self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_eyebrowFacialSkinning_GRP", ss=True, p=self.skel_grp)
            cmds.parent(self.center_joint, self.skinning_trn)

            if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
                self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
            cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

            rebuilded = cmds.rebuildCurve(curve, ch=0, rpo=0, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=2, d=3, tol=0.01)[0]
            cmds.parent(rebuilded, self.module_trn)
            cmds.select(rebuilded, r=True)
            cmds.nurbsCurveToBezier()
        
        
            self.main_ctl, self.main_ctl_grp = controller_creator(
                    name=f"{self.side}_eyebrowMain",
                    suffixes=["GRP", "OFF","ANM"],
                    lock=["sz", "sy", "sx", "visibility"],
                    ro=False,
                    parent= self.controllers_trn
                )
            
            cmds.addAttr(self.main_ctl, shortName="slidingSep", niceName="Sliding ———", enumName="———",attributeType="enum", keyable=True)
            cmds.setAttr(self.main_ctl+".slidingSep", channelBox=True, lock=True)
            cmds.addAttr(self.main_ctl, shortName="sliding", niceName="Sliding",minValue=0,defaultValue=0, maxValue=1, keyable=True)

            clts = []
            ctls_grps = []

            main_4b4 = []
            tan_4b4 = []
            all_4b4 = []

            for i, cv in enumerate(cmds.ls(f"{rebuilded}.cv[*]", fl=True)):
                base = (i // 3) + 1
                mod = i % 3
                if mod == 0:
                    name = f"{self.side}_eyebrow{base:02d}"
                    lock=["sz", "sy", "visibility"]
                    if i == 0 or i == len(cmds.ls(f"{rebuilded}.cv[*]", fl=True))-1:
                        tan_vis = False
                    else:
                        tan_vis = True
                    
                elif mod == 1:
                    name = f"{self.side}_eyebrow{base:02d}Tan02"
                    lock=["rz","ry","rx", "sz", "sy","sx", "visibility"]
                    tan_vis=False

                else:
                    name = f"{self.side}_eyebrow{base+1:02d}Tan01"
                    lock=["rz","ry","rx", "sz", "sy","sx", "visibility"]
                    tan_vis=False


                ctl, ctl_grp = controller_creator(
                    name=name,
                    suffixes=["GRP", "OFF","ANM"],
                    lock=lock,
                    ro=False,
                    parent= self.controllers_trn
                )

                if tan_vis:
                    cmds.addAttr(ctl, shortName="tangents", niceName="Tangents ———", enumName="———",attributeType="enum", keyable=True)
                    cmds.setAttr(ctl+".tangents", channelBox=True, lock=True)
                    cmds.addAttr(ctl, shortName="tangentVisibility", niceName="Tangent Visibility", attributeType="bool", keyable=False)
                    cmds.setAttr(ctl+".tangentVisibility", channelBox=True)

                pos = cmds.pointPosition(cv, world=True)

                pos_init, parm = core.getClosestParamToWorldMatrixCurve(curve = rebuilded, pos=pos, both=True)  

                parm_sum = parm + 0.05 if parm+0.05 <= 1 else parm - 0.05

                pos_aim = core.getPositionFromParmCurve(curve = rebuilded, u_value=parm_sum)
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
                    if i == int(len(cmds.ls(f"{rebuilded}.cv[*]", fl=True))/2):
                        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{self.main_ctl_grp[0]}.offsetParentMatrix", force=True)

                else:
                    multmatrix = cmds.createNode("multMatrix", name=f"{name}_MMX", ss=True)
                    cmds.setAttr(f"{multmatrix}.matrixIn[0]", 1, 0, 0, 0,
                                                    0, 1, 0, 0,
                                                    0, 0, -1, 0,
                                                    0, 0, 0, 1, type="matrix")
                    cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{multmatrix}.matrixIn[1]", force=True)
                    cmds.connectAttr( f"{multmatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix", force=True)
                    if i == int(len(cmds.ls(f"{rebuilded}.cv[*]", fl=True))/2):
                        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{self.main_ctl_grp[0]}.offsetParentMatrix", force=True)

                mmx = core.local_mmx(ctl, ctl_grp[0])
                
                row_from_matrix = cmds.createNode("rowFromMatrix", name=f"{name}_RFM", ss=True)
                cmds.connectAttr(f"{mmx}", f"{row_from_matrix}.matrix", force=True)
                for axis in ["X", "Y", "Z"]:
                    cmds.connectAttr(f"{row_from_matrix}.output{axis}", f"{rebuilded}.controlPoints[{i}].{axis.lower()}Value", force=True)
 
                cmds.setAttr(f"{row_from_matrix}.input", 3)



            for i, ctl in enumerate(clts):
                base = (i // 3) + 1
                mod = i % 3
                if mod == 0:
                    core.local_space_parent(ctl, parents=[self.main_ctl], default_weights=0.5)

                elif mod == 1:
                    core.local_space_parent(ctl, parents=[clts[(base - 1) * 3]], default_weights=0.5)
                    try:
                        cmds.setAttr(f"{ctl}.visibility", lock=False)
                        cmds.connectAttr(f"{clts[(base - 1) * 3]}.tangentVisibility", f"{ctl}.visibility", force=True)
                        cmds.setAttr(f"{ctl}.visibility", lock=True)

                    except:
                        pass
                else:
                    core.local_space_parent(ctl, parents=[clts[base * 3]], default_weights=0.5)
                    try:
                        cmds.setAttr(f"{ctl}.visibility", lock=False)

                        cmds.connectAttr(f"{clts[base * 3]}.tangentVisibility", f"{ctl}.visibility", force=True)
                        cmds.setAttr(f"{ctl}.visibility", lock=True)

                    except:
                        pass

            fbf_positions = []
            mmx_ups = []

            sliding_fbf = []

            for i, cv in enumerate(cmds.ls(f"{curve}.cv[*]", fl=True)):
                
                name = f"{self.side}_eyebrow{i+1:02d}"

                pos = cmds.pointPosition(cv, world=True)


                parm = core.getClosestParamToWorldMatrixCurve(curve = rebuilded, pos=pos)  

                curve_shape = cmds.listRelatives(rebuilded, shapes=True)[0]

                point_on_surface = cmds.createNode("pointOnCurveInfo", name=f"{name}_POCI", ss=True)
                cmds.setAttr(f"{point_on_surface}.parameter", parm)

                cmds.connectAttr(f"{curve_shape}.worldSpace[0]", f"{point_on_surface}.inputCurve", force=True)

                matrix_node = cmds.createNode('fourByFourMatrix', name=f"{name}_FBF", ss=True)

                cmds.connectAttr(f"{point_on_surface}.positionX", f"{matrix_node}.in30", force=True)
                cmds.connectAttr(f"{point_on_surface}.positionY", f"{matrix_node}.in31", force=True)
                cmds.connectAttr(f"{point_on_surface}.positionZ", f"{matrix_node}.in32", force=True)

                multmatrix_up = cmds.createNode("multMatrix", name=f"{name}Up_MMX", ss=True)   
                cmds.setAttr(f"{multmatrix_up}.matrixIn[0]", 1, 0, 0, 0,
                                                    0, 0, 1, 0,
                                                    0, -1, 0, 0,
                                                    0, 1, 0, 1, type="matrix")         
                cmds.connectAttr(f"{matrix_node}.output", f"{multmatrix_up}.matrixIn[1]", force=True)   

                mmx_ups.append(multmatrix_up)
                fbf_positions.append(matrix_node)

                closest_point_on_surface = cmds.createNode("closestPointOnSurface", name=f"{name}Sliding_CPS", ss=True)

                cmds.connectAttr(f"{self.nurbsSurface}.worldSpace[0]", f"{closest_point_on_surface}.inputSurface", force=True)

                cmds.connectAttr(f"{matrix_node}.in30", f"{closest_point_on_surface}.inPositionX", force=True)
                cmds.connectAttr(f"{matrix_node}.in31", f"{closest_point_on_surface}.inPositionY", force=True)
                cmds.connectAttr(f"{matrix_node}.in32", f"{closest_point_on_surface}.inPositionZ", force=True)

                # point_on_surface = cmds.createNode("pointOnSurfaceInfo", name=f"{name}Sliding_POSI", ss=True)
                # cmds.connectAttr(f"{self.nurbsSurface}.worldSpace[0]", f"{point_on_surface}.inputSurface", force=True)
                # cmds.connectAttr(f"{closest_point_on_surface}.parameterU", f"{point_on_surface}.parameterU", force=True)
                # cmds.connectAttr(f"{closest_point_on_surface}.parameterV", f"{point_on_surface}.parameterV", force=True)
                # cmds.setAttr(f"{point_on_surface}.parameterU", u)
                # cmds.setAttr(f"{point_on_surface}.parameterV", v)



                # matrix_node = cmds.createNode('fourByFourMatrix', name=f"{name}Sliding_FBF", ss=True)

                # cmds.connectAttr(f"{point_on_surface}.normalizedNormalX", f"{matrix_node}.in10", force=True)
                # cmds.connectAttr(f"{point_on_surface}.normalizedNormalY", f"{matrix_node}.in11", force=True)
                # cmds.connectAttr(f"{point_on_surface}.normalizedNormalZ", f"{matrix_node}.in12", force=True)

                # cmds.connectAttr(f"{point_on_surface}.normalizedTangentVX", f"{matrix_node}.in00", force=True)
                # cmds.connectAttr(f"{point_on_surface}.normalizedTangentVY", f"{matrix_node}.in01", force=True)
                # cmds.connectAttr(f"{point_on_surface}.normalizedTangentVZ", f"{matrix_node}.in02", force=True)

                # cmds.connectAttr(f"{point_on_surface}.normalizedTangentUX", f"{matrix_node}.in20", force=True)
                # cmds.connectAttr(f"{point_on_surface}.normalizedTangentUY", f"{matrix_node}.in21", force=True)
                # cmds.connectAttr(f"{point_on_surface}.normalizedTangentUZ", f"{matrix_node}.in22", force=True)

                # cmds.connectAttr(f"{point_on_surface}.positionX", f"{matrix_node}.in30", force=True)
                # cmds.connectAttr(f"{point_on_surface}.positionY", f"{matrix_node}.in31", force=True)
                # cmds.connectAttr(f"{point_on_surface}.positionZ", f"{matrix_node}.in32", force=True)

                uv_pin = cmds.createNode("uvPin", name=f"{name}Sliding_UVP", ss=True)
                cmds.connectAttr(f"{self.nurbsSurface}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)
                cmds.connectAttr(f"{closest_point_on_surface}.parameterU", f"{uv_pin}.coordinate[0].coordinateU", force=True)
                cmds.connectAttr(f"{closest_point_on_surface}.parameterV", f"{uv_pin}.coordinate[0].coordinateV", force=True)

                sliding_fbf.append(uv_pin)


            for i, node in enumerate(fbf_positions):
                name = f"{self.side}_eyebrow{i+1:02d}"
                aim_matrix = cmds.createNode("aimMatrix", name=f"{name}_AMX", ss=True)
                cmds.connectAttr(f"{node}.output", f"{aim_matrix}.inputMatrix", force=True)
                try:
                    cmds.connectAttr(f"{fbf_positions[i+1]}.output", f"{aim_matrix}.primaryTargetMatrix", force=True)
                    
                except:
                    cmds.connectAttr(f"{fbf_positions[i-1]}.output", f"{aim_matrix}.primaryTargetMatrix", force=True)
                    cmds.setAttr(f"{aim_matrix}.primaryInputAxis", -1, 0, 0, type="double3")


                cmds.connectAttr(f"{mmx_ups[i]}.matrixSum", f"{aim_matrix}.secondaryTargetMatrix", force=True)
                cmds.setAttr(f"{aim_matrix}.secondaryMode", 1)

               

                parentMatrix = cmds.createNode("parentMatrix", name=f"{name}Sliding_PM", ss=True)
                cmds.setAttr(f"{parentMatrix}.inputMatrix", cmds.getAttr(f"{aim_matrix}.outputMatrix"), type="matrix")
                cmds.connectAttr(f"{sliding_fbf[i]}.outputMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)

                offset = core.get_offset_matrix(f"{aim_matrix}.outputMatrix", f"{sliding_fbf[i]}.outputMatrix[0]")
                cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")

                cmds.connectAttr(f"{self.main_ctl}.sliding", f"{parentMatrix}.target[0].weight", force=True)

                cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{parentMatrix}.target[1].targetMatrix", force=True)

                reverse = cmds.createNode("reverse", name=f"{name}Sliding_REV", ss=True)
                cmds.connectAttr(f"{self.main_ctl}.sliding", f"{reverse}.inputX", force=True)
                cmds.connectAttr(f"{reverse}.outputX", f"{parentMatrix}.target[1].weight", force=True)

                pick_matrix = cmds.createNode("pickMatrix", name=f"{name}Sliding_PMK", ss=True)
                cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{pick_matrix}.inputMatrix", force=True)
                cmds.setAttr(f"{pick_matrix}.useRotate", 0)

                joint = cmds.createNode("joint", name=f"{name}_JNT", ss=True, p=self.skinning_trn)
                cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", force=True)

                joint = cmds.createNode("joint", name=f"{name}Rotation_JNT", ss=True, p=self.skinning_trn)
                cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{joint}.offsetParentMatrix", force=True)

            self.data_exporter.append_data(f"{self.side}_eyebrowModule", 
                            {"skinning_transform": self.skinning_trn,

                            }
                            )

