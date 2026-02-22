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

class NoseModule():
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

        self.module_trn = cmds.createNode("transform", name=f"C_noseModule_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"C_noseControllers_GRP", ss=True, parent=self.masterWalk_ctl)
        cmds.setAttr(f"{self.controllers_trn}.inheritsTransform", 0)
        self.tangent_controllers_trn = cmds.createNode("transform", name=f"C_noseTangentControllers_GRP", ss=True, parent=self.controllers_trn)

        self.skinning_trn = cmds.createNode("transform", name=f"C_noseFacialSkinning_GRP", ss=True, p=self.skel_grp)
        try:
            parentMatrix = cmds.createNode("parentMatrix", name=f"C_noseModule_PM", ss=True)
            cmds.connectAttr(f"{self.head_ctl}.worldMatrix[0]", f"{parentMatrix}.target[0].targetMatrix", force=True)
            offset = core.get_offset_matrix(f"{self.controllers_trn}.worldMatrix", f"{self.head_ctl}.worldMatrix")
            cmds.setAttr(f"{parentMatrix}.target[0].offsetMatrix", offset, type="matrix")
            cmds.connectAttr(f"{parentMatrix}.outputMatrix", f"{self.controllers_trn}.offsetParentMatrix", force=True)
        except:
            pass

        self.create_chain()

        self.data_exporter.append_data(f"{self.side}_noseModule", 
                            {"skinning_transform": self.skinning_trn,

                            }
                            )


    def create_chain(self):
        self.guides = guide_import(self.guide_name, all_descendents=True, path=None)

        if cmds.attributeQuery("moduleName", node=self.guides[0], exists=True):
            self.enum_str = cmds.attributeQuery("moduleName", node=self.guides[0], listEnum=True)[0]
        cmds.addAttr(self.skinning_trn, longName="moduleName", attributeType="enum", enumName=self.enum_str, keyable=False)


        for guide in self.guides:
            self.side = guide.split("_")[0]

            if "Base" in guide:
                self.base_nose = guide
            if "Tip" in guide:
                self.tip_nose = guide
            if "Main" in guide:
                self.main_nose = guide
            if "Flare" in guide:
                if "L" in self.side:
                    self.l_flare_nose = guide
                if "R" in self.side:
                    self.r_flare_nose = guide
            if "inner" in guide:
                if "L" in self.side:
                    self.l_inner_nose = guide
                if "R" in self.side:
                    self.r_inner_nose = guide

        base_guide = cmds.createNode("aimMatrix", name=f"C_noseBase_AMX", ss=True)
        cmds.connectAttr(f"{self.base_nose}.worldMatrix[0]", f"{base_guide}.inputMatrix", force=True)       
        cmds.connectAttr(f"{self.main_nose}.worldMatrix[0]", f"{base_guide}.primaryTargetMatrix", force=True) 
        cmds.setAttr(f"{base_guide}.primaryInputAxis", 0, -1, 0)

        l_inner_guide = cmds.createNode("aimMatrix", name=f"L_noseInner_AIM", ss=True)
        cmds.connectAttr(f"{self.l_inner_nose}.worldMatrix[0]", f"{l_inner_guide}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.l_flare_nose}.worldMatrix[0]", f"{l_inner_guide}.primaryTargetMatrix", force=True)
        cmds.connectAttr(f"{self.tip_nose}.worldMatrix[0]", f"{l_inner_guide}.secondaryTargetMatrix", force=True)
        cmds.setAttr(f"{l_inner_guide}.secondaryMode", 1)

        l_flare_guide = cmds.createNode("blendMatrix", name=f"L_noseFlare_BLM", ss=True)
        cmds.connectAttr(f"{self.l_flare_nose}.worldMatrix[0]", f"{l_flare_guide}.inputMatrix", force=True)
        cmds.connectAttr(f"{l_inner_guide}.outputMatrix", f"{l_flare_guide}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{l_flare_guide}.target[0].translateWeight", 0)

        r_inner_guide_base = cmds.createNode("aimMatrix", name=f"R_noseInner_AIM", ss=True)
        cmds.connectAttr(f"{self.r_inner_nose}.worldMatrix[0]", f"{r_inner_guide_base}.inputMatrix", force=True)
        cmds.connectAttr(f"{self.r_flare_nose}.worldMatrix[0]", f"{r_inner_guide_base}.primaryTargetMatrix", force=True)
        cmds.connectAttr(f"{self.tip_nose}.worldMatrix[0]", f"{r_inner_guide_base}.secondaryTargetMatrix", force=True)
        cmds.setAttr(f"{r_inner_guide_base}.secondaryMode", 1)
        cmds.setAttr(f"{r_inner_guide_base}.primaryInputAxis", -1, 0, 0)
        r_inner_guide = cmds.createNode("multMatrix", name=f"R_noseInner_MM", ss=True)
        cmds.setAttr(f"{r_inner_guide}.matrixIn[0]", -1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, type="matrix")
        cmds.connectAttr(f"{r_inner_guide_base}.outputMatrix", f"{r_inner_guide}.matrixIn[1]", force=True)
        
        r_flare_guide = cmds.createNode("blendMatrix", name=f"R_noseFlare_BLM", ss=True)
        cmds.connectAttr(f"{self.r_flare_nose}.worldMatrix[0]", f"{r_flare_guide}.inputMatrix", force=True)
        cmds.connectAttr(f"{r_inner_guide}.matrixSum", f"{r_flare_guide}.target[0].targetMatrix", force=True)
        cmds.setAttr(f"{r_flare_guide}.target[0].translateWeight", 0)

        guide_order = [f"{base_guide}.outputMatrix", f"{self.main_nose}.worldMatrix[0]",f"{self.tip_nose}.worldMatrix[0]", f"{l_flare_guide}.outputMatrix",f"{r_flare_guide}.outputMatrix", f"{l_inner_guide}.outputMatrix", f"{r_inner_guide}.matrixSum"]

        ctls = []

        for i, guide in enumerate(guide_order):

            if i >= 0 and i <= 4:
                lock=["visibility"]
            else:
                lock=["tx", "ty", "tz", "rx", "ry", "rz", "visibility"]
                

            name  = f"{guide.split('_')[0]}_{guide.split('_')[1]}"
            ctl, controller_grp = controller_creator(
                name= name,
                suffixes=["GRP", "OFF", "ANM"],
                lock=lock,
                ro=True,
                parent=self.controllers_trn
            )
            ctls.append(ctl)

            cmds.connectAttr(guide, f"{controller_grp[0]}.offsetParentMatrix", force=True)

            mmx = core.local_mmx(ctl, controller_grp[0])

            joint = cmds.createNode("joint", name=f"{name}_JNT", parent=self.skinning_trn)
            cmds.connectAttr(mmx, f"{joint}.offsetParentMatrix", force=True)



        core.local_space_parent(ctls[2], parents=[ctls[1]])

        core.local_space_parent(ctls[5], parents=[ctls[1]])
        core.local_space_parent(ctls[6], parents=[ctls[1]])

        core.local_space_parent(ctls[3], parents=[ctls[5]])
        core.local_space_parent(ctls[4], parents=[ctls[6]])

        