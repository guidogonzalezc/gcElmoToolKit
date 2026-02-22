import maya.cmds as cmds

for items in cmds.ls(sl=True):
    shapes = cmds.listRelatives(items, shapes=True)
    if shapes:
        for shape in shapes:
            cmds.setAttr(f"{shape}.overrideEnabled", 0)

    cmds.setAttr(f"{items}.overrideEnabled", 1)
    cmds.setAttr(f"{items}.overrideColor", 6)  # Reference display type