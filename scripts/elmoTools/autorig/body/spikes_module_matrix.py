import maya.cmds as cmds
from elmoTools.utils.curve_tool import controller_creator
from elmoTools.utils.guide_creation import guide_import
from elmoTools.utils.core import get_closest_transform
from elmoTools.utils.space_switch import fk_switch
from elmoTools.utils import data_export
import maya.api.OpenMaya as om
from importlib import reload
import re
reload(data_export)


class SpikesModule(object):
    
    def __init__(self):

        self.data_exporter = data_export.DataExport()

        self.modules_grp = self.data_exporter.get_data("basic_structure", "modules_GRP")
        self.skel_grp = self.data_exporter.get_data("basic_structure", "skel_GRP")
        self.masterWalk_ctl = self.data_exporter.get_data("basic_structure", "masterWalk_CTL")

        self.neck_skinning = self.data_exporter.get_data(f"C_neckModule", "skinning_transform")
        self.spine_skinning = self.data_exporter.get_data(f"C_spineModule", "skinning_transform")
        self.tail_skinning = self.data_exporter.get_data(f"C_tailModule", "skinning_transform")


    def make(self, guide_name):

        """
        Create the spikes module
        
        """

        self.guides = guide_import(guide_name, all_descendents=True, useGuideRotation=True)
        self.side = self.guides[0].split("_")[0]

        self.name = guide_name.split("_")[1]
        self.name = re.sub(r"\d+", "", self.name)

        self.ctl_guide = self.guides[0]
        self.spikes_guides = self.guides[1:]

        self.module_trn = cmds.createNode("transform", name=f"{self.side}_{self.name}Module_GRP", ss=True, parent=self.modules_grp)
        self.controllers_trn = cmds.createNode("transform", name=f"{self.side}_{self.name}Controllers_GRP", ss=True, parent=self.masterWalk_ctl)
        self.skinning_trn = cmds.createNode("transform", name=f"{self.side}_{self.name}Skinning_GRP", ss=True, parent=self.skel_grp)   

        self.setup_wave_on_chain()

        self.data_exporter.append_data(
            f"{self.side}_{self.name}Module",
            {
                "skinning_transform": self.skinning_trn,
            }
        )


    def setup_wave_on_chain(self, axis="rotateZ"):
        """
        Creates a wave setup on a joint chain driven by a curve's custom attributes.
        """
        self.settings_ctl, self.settings_grp = controller_creator(
                    name=f"{self.side}_{self.name}Attributes",
                    suffixes=["GRP"],
                    parent=self.controllers_trn,
                    lock=["tx", "ty", "tz" ,"rx", "ry", "rz", "sx", "sy", "sz", "visibility"],
                    ro=False
                )
        
        cmds.addAttr(self.settings_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———",attributeType="enum", keyable=True)
        cmds.setAttr(self.settings_ctl+".extraAttr", channelBox=True, lock=True)

        cmds.connectAttr(f"{self.ctl_guide}.worldMatrix[0]", f"{self.settings_grp[0]}.offsetParentMatrix")

        joints_default = []

        for skinning_grp in [self.neck_skinning, self.spine_skinning, self.tail_skinning]:
            relatives = cmds.listRelatives(skinning_grp, children=True, type="transform") or []
            for r in relatives:
                joints_default.append(r)
        if joints_default:
            pos = cmds.xform(self.ctl_guide, q=True, ws=True, t=True)
            closest = get_closest_transform(pos, joints_default)

            fk_switch(target = self.settings_ctl, sources= [closest])

            cmds.setAttr(f"{self.settings_ctl}.RotateValue", keyable=False, channelBox=False)
            cmds.setAttr(f"{self.settings_ctl}.SpaceSwitchSep", keyable=False, channelBox=False)
            cmds.setAttr(f"{self.settings_ctl}.TranslateValue", keyable=False, channelBox=False)

        joints = []
        for guide in self.spikes_guides:
            joint = cmds.createNode("joint", name=guide.replace("GUIDE", "JNT"), parent=self.skinning_trn)
            cmds.connectAttr(f"{guide}.worldMatrix[0]", f"{joint}.offsetParentMatrix")
            joints.append(joint)


        attr_data = {
            "waveAmp": 15.0, 
            "waveSpeed": 5.0, 
            "waveOffset": 10
        }
        
        for attr, val in attr_data.items():
            if not cmds.attributeQuery(attr, node=self.settings_ctl, exists=True):
                cmds.addAttr(self.settings_ctl, ln=attr, at="double", k=True, dv=val)

        time_mult = cmds.createNode("multiply", n=f"{self.settings_ctl}_time_mult")
        
        cmds.connectAttr("time1.outTime", f"{time_mult}.input[0]")
        cmds.connectAttr(f"{self.settings_ctl}.waveSpeed", f"{time_mult}.input[1]")

        for i, jnt in enumerate(joints):
            cmds.setAttr(f"{jnt}.rotate", 0, 0, 0)
            
            name = jnt.split("|")[-1]

            offset_mult = cmds.createNode("multiply", n=f"{name}_offset_mult")
            
            cmds.setAttr(f"{offset_mult}.input[0]", float(i))
            cmds.connectAttr(f"{self.settings_ctl}.waveOffset", f"{offset_mult}.input[1]")

            phase_sum = cmds.createNode("sum", n=f"{name}_phase_sum")
            
            cmds.connectAttr(f"{time_mult}.output", f"{phase_sum}.input[0]")
            cmds.connectAttr(f"{offset_mult}.output", f"{phase_sum}.input[1]")

            sin_node = cmds.createNode("sin", n=f"{name}_sin")

            cmds.connectAttr(f"{phase_sum}.output", f"{sin_node}.input") 

            amp_mult = cmds.createNode("multiply", n=f"{name}_amp_mult")
            
            cmds.connectAttr(f"{sin_node}.output", f"{amp_mult}.input[0]")
            cmds.connectAttr(f"{self.settings_ctl}.waveAmp", f"{amp_mult}.input[1]")

            cmds.connectAttr(f"{amp_mult}.output", f"{jnt}.{axis}")
