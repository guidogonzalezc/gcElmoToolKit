#Python libraries import
from unicodedata import name
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
from elmoTools.utils import basic_structure
import maya.api.OpenMaya as om

reload(de_boors_002)
reload(guide_creation)
reload(ss)
reload(core)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class MembraneModule(object):

    def __init__(self):
        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")
        self.muscle_locators = self.data_exporter.get_data("basic_structure", "muscleLocators_GRP")
        self.skeleton_hierarchy = self.data_exporter.get_data("basic_structure", "skeletonHierarchy_GRP")

    def make(self, guide_name):

        """
        Create a limb rig with controllers and constraints.
        This function sets up the basic structure for a limb, including controllers and constraints.
        """      
        self.side = guide_name.split("_")[0]

        if self.side == "L":
            self.primary_aim = "x"
            self.secondary_aim = "y"
        
        elif self.side == "R":
            self.primary_aim = "-x"
            self.secondary_aim = "y"

        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_membraneModule_GRP", parent=self.modules_grp, ss=True)
        self.individual_controllers_grp = cmds.createNode("transform", name=f"{self.side}_membraneControllers_GRP", parent=self.masterWalk_ctl, ss=True)
        self.skinning_grp = cmds.createNode("transform", name=f"{self.side}_membraneSkinningJoints_GRP", parent=self.skeleton_hierarchy, ss=True)

        cmds.setAttr(f"{self.individual_controllers_grp}.inheritsTransform", 0)
        
        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])

        self.guides = guide_import(guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]

        # cmds.addAttr(self.skinnging_grp, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        self.secondary_membranes()

        self.main_membrane()

        # if len(self.guides) > 0: 

        #     self.forearm_membrane()


        self.data_exporter.append_data(
            f"{self.side}_membraneModule",
            {
                # "skinning_transform": self.skinnging_grp,
            }
        )


    def main_membrane(self):
        data_exporter = data_export.DataExport()

        spine_joints = cmds.listRelatives(data_exporter.get_data("C_spineModule", "skinning_transform"), allDescendents=True, type="joint")
        tail_joints = cmds.listRelatives(data_exporter.get_data("C_tailModule", "skinning_transform"), allDescendents=True, type="joint")
        arm_joints = cmds.listRelatives(data_exporter.get_data(f"{self.side}_armModule", "skinning_transform"), allDescendents=True, type="joint")
        membran_joints = cmds.listRelatives(data_exporter.get_data(f"{self.side}_firstFinger00Module", "skinning_transform"), allDescendents=True, type="joint")

        ctls = []

        # self.forearm_guide = self.guides[1]
        # self.guides =[self.guides[0]]

        shapes = cmds.listRelatives(self.guides[0], shapes=True, noIntermediate=True) or []
        guide_shape = shapes[0] if shapes else self.guides[0]
        main_controller_guide_pos = cmds.pointPosition(f"{guide_shape}.cv[1][3]", world=True)
        main_controller_guide = cmds.createNode("transform", name=f"{self.side}_MainMembrane_GUIDE", parent=self.guides_grp, ss=True)
        cmds.xform(main_controller_guide, ws=True, t=main_controller_guide_pos)

        main_controller, main_controller_grp = controller_creator(
            name=f"{self.side}_MainMembrane",
            suffixes=["GRP", "ANM"],
            lock=["scaleX", "scaleY", "scaleZ", "visibility"],
            ro=True,
            parent=self.individual_controllers_grp
        )

        cmds.addAttr(main_controller, shortName="extraSep", niceName="EXTRA ATTRIBUTES ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(main_controller+".extraSep", channelBox=True, lock=True)
        cmds.addAttr(main_controller, shortName="membranePush", niceName="Membrane Push", defaultValue=300, keyable=True)

        third_row_closest = []
        first_row_closest = []

        all_joints = spine_joints + tail_joints + membran_joints + arm_joints
        cv_list = cmds.ls(f"{guide_shape}.cv[0][*]", flatten=True)

        for i in range(2):
            for secondary_index in range(len(cv_list)-1):

                closest_pos = cmds.pointPosition(f"{guide_shape}.cv[{i*2}][{secondary_index}]", world=True) 
                closest_transform = core.get_closest_transform(closest_pos, all_joints)

                if i == 0:
                    first_row_closest.append(closest_transform)

                elif i == 1:
                    third_row_closest.append(closest_transform)


        blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_MainMembrane_BMX", ss=True)

        cmds.connectAttr(f"{membran_joints[-1]}.worldMatrix[0]", f"{blend_matrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{first_row_closest[-1]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{blend_matrix}.target[0].translateWeight", 0.5)
        pickMatrix = cmds.createNode("pickMatrix", name=f"{self.side}_MainMembrane_PMX", ss=True)
        cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{pickMatrix}.inputMatrix", force=True)
        # cmds.setAttr(f"{pickMatrix}.useRotate", 0)

        cmds.connectAttr(f"{pickMatrix}.outputMatrix", f"{main_controller_grp[0]}.offsetParentMatrix")

        aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_MainMembrane_AMX", ss=True)
        cmds.connectAttr(f"{arm_joints[6]}.worldMatrix[0]", f"{aim_matrix}.inputMatrix")
        cmds.connectAttr(f"{main_controller}.worldMatrix[0]", f"{aim_matrix}.primaryTargetMatrix")
        cmds.connectAttr(f"{arm_joints[1]}.worldMatrix[0]", f"{aim_matrix}.secondaryTargetMatrix")
        cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
        cmds.setAttr(f"{aim_matrix}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")

        skinning_joint = cmds.createNode("joint", name=f"{self.side}_MainMembrane_JNT", ss=True, parent=self.individual_module_grp)

        dm_a = cmds.createNode("decomposeMatrix", name=f"{self.side}_MainMembranePush01_DCM", ss=True)
        dm_b = cmds.createNode("decomposeMatrix", name=f"{self.side}_MainMembranePush02_DCM", ss=True)
        dm_c = cmds.createNode("decomposeMatrix", name=f"{self.side}_MainMembranePush03_DCM", ss=True)

        cmds.connectAttr(f"{arm_joints[0]}.worldMatrix[0]", dm_a + ".inputMatrix")
        cmds.connectAttr(f"{arm_joints[6]}.worldMatrix[0]", dm_b + ".inputMatrix")
        cmds.connectAttr(f"{arm_joints[-1]}.worldMatrix[0]", dm_c + ".inputMatrix")


        vec_ba = cmds.createNode("plusMinusAverage", name=f"{self.side}_MainMembraneVector01_PMA", ss=True)
        cmds.setAttr(vec_ba + ".operation", 2) 
        cmds.connectAttr(dm_a + ".outputTranslate", vec_ba + ".input3D[0]")
        cmds.connectAttr(dm_b + ".outputTranslate", vec_ba + ".input3D[1]")

        vec_bc = cmds.createNode("plusMinusAverage", name=f"{self.side}_MainMembraneVector02_PMA", ss=True)
        cmds.setAttr(vec_bc + ".operation", 2)
        cmds.connectAttr(dm_c + ".outputTranslate", vec_bc + ".input3D[0]")
        cmds.connectAttr(dm_b + ".outputTranslate", vec_bc + ".input3D[1]")

        angle_node = cmds.createNode("angleBetween", name=f"{self.side}_MainMembraneAngle_AB", ss=True)
        cmds.connectAttr(vec_ba + ".output3D", angle_node + ".vector1")
        cmds.connectAttr(vec_bc + ".output3D", angle_node + ".vector2")

        remap = cmds.createNode("remapValue", name=f"{self.side}_push_remap", ss=True)
        cmds.connectAttr(angle_node + ".angle", remap + ".inputValue")

        angle = cmds.getAttr(f"{angle_node}.axisAngle.angle")
        cmds.setAttr(remap + ".inputMin", angle)
        cmds.setAttr(remap + ".inputMax", 45.0)
        
        cmds.setAttr(remap + ".outputMin", 0.0)
        cmds.connectAttr(main_controller + ".membranePush", remap + ".outputMax")   
        
        cmds.setAttr(remap + ".value[0].value_Interp", 2)

        # cmds.connectAttr(remap + ".outValue", "{}.{}".format(push_jnt, push_axis))
        
        fourbyfour_matrix = cmds.createNode("fourByFourMatrix", name=f"{self.side}_MainMembranePush_FFMM", ss=True)
        cmds.connectAttr(remap + ".outValue", f"{fourbyfour_matrix}.in30")

        multmatrix = cmds.createNode("multMatrix", name=f"{self.side}_MainMembranePush_MMX", ss=True)
        cmds.connectAttr(f"{fourbyfour_matrix}.output", f"{multmatrix}.matrixIn[0]")
        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{multmatrix}.matrixIn[1]")


        cmds.connectAttr(f"{multmatrix}.matrixSum", f"{skinning_joint}.offsetParentMatrix", force=True)

        skinning_list = first_row_closest
        skinning_list.extend(third_row_closest)
        skinning_list.append(skinning_joint)

        nurbs_skincluster = cmds.skinCluster(skinning_list, self.guides[0], toSelectedBones=True, maximumInfluences=1, normalizeWeights=1, name=f"{self.side}_MainMembrane_SKN")[0]
        for secondary_index in range(len(cv_list)-1):
            cmds.skinPercent(nurbs_skincluster, f"{self.guides[0]}.cv[1][{secondary_index}]", transformValue=[(skinning_joint, 1)])

        rebuilded_surface = cmds.rebuildSurface(
            guide_shape,
            ch=True, rpo=0, rt=0, end=1, kr=0, kcp=0, kc=0,
            su=2, du=3, sv=4, dv=3, tol=0.01, fr=0, dir=2
        )[0]
        cmds.delete(rebuilded_surface, constructionHistory=True)

        rebuilded_surface = cmds.rename(rebuilded_surface, f"{self.side}_MainMembrane_NURBS")
        cmds.parent(rebuilded_surface, self.individual_module_grp)

        secondary_skinning_joints = []
        secondary_skinning_joints = first_row_closest
        secondary_skinning_joints.extend(third_row_closest)

        uv_pin = cmds.createNode("uvPin", name=f"{self.side}_primaryMembraneFirstLayer_UVP", ss=True)
        cmds.connectAttr(f"{self.guides[0]}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)

        if self.side == "L":
            cmds.setAttr(f"{uv_pin}.normalAxis", 1)
            cmds.setAttr(f"{uv_pin}.tangentAxis", 2)
        else:
            cmds.setAttr(f"{uv_pin}.normalAxis", 1)
            cmds.setAttr(f"{uv_pin}.tangentAxis", 5)

        count = 0
        for i, (name) in enumerate(["Inner", "Middle", "Outer"]):
            secondary_controllers = []
            pick_matrices = []
            ctls = []
            for index in range(len(cv_list)-1):
                u, v = core.getClosestParamsToPositionSurface(self.guides[0], cmds.pointPosition(f"{rebuilded_surface}.cv[{i+1}][{index}]", world=True))

                # uv_pin = cmds.createNode("uvPin", name=f"{self.side}_{name}Membrane0{index+1}_UVP", ss=True)
                # cmds.connectAttr(f"{self.guides[0]}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)
                cmds.setAttr(f"{uv_pin}.coordinate[{count}].coordinateU", u)
                cmds.setAttr(f"{uv_pin}.coordinate[{count}].coordinateV", v)

                ctl = None
                if index == int((len(cv_list)-1)*0.25) or index == int((len(cv_list)-1)*0.5) or index == int((len(cv_list)-1)*0.75):
                    ctl, ctl_grp = controller_creator(
                    name=f"{self.side}_{name}PrimaryMembrane0{index+1}",
                    suffixes=["GRP", "ANM"],
                    lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                    ro=True,
                    parent=self.individual_controllers_grp
                    )
                

                joint = cmds.createNode("joint",  name=f"{self.side}_{name}PrimaryMembrane0{index+1}_JNT", ss=True, parent=self.individual_module_grp)

                            
                if index == 0:
                    cmds.connectAttr(f"{uv_pin}.outputMatrix[{count}]", f"{joint}.offsetParentMatrix", force=True)

                    ctls.append(joint)

                else:
                    multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{name}PrimaryMembrane0{index+1}Offset_MMX", ss=True)
                    multMatrix_wm = cmds.createNode("multMatrix", name=f"{self.side}_{name}PrimaryMembrane0{index+1}WM_MMX", ss=True)
                    inverseMatrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{name}PrimaryMembrane0{index+1}IMX", ss=True)
                    cmds.connectAttr(f"{uv_pin}.outputMatrix[{count-1}]", f"{inverseMatrix}.inputMatrix")

                    cmds.connectAttr(f"{uv_pin}.outputMatrix[{count}]", f"{multMatrix}.matrixIn[0]")
                    cmds.connectAttr(f"{inverseMatrix}.outputMatrix", f"{multMatrix}.matrixIn[1]")
                    cmds.connectAttr(f"{multMatrix}.matrixSum", f"{multMatrix_wm}.matrixIn[0]")
                    cmds.connectAttr(f"{ctls[-1]}.worldMatrix[0]", f"{multMatrix_wm}.matrixIn[1]")
                    if ctl:
                        cmds.connectAttr(f"{multMatrix_wm}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")
                        cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")
                        ctls.append(ctl)
                    else:
                        cmds.connectAttr(f"{multMatrix_wm}.matrixSum", f"{joint}.offsetParentMatrix")
                        ctls.append(joint)

                count += 1
                pick_matrices.append(uv_pin)
                secondary_skinning_joints.append(joint)
                
        nurbs_skincluster = cmds.skinCluster(secondary_skinning_joints, rebuilded_surface, toSelectedBones=True, maximumInfluences=1, normalizeWeights=1, name=f"{self.side}_MainMembraneRebuild_SKN")[0]

        rebuilded_shape = cmds.listRelatives(rebuilded_surface, shapes=True, noIntermediate=True)[0]

        u_row = 10
        v_row = 10

        uv_pin = cmds.createNode("uvPin", name=f"{self.side}_primaryMembraneEnd_UVP", ss=True)
        cmds.connectAttr(f"{rebuilded_shape}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)

        if self.side == "L":
            cmds.setAttr(f"{uv_pin}.normalAxis", 1)
            cmds.setAttr(f"{uv_pin}.tangentAxis", 2)
        else:
            cmds.setAttr(f"{uv_pin}.normalAxis", 1)
            cmds.setAttr(f"{uv_pin}.tangentAxis", 5)

        

        count = 0
        for i in range(u_row):
            for index in range(v_row):
                # split 1.0 into 'range(6)' steps -> 0.0, 0.2, 0.4, 0.6, 0.8, 1.0
                cmds.setAttr(f"{uv_pin}.coordinate[{count}].coordinateU", float(i) / (u_row - 1))
                cmds.setAttr(f"{uv_pin}.coordinate[{count}].coordinateV", float(index) / (v_row - 1))

                joint = cmds.createNode("joint", name=f"{self.side}_primaryMembrane{i}{index+1}_JNT", ss=True, parent=self.skinning_grp)
                cmds.connectAttr(f"{uv_pin}.outputMatrix[{count}]", f"{joint}.offsetParentMatrix", force=True)
                count += 1

    def secondary_membranes(self):

        input_val = 0
        skinning_joints = []
        while True:
            joint_name = f"{self.side}_{core.number_to_ordinal_word(input_val + 1)}Finger00Module"
            joint = self.data_exporter.get_data(joint_name, "skinning_transform")
            if joint is None:
                break
            skinning_joints.append(joint)
            input_val += 1


        for i in range(len(skinning_joints)-1):
            joint_list_one = cmds.listRelatives(skinning_joints[i], children=True, type="joint")
            joint_list_two = cmds.listRelatives(skinning_joints[i+1], children=True, type="joint")
            
            for values in [0.5]:

                ctls = []
                ctls_grp = []
                pick_matrix_nodes = []
                membranes_wm_aim = []
                mid_positions = []

                falanges_selected_joints = []

                for index, (joint_one, joint_two) in enumerate(zip(joint_list_one, joint_list_two)):
                    if values == 0.5:
                        name = "MainController"
                    y_axis_aim = cmds.createNode("aimMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}_AMX", ss=True)
                    cmds.connectAttr(f"{joint_two}.worldMatrix[0]", f"{y_axis_aim}.inputMatrix")
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{y_axis_aim}.primaryTargetMatrix")
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{y_axis_aim}.secondaryTargetMatrix")
                    cmds.setAttr(f"{y_axis_aim}.primaryInputAxis", *self.primary_aim_vector, type="double3")
                    cmds.setAttr(f"{y_axis_aim}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{y_axis_aim}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{y_axis_aim}.secondaryMode", 2)

                    y_axis_aim_translate = cmds.createNode("blendMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}_BMX", ss=True)
                    cmds.connectAttr(f"{y_axis_aim}.outputMatrix", f"{y_axis_aim_translate}.inputMatrix")
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{y_axis_aim_translate}.target[0].targetMatrix")
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].scaleWeight", 0)
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].translateWeight", values) # Cambiar valor para 0.25 0.5 0.75
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].rotateWeight", 0)
                    cmds.setAttr(f"{y_axis_aim_translate}.target[0].shearWeight", 0)

                    mult_side = 1 if self.side == "L" else -1

                    y_axis_aim_end_pos = cmds.createNode("multMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}_MMX", ss=True)
                    cmds.setAttr(f"{y_axis_aim_end_pos}.matrixIn[0]",   1, 0, 0, 0, 
                                                                        0, 1, 0, 0, 
                                                                        0, 0, 1, 0, 
                                                                        0, 50*mult_side, 0, 1, type="matrix")
                    cmds.connectAttr(f"{y_axis_aim_translate}.outputMatrix", f"{y_axis_aim_end_pos}.matrixIn[1]")   

                    mid_position = cmds.createNode("wtAddMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}_WTM", ss=True)
                    cmds.connectAttr(f"{joint_one}.worldMatrix[0]", f"{mid_position}.wtMatrix[0].matrixIn")
                    cmds.connectAttr(f"{joint_two}.worldMatrix[0]", f"{mid_position}.wtMatrix[1].matrixIn")
                    cmds.setAttr(f"{mid_position}.wtMatrix[0].weightIn", values) # Cambiar valor para 0.25 0.5 0.75
                    cmds.setAttr(f"{mid_position}.wtMatrix[1].weightIn", 1-values) # Cambiar valor para 0.25 0.5 0.75

                    front_offset_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}FrontOffset_MMX", ss=True)
                    cmds.setAttr(f"{front_offset_multMatrix}.matrixIn[0]",   1, 0, 0, 0, 
                                                                            0, 1, 0, 0,
                                                                            0, 0, 1, 0,
                                                                            10, 0, 0, 1, type="matrix")
                    cmds.connectAttr(f"{mid_position}.matrixSum", f"{front_offset_multMatrix}.matrixIn[1]")

                    membran_wm_aim = cmds.createNode("aimMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}End_AMX", ss=True)
                    cmds.connectAttr(f"{mid_position}.matrixSum", f"{membran_wm_aim}.inputMatrix")
                    cmds.connectAttr(f"{y_axis_aim_end_pos}.matrixSum", f"{membran_wm_aim}.secondaryTargetMatrix")

                    cmds.setAttr(f"{membran_wm_aim}.primaryInputAxis", *self.primary_aim_vector, type="double3")
                    cmds.setAttr(f"{membran_wm_aim}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{membran_wm_aim}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                    cmds.setAttr(f"{membran_wm_aim}.secondaryMode", 1)

                    ctl = None
                    if index == int((len(joint_list_one)-1)*0.25) or index == int((len(joint_list_one)-1)*0.5) or index == int((len(joint_list_one)-1)*0.75):
                        ctl, ctl_grp = controller_creator(
                        name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{len(ctls_grp)+1}",
                        suffixes=["GRP", "ANM"],
                        lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                        ro=True,
                        parent=self.individual_controllers_grp
                        )
                        ctls_grp.append(ctl_grp)
                    

                    pick_matrix = cmds.createNode("pickMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}_PMX", ss=True)

                    cmds.connectAttr(f"{membran_wm_aim}.outputMatrix", f"{pick_matrix}.inputMatrix")
                    cmds.setAttr(f"{pick_matrix}.useScale", 0)

                    joint = cmds.createNode("joint", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}_JNT", ss=True, parent=self.individual_module_grp)
                    
                    falanges_selected_joints.append(joint_one)
                    falanges_selected_joints.append(joint)
                    falanges_selected_joints.append(joint_two)
                    
                    if index == 0:
                        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{joint}.offsetParentMatrix")
                        ctls.append(joint)

                    else:
                        multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}Offset_MMX", ss=True)
                        multMatrix_wm = cmds.createNode("multMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}WM_MMX", ss=True)
                        inverseMatrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1)}Membrane{name}0{index+1}IMX", ss=True)
                        cmds.connectAttr(f"{pick_matrix_nodes[-1]}.outputMatrix", f"{inverseMatrix}.inputMatrix")

                        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{multMatrix}.matrixIn[0]")
                        cmds.connectAttr(f"{inverseMatrix}.outputMatrix", f"{multMatrix}.matrixIn[1]")
                        cmds.connectAttr(f"{multMatrix}.matrixSum", f"{multMatrix_wm}.matrixIn[0]")
                        cmds.connectAttr(f"{ctls[-1]}.worldMatrix[0]", f"{multMatrix_wm}.matrixIn[1]")
                        if ctl:
                            cmds.connectAttr(f"{multMatrix_wm}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")
                            cmds.connectAttr(f"{ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")
                            ctls.append(ctl)
                        else:
                            cmds.connectAttr(f"{multMatrix_wm}.matrixSum", f"{joint}.offsetParentMatrix")
                            ctls.append(joint)


                   

                    pick_matrix_nodes.append(pick_matrix)
                    membranes_wm_aim.append(membran_wm_aim)
                    mid_positions.append(mid_position)

                for aim_loop, wm_aim in enumerate(membranes_wm_aim):
                    try:
                        cmds.connectAttr(f"{mid_positions[aim_loop+1]}.matrixSum", f"{wm_aim}.primaryTargetMatrix")
                    except IndexError:
                        cmds.connectAttr(f"{mid_positions[aim_loop-1]}.matrixSum", f"{wm_aim}.primaryTargetMatrix")
                        pv = self.primary_aim_vector * -1
                        cmds.setAttr(f"{membran_wm_aim}.primaryInputAxis", pv.x, pv.y, pv.z, type="double3")

                
                plane = cmds.nurbsPlane(p=(0, 0, 0), ax=(0, 1, 0), w=1, lr=1, d=2, u=1, v=len(joint_list_one)-2, ch=0, n=f"{self.side}_{core.number_to_ordinal_word(i+1)}MembraneSkinCluster_NSP")[0]
                cmds.parent(plane, self.individual_module_grp)

                plane_shape = cmds.listRelatives(plane, shapes=True, noIntermediate=True)[0]

                count = 0
                for v_value in range(len(joint_list_one)):
                    for u_value in range(3):
                        pos = cmds.xform(falanges_selected_joints[count], q=True, ws=True, t=True)
                        cmds.xform(f"{plane}.cv[{u_value}][{v_value}]", ws=True, t=pos)
                        count += 1
                
                skincluster = cmds.skinCluster(falanges_selected_joints, plane, toSelectedBones=True, maximumInfluences=1, normalizeWeights=1, name=f"{self.side}_{core.number_to_ordinal_word(i+1)}MembraneSkinCluster_SKN")[0]


                u_row = 10
                v_row = 15
                uv_pin = cmds.createNode("uvPin", name=f"{self.side}_{core.number_to_ordinal_word(i+1).capitalize()}Membrane_UVP", ss=True)
                cmds.connectAttr(f"{plane_shape}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)

                if self.side == "L":
                    cmds.setAttr(f"{uv_pin}.normalAxis", 1)
                    cmds.setAttr(f"{uv_pin}.tangentAxis", 2)
                else:
                    cmds.setAttr(f"{uv_pin}.normalAxis", 1)
                    cmds.setAttr(f"{uv_pin}.tangentAxis", 5)


                count = 0

                for i_u_row in range(u_row):

                    for index in range(v_row):
                        # uv_pin = cmds.createNode("uvPin", name=f"{self.side}_{core.number_to_ordinal_word(i+1).capitalize()}Membrane{i_u_row}{index+1}_UVP", ss=True)
                        cmds.setAttr(f"{uv_pin}.coordinate[{count}].coordinateU", float(i_u_row) / (u_row - 1))
                        cmds.setAttr(f"{uv_pin}.coordinate[{count}].coordinateV", float(index) / (v_row - 1))

                        # cmds.connectAttr(f"{plane_shape}.worldSpace[0]", f"{uv_pin}.deformedGeometry", force=True)

                        joint = cmds.createNode("joint", name=f"{self.side}_{core.number_to_ordinal_word(i+1).capitalize()}Membrane{i_u_row}{index+1}_JNT", ss=True, parent=self.skinning_grp)
                        # cmds.connectAttr(f"{uv_pin}.outputMatrix[{count}]", f"{joint}.offsetParentMatrix", force=True)

                        aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{core.number_to_ordinal_word(i+1).capitalize()}Membrane{i_u_row}{index+1}_AMX", ss=True)
                        cmds.connectAttr(f"{uv_pin}.outputMatrix[{count}]", f"{aim_matrix}.inputMatrix")

                        if index != v_row -1:
                            cmds.connectAttr(f"{uv_pin}.outputMatrix[{count+1}]", f"{aim_matrix}.primaryTargetMatrix")
                        else:
                            cmds.connectAttr(f"{uv_pin}.outputMatrix[{count-1}]", f"{aim_matrix}.primaryTargetMatrix")
                            pv = self.primary_aim_vector * -1
                            cmds.setAttr(f"{aim_matrix}.primaryInputAxis", pv.x, pv.y, pv.z, type="double3")

                        cmds.connectAttr(f"{uv_pin}.outputMatrix[{count}]", f"{aim_matrix}.secondaryTargetMatrix")
                        cmds.setAttr(f"{aim_matrix}.secondaryInputAxis", *self.secondary_aim_vector, type="double3")
                        cmds.setAttr(f"{aim_matrix}.secondaryTargetVector", *self.secondary_aim_vector, type="double3")
                        cmds.setAttr(f"{aim_matrix}.secondaryMode", 2)

                        cmds.connectAttr(f"{aim_matrix}.outputMatrix", f"{joint}.offsetParentMatrix", force=True)


                        count += 1

