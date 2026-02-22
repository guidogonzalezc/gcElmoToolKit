import sys
from functools import partial

import maya.api.OpenMaya as Om2
import maya.cmds as cmds


def reset_selected(transformations=True, user_defined=True, *args):
    """Resets transform and/or custom attribute values for the selected dag nodes.

    Args:
        transformations (bool): If True resets all transformations. Default to True.
        user_defined (bool): If True sets the default values for the user defined attributes. Defaults to True
    """
    if not cmds.ls(selection=True):
        cmds.error("Nothing selected")

    for dag_node in cmds.ls(selection=True):
        if transformations and (cmds.objectType(dag_node, isType="transform") or cmds.objectType(dag_node, isType="joint")):
            transformation_attrs = ["translate", "rotate", "scale"]
            if cmds.objectType(dag_node, isType="joint"):
                transformation_attrs.extend(["jointOrient", "preferredAngle", "stiffness"])

            for attr in transformation_attrs:
                for axis in ("X", "Y", "Z"):
                    try:
                        cmds.setAttr(f"{dag_node}.{attr}{axis}", 1 if attr == "scale" else 0)
                    except RuntimeError:  # Locked and connected attribute would make this not work
                        pass

        if not user_defined or not cmds.objectType(dag_node, isType="transform"):
            continue

        # Reset the custom numeric attributes to the default value
        for attr in cmds.listAttr(dag_node, userDefined=True) or []:
            numeric_attrs = ("double", "float", "long", "short", "bool", "doubleAngle", "doubleLinear", "enum")
            if not cmds.addAttr(f"{dag_node}.{attr}", q=True, attributeType=True) in numeric_attrs:
                continue
            try:
                cmds.setAttr(f"{dag_node}.{attr}", cmds.addAttr(f"{dag_node}.{attr}", q=True, defaultValue=True))
            except RuntimeError:
                continue


def create_on_selection(object_type, *args):
    """
    Creates the desired object type and places it based on the manipulator or selection.

    Args:
        object_type (str): "locator" or "joint"
    """
    if object_type not in ("locator", "joint"):
        raise ValueError("`object_type` must be `locator` or `joint`")

    context_func = {"Move": cmds.manipMoveContext, "Rotate": cmds.manipRotateContext, "Scale": cmds.manipScaleContext}

    current_ctx = cmds.currentCtx()
    object_name = cmds.superCtx(current_ctx, q=True)

    selection = cmds.ls(sl=True, flatten=True)

    pos, rot = [0, 0, 0], [0, 0, 0]

    if context_func.get(object_name) and context_func[object_name](object_name, q=True, manipVisible=True):
        pos = context_func[object_name](object_name, q=True, position=True)
        mode = context_func[object_name](object_name, q=True, mode=True)
        if mode == 0:  # object
            mtx = cmds.xform(selection[-1], q=True, worldSpace=True, matrix=True)
            rot = Om2.MTransformationMatrix(Om2.MMatrix(mtx)).rotation()  # MEulerRotation
            rot = [Om2.MAngle(i).asDegrees() for i in rot.asVector()]

        elif (mode == 6 and not object_name == "Rotate") or (mode == 3 and object_name == "Rotate"):  # custom
            rot = cmds.manipPivot(q=True, o=True)[0]

    elif selection:  # If the manip is not visible use the selected items to find the position and rotation
        all_positions = []
        for s in selection:
            position = cmds.xform(s, q=True, ws=True, translation=True)
            # If faces or edges are selected positions for all vertices are returned in a single list. Pack them
            positions = [position[i:i + 3] for i in range(0, len(position), 3)]
            all_positions.extend(positions)

        if len(selection) == 1:  # Rotation not stored if the selection is multiple, vertices maybe
            rot = cmds.xform(selection[0], q=True, ws=True, rotation=True)

        pos = [sum(x) / len(all_positions) for x in zip(*all_positions)]

    if object_type == "locator":
        new_object = cmds.listRelatives(cmds.createNode("locator", skipSelect=True), parent=True)[0]
        cmds.select(new_object)
    else:
        new_object = cmds.createNode("joint")

    if new_object:
        cmds.xform(new_object, translation=pos, rotation=rot, worldSpace=True)


def create_offset_grp(*args):
    """
    Creates an offset group for the selection.
    """
    selected_object = cmds.ls(sl=True)
    if len(selected_object) > 1:
        cmds.error("Select ONE and only ONE object to create the offset")

    selected_object = selected_object[0]
    current_parent = cmds.listRelatives(selected_object, parent=True)

    index = 0
    while cmds.objExists(f"{selected_object}OFF{str(index).zfill(2) if index else ''}"):
        index += 1

    offset_grp = cmds.createNode("transform", name=f"{selected_object}OFF{str(index).zfill(2) if index else ''}", ss=True)
    if current_parent:
        cmds.parent(offset_grp, current_parent)

    cmds.delete(cmds.parentConstraint(selected_object, offset_grp))
    cmds.parent(selected_object, offset_grp)


