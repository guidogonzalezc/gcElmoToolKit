import maya.cmds as cmds
import maya.api.OpenMaya as om
from elmoTools.utils import data_export
from elmoTools.utils.core import get_offset_matrix
import sys


def leg_pv_spaceswitch(localHip, legPv, footCtl, root):

    side = legPv.split("_")[0]
    pv_SPC = legPv.replace("_CTL", "_SDK")
  
    cmds.addAttr(legPv, shortName="spaceSwitchSep", niceName="SPACE SWITCH_____", enumName="_____",attributeType="enum", keyable=True)
    cmds.setAttr(legPv+".spaceSwitchSep", channelBox=True, lock=True)
    cmds.addAttr(legPv, shortName="automaticPoleVector", niceName="Automatic PoleVector", maxValue=1, minValue=0,defaultValue=1, keyable=True)
    cmds.addAttr(legPv, shortName="spaceSwitchValue", niceName="Space Switch Value", maxValue=1, minValue=0,defaultValue=1, keyable=True)

    pelvis_trn = cmds.createNode("transform", name=f"{side}_followPelvis_TRN", parent=f"{side}_legModule_GRP")
    foot_trn = cmds.createNode("transform", name=f"{side}_followFoot_TRN", parent=pelvis_trn)

    cmds.pointConstraint(root, pelvis_trn, maintainOffset=False)  

    cmds.aimConstraint(
        footCtl, pelvis_trn, 
        aimVector=(0, -1, 0), 
        upVector=(1, 0, 0), 
        worldUpType="objectrotation", 
        worldUpVector=(1, 0, 0), 
        worldUpObject=localHip
    )

    cmds.aimConstraint(
        footCtl, foot_trn,
        aimVector=(0, -1, 0),
        upVector=(1, 0, 0),
        worldUpType="objectrotation",
        worldUpVector=(1, 0, 0),
        worldUpObject=footCtl,
        maintainOffset=False
    )

    cmds.parentConstraint(foot_trn, pv_SPC, maintainOffset=True)

    cmds.setKeyframe(foot_trn, attribute="rotate")
    cmds.setKeyframe(pv_SPC, attribute="rotate")
    cmds.setKeyframe(pv_SPC, attribute="translate")

    cmds.connectAttr(f"{legPv}.spaceSwitchValue", f"{foot_trn}.blendAim1")
    cmds.connectAttr(f"{legPv}.automaticPoleVector", f"{pv_SPC}.blendParent1")

