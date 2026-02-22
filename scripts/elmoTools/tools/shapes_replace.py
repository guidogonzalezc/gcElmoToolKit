import maya.cmds as cmds

# original = cmds.ls(selection=True)[0]
target = cmds.ls(selection=True)[0]

# for item in cmds.listRelatives(target, shapes=True):
#     cmds.delete(item)

# for i, item in enumerate(cmds.listRelatives(original, shapes=True)):
#     suffix = "" if i == 0 else str(i+1).zfill(1)
#     name = target + "Shape" + suffix
#     item = cmds.rename(item, name)
#     cmds.parent(item, target, shape=True, relative=True)

# cmds.delete(original)

cmds.setAttr(f"{target}.overrideEnabled", 1)
cmds.setAttr(f"{target}.overrideColor", 18)

    
        