def match(translate=True, rotate=True, *args):
    """Match transform values.

    Args:
        translate (bool): If True matches the translation values. Defaults to True.
        rotate (bool): If True matches the rotation values. Defaults to True.
    """
    selection = cmds.ls(sl=True)

    if len(selection) < 2:
        cmds.error("Select 2 or more objects")

    object_to_match = selection[-1]
    matching_objects = selection[0: -1]

    for dest in matching_objects:
        if translate:
            cmds.delete(cmds.pointConstraint(object_to_match, dest, mo=False)[0])
        if rotate:
            cmds.delete(cmds.orientConstraint(object_to_match, dest, mo=False)[0])


def remove_animation(*args):
    """Removes the animation for your selection."""

    selection = cmds.ls(sl=True)

    if not selection:
        cmds.error("Nothing selected or no AnimControls could be found")

    cmds.cutKey(selection)
    cmds.currentTime(1)

    sys.stdout.write("Animation removed")


def mirror_selection(add, *args):
    """
    Adds mirror objects to the selection or replaces the current selection with the mirror objects.
    Upper and lower conventions are accepted. "side" must be the first token name.

    Args:
        add(bool): If True mirror objects are added to the current selection. False replaces de selection
    """
    # Remember to update AnimScripts if this function is updated

    selection = cmds.ls(sl=True)
    mirror_sides_dict = {"L": "R", "l": "r", "R": "L", "r": "l"}
    if not selection:
        cmds.warning("Nothing selected")
        return
    select_set = set()
    for item in selection:
        if add:
            select_set.add(item)
        if mirror_sides_dict.get(item[0]):
            mirror_item = mirror_sides_dict[item[0]] + item[1:]
            if cmds.objExists(mirror_item):
                select_set.add(mirror_item)
        elif not add:  # If object has no left or right side keep it in the selection even if add=False
            select_set.add(item)

    cmds.select(list(select_set), replace=True)


class elmoMarkingMenu:
    def __init__(self):
        """
        First call the class.
        Open the markingMenu using: alt + shift + R Click
        """
        self.menu_name = "elmoMarkingMenu"

        if cmds.popupMenu(self.menu_name, exists=True):
            cmds.deleteUI(self.menu_name)

        cmds.popupMenu(
            self.menu_name,
            markingMenu=True,
            button=3,
            allowOptionBoxes=True,
            sh=True,
            alt=True,
            parent="viewPanes",
            postMenuCommandOnce=True,
            postMenuCommand=self._build_marking_menu
        )

    def _build_marking_menu(self, menu, *args):
        self.modify_transform_north_submenu(parent=menu)
        cmds.menuItem(
            parent=menu,
            label="Locator",
            radialPosition="NE",
            command=partial(create_on_selection, "locator"),
            image="locator.png")
        cmds.menuItem(
            parent=menu,
            label="Joint",
            radialPosition="E",
            command=partial(create_on_selection, "joint"),
            image="kinJoint.png")

        cmds.menuItem(
            parent=menu,
            label="Create Offset",
            radialPosition="SE",
            command=create_offset_grp,
            image="transform.svg")

        self.matchers_west_submenu(parent=menu)

        cmds.menuItem(
            parent=menu,
            label="Match All",
            radialPosition="SW",
            command=partial(match, True, True),
            image="menuIconModify.png")
        cmds.menuItem(
            parent=menu,
            label="Reset All Selected",
            radialPosition="NW",
            command=partial(reset_selected, True, True),
            image="redrawPaintEffects.png")

        # List
        cmds.menuItem(parent=menu, label="Save Sel", command="mmSel = cmds.ls(sl=True)")
        cmds.menuItem(parent=menu, label="Add Sel", command="cmds.select(mmSel, add=True)")
        cmds.menuItem(parent=menu, divider=True)
        cmds.menuItem(parent=menu, label="Flip Sel", command=partial(mirror_selection, False))
        cmds.menuItem(parent=menu, label="Mirror Sel", command=partial(mirror_selection, True))
        cmds.menuItem(parent=menu, divider=True)
        cmds.menuItem(parent=menu, label="Remove animation", command=remove_animation, image="setKeyframe.png")

    @staticmethod
    def modify_transform_north_submenu(parent):
        north_submenu = cmds.menuItem(parent=parent, label="Reset Transforms", radialPosition="N", subMenu=True)
        cmds.menuItem(
            parent=north_submenu,
            label="Reset Transform(s)",
            radialPosition="W",
            command=partial(reset_selected, True, False))
        cmds.menuItem(
            parent=north_submenu,
            label="Reset Default Value(s)",
            radialPosition="E",
            command=partial(reset_selected, False, True))

    @staticmethod
    def matchers_west_submenu(parent):
        north_submenu = cmds.menuItem(parent=parent, label="Matchers", radialPosition="W", subMenu=True)
        cmds.menuItem(
            parent=north_submenu,
            label="Match Pos",
            radialPosition="N",
            command=partial(match, True, False),
            image="menuIconModify.png")
        cmds.menuItem(
            parent=north_submenu,
            label="Match Rot",
            radialPosition="S",
            command=partial(match, False, True),
            image="menuIconModify.png")


if __name__ == '__main__':
    elmoMarkingMenu()