def fk_switch(target, sources = [], default_rotate = 1, default_translate = 1, sources_names = [], pv=False):
    """
    Switch the matrix space of a target control to multiple source controls in Maya.

    Args:
        target (str): The name of the target control to switch space for.
        sources (list, optional): A list of source controls to switch to. Defaults to [None].
        default_value (float, optional): The default value for the follow attribute. Defaults to 1.
    """
    # try:
    target_grp = target.replace("CTL", "GRP")
    if not cmds.objExists(target):
        target_grp = target
    if not cmds.objExists(target_grp):
        om.MGlobal.displayError(f"Target group '{target_grp}' does not exist.")
        return
    
    cmds.setAttr(f"{target_grp}.inheritsTransform", 0)

    connections = cmds.listConnections(f"{target_grp}.offsetParentMatrix", plugs=True, source=True, destination=False)[0]

    data_exporter = data_export.DataExport()


    masterWalk_ctl = data_exporter.get_data("basic_structure", "masterWalk_CTL")


    parent_matrix_masterwalk = cmds.createNode("parentMatrix", name=target.replace("_CTL", "MasterwalkSpace_PM"), ss=True)
    parent_matrix_parents = cmds.createNode("parentMatrix", name=target.replace("_CTL", "Space_PM"), ss=True)
    blend_matrix = cmds.createNode("blendMatrix", name=target.replace("_CTL", "Space_BMX"), ss=True)
    cmds.addAttr(target, longName="SpaceSwitchSep", niceName = "Space Switches  ———", attributeType="enum", enumName="———", keyable=True)
    cmds.setAttr(f"{target}.SpaceSwitchSep", channelBox=True, lock=True)   
    spaces = [src.split("_")[1] for src in sources]
    name_space = [src_name for src_name in sources_names]


    if len(sources) > 1:
        cmds.addAttr(target, longName="SpaceFollow", attributeType="enum", enumName=":".join(name_space), keyable=True)

        for i, driver in enumerate(sources):

            condition = cmds.createNode("condition", name=target.replace('_CTL', f"Space0{i}_CON"), ss=True)
            cmds.setAttr(f"{condition}.firstTerm", i)
            cmds.connectAttr(f"{target}.SpaceFollow", f"{condition}.secondTerm")
            cmds.setAttr(f"{condition}.operation", 0)
            cmds.setAttr(f"{condition}.colorIfFalseR", 0)
            cmds.setAttr(f"{condition}.colorIfTrueR", 1)


            cmds.connectAttr(f"{condition}.outColorR", f"{parent_matrix_parents}.target[{i}].weight")
    cmds.addAttr(target, longName="TranslateValue", attributeType="float", min=0, max=1, defaultValue=default_translate, keyable=True)
    cmds.addAttr(target, longName="RotateValue", attributeType="float", min=0, max=1, defaultValue=default_rotate, keyable=True)

    cmds.connectAttr(connections, f"{parent_matrix_parents}.inputMatrix")
    cmds.connectAttr(connections, f"{parent_matrix_masterwalk}.inputMatrix")
    cmds.connectAttr(f"{parent_matrix_parents}.outputMatrix", f"{blend_matrix}.target[0].targetMatrix")
    cmds.connectAttr(f"{parent_matrix_masterwalk}.outputMatrix", f"{blend_matrix}.inputMatrix")

    offset_masterwalk = get_offset_matrix(target_grp, masterWalk_ctl)
    cmds.connectAttr(f"{masterWalk_ctl}.worldMatrix[0]", f"{parent_matrix_masterwalk}.target[0].targetMatrix")
    cmds.setAttr(f"{parent_matrix_masterwalk}.target[0].offsetMatrix", offset_masterwalk, type="matrix")
    for z, driver in enumerate(sources):
        off_matrix = get_offset_matrix(target_grp, driver)
        if "." in driver:
            cmds.connectAttr(f"{driver}", f"{parent_matrix_parents}.target[{z}].targetMatrix") 
        else:
            cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{parent_matrix_parents}.target[{z}].targetMatrix") 

        if pv:
            multmatrix = cmds.createNode("multMatrix", name=target.replace("_CTL", f"{spaces[z]}LiveOffset_MMX"), ss=True)
            cmds.connectAttr(f"{connections}", f"{multmatrix}.matrixIn[0]")
            matrix = cmds.getAttr(f"{driver}.worldInverseMatrix[0]")
            cmds.setAttr(f"{multmatrix}.matrixIn[1]", matrix, type="matrix")
            cmds.connectAttr(f"{multmatrix}.matrixSum", f"{parent_matrix_parents}.target[{z}].offsetMatrix")
        else:
            cmds.setAttr(f"{parent_matrix_parents}.target[{z}].offsetMatrix", off_matrix, type="matrix")

    cmds.connectAttr(f"{target}.RotateValue", f"{blend_matrix}.target[0].rotateWeight")
    cmds.connectAttr(f"{target}.TranslateValue", f"{blend_matrix}.target[0].translateWeight")
    cmds.setAttr(f"{blend_matrix}.target[0].scaleWeight", 0)
    cmds.setAttr(f"{blend_matrix}.target[0].shearWeight", 0)
    cmds.connectAttr(f"{blend_matrix}.outputMatrix", f"{target_grp}.offsetParentMatrix", force=True)

    # except Exception as e:
    #     om.MGlobal.displayError(f"Error in fk_switch: {e}")
    #     sys.exit()