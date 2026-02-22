#Python libraries import
import json
from maya import cmds
from importlib import reload
import maya.api.OpenMaya as om
import math
import maya.mel as mel


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


reload(de_boors_002)
reload(guide_creation)
reload(ss)
reload(core)

AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}

class FalangeModule(object):

    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")
        self.guides_grp = self.data_exporter.get_data("basic_structure", "guides_GRP")

    def hand_distribution(self, guide_name):      
        
        self.hand_guide = guide_import(guide_name, all_descendents=False, path=None)[0]
        if cmds.attributeQuery("moduleName", node=self.hand_guide, exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.hand_guide, listEnum=True)[0]
        else:
            self.enum_str = "———"

        self.side = guide_name.split("_")[0]


        self.individual_module_grp = cmds.createNode("transform", name=f"{self.side}_handModule_GRP", parent=self.modules_grp, ss=True)
        self.individual_controllers_grp = cmds.createNode("transform", name=f"{self.side}_handControllers_GRP", parent=self.masterWalk_ctl, ss=True)

        self.switch_ctl, self.switch_ctl_grp = controller_creator(
            name=f"{self.side}_hand",
            suffixes=["GRP", "SDK"],
            lock=["tx", "ty", "tz" ,"sx", "sy", "sz", "visibility"],
            ro=False,
            parent=self.individual_controllers_grp
        )

        cmds.connectAttr(f"{self.hand_guide}.worldMatrix[0]", f"{self.switch_ctl_grp[0]}.offsetParentMatrix")

        
        cmds.addAttr(self.switch_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.switch_ctl+".extraAttr", channelBox=True, lock=True)
        cmds.addAttr(self.switch_ctl, shortName="switchIkFk", niceName="Switch IK --> FK", maxValue=1, minValue=0,defaultValue=0, keyable=True)
        cmds.addAttr(self.switch_ctl, shortName="bendysVis", niceName="Bendys Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(self.switch_ctl+".bendysVis", channelBox=True)
        cmds.addAttr(self.switch_ctl, shortName="curvature", niceName="Curvature", maxValue=1, minValue=0,defaultValue=0, keyable=True)

        

        self.ik_visibility_rev = cmds.createNode("reverse", name=f"{self.side}_handFkVisibility_REV", ss=True)
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{self.ik_visibility_rev}.inputX")

        if self.side == "L":
            self.primary_aim = "x"
            if core.DataManager.get_asset_name() == "azhurean":
                self.secondary_aim = "-y"
            else:
                self.secondary_aim = "y"

        elif self.side == "R":
            self.primary_aim = "-x"
            if core.DataManager.get_asset_name() == "azhurean":
                self.secondary_aim = "y"
            else:
                self.secondary_aim = "-y"

        final_path = core.DataManager.get_guide_data()


        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)

        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        skinning_joints_list = []
        for template_name, guides in guides_data.items():
            if not isinstance(guides, dict):
                continue    

            for guide_name, guide_info in guides.items():
                if guide_info.get("parent") == self.hand_guide:
                    guides_pass = guide_import(guide_name, all_descendents=True, path=None)
                    self.names = [name.split("_")[1] for name in guides_pass[1:]]

                    skinning_joints = self.make(guide_name=guides_pass)
                    skinning_joints_list.append(skinning_joints)

                    
                    self.data_exporter.append_data(f"{self.side}_{self.names[0]}Module", 
                                        {"skinning_transform": self.skinnging_grp,
                                         "fk_ctls": self.fk_ctls,
                                         "pv_ctl": self.pv_ik_ctl,
                                         "root_ctl": self.root_ik_ctl,
                                         "end_ik": self.hand_ik_ctl,
                                         "settings_ctl": self.switch_ctl,
                                         "metacarpal_ctl": self.metacarpal_ctl,
                                        }
                                        )
                    
        data={
            "module": self.individual_module_grp,
            # "skinning_transform": self.skinnging_grp,
            "skinning_transform": None,
            "controllers": self.individual_controllers_grp,
            "attributes_ctl": self.switch_ctl
        }
        
        core.DataManager.set_finger_data(core.DataManager, side=self.side, data=data)

    def make(self, guide_name):

        self.metatarsal = guide_name[0]
        self.guides = guide_name[1:]


        # cmds.connectAttr(f"{self.metatarsal}.outputMatrix", f"{self.guides[0]}.offsetParentMatrix")

        """
        Create a limb rig with controllers and constraints.
        This function sets up the basic structure for a limb, including controllers and constraints.
        """      
        self.skinnging_grp = cmds.createNode("transform", name=f"{self.side}_{self.names[0]}SkinningJoints_GRP", parent=self.skel_grp, ss=True)
        
        self.primary_aim_vector = om.MVector(AXIS_VECTOR[self.primary_aim])
        self.secondary_aim_vector = om.MVector(AXIS_VECTOR[self.secondary_aim])

        cmds.addAttr(self.skinnging_grp, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)

        order = [[self.guides[0], self.guides[1], self.guides[2]], [self.guides[1], self.guides[2], self.guides[0]], [self.guides[2], self.guides[3], self.guides[1]]]

        aim_matrix_guides = []

        for i in range(len(self.guides)-1):

            aim_matrix = cmds.createNode("aimMatrix", name=f"{self.side}_{self.names[i]}Guide_AMX", ss=True)

            cmds.setAttr(aim_matrix + ".primaryInputAxis", *self.primary_aim_vector, type="double3")
            cmds.setAttr(aim_matrix + ".secondaryInputAxis", *self.secondary_aim_vector, type="double3")
            cmds.setAttr(aim_matrix + ".secondaryTargetVector", 0,1,0, type="double3")
            
            cmds.setAttr(aim_matrix + ".primaryMode", 1)
            cmds.setAttr(aim_matrix + ".secondaryMode", 1)

            cmds.connectAttr(order[i][0] + ".worldMatrix[0]", aim_matrix + ".inputMatrix")
            cmds.connectAttr(order[i][1] + ".worldMatrix[0]", aim_matrix + ".primaryTargetMatrix")
            cmds.connectAttr(order[i][2] + ".worldMatrix[0]", aim_matrix + ".secondaryTargetMatrix")

            aim_matrix_guides.append(aim_matrix)

        
        blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.names[-1]}Guide_BLM", ss=True)
        cmds.connectAttr(f"{aim_matrix_guides[-1]}.outputMatrix", f"{blend_matrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.guides[-1]}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)

        meta_name = ''.join(ch for ch in self.names[0] if not ch.isdigit())


        metatarsal_blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_{meta_name}MetacarpalGuide_BLM", ss=True)
        cmds.connectAttr(f"{aim_matrix_guides[0]}.outputMatrix", f"{metatarsal_blend_matrix}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.metatarsal}.worldMatrix[0]", f"{metatarsal_blend_matrix}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{metatarsal_blend_matrix}.target[0].scaleWeight", 0)
        cmds.setAttr(f"{metatarsal_blend_matrix}.target[0].rotateWeight", 0)
        cmds.setAttr(f"{metatarsal_blend_matrix}.target[0].shearWeight", 0)

        self.metacarpal_ctl, self.metacarpal_grp = controller_creator(
            name=f"{self.side}_{meta_name}Metacarpal",
            suffixes=["GRP", "ANM"],
            lock=["sx","sz","sy","visibility"],
            ro=True,
            parent=self.individual_controllers_grp
        )

        cmds.connectAttr(f"{metatarsal_blend_matrix}.outputMatrix", f"{self.metacarpal_grp[0]}.offsetParentMatrix")

        joint = cmds.createNode("joint", name=f"{self.side}_{meta_name}Metacarpal_JNT", ss=True, parent=self.skinnging_grp)
        cmds.connectAttr(f"{self.metacarpal_ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")

        self.guides_matrix = [aim_matrix_guides[0], aim_matrix_guides[1], aim_matrix_guides[2], blend_matrix]

        self.fk_rig()

        return self.joints

    def fk_rig(self):
        """
        Create FK chain for the limb.
        This function creates a forward kinematics chain for the limb, including controllers and constraints.
        """
        self.fk_ctls = []
        self.fk_grps = []
        self.fk_offset = []
        self.fk_sdks = []
        for i, guide in enumerate(self.guides_matrix):

            ctl, ctl_grp = controller_creator(
                name=self.guides[i].replace("_GUIDE", "Fk"),
                suffixes=["GRP", "SDK", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.fk_ctls[-1] if self.fk_ctls else self.individual_controllers_grp)

            if not i ==len(self.guides_matrix)-1:
                cmds.addAttr(ctl, shortName="strechySep", niceName="Strechy ———", enumName="———",attributeType="enum", keyable=True)
                cmds.setAttr(ctl+".strechySep", channelBox=True, lock=True)
                cmds.addAttr(ctl, shortName="stretch", niceName="Stretch",minValue=1,defaultValue=1, keyable=True)

                

            if not i == 0:
                subtract = cmds.createNode("subtract", name=f"{self.side}_{self.names[i]}FkOffset0{i}_SUB", ss=True)
                cmds.connectAttr(f"{self.fk_ctls[-1]}.stretch", f"{subtract}.input1")
                cmds.setAttr( f"{subtract}.input2", 1)
                cmds.connectAttr(f"{subtract}.output", f"{ctl_grp[0]}.tx")
                

                offset_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[i]}FkOffset0{i+1}_MMX", ss=True)
                inverse_matrix = cmds.createNode("inverseMatrix", name=f"{self.side}_{self.names[i]}FkOffset0{i+1}_IMX", ss=True)
                cmds.connectAttr(f"{guide}.outputMatrix", f"{offset_multMatrix}.matrixIn[0]")

                cmds.connectAttr(f"{self.guides_matrix[i-1]}.outputMatrix", f"{inverse_matrix}.inputMatrix")

                cmds.connectAttr(f"{inverse_matrix}.outputMatrix", f"{offset_multMatrix}.matrixIn[1]")
            

                cmds.connectAttr(f"{offset_multMatrix}.matrixSum", f"{ctl_grp[0]}.offsetParentMatrix")


                for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                    try:
                        cmds.setAttr(f"{ctl_grp[0]}.{attr}", 0)
                    except:
                        pass

            else:
                cmds.connectAttr(f"{guide}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix")




            self.fk_ctls.append(ctl)
            self.fk_grps.append(ctl_grp) 
            self.fk_sdks.append(ctl_grp[1])

        self.fk_wm = [f"{ctl}.worldMatrix[0]" for ctl in self.fk_ctls]

        self.ik_rig()

    def ik_rig(self):
        """
        Create IK chain for the limb.
        This function creates an inverse kinematics chain for the limb, including controllers and constraints.
        """
        self.ik_controllers = cmds.createNode("transform", name=f"{self.side}_{self.names[0]}IkControllers_GRP", parent=self.individual_controllers_grp, ss=True)

        self.root_ik_ctl, self.root_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.names[0]}RootIk",
            suffixes=["GRP", "ANM"],
            lock=["rx", "ry", "rz", "sx","sz","sy","visibility"],
            ro=True,
            parent=self.ik_controllers
        )
        self.pv_ik_ctl, self.pv_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.names[1]}PV",
            suffixes=["GRP", "ANM"],
            lock=["rx", "ry", "rz", "sx","sz","sy","visibility"],
            ro=False,
            parent=self.ik_controllers

        )
        self.hand_ik_ctl, self.hand_ik_ctl_grp = controller_creator(
            name=f"{self.side}_{self.names[-1]}Ik",
            suffixes=["GRP", "ANM"],
            lock=["visibility"],
            ro=True,
            parent=self.ik_controllers

        )

        cmds.addAttr(self.hand_ik_ctl, shortName="attachedFk", niceName="Fk ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.hand_ik_ctl+".attachedFk", channelBox=True, lock=True)
        cmds.addAttr(self.hand_ik_ctl, shortName="attachedFKVis", niceName="Attached FK Visibility", attributeType="bool", keyable=False)
        cmds.setAttr(self.hand_ik_ctl+".attachedFKVis", channelBox=True)

        self.attached_fk_vis = cmds.createNode("condition", name=f"{self.side}_{self.names[-1]}AttachedFk_VIS", ss=True)
        cmds.setAttr(f"{self.attached_fk_vis}.operation", 0)
        cmds.setAttr(f"{self.attached_fk_vis}.colorIfFalseR", 0)
        cmds.setAttr(f"{self.attached_fk_vis}.secondTerm", 0)
        cmds.connectAttr(f"{self.hand_ik_ctl}.attachedFKVis", f"{self.attached_fk_vis}.colorIfTrueR")
        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{self.attached_fk_vis}.firstTerm")

        cmds.connectAttr(self.guides_matrix[-1] + ".outputMatrix", f"{self.hand_ik_ctl_grp[0]}.offsetParentMatrix")

        cmds.addAttr(self.pv_ik_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.pv_ik_ctl+".extraAttr", channelBox=True, lock=True)
        
        cmds.connectAttr(f"{self.guides_matrix[0]}.outputMatrix", f"{self.root_ik_ctl_grp[0]}.offsetParentMatrix")      

        pv_pos_multMatrix = cmds.createNode("multMatrix", name=f"{self.side}_{self.names[1]}PVPosition_MMX", ss=True)
        cmds.connectAttr(f"{self.guides_matrix[1]}.outputMatrix", f"{pv_pos_multMatrix}.matrixIn[1]")
        cmds.connectAttr(f"{pv_pos_multMatrix}.matrixSum", f"{self.pv_ik_ctl_grp[0]}.offsetParentMatrix")

        pv_pos_4b4 = cmds.createNode("fourByFourMatrix", name=f"{self.side}_{self.names[1]}PVPosition_F4X", ss=True)
        cmds.connectAttr(f"{pv_pos_4b4}.output", f"{pv_pos_multMatrix}.matrixIn[0]")

        pos1 = cmds.xform(self.guides[0], q=True, ws=True, t=True)
        pos2 = cmds.xform(self.guides[1], q=True, ws=True, t=True)

        distance01 = math.sqrt(sum([(a - b) ** 2 for a, b in zip(pos1, pos2)]))

        pos3 = cmds.xform(self.guides[0], q=True, ws=True, t=True)
        pos4 = cmds.xform(self.guides[1], q=True, ws=True, t=True)

        distance02 = math.sqrt(sum([(a - b) ** 2 for a, b in zip(pos3, pos4)]))

        if self.side == "R":
            cmds.setAttr(f"{pv_pos_4b4}.in31",(distance01+distance02)*-1)
        else:
            cmds.setAttr(f"{pv_pos_4b4}.in31", (distance01+distance02))


        if not cmds.pluginInfo("ikSpringSolver", query=True, loaded=True):
            cmds.loadPlugin("ikSpringSolver")
        
        mel.eval("ikSpringSolver")
        joints = []
        for i, guide in enumerate(self.guides_matrix):
            joint = cmds.createNode("joint", name=guide.replace("Guide_AMX", "Ik_JNT").replace("Guide_BLM", "Ik_JNT"), ss=True, parent=self.individual_module_grp if not joints else joints[-1])
            if i == 0:
                # pick_matrix = cmds.createNode("pickMatrix", name=f"{self.side}_{self.names[0]}RootIk_PIM", ss=True)
                # cmds.connectAttr(f"{self.root_ik_ctl}.worldMatrix[0]", f"{pick_matrix}.inputMatrix")
                # cmds.setAttr(f"{pick_matrix}.useRotate", 0)
                # cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{joint}.offsetParentMatrix")
                blend_matrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.names[0]}RootIk_BLM", ss=True)
                cmds.connectAttr(f"{self.root_ik_ctl}.worldMatrix[0]", f"{blend_matrix}.target[0].targetMatrix")
                cmds.connectAttr(f"{self.guides_matrix[0]}.outputMatrix", f"{blend_matrix}.inputMatrix")
                cmds.setAttr(f"{blend_matrix}.target[0].rotateWeight", 0)
                cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{joint}.offsetParentMatrix")

                # cmds.connectAttr(f"{self.root_ik_ctl}.worldMatrix[0]", f"{joint}.offsetParentMatrix")
            else:
                temp_trn = cmds.createNode("transform", name=guide.replace("Guide_AMX", "Ik_Temp_TRN").replace("Guide_BLM", "Ik_Temp_TRN"), ss=True)
                cmds.connectAttr(f"{guide}.outputMatrix", f"{temp_trn}.offsetParentMatrix")
                cmds.matchTransform(joint, temp_trn, position=True, rotation=True)
                cmds.delete(temp_trn)

            joints.append(joint)

        for joint in joints:
            cmds.setAttr(f"{joint}.rz", -5)

        spring_solver = cmds.ikHandle(n=f"{self.side}_{self.names[0]}IkHandle", sj=joints[0], ee=joints[-1], sol="ikSpringSolver")
        cmds.poleVectorConstraint(f"{self.pv_ik_ctl}", spring_solver[0])

        self.zero_value = cmds.createNode("floatConstant", name=f"{self.side}_{self.names[0]}IkHandle0_FC", ss=True)
        cmds.setAttr(f"{self.zero_value}.inFloat", 0)

        pick_matrix = cmds.createNode("pickMatrix", name=f"{self.side}_{self.names[0]}IkHandle_PIM", ss=True)
        cmds.connectAttr(f"{self.hand_ik_ctl}.worldMatrix[0]", f"{pick_matrix}.inputMatrix")
        cmds.setAttr(f"{pick_matrix}.useRotate", 0)

        for attr in ["tx", "ty", "tz"]:
            cmds.connectAttr(f"{self.zero_value}.outFloat", f"{spring_solver[0]}.{attr}")

        cmds.connectAttr(f"{pick_matrix}.outputMatrix", f"{spring_solver[0]}.offsetParentMatrix")
        
        cmds.setAttr(f"{joints[-1]}.rz", 0)


        cmds.parent(spring_solver[0], self.individual_module_grp)

        self.ik_wm = [f"{joint}.worldMatrix[0]" for joint in joints]

        self.attached_fk()

    def attached_fk(self):
        """
        Creates the attached FK controllers for the neck module, including sub-neck controllers and joints.

        Args:
            self: Instance of the SpineModule class.
        Returns:
            list: A list of sub-neck joint names created for the attached FK system.
        """
        
        ctls_sub_neck = []

        self.attached_fk_ctls = []
        self.attached_fk_sdks = []
        for i, joint in enumerate(self.ik_wm):
            name = joint.split(".")[0].split("_")[1]

            ctl, controller_grp = controller_creator(
                name=f"{self.side}_{name}AttachedFk",
                suffixes=["GRP", "SDK", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
                parent=ctls_sub_neck[-1] if ctls_sub_neck else self.individual_controllers_grp
            )

            if i == 0:
                cmds.setAttr(f"{controller_grp[0]}.inheritsTransform", 0)
                # cmds.connectAttr(f"{self.hand_ik_ctl}.attachedFKVis", f"{controller_grp[0]}.visibility")
                cmds.connectAttr(f"{self.attached_fk_vis}.outColorR", f"{controller_grp[0]}.visibility")
                cmds.connectAttr(f"{joint}", f"{controller_grp[0]}.offsetParentMatrix")

            else:
                mmt = cmds.createNode("multMatrix", n=f"{self.side}_{name}SubAttachedFk0{i+1}_MMT")

                inverse = cmds.createNode("inverseMatrix", n=f"{self.side}_{name}SubAttachedFk0{i+1}_IMX")
                cmds.connectAttr(f"{self.ik_wm[i-1]}", f"{inverse}.inputMatrix")
                cmds.connectAttr(f"{joint}", f"{mmt}.matrixIn[0]")
                cmds.connectAttr(f"{inverse}.outputMatrix", f"{mmt}.matrixIn[1]")
                cmds.connectAttr(f"{mmt}.matrixSum", f"{controller_grp[0]}.offsetParentMatrix")

                for attr in ["translateX","translateY","translateZ", "rotateX", "rotateY", "rotateZ"]:
                    cmds.setAttr(f"{controller_grp[0]}.{attr}", 0)

            ctls_sub_neck.append(ctl)
            self.attached_fk_ctls.append(ctl)
            self.attached_fk_sdks.append(controller_grp[1])

        self.ik_wm = [f"{ctl}.worldMatrix[0]" for ctl in ctls_sub_neck]

        self.pairblends()

    def pairblends(self):

        cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{self.fk_grps[0][0]}.visibility", force=True)
        cmds.connectAttr(f"{self.ik_visibility_rev}.outputX", f"{self.ik_controllers}.visibility")


        self.blend_wm = []
        for i, (fk, ik) in enumerate(zip(self.fk_wm, self.ik_wm)):
            name = fk.replace("Fk_CTL.worldMatrix[0]", "")

            blendMatrix = cmds.createNode("blendMatrix", name=f"{name}_BLM", ss=True)
            cmds.connectAttr(ik, f"{blendMatrix}.inputMatrix")
            cmds.connectAttr(fk, f"{blendMatrix}.target[0].targetMatrix")
            cmds.connectAttr(f"{self.switch_ctl}.switchIkFk", f"{blendMatrix}.target[0].weight")

            self.blend_wm.append(f"{blendMatrix}.outputMatrix")

        name = self.blend_wm[0].replace("_BLM.outputMatrix", "")
        
        self.shoulder_rotate_matrix = self.blend_wm[0]

        self.bendys()


    def getClosestParamToWorldMatrix(self, curveDagPath, worldMatrix):
        """
        Returns the closest parameter (u) on the curve to the given worldMatrix.
        """
        curveFn = om.MFnNurbsCurve(curveDagPath)

        # Extract the translation as an MPoint
        translation = om.MTransformationMatrix(worldMatrix).translation(om.MSpace.kWorld)
        point = om.MPoint(translation)

        # closestPoint() returns (MPoint, paramU)
        closestPoint, paramU = curveFn.closestPoint(point, space=om.MSpace.kWorld)

        return paramU





    def bendys(self):
        self.bendy_controllers = cmds.createNode("transform", name=f"{self.side}_{self.names[1]}BendyControllers_GRP", parent=self.individual_controllers_grp, ss=True)
        cmds.connectAttr(f"{self.switch_ctl}.bendysVis", f"{self.bendy_controllers}.visibility")
        cmds.setAttr(f"{self.bendy_controllers}.inheritsTransform", 0)

        curve = cmds.curve(d=3, p=[(0, 0, 0)] * 4, name=f"{self.side}_{self.names[1]}Bendy_CRV")
        curve_shape = cmds.listRelatives(curve, shapes=True)[0]

        for i, pos in enumerate(self.blend_wm):
            decompose = cmds.createNode("decomposeMatrix", name=f"{pos.replace('.outputMatrix', '')}_DMT", ss=True)
            cmds.connectAttr(f"{pos}", f"{decompose}.inputMatrix")
            cmds.connectAttr(f"{decompose}.outputTranslate", f"{curve_shape}.controlPoints[{i}]")

        parameters = []
        bendy_ctls = []
        stiff_joints = []
        for i, bendy in enumerate(["UpperBendy", "MiddleBendy", "LowerBendy"]):
            ctl, ctl_grp = controller_creator(
                name=f"{self.side}_{self.names[i]}{bendy}",
                suffixes=["GRP", "ANM"],
                lock=["scaleX", "scaleY", "scaleZ", "visibility"],
                ro=True,
            )

            cmds.parent(ctl_grp[0], self.bendy_controllers)
            bendy_ctls.append(ctl)

            initial_matrix = self.shoulder_rotate_matrix if i == 0 else self.blend_wm[i]

            blendMatrix = cmds.createNode("blendMatrix", name=f"{self.side}_{self.names[i]}{bendy}_BLM", ss=True)
            cmds.connectAttr(f"{initial_matrix}", f"{blendMatrix}.inputMatrix")
            cmds.connectAttr(f"{self.blend_wm[i+1]}", f"{blendMatrix}.target[0].targetMatrix")
            cmds.setAttr(f"{blendMatrix}.target[0].scaleWeight", 0)
            cmds.setAttr(f"{blendMatrix}.target[0].translateWeight", 0.5)
            cmds.setAttr(f"{blendMatrix}.target[0].rotateWeight", 0)
            cmds.setAttr(f"{blendMatrix}.target[0].shearWeight", 0)

            if i == 0:
                cmds.connectAttr(f"{self.blend_wm[i]}", f"{blendMatrix}.target[1].targetMatrix")
                cmds.setAttr(f"{blendMatrix}.target[1].scaleWeight", 0)
                cmds.setAttr(f"{blendMatrix}.target[1].translateWeight", 0)
                cmds.setAttr(f"{blendMatrix}.target[1].rotateWeight", 0.5)
                cmds.setAttr(f"{blendMatrix}.target[1].shearWeight", 0)

            cmds.connectAttr(f"{blendMatrix}.outputMatrix", f"{ctl_grp[0]}.offsetParentMatrix") 
    
            joint01 = cmds.createNode("joint", name=f"{self.side}_{self.names[i]}{bendy}Roll01_JNT", ss=True, parent=self.individual_module_grp)
            joint02 = cmds.createNode("joint", name=f"{self.side}_{self.names[i]}{bendy}Roll02_JNT", ss=True, parent=joint01)
            pickMatrix = cmds.createNode("pickMatrix", name=f"{self.side}_{self.names[i]}{bendy}Roll_PIM", ss=True)
            cmds.setAttr(f"{pickMatrix}.useRotate", 0)

            cmds.connectAttr(self.blend_wm[i], f"{pickMatrix}.inputMatrix")
            cmds.connectAttr(f"{pickMatrix}.outputMatrix", f"{joint01}.offsetParentMatrix")


            distance_node = cmds.createNode("distanceBetween", name=f"{self.side}_{self.names[i]}{bendy}Distance_DB", ss=True)
            cmds.connectAttr(f"{self.blend_wm[i]}", f"{distance_node}.inMatrix1")
            cmds.connectAttr(f"{self.blend_wm[i+1]}", f"{distance_node}.inMatrix2")

            distance_normalized = cmds.createNode("divide", name=f"{self.side}_{self.names[i]}{bendy}DistanceNormalized_DIV", ss=True)
            cmds.connectAttr(f"{distance_node}.distance", f"{distance_normalized}.input1")
            cmds.connectAttr(f"{self.masterWalk_ctl}.globalScale", f"{distance_normalized}.input2")

            if self.side == "L":
                cmds.connectAttr(f"{distance_normalized}.output", f"{joint02}.translateX")
            else:
                negate_translate = cmds.createNode("negate", name=f"{self.side}_{self.names[i]}{bendy}NegateTranslate_NEG", ss=True)
                cmds.connectAttr(f"{distance_normalized}.output", f"{negate_translate}.input")
                cmds.connectAttr(f"{negate_translate}.output", f"{joint02}.translateX")

            # cmds.connectAttr(f"{distance_node}.distance", f"{joint02}.translateX")

            ik_handle_sc = cmds.ikHandle(name=f"{self.side}_{self.names[i]}{bendy}Roll_IK", sj=joint01, ee=joint02, sol="ikSCsolver")[0]
            cmds.parent(ik_handle_sc, self.individual_module_grp)
            cmds.connectAttr(self.blend_wm[i+1], f"{ik_handle_sc}.offsetParentMatrix")
            for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
                cmds.connectAttr(f"{self.zero_value}.outFloat", f"{ik_handle_sc}.{attr}")

            cvMatrices = [self.blend_wm[i], f"{ctl}.worldMatrix[0]", f"{joint02}.worldMatrix[0]"]

            self.twist_number = 5

            t_values = []
            for index in range(self.twist_number):
                t = 0.95 if index == self.twist_number - 1 else index / (float(self.twist_number) - 1)
                t_values.append(t)

 
            skinning_joints = de_boors_002.de_boor_ribbon(aim_axis=self.primary_aim, up_axis=self.secondary_aim, cvs= cvMatrices, num_joints=self.twist_number, name = f"{self.side}_{self.names[i]}{bendy}", parent=self.skinnging_grp, custom_parm=t_values, negate_secundary=False)

            if bendy == "LowerBendy":
                joint = cmds.createNode("joint", name= f"{self.side}_{self.names[i]}{bendy}0{self.twist_number+1}_JNT", ss=True, parent=self.skinnging_grp)
                cmds.connectAttr(f"{self.blend_wm[i+1]}", f"{joint}.offsetParentMatrix")
                skinning_joints.append(joint)


            for joint in skinning_joints:

                stiff_joints.append(joint)

                selection_list = om.MSelectionList()
                selection_list.add(curve)
                curve_dag_path = selection_list.getDagPath(0)

                ctl_sel = om.MSelectionList()
                ctl_sel.add(joint)
                ctlDag = ctl_sel.getDagPath(0)
                worldMatrix = ctlDag.inclusiveMatrix()

                u = self.getClosestParamToWorldMatrix(curveDagPath=curve_dag_path, worldMatrix=worldMatrix)
                parameters.append(u)

        clean_name = ''.join([c for c in f"{self.side}_{self.names[1]}Curvature" if not c.isdigit()])
        curvature_joints = de_boors_002.de_boor_ribbon(
            aim_axis=self.primary_aim,
            up_axis=self.secondary_aim,
            cvs=self.blend_wm,
            num_joints=len(parameters),
            name=clean_name,
            parent=self.skinnging_grp,
            custom_parm=parameters
        )

        cmds.delete(curve)
        self.joints = []

        for i, (stiff, curvature) in enumerate(zip(stiff_joints, curvature_joints)):
            stiff_input = cmds.listConnections(f"{stiff}.offsetParentMatrix", plugs=True, source=True, destination=False)
            curvature_input = cmds.listConnections(f"{curvature}.offsetParentMatrix", plugs=True, source=True, destination=False)

            name = curvature.replace("Curvature", "").replace("JNT", "")
            blend_matrix = cmds.createNode("blendMatrix", n=f"{name}WM_BLM", ss=True)
            cmds.connectAttr(f"{stiff_input[0]}", f"{blend_matrix}.inputMatrix")
            cmds.connectAttr(f"{curvature_input[0]}", f"{blend_matrix}.target[0].targetMatrix")
            cmds.connectAttr(f"{self.switch_ctl}.curvature", f"{blend_matrix}.target[0].weight")
            joint = cmds.createNode("joint", name=f"{name}JNT", ss=True, parent=self.skinnging_grp)
            cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{joint}.offsetParentMatrix")
            self.joints.append(joint)
            cmds.delete(stiff, curvature)

        # QUEDA HACER EL BLENDING

        index = int(len(self.joints)//3)

        core.pv_locator(name=f"{self.side}_{self.names[1]}PVLocator", parents=[self.pv_ik_ctl, self.joints[index]], parent_append=self.ik_controllers)

        self.attributes()

    def attributes(self):

        """
        Add attributes to the hand controller for CURL, SPREAD, and FIST controls.
        """

        # Connect hand rotations to the fingers SDK (attached and FK)

        for sdk in self.attached_fk_sdks:
            cmds.connectAttr(f"{self.switch_ctl}.rx", f"{sdk}.rx")
            cmds.connectAttr(f"{self.switch_ctl}.rz", f"{sdk}.rz")

            if "01" in sdk or "02" in sdk or "03" in sdk:
                continue
            else:
                if "first" in sdk or "fourth" in sdk:
                    multiply = cmds.createNode("multiply", n=sdk.replace("SDK", "MLT"))
                    cmds.connectAttr(f"{self.switch_ctl}.ry", f"{multiply}.input[0]")
                    if "first" in sdk:
                        condition_node = cmds.createNode("condition", n=sdk.replace("SDK", "CON"))
                        cmds.setAttr(f"{condition_node}.operation", 4) # Less
                        cmds.setAttr(f"{condition_node}.colorIfTrueR", 1.4)
                        cmds.setAttr(f"{condition_node}.colorIfFalseR", 0.3)
                        cmds.connectAttr(f"{self.switch_ctl}.ry", f"{condition_node}.firstTerm")
                        cmds.connectAttr(f"{condition_node}.outColorR", f"{multiply}.input[1]")

                    else:
                        cmds.setAttr(f"{multiply}.input[1]", 0.8)
                    cmds.connectAttr(f"{multiply}.output", f"{sdk}.ry")
                else:
                    cmds.connectAttr(f"{self.switch_ctl}.ry", f"{sdk}.ry")
            
            

        for sdk in self.fk_sdks: 
            if "03" not in sdk: # Avoid last controller
                cmds.connectAttr(f"{self.switch_ctl}.rx", f"{sdk}.rx")
                cmds.connectAttr(f"{self.switch_ctl}.rz", f"{sdk}.rz")
                
                if "01" in sdk or "02" in sdk or "03" in sdk:
                    continue
                else:
                    if "first" in sdk or "fourth" in sdk:
                        multiply = cmds.createNode("multiply", n=sdk.replace("SDK", "MLT"))
                        cmds.connectAttr(f"{self.switch_ctl}.ry", f"{multiply}.input[0]")
                        if "first" in sdk:
                            condition_node = cmds.createNode("condition", n=sdk.replace("SDK", "CON"))
                            cmds.setAttr(f"{condition_node}.operation", 4) # Less
                            cmds.setAttr(f"{condition_node}.colorIfTrueR", 1.4)
                            cmds.setAttr(f"{condition_node}.colorIfFalseR", 0.3)
                            cmds.connectAttr(f"{self.switch_ctl}.ry", f"{condition_node}.firstTerm")
                            cmds.connectAttr(f"{condition_node}.outColorR", f"{multiply}.input[1]")

                        else:
                            cmds.setAttr(f"{multiply}.input[1]", 0.8)
                        cmds.connectAttr(f"{multiply}.output", f"{sdk}.ry")
                    else:
                        cmds.connectAttr(f"{self.switch_ctl}.ry", f"{sdk}.ry")

            


        



# cmds.file(new=True, force=True)

# core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/test_03.guides")
# core.DataManager.set_ctls_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/curves/AYCHEDRAL_curves_001.json")

# basic_structure.create_basic_structure(asset_name="dragon")
# a = falangeModule("L_firstMetacarpal_GUIDE").make()
