import maya.cmds as cmds
import maya.OpenMaya as om
import os
from importlib import reload
import json
import re

from elmoTools.utils import core
from elmoTools.utils import data_export
import maya.api.OpenMaya as om
from elmoTools.utils import curve_tool
from elmoTools.ui import project_manager

reload(curve_tool)
reload(core)
reload(project_manager)

class GuideCreation(object):
    """
    Base class to create guides in the Maya scene.
    Contains shared logic for guide creation.
    """

    position_data = {}
    value = 0

    def build_curves_from_template(self, type, transform_name):
        """
        Builds controller curves from a predefined template JSON file.
        If a specific target transform name is provided, it filters the curves to only create those associated with that transform.
        If no target transform name is provided, it creates all curves defined in the template.
        """
            
        curve_data = {
            "arrow": {
                "shapes": [
                    {
                        "curve": {
                            "cvs": [
                                [0.05710937039931652, -0.46208100343651526, 1.2381136152831843e-06],
                                [-0.13243611287906498, -0.43980584749283874, 1.1784288984233384e-06],
                                [-0.2709619403561311, -0.46741316704204877, 1.2524007734001178e-06],
                                [-0.3110801360209462, -0.4997154863303799, 1.3389525706362542e-06],
                                [-0.3125322482823646, -0.5452255108954519, 1.4608934871137462e-06],
                                [-0.3279198465141865, -1.0274752154006066, 2.7530477212710005e-06],
                                [-0.3293719587755938, -1.072985239965675, 2.874988637748483e-06],
                                [-0.2913151372523647, -1.1052875592540063, 2.96154043498462e-06],
                                [-0.1504102897778976, -1.1343047230011487, 3.0392898885329146e-06],
                                [0.040251692463613487, -1.1134394112554025, 2.9833827502445854e-06],
                                [0.9838829618428812, -0.9500234372888587, 2.545521118154057e-06],
                                [1.0820129424698943, -0.8688846951636224, 2.3281155537506556e-06],
                                [1.1222758743474053, -0.7876195094560698, 2.1103711926434997e-06],
                                [1.0843407745637117, -0.7055646343449953, 1.8905109142078366e-06],
                                [0.9885386260305203, -0.623383315651595, 1.6703118390683945e-06],
                                [0.05710937039931652, -0.46208100343651526, 1.2381136152831843e-06]
                            ],
                            "form": "open",
                            "knots": [
                                0.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 13.0, 13.0
                            ],
                            "degree": 3
                        }
                    }
                ]
            },
            "settings": {
                "shapes": [
                    {
                        "curve": {
                            "cvs": [
                                [0.27583961709940663, 1.1100465970347986, 2.3349109140730323e-07],
                                [0.2760224292833038, 0.27746594834149785, 2.0823220965254452e-07],
                                [1.1042723272392925, 0.2772831361576038, 8.076698100604056e-07],
                                [1.1043942020285566, -0.2777706296379296, 7.90830555557233e-07],
                                [0.27614430407258217, -0.27758781745403516, 1.9139295514937222e-07],
                                [0.2763271162564531, -1.1101684661473408, 1.6613407339461295e-07],
                                [-0.27583948238085565, -1.1100465913580786, -2.3349099354396076e-07],
                                [-0.27602229456474703, -0.2774659426647736, -2.0823211178920218e-07],
                                [-1.1042721925207435, -0.277283130480879, -8.076697121970679e-07],
                                [-1.1043940673100048, 0.2777706353146552, -7.90830457693897e-07],
                                [-0.27614416935401165, 0.2775878231307607, -1.913928572860296e-07],
                                [-0.27632698153791013, 1.1101684718240596, -1.6613397553127101e-07],
                                [0.27583961709940663, 1.1100465970347986, 2.3349109140730323e-07],
                                [0.27583948238086897, 1.1100465913580817, 2.3349099354396645e-07],
                                [-0.2763271162564669, 1.1101684661473432, -1.6613407339460769e-07],
                                [-0.27632698153791013, 1.1101684718240596, -1.6613397553127101e-07],
                                [-0.2763271162564669, 1.1101684661473432, -1.6613407339460769e-07],
                                [-0.27614430407256974, 0.27758781745404004, -1.9139295514936631e-07],
                                [-1.1043942020285564, 0.2777706296379332, -7.908305555572311e-07],
                                [-1.1043940673100048, 0.2777706353146552, -7.90830457693897e-07],
                                [-1.1042721925207435, -0.277283130480879, -8.076697121970679e-07],
                                [-1.1042723272392956, -0.2772831361575999, -8.076698100604056e-07],
                                [-1.1043942020285564, 0.2777706296379332, -7.908305555572311e-07],
                                [-1.1042723272392956, -0.2772831361575999, -8.076698100604056e-07],
                                [-0.276022429283306, -0.2774659483414943, -2.0823220965253864e-07],
                                [-0.2758396170994102, -1.1100465970348, -2.3349109140729796e-07],
                                [-0.27583948238085565, -1.1100465913580786, -2.3349099354396076e-07],
                                [-0.27602229456474703, -0.2774659426647736, -2.0823211178920218e-07],
                                [-0.276022429283306, -0.2774659483414943, -2.0823220965253864e-07],
                                [-0.2758396170994102, -1.1100465970348, -2.3349109140729796e-07],
                                [0.276326981537907, -1.1101684718240636, 1.6613397553127612e-07],
                                [0.2763271162564531, -1.1101684661473408, 1.6613407339461295e-07],
                                [-0.27583948238085565, -1.1100465913580786, -2.3349099354396076e-07],
                                [-0.2758396170994102, -1.1100465970348, -2.3349109140729796e-07],
                                [0.276326981537907, -1.1101684718240636, 1.6613397553127612e-07],
                                [0.27614416935402675, -0.2775878231307562, 1.9139285728603528e-07],
                                [1.1043940673100092, -0.27777063531465007, 7.908304576938965e-07],
                                [1.1043942020285566, -0.2777706296379296, 7.90830555557233e-07],
                                [0.27614430407258217, -0.27758781745403516, 1.9139295514937222e-07],
                                [0.27614416935402675, -0.2775878231307562, 1.9139285728603528e-07],
                                [1.1043940673100092, -0.27777063531465007, 7.908304576938965e-07],
                                [1.1042721925207433, 0.2772831304808836, 8.076697121970698e-07],
                                [0.27602229456475014, 0.2774659426647772, 2.0823211178920748e-07],
                                [0.2760224292833038, 0.27746594834149785, 2.0823220965254452e-07],
                                [1.1042723272392925, 0.2772831361576038, 8.076698100604056e-07],
                                [1.1042721925207433, 0.2772831304808836, 8.076697121970698e-07],
                                [0.27602229456475014, 0.2774659426647772, 2.0823211178920748e-07],
                                [0.27583948238086897, 1.1100465913580817, 2.3349099354396645e-07],
                                [0.27583961709940663, 1.1100465970347986, 2.3349109140730323e-07],
                                [-0.27632698153791013, 1.1101684718240596, -1.6613397553127101e-07],
                                [-0.2763271162564669, 1.1101684661473432, -1.6613407339460769e-07],
                                [-0.27614430407256974, 0.27758781745404004, -1.9139295514936631e-07],
                                [-0.27614416935401165, 0.2775878231307607, -1.913928572860296e-07],
                                [-1.1043940673100048, 0.2777706353146552, -7.90830457693897e-07],
                                [-1.1043942020285564, 0.2777706296379332, -7.908305555572311e-07]
                            ],
                            "form": "open",
                            "knots": [
                                0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0, 52.0, 53.0, 54.0
                            ],
                            "degree": 1
                        }
                    }
                ]
            }
        }

        created_transforms = []
        type_data = curve_data[type]
        shapes_data = type_data.get("shapes", [])

        dag_modifier = om.MDagModifier()
        transform_obj = dag_modifier.createNode("transform")
        dag_modifier.doIt()
        transform_fn = om.MFnDagNode(transform_obj)
        i = 1
        while cmds.objExists(transform_name):
            if not re.search(r"\d+_GUIDE$", transform_name):
                transform_name = transform_name.replace("_GUIDE", f"0{i}_GUIDE")
            else:
                transform_name = transform_name.replace(f"{i-1}_GUIDE", f"{i}_GUIDE")
            i += 1
        final_name = transform_fn.setName(transform_name)
        created_transforms.append(final_name)

        created_shapes = []
        for idx, shape_data in enumerate(shapes_data):
            curve_info = shape_data["curve"]
            cvs = curve_info["cvs"]
            degree = curve_info["degree"]
            knots = curve_info["knots"]
            form = curve_info["form"]

            form_flags = {
                "open": om.MFnNurbsCurve.kOpen,
                "closed": om.MFnNurbsCurve.kClosed,
                "periodic": om.MFnNurbsCurve.kPeriodic
            }
            form_flag = form_flags.get(form, om.MFnNurbsCurve.kOpen)

            points = om.MPointArray()
            for pt in cvs:
                points.append(om.MPoint(pt[0], pt[1], pt[2]))

            curve_fn = om.MFnNurbsCurve()
            shape_obj = curve_fn.create(
                points,
                knots,
                degree,
                form_flag,
                False,
                True,
                transform_obj
            )

            shape_fn = om.MFnDagNode(shape_obj)
            shape_fn.setName(f"{type}Shape{idx}")

            fn_dep = om.MFnDependencyNode(shape_obj)
            fn_dep.findPlug('alwaysDrawOnTop', False).setBool(True)

            created_shapes.append(shape_obj)

        return created_transforms

    def controller_creator(self,name, type, parent=None, match=None, color=6):
        """
        Creates a controller with a specific name and offset transforms and returns the controller and the groups.

        Args:
            name (str): Name of the controller.
            suffixes (list): List of suffixes for the groups to be created. Default is ["GRP"].
        """
        lock=["scaleX", "scaleY", "scaleZ", "visibility"]
        prefix="GUIDE"

        

        ctl = self.build_curves_from_template(type=type, transform_name=f"{name}_{prefix}")[0]



        if not ctl:
            ctl = cmds.circle(name=f"{name}_{prefix}", ch=False)

        if parent:
            cmds.parent(ctl, parent)

        cmds.setAttr(f"{ctl}.overrideEnabled", 1)
        cmds.setAttr(f"{ctl}.overrideColor", color)

        if match:
            if cmds.objExists(match):
                cmds.xform(ctl, ws=True, t=cmds.xform(match, q=True, ws=True, t=True))
                cmds.xform(ctl, ws=True, ro=cmds.xform(match, q=True, ws=True, ro=True))


        for attr in lock:
            if "scale" in attr:
                try:
                    cmds.connectAttr(f"{self.guides_trn}.guideScale", f"{ctl}.{attr}", force=True)
                except:
                    pass
            cmds.setAttr(f"{ctl}.{attr}", keyable=False, channelBox=False, lock=True)

        return ctl

    def create_guides(self, guides_trn, buffers_trn):
        self.guides_trn = guides_trn
        self.buffers_trn = buffers_trn
        for side in self.sides:
            color = {"L": 6, "R": 13}.get(side, 17)
            self.guides = []
            for i, (joint_name, positions) in enumerate(self.position_data.items()):
                if len(positions) >= 3 or None in positions:
                    parent = positions[1]
                    type = positions[-2]
                    rotation = positions[-1]
                    positions = positions[0]
                if len(joint_name.split("_")) > 1:
                    side = joint_name.split("_")[0]
                    joint_name =joint_name.split("_")[1]


                positions = [0,0,0] if positions is None else positions
                rotation = [0,0,0] if rotation is None else rotation
                parent = None if parent == None else parent
                type = "joint" if type == None else type

                temp_pos = None

                if parent is None and type == "joint":
                    parent = self.guides_trn if not self.guides else self.guides[-1]
                    if "Settings" in joint_name:
                        parent = self.guides[0]
                        type = "settings"
                    
                    if "localHip" in joint_name:
                        parent = self.guides_trn

                    if "Distance" in joint_name:
                        parent = self.guides_trn

                    if self.limb_name == "mouth" or self.limb_name == "eye":
                        parent = self.guides_trn if not self.guides else self.guides[0]

                if not "Sliding" in joint_name and not "Curve" in joint_name:
                    temp_pos = cmds.createNode("transform", name=f"{side}_{joint_name}_temp")
                    cmds.setAttr(temp_pos + ".translate", positions[0], positions[1], positions[2], type="double3")
                    cmds.setAttr(temp_pos + ".rotate", rotation[0], rotation[1], rotation[2], type="double3")
                    if "Transform" in joint_name:
                        guide = cmds.createNode("transform", name=f"{side}_{joint_name}_GUIDE")
                        cmds.parent(guide, parent)

                    if "Settings" in joint_name:   
                        guide = self.controller_creator(
                            f"{side}_{joint_name}",
                            type="settings",
                            parent=parent,
                            match=temp_pos,
                            color=color,
                        )

                    else:

                        guide = cmds.createNode("joint", name=f"{side}_{joint_name}_GUIDE", parent=parent, ss=True)
                        cmds.setAttr(guide + ".overrideEnabled", 1)
                        cmds.setAttr(guide + ".overrideColor", color)
                        cmds.matchTransform(guide, temp_pos)
                        cmds.setAttr(f"{guide}.drawStyle", 3)
                        cmds.setAttr(f"{guide}.radius", 1)

                elif "Curve" in joint_name:
                    guide = create_curve_guide(f"{side}_{joint_name}_GUIDE")
                    cmds.parent(guide, parent)

                else:
                    guide = curve_tool.build_surfaces_from_template(core.DataManager.get_guide_data(), target_transform_name=f"{side}_{joint_name}_GUIDE")
                    cmds.parent(guide, parent)

                if "Sliding" in joint_name:
                    attr_name = "NurbsSurface"
                elif "Transform" in joint_name:
                    attr_name = "Transform"
                else:
                    attr_name = "Guide"

                cmds.addAttr(guide, longName="guideTypeObject", attributeType="enum", enumName=attr_name, keyable=False)

                if i == 0:
                    if hasattr(self, "twist_joints"):
                        attr_name = "jointTwist"
                        cmds.addAttr(guide, longName=attr_name, attributeType="float", defaultValue=self.twist_joints, keyable=False)
                        cmds.setAttr(f"{guide}.{attr_name}", self.twist_joints)
                    
                    if self.controller_number:
                        attr_name = "controllerNumber"
                        cmds.addAttr(guide, longName=attr_name, attributeType="long", defaultValue=self.controller_number, keyable=False)
                        cmds.setAttr(f"{guide}.{attr_name}", self.controller_number)

                    if self.prefix:
                        enum_name = "prefix"
                        cmds.addAttr(guide, longName=enum_name, attributeType="enum", enumName=self.prefix, keyable=False)

                    cmds.addAttr(guide, longName="moduleName", attributeType="enum", enumName=self.limb_name, keyable=False)

                if temp_pos:
                    cmds.delete(temp_pos)
                    temp_pos = None

                self.guides.append(guide)
            enum_name = ":".join(self.guides)
            cmds.addAttr(self.guides[0], longName="guide_name", attributeType="enum", enumName=enum_name, keyable=False)

            meta = []

            for i in range(len(self.guides) - 1):
                if "Settings" in self.guides[i+1] or "localHip" in self.guides[i+1] or self.limb_name == "mouth" or self.limb_name == "eye" or self.limb_name == "eyebrow" or self.limb_name == "cheek" or self.limb_name == "cheekBone":
                    continue
                if "metacarpal" in self.guides[i] or "Metacarpal" in self.guides[i]:
                    try:
                        if cmds.listRelatives(self.guides[i], parent=True) != [self.guides[0]]:
                            cmds.parent(self.guides[i], self.guides[0])
                    except:
                        pass
                    curve = cmds.curve(d=1, p=[(1, 0, 0), (2, 0, 0)], n=f"{self.guides[i]}_to_{self.guides[0]}_CRV")
                    dcmp = cmds.createNode("decomposeMatrix", name=f"{self.guides[i]}_to_{self.guides[0]}{i}_DCM", ss=True)
                    dcmp02 = cmds.createNode("decomposeMatrix", name=f"{self.guides[i]}_to_{self.guides[0]}{i+1}_DCM", ss=True)
                    cmds.connectAttr(self.guides[i] + ".worldMatrix[0]", dcmp + ".inputMatrix")
                    cmds.connectAttr(self.guides[0] + ".worldMatrix[0]", dcmp02 + ".inputMatrix")
                    cmds.connectAttr(dcmp + ".outputTranslate", curve + ".controlPoints[0]")
                    cmds.connectAttr(dcmp02 + ".outputTranslate", curve + ".controlPoints[1]")
                    cmds.parent(curve, self.buffers_trn)
                    cmds.setAttr(curve + ".overrideEnabled", 1)
                    cmds.setAttr(curve + ".overrideDisplayType", 2)
                    cmds.setAttr(cmds.listRelatives(curve, shapes=True)[0] + ".alwaysDrawOnTop", 1)


                if not "Metacarpal" in self.guides[i+1]:
                    number = i+1 if not "Distance" in self.guides[i] else 1
                    curve = cmds.curve(d=1, p=[(1, 0, 0), (2, 0, 0)], n=f"{self.guides[i]}_to_{self.guides[number]}_CRV")
                    dcmp = cmds.createNode("decomposeMatrix", name=f"{self.guides[i]}_to_{self.guides[number]}{i}_DCM", ss=True)
                    dcmp02 = cmds.createNode("decomposeMatrix", name=f"{self.guides[i]}_to_{self.guides[number]}{i+1}_DCM", ss=True)
                    cmds.connectAttr(self.guides[i] + ".worldMatrix[0]", dcmp + ".inputMatrix")
                    cmds.connectAttr(self.guides[number] + ".worldMatrix[0]", dcmp02 + ".inputMatrix")
                    cmds.connectAttr(dcmp + ".outputTranslate", curve + ".controlPoints[0]")
                    cmds.connectAttr(dcmp02 + ".outputTranslate", curve + ".controlPoints[1]")
                    cmds.parent(curve, self.buffers_trn)
                    cmds.setAttr(curve + ".overrideEnabled", 1)
                    cmds.setAttr(curve + ".overrideDisplayType", 2)
                    cmds.setAttr(cmds.listRelatives(curve, shapes=True)[0] + ".alwaysDrawOnTop", 1)
                
            if self.aim_name:
                arrrow_buffer = self.controller_creator(
                    f"{side}_{self.limb_name}Buffer",
                    type="arrow",
                    parent=self.buffers_trn,
                    match=None,
                )
                cmds.setAttr(arrrow_buffer + ".overrideEnabled", 1)
                cmds.setAttr(arrrow_buffer + ".overrideDisplayType", 2)

                aimMatrix = cmds.createNode("aimMatrix", name=f"{side}_{self.aim_name}_Aim_AMX", ss=True)
                cmds.setAttr(aimMatrix + ".primaryInputAxis", 1, 0, 0, type="double3")
                cmds.setAttr(aimMatrix + ".secondaryInputAxis", 0, -1, 0, type="double3")
                cmds.setAttr(aimMatrix + ".primaryMode", 1)
                cmds.setAttr(aimMatrix + ".secondaryMode", 1)

                value = self.aim_offset

                cmds.connectAttr(self.guides[1 + value] + ".worldMatrix[0]", aimMatrix + ".inputMatrix")
                cmds.connectAttr(aimMatrix + ".outputMatrix", arrrow_buffer + ".offsetParentMatrix")
                cmds.connectAttr(self.guides[2 + value] + ".worldMatrix[0]", aimMatrix + ".primaryTargetMatrix")
                cmds.connectAttr(self.guides[3 + value] + ".worldMatrix[0]", aimMatrix + ".secondaryTargetMatrix")

        cmds.select(self.guides[0])
        return self.guides

def get_data(name, module_name=False):

    final_path = core.DataManager.get_guide_data()

    try:
        with open(final_path, "r") as infile:
            guides_data = json.load(infile)
    except Exception as e:
        if module_name:
            return None, None, None, None
        else:
            return None, None

    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue
        for guide_name, guide_info in guides.items():
            name = name.replace("_GUIDE", "")   
            if f"{name}_GUIDE" == guide_name:
                try: 
                    world_position = guide_info.get("worldPosition")
                except:
                    world_position = None
                try:
                    world_rotation = guide_info.get("worldRotation")
                except:
                    world_rotation = None

                parent = guide_info.get("parent")
                guideTyep = guide_info.get("guide_type_object")

                if module_name:
                        moduleName = guide_info.get("moduleName")
                        prefix = guide_info.get("prefix")
                        return world_position, parent, moduleName, prefix, guideTyep, world_rotation
                

                else:
                    return world_position, parent, guideTyep, world_rotation
    if module_name:
        return None, None, None, None, None
    else:
        return None, None, None

class ArmGuideCreation(GuideCreation):
    """
    Guide creation for arms.
    """
    def __init__(self, side = "L", twist_joints=5):
        self.sides = side
        self.twist_joints = twist_joints
        self.limb_name = "arm"
        self.aim_name = "shoulder"
        self.aim_offset = 0
        self.prefix = None
        self.controller_number = None
        self.position_data = {
            "clavicle": get_data(f"{self.sides}_clavicle"),
            "shoulder": get_data(f"{self.sides}_shoulder"),
            "elbow": get_data(f"{self.sides}_elbow"),
            "wrist": get_data(f"{self.sides}_wrist"),
            "armSettings": get_data(f"{self.sides}_armSettings"),
            "shoulderFrontDistance": get_data(f"{self.sides}_shoulderFrontDistance"),
            "shoulderUpDistance": get_data(f"{self.sides}_shoulderUpDistance"),
        }

class LegGuideCreation(GuideCreation):
    """
    Guide creation for legs.
    """
    def __init__(self, side = "L", twist_joints=5):
        self.sides = side
        self.twist_joints = twist_joints
        self.limb_name = "leg"
        self.aim_name = "hip"
        self.aim_offset = 0
        self.prefix = None
        self.controller_number = None
        self.position_data = {
            "hip": get_data(f"{self.sides}_hip"),
            "knee": get_data(f"{self.sides}_knee"),
            "ankle": get_data(f"{self.sides}_ankle"),
            "foot": get_data(f"{self.sides}_foot"),
            "toe": get_data(f"{self.sides}_toe"),
            "legSettings": get_data(f"{self.sides}_legSettings"),
        }

class BackLegGuideCreation(GuideCreation):
    """
    Guide creation for back legs.
    """
    def __init__(self, side = "L", twist_joints=5):
        self.sides = side
        self.twist_joints = twist_joints
        self.limb_name = "backLeg"
        self.aim_name = "hip"
        self.aim_offset = -1
        self.controller_number = None
        self.prefix = None
        self.position_data = {
        "hip": get_data(f"{self.sides}_hip", module_name=True),
        "backKnee": get_data(f"{self.sides}_backKnee"),
        "backAnkle": get_data(f"{self.sides}_backAnkle"),
        "backFoot": get_data(f"{self.sides}_backFoot"),
        "backToe": get_data(f"{self.sides}_backToe"),
        "backLegSettings": get_data(f"{self.sides}_backLegSettings"),
        "backLegFrontDistance": get_data(f"{self.sides}_backLegFrontDistance"),
    }
                
class FrontLegGuideCreation(GuideCreation):
    """
    Guide creation for front legs.
    """
    def __init__(self, side = "L", twist_joints=5):
        self.sides = side
        self.twist_joints = twist_joints
        self.limb_name = "frontLeg"
        self.aim_name = "hip"
        self.aim_offset = -1
        self.controller_number = None
        self.prefix = None
        self.position_data = {
        "frontScapula": get_data(f"{self.sides}_frontScapula", module_name=True),
        "frontHip": get_data(f"{self.sides}_frontHip", module_name=True),
        "frontKnee": get_data(f"{self.sides}_frontKnee"),
        "frontAnkle": get_data(f"{self.sides}_frontAnkle"),
        "frontFoot": get_data(f"{self.sides}_frontFoot"),
        "frontToe": get_data(f"{self.sides}_frontToe"),
        "frontLegSettings": get_data(f"{self.sides}_frontLegSettings"),
        "frontLegFrontDistance": get_data(f"{self.sides}_frontLegFrontDistance"),
    }

class SpineQuadGuideCreation(GuideCreation):
    """
    Guide creation for spine.
    """
    def __init__(self, side = "C", twist_joints=5,type="biped"):
        self.sides = side
        self.twist_joints = twist_joints
        self.type = type
        self.limb_name = "spineQuad"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
        "spine01": get_data(f"{self.sides}_spine01"),
        "spine02": get_data(f"{self.sides}_spine02"),
        "localHip": get_data(f"{self.sides}_localHip"),
    }

class SpineBipedGuideCreation(GuideCreation):
    """
    Guide creation for spine.
    """
    def __init__(self, side = "C", twist_joints=5,type="biped"):
        self.sides = side
        self.twist_joints = twist_joints
        self.type = type
        self.limb_name = "spine"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
        "spine01": get_data(f"{self.sides}_spine01"),
        "spine02": get_data(f"{self.sides}_spine02"),
        "localHip": get_data(f"{self.sides}_localHip"),
    }
        
class NeckQuadGuideCreation(GuideCreation):
    """
    Guide creation for neck.
    """
    def __init__(self, side = "C", twist_joints=5, type=0):
        self.sides = side
        self.type = type
        self.twist_joints = twist_joints
        self.limb_name = "neckQuad"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
            "neck": get_data(f"{self.sides}_neck"),
            "head": get_data(f"{self.sides}_head"),
            "centerUpHeadDistance": get_data(f"C_centerUpHeadDistance"),
            "leftHeadDistance": get_data(f"C_leftHeadDistance"),
            "rightHeadDistance": get_data(f"C_rightHeadDistance"),
            "centerDownHeadDistance": get_data(f"C_centerDownHeadDistance"),
        }

class NeckBipedGuideCreation(GuideCreation):
    """
    Guide creation for neck.
    """
    def __init__(self, side = "C", twist_joints=5, type=0):
        self.sides = side
        self.type = type
        self.twist_joints = twist_joints
        self.limb_name = "neck"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
            "neck": get_data(f"{self.sides}_neck"),
            "head": get_data(f"{self.sides}_head"),
        }

class TailGuideCreation(GuideCreation):
    """
    Guide creation for tail.
    """
    def __init__(self, side = "C", twist_joints=5, type=0):
        self.sides = side
        self.type = type
        self.twist_joints = twist_joints
        self.limb_name = "tail"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
            "tail01": get_data(f"{self.sides}_tail01"),
            "tail02": get_data(f"{self.sides}_tail02"),
            "centerUpTailDistance": get_data(f"C_centerUpTailDistance"),
            "leftTailDistance": get_data(f"C_leftTailDistance"),
            "rightTailDistance": get_data(f"C_rightTailDistance"),
            "centerDownTailDistance": get_data(f"C_centerDownTailDistance"),
        }

class TongueGuideCreation(GuideCreation):
    """
    Guide creation for tongue.
    """
    def __init__(self, side = "C", twist_joints=5, type=0):
        self.sides = side
        self.type = type
        self.twist_joints = twist_joints
        self.limb_name = "tongue"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
            "tongue01": get_data(f"{self.sides}_tongue01"),
            "tongue02": get_data(f"{self.sides}_tongue02"),
        }

class MembraneCreation(GuideCreation):
    """
    Guide creation for neck.
    """
    def __init__(self, side = "L"):
        self.sides = side
        self.type = None
        self.limb_name = "membran"
        self.aim_name = None
        self.prefix = None
        self.controller_number = None
        self.position_data = {
             
            "wingSliding": get_data(f"{self.sides}_wingSliding"),

            # "primaryMembran01": get_data(f"{self.sides}_primaryMembran01"),
            # "primaryMembran02": get_data(f"{self.sides}_primaryMembran02"),
            # "primaryMembran03": get_data(f"{self.sides}_primaryMembran03"),
            # "primaryMembran04": get_data(f"{self.sides}_primaryMembran04"),
        }


class HandGuideCreation(GuideCreation):
    """
    Guide creation for hands.
    """
    def __init__(self, side = "L", controller_number = 5, type_name = "handBiped"):
        self.sides = side
        self.limb_name = type_name
        self.aim_name = None
        self.aim_offset = 1
        self.prefix = None
        self.controller_number = controller_number

        if type_name == "handBiped":
            self.position_data = {
                "hand": get_data(f"{self.sides}_hand"),
                "metacarpalIndex": get_data(f"{self.sides}_metacarpalIndex"),
                "index01": get_data(f"{self.sides}_index01"),
                "index02": get_data(f"{self.sides}_index02"),
                "index03": get_data(f"{self.sides}_index03"),
                "indexEnd": get_data(f"{self.sides}_indexEnd"),
                "metacarpalMiddle": get_data(f"{self.sides}_metacarpalMiddle"),
                "middle01": get_data(f"{self.sides}_middle01"),
                "middle02": get_data(f"{self.sides}_middle02"),
                "middle03": get_data(f"{self.sides}_middle03"),
                "middleEnd": get_data(f"{self.sides}_middleEnd"),
                "metacarpalRing": get_data(f"{self.sides}_metacarpalRing"),
                "ring01": get_data(f"{self.sides}_ring01"),
                "ring02": get_data(f"{self.sides}_ring02"),
                "ring03": get_data(f"{self.sides}_ring03"),
                "ringEnd": get_data(f"{self.sides}_ringEnd"),
                "metacarpalPinky": get_data(f"{self.sides}_metacarpalPinky"),
                "pinky01": get_data(f"{self.sides}_pinky01"),
                "pinky02": get_data(f"{self.sides}_pinky02"),
                "pinky03": get_data(f"{self.sides}_pinky03"),
                "pinkyEnd": get_data(f"{self.sides}_pinkyEnd"),
                "metacarpalThumb": get_data(f"{self.sides}_metacarpalThumb"),
                "thumb01": get_data(f"{self.sides}_thumb01"),
                "thumb02": get_data(f"{self.sides}_thumb02"),
                "thumbEnd": get_data(f"{self.sides}_thumbEnd"),
            }
        elif type_name == "handQuad":
            self.position_data = {
                "hand": get_data(f"{self.sides}_hand"),
            }

            for item in range(int(controller_number)):
                name = core.number_to_ordinal_word(item + 1)
                if name == "first":
                    self.position_data.update({
                        f"{name}Metacarpal": get_data(f"{self.sides}_{name}Metacarpal"),
                        f"{name}Finger00": get_data(f"{self.sides}_{name}Finger00"),
                        f"{name}Finger01": get_data(f"{self.sides}_{name}Finger01"),
                        f"{name}Finger02": get_data(f"{self.sides}_{name}Finger02"),
                        f"{name}Finger03": get_data(f"{self.sides}_{name}Finger03"),
                    })
                else:
                    self.position_data.update({
                        f"{name}Metacarpal": get_data(f"{self.sides}_{name}Metacarpal"),
                        f"{name}Finger00": get_data(f"{self.sides}_{name}Finger00"),
                        f"{name}Finger01": get_data(f"{self.sides}_{name}Finger01"),
                        f"{name}Finger02": get_data(f"{self.sides}_{name}Finger02"),
                        f"{name}Finger03": get_data(f"{self.sides}_{name}Finger03"),
                    })

class FootGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="foot"):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = "foot"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None
        ctl = "" if self.reverse_foot_name == "foot" else self.reverse_foot_name
        first_b_letter = "b" if ctl == "" else "B"
        first_h_letter = "h" if ctl == "" else "H"
        first_r_letter = "r" if ctl == "" else "R"
        self.position_data = {
        f"{ctl}{first_b_letter}ankOut": get_data(f"{self.sides}_{ctl}{first_b_letter}ankOut"),
        f"{ctl}{first_b_letter}ankIn": get_data(f"{self.sides}_{ctl}{first_b_letter}ankIn"),
        f"{ctl}{first_h_letter}eel": get_data(f"{self.sides}_{ctl}{first_h_letter}eel"),
        f"{ctl}{first_r_letter}oll": get_data(f"{self.sides}_{ctl}{first_r_letter}oll"),


    }

class FkFingersGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="foot", prefix=False, controller_number=3):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = "fkFinger"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = int(controller_number)
        self.prefix = None
       
        self.position_data = {}
        for i in range(0, int(self.controller_number)):
            if i == 0:
                name = f"{limb_name}Metacarpal" if int(controller_number) >= 4 else f"{limb_name}0{i}"
            else:
                name = f"{limb_name}0{i}"
            self.position_data[f"{name}"] = get_data(f"{self.sides}_{name}")

class SpikesGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="spikes", prefix=False):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = "spikes"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = 0
        self.prefix = None

        final_path = core.DataManager.get_guide_data()
        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        guide_set_name = next(iter(guides_data))
        parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}

        def collect_descendants(parent, parent_map):
            descendants = []
            children = [joint for joint, p in parent_map.items() if p == parent]
            for child in children:
                descendants.append(child)
                descendants.extend(collect_descendants(child, parent_map))
            return descendants

        all_child_guides = collect_descendants(limb_name, parent_map)
        self.position_data = {
                limb_name: get_data(limb_name),
        }
        try:
            for guide in all_child_guides:
                self.position_data.update({
                    guide.replace("_GUIDE", ""): get_data(guide.replace("_GUIDE", "")),
                })

        except:
            pass



class FootFingersGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="foot", prefix=False, controller_number=3):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = limb_name
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = int(controller_number)
        self.prefix = None
        ctl = "" if prefix == False else self.reverse_foot_name
        def maybe_cap(s):
            return s.capitalize() if ctl else s

        names = ["thumb", "index", "middle", "pinky", "ring"]
        self.position_data = {}
        for i in range(0, int(self.controller_number)):
            self.position_data[f"{ctl}{maybe_cap(names[i])}01"] = get_data(f"{self.sides}_{ctl}{maybe_cap(names[i])}01")
            self.position_data[f"{ctl}{maybe_cap(names[i])}02"] = get_data(f"{self.sides}_{ctl}{maybe_cap(names[i])}02")
            self.position_data[f"{ctl}{maybe_cap(names[i])}03"] = get_data(f"{self.sides}_{ctl}{maybe_cap(names[i])}03")
        
class JiggleJoint(GuideCreation):
    """
    Guide creation for jiggle joints.
    """
    sides = ["L", "R"]
    limb_name = "jiggleJoint"
    aim_name = None
    aim_offset = 0

    def __init__(self, prefix="tail"):
        self.prefix = prefix
        position_data = {
            f"{prefix}JiggleJoint": get_data(f"{prefix}JiggleJoint"),

        }
        self.position_data.update(position_data)

class NoseGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="nose"):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = "nose"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None

        self.position_data = {
        f"noseBase": get_data(f"C_noseBase"),
        f"noseMain": get_data(f"C_noseMain"),
        f"noseTip": get_data(f"C_noseTip"),
        f"L_noseFlare": get_data(f"L_noseFlare"),
        f"R_noseFlare": get_data(f"R_noseFlare"),
        f"L_innerNose": get_data(f"L_innerNose"),
        f"R_innerNose": get_data(f"R_innerNose"),


    }
        
class CheekGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="cheek"):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = "cheek"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None

        self.position_data = {
        f"cheek": get_data(f"{self.sides}_cheek"),
    }
        
class CheekBoneGuideCreation(GuideCreation):
    """
    Guide creation for feet.
    """
    def __init__(self, side = "L", limb_name="cheekBone", input_name="cheekBone"):
        self.sides = side
        self.reverse_foot_name = limb_name
        self.limb_name = "cheekBone"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None

        final_path = core.DataManager.get_guide_data()
        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        guide_set_name = next(iter(guides_data))
        parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}


        def collect_descendants(parent, parent_map):
            descendants = []
            children = [joint for joint, p in parent_map.items() if p == parent]

            for child in children:
                descendants.append(child)
                descendants.extend(collect_descendants(child, parent_map))
            return descendants



        all_child_guides = [f"{self.sides}_{input_name}_GUIDE"] + collect_descendants(f"{self.sides}_{input_name}_GUIDE", parent_map)
        self.position_data = {}

        try:
            for guide in all_child_guides:
                self.position_data.update({
                    guide.split("_")[1]: get_data(guide.replace("_GUIDE", "")),
                })
        except:
            pass


class MouthGuideCreation(GuideCreation):
    """
    Guide creation for mouth.
    """
    def __init__(self, side = "C", input_name="mouthCurve"):
        self.sides = side
        self.limb_name = "mouth"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None

        final_path = core.DataManager.get_guide_data()
        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        guide_set_name = next(iter(guides_data))
        parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}

        def collect_descendants(parent, parent_map):
            descendants = []
            children = [joint for joint, p in parent_map.items() if p == parent]
            for child in children:
                descendants.append(child)
                descendants.extend(collect_descendants(child, parent_map))
            return descendants

        all_child_guides = [input_name] + collect_descendants(input_name, parent_map)
        print(all_child_guides)
        self.position_data = {
               # "jaw": get_data(f"{self.sides}_jaw"),
        }

        try:
            for guide in all_child_guides:
                self.position_data.update({
                    # guide.split("_")[1]: get_data(guide.replace("_GUIDE", "")),
                    guide.replace("_GUIDE", ""): get_data(guide.replace("_GUIDE", "")),
                })
            print(self.position_data    )
        except:
            pass

class EyebrowGuideCreation(GuideCreation):
    """
    Guide creation for eyebrow.
    """
    def __init__(self, side = "C", input_name="eyebrow"):
        self.sides = side
        self.limb_name = "eyebrow"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None

        final_path = core.DataManager.get_guide_data()
        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        guide_set_name = next(iter(guides_data))
        parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}

        def collect_descendants(parent, parent_map):
            descendants = []
            children = [joint for joint, p in parent_map.items() if p == parent]
            for child in children:
                descendants.append(child)
                descendants.extend(collect_descendants(child, parent_map))
            return descendants

        self.position_data = {
                "centerBrow": get_data(f"{self.sides}_centerBrow"),
        }
        all_child_guides = collect_descendants(input_name, parent_map)

        try:
            for guide in all_child_guides:
                self.position_data.update({
                    guide.replace("_GUIDE", ""): get_data(guide.replace("_GUIDE", "")),
                })

        except:
            pass

class EyesGuideCreation(GuideCreation):
    """
    Guide creation for eye.
    """
    def __init__(self, side = "L", input_name="eyeCurve"):
        self.sides = side
        self.limb_name = "eye"
        self.aim_name = None
        self.aim_offset = 0
        self.controller_number = None
        self.prefix = None

        final_path = core.DataManager.get_guide_data()
        try:
            with open(final_path, "r") as infile:
                guides_data = json.load(infile)
        except Exception as e:
            om.MGlobal.displayError(f"Error loading guides data: {e}")

        guide_set_name = next(iter(guides_data))
        parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}

        def collect_descendants(parent, parent_map):
            descendants = []
            children = [joint for joint, p in parent_map.items() if p == parent]
            for child in children:
                descendants.append(child)
                descendants.extend(collect_descendants(child, parent_map))
            return descendants

        all_child_guides = [input_name] + collect_descendants(input_name, parent_map)
        self.position_data = {
                "eye": get_data(f"{self.sides}_eye"),
                "endEye": get_data(f"{self.sides}_endEye"),
        }

        try:
            for guide in all_child_guides:
                self.position_data.update({
                    guide.split("_")[1]: get_data(guide.replace("_GUIDE", "")),
            })
        except:
            pass


def load_guides(path = ""):

    core.load_data()

    final_path = core.DataManager.get_guide_data()

    model_path = core.DataManager.get_model_path()
    if model_path and os.path.exists(model_path):
        cmds.file(model_path, o=True, f=True)
        om.MGlobal.displayInfo(f"Imported model from {model_path}")

    try:
        with open(final_path, "r") as infile:
            guides_data = json.load(infile)

    except Exception as e:
        om.MGlobal.displayError(f"Error loading guides data: {e}")

    # Example: get world position and rotation for "wrist"

    if not cmds.objExists("guides_GRP"):
        guides_trn = cmds.createNode("transform", name="guides_GRP", ss=True)
    else:
        guides_trn = "guides_GRP"

    if not cmds.attributeQuery("adonisSetup", node=guides_trn, exists=True):
            cmds.addAttr(guides_trn, longName="adonisSetup", attributeType="bool", defaultValue=False, keyable=False)

    if not cmds.objExists("buffers_GRP"):
        buffers_trn = cmds.createNode("transform", name="buffers_GRP", ss=True)
    else:
        buffers_trn = "buffers_GRP"
        if cmds.listRelatives(buffers_trn, parent=True) != [guides_trn]:
            cmds.parent(buffers_trn, guides_trn)

    cmds.setAttr(f"{buffers_trn}.hiddenInOutliner ", True)

    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            if template_name == "adonis":
                cmds.setAttr(f"{guides_trn}.adonisSetup", guides)
            continue  
        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":
                if guide_info.get("moduleName") == "leg":
                    LegGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "arm":
                    ArmGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "backLeg":
                    BackLegGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "frontLeg":
                    FrontLegGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "spineQuad":
                    SpineQuadGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist"), type=guide_info.get("type")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "spine":
                    SpineBipedGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist"), type=guide_info.get("type")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "neckQuad":
                    NeckQuadGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist"), type=guide_info.get("type")).create_guides(guides_trn, buffers_trn)
                
                if guide_info.get("moduleName") == "neck":
                    NeckBipedGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist"), type=guide_info.get("type")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "tail":
                    TailGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist"), type=guide_info.get("type")).create_guides(guides_trn, buffers_trn)
                    
                if guide_info.get("moduleName") == "tongue":
                    TongueGuideCreation(side=guide_name.split("_")[0], twist_joints=guide_info.get("jointTwist"), type=guide_info.get("type")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "foot":
                    limb_name = "foot" if guide_name.split("_")[1].split("BankOut")[0] == "bankOut" else guide_name.split("_")[1].split("BankOut")[0]
                    FootGuideCreation(side=guide_name.split("_")[0], limb_name=limb_name).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "handQuad" or guide_info.get("moduleName") == "handBiped":
                    HandGuideCreation(side=guide_name.split("_")[0], controller_number=guide_info.get("controllerNumber"), type_name=guide_info.get("moduleName")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "membran":
                    MembraneCreation(side=guide_name.split("_")[0]).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "eye":
                    EyesGuideCreation(side=guide_name.split("_")[0], input_name=guide_name).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "eyebrow":
                    EyebrowGuideCreation(side=guide_name.split("_")[0], input_name=guide_name).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "fkFinger":
                    name = guide_name.split("_")[1].replace("Metacarpal", "")
                    name = re.sub(r"\d+", "", name)
                    FkFingersGuideCreation(side=guide_name.split("_")[0], limb_name=name, prefix=False, controller_number=guide_info.get("controllerNumber")).create_guides(guides_trn, buffers_trn)
                                    
                if guide_info.get("moduleName") == "backLegFoot" or guide_info.get("moduleName") == "frontLegFoot" or "footBack" in guide_name or "footFront" in guide_name:
                    if "backLegFoot" in guide_name or "frontLegFoot" in guide_name or "footBack" in guide_name or "footFront" in guide_name:
                        FootFingersGuideCreation(side=guide_name.split("_")[0], limb_name=guide_info.get("moduleName"), prefix=True, controller_number=guide_info.get("controllerNumber")).create_guides(guides_trn, buffers_trn)
                    else:
                        FootFingersGuideCreation(side=guide_name.split("_")[0], limb_name=guide_info.get("moduleName"), prefix=False, controller_number=guide_info.get("controllerNumber")).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "mouth":
                    MouthGuideCreation(side=guide_name.split("_")[0],input_name=guide_name).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "nose":
                    NoseGuideCreation(side=guide_name.split("_")[0],limb_name=guide_name).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "cheek":
                    CheekGuideCreation(side=guide_name.split("_")[0],limb_name=guide_name).create_guides(guides_trn, buffers_trn)
                
                if guide_info.get("moduleName") == "cheekBone":
                    name = guide_name.split("_")[1]
                    CheekBoneGuideCreation(side=guide_name.split("_")[0],limb_name=guide_name, input_name=name).create_guides(guides_trn, buffers_trn)

                if guide_info.get("moduleName") == "spikes":
                    SpikesGuideCreation(side=guide_name.split("_")[0],limb_name=guide_name).create_guides(guides_trn, buffers_trn)


def create_curve_guide(name=""):

    path = core.DataManager.get_guide_data()

    with open(path, "r") as f:
        guide_data = json.load(f)
    
    data = None

    for key, index_data in guide_data[next(iter(guide_data))].items():
        if key == name:
            data = index_data

    if data is None:
        om.MGlobal.displayError(f"Guide data for {name} not found.")
        return None

    dag_modifier = om.MDagModifier()
    transform_obj = dag_modifier.createNode("transform")
    dag_modifier.doIt()
    transform_fn = om.MFnDagNode(transform_obj)
    transform_fn.setName(name)
    dag_modifier.doIt()

    created_shapes = []

    # curve_info = guide_data["curve"]
    cvs = data.get("cvs")
    degree = data.get("degree")
    knots = data.get("knots")
    form = data.get("form")

    form_flags = {
        "open": om.MFnNurbsCurve.kOpen,
        "closed": om.MFnNurbsCurve.kClosed,
        "periodic": om.MFnNurbsCurve.kPeriodic
    }
    form_flag = form_flags.get(form, om.MFnNurbsCurve.kOpen)

    points = om.MPointArray()
    for pt in cvs:
        points.append(om.MPoint(pt[0], pt[1], pt[2]))

    curve_fn = om.MFnNurbsCurve()
    shape_obj = curve_fn.create(
        points,
        knots,
        degree,
        form_flag,
        False,    
        True,     
        transform_obj
    )

    shape_fn = om.MFnDagNode(shape_obj)
    shape_fn.setName(name + "Shape")
    created_shapes.append(shape_obj)

    return transform_fn.name()

def curve_data(curve):
    shape = cmds.listRelatives(curve, shapes=True, fullPath=True, type="nurbsCurve")[0] or []
    sel_list = om.MSelectionList()
    shape_data_list = []

    sel_list.clear()
    sel_list.add(shape)
    shape_obj = sel_list.getDependNode(0)

    curve_fn = om.MFnNurbsCurve(shape_obj)

    cvs = []
    for i in range(curve_fn.numCVs):
        pt = curve_fn.cvPosition(i)
        cvs.append((pt.x, pt.y, pt.z))

    form_types = {
        om.MFnNurbsCurve.kOpen: "open",
        om.MFnNurbsCurve.kClosed: "closed",
        om.MFnNurbsCurve.kPeriodic: "periodic"
    }

    form = form_types.get(curve_fn.form, "unknown")
    if form == "unknown":
        om.MGlobal.displayWarning(f"Curve form unknown for {shape}")

    knots = curve_fn.knots()
    degree = curve_fn.degree

    shape_data_list = {
        "cvs": cvs,
        "form": form,
        "knots": list(knots),
        "degree": degree
        }


    return shape_data_list

def guides_export(mirror=False):
        """
        Exports the guides from the selected folder in the Maya scene to a JSON file.
        """

        TEMPLATE_FILE = core.DataManager.get_guide_data()
        print(f"Exporting guides to {TEMPLATE_FILE}")
        
        guides_folder = cmds.ls("guides_GRP", type="transform")

        if guides_folder:
                guides_descendents = [
                                node for node in cmds.listRelatives(guides_folder[0], allDescendents=True, type="transform")
                                if "buffer" not in node.lower() and "_guide_crv" not in node.lower()
                ]


                if not guides_descendents:
                        om.MGlobal.displayError("No guides found in the scene.")
                        return


                guides_get_translation = []
                guides_get_rotation = []
                if mirror == True:
                    for guide in guides_descendents:
                        if "R_" in guide:
                            guide_l = guide.replace("R_", "L_")
                            xform_value = cmds.xform(guide_l, q=True, ws=True, translation=True)
                            xform_value = [xform_value[0]*-1, xform_value[1], xform_value[2]]

                            xform_value_rotate = cmds.xform(guide_l, q=True, ws=True, rotation=True)
                            xform_value_rotate = [xform_value_rotate[0], xform_value_rotate[1]*-1, xform_value_rotate[2]*-1]
                        elif "L_" in guide or "C_" in guide:
                            xform_value = cmds.xform(guide, q=True, ws=True, translation=True)
                            xform_value_rotate = cmds.xform(guide, q=True, ws=True, rotation=True)

                        guides_get_translation.append(xform_value)
                        guides_get_rotation.append(xform_value_rotate)

                else:
                    guides_get_translation = [cmds.xform(guide, q=True, ws=True, translation=True) for guide in guides_descendents]
                    guides_get_rotation = [cmds.xform(guide, q=True, ws=True, rotation=True) for guide in guides_descendents]
              
                guides_parents = [cmds.listRelatives(guide, parent=True)[0] for guide in guides_descendents]
                guides_joint_twist = []
                guides_type = []
                guides_module_name = []
                guides_prefix_name = []
                guides_ctl_number = []
                guides_type_object = []
                guides_cvs = []

                for guide in guides_descendents:
                        # Try to get 'jointTwist' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("jointTwist", node=guide, exists=True):
                                joint_twist = cmds.getAttr(f"{guide}.jointTwist")
                        else:
                                joint_twist = "Child"
                        guides_joint_twist.append(joint_twist)

                        # Try to get 'type' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("type", node=guide, exists=True):
                                guide_type = cmds.getAttr(f"{guide}.type")
                        else:
                                guide_type = "Child"
                        guides_type.append(guide_type)

                        # Try to get 'type' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("controllerNumber", node=guide, exists=True):
                                guide_type = cmds.getAttr(f"{guide}.controllerNumber")
                        else:
                                guide_type = "Child"
                        guides_ctl_number.append(guide_type)

                        if cmds.attributeQuery("guideTypeObject", node=guide, exists=True):
                                # guide_type_object = cmds.getAttr(f"{guide}.guideTypeObject")

                                index = cmds.getAttr(f"{guide}.guideTypeObject")
                                enum_string = cmds.addAttr(f"{guide}.guideTypeObject", q=True, en=True)
                                enum_list = enum_string.split(":")
                                guide_type_object = enum_list[index]
                        else:
                                guide_type_object = "Child"
                        guides_type_object.append(guide_type_object)

                        # Try to get 'moduleName' attribute, if not present, set value as 'Child'
                        if cmds.attributeQuery("moduleName", node=guide, exists=True):
                            index = cmds.getAttr(f"{guide}.moduleName")
                            enum_string = cmds.addAttr(f"{guide}.moduleName", q=True, en=True)
                            enum_list = enum_string.split(":")
                            module_name = enum_list[index]

                        else:
                                module_name = "Child"
                        guides_module_name.append(module_name)
                        

                        if cmds.attributeQuery("prefix", node=guide, exists=True):
                                index = cmds.getAttr(f"{guide}.prefix")
                                enum_string = cmds.addAttr(f"{guide}.prefix", q=True, en=True)
                                enum_list = enum_string.split(":")
                                prefix_name = enum_list[index]  
                        else:
                                prefix_name = "Child"
                        guides_prefix_name.append(prefix_name)



        else:
                om.MGlobal.displayError("No guides found in the scene.")
                return
        
        guides_name = core.DataManager.get_asset_name() if core.DataManager.get_asset_name() else os.path.splitext(os.path.basename(TEMPLATE_FILE))[0]
        try:
            adonis = int(cmds.getAttr(f"{guides_folder[0]}.adonisSetup"))
        except:
            adonis = 0

        guides_data = {guides_name: {},
                    "adonis": adonis}

        for i, guide in enumerate(guides_descendents):
                if guides_type_object[i] == "NurbsSurface":
                    guides_data[guides_name][guide] = curve_tool.get_all_nurbs_surfaces_data(guide)

                    guides_data[guides_name][guide].update({
                        "parent": guides_parents[i],
                        "jointTwist": guides_joint_twist[i],
                        "type": guides_type[i],
                        "moduleName": guides_module_name[i],
                        "prefix": guides_prefix_name[i],
                        "controllerNumber": guides_ctl_number[i],
                        "guide_type_object": guides_type_object[i],
                    })
                elif guides_type_object[i] == "Curve" or "Curve" in guide:

                    if guides_type_object[i] != "Curve":
                         guides_type_object[i] = "Curve"

                    guides_data[guides_name][guide] = curve_data(guide)

                    guides_data[guides_name][guide].update({
                        "parent": guides_parents[i],
                        "jointTwist": guides_joint_twist[i],
                        "type": guides_type[i],
                        "moduleName": guides_module_name[i],
                        "prefix": guides_prefix_name[i],
                        "controllerNumber": guides_ctl_number[i],
                        "guide_type_object": guides_type_object[i],
                    })
                else:
                    guides_data[guides_name][guide] = {
                            "worldPosition": guides_get_translation[i],
                            "worldRotation": guides_get_rotation[i],
                            "parent": guides_parents[i],
                            "jointTwist": guides_joint_twist[i],
                            "type": guides_type[i],
                            "moduleName": guides_module_name[i],
                            "prefix": guides_prefix_name[i],
                            "controllerNumber": guides_ctl_number[i],
                            "guide_type_object": guides_type_object[i],

                    }


        with open(os.path.join(TEMPLATE_FILE), "w") as outfile:
                json.dump(guides_data, outfile, indent=4)

        om.MGlobal.displayInfo(f"Guides data exported to {TEMPLATE_FILE}")

def guide_import(joint_name, all_descendents=True, path=None, useGuideRotation=False):
        """
        Imports guides from a JSON file into the Maya scene.
        
        Args:
                joint_name (str): The name of the joint to import. If "all", imports all guides.
                all_descendents (bool): If True, imports all descendents of the specified joint. Defaults to True.
        Returns:
                list: A list of imported joint names if joint_name is not "all", otherwise returns the world position and rotation of the specified joint.
        """
        
        data_exporter = data_export.DataExport()
        guides_grp = data_exporter.get_data("basic_structure", "guides_GRP")


        if cmds.objExists(guides_grp):
                guide_grp = guides_grp
        else:
                guide_grp = cmds.createNode("transform", name="guides_GRP")

        transforms_chain_export = []

        if all_descendents:
                
            if all_descendents is True:
                world_position, parent, moduleName, prefix, guideType, world_rotation = get_data(joint_name, module_name=True)
                if guideType == "Guide" or guideType == "Transform":
                    guide_transform = cmds.createNode('transform', name=joint_name)
                    cmds.xform(guide_transform, ws=True, t=world_position)
                    if useGuideRotation:    
                        cmds.xform(guide_transform, ws=True, ro=world_rotation)
                elif guideType == "NurbsSurface":
                    guide_transform = curve_tool.build_surfaces_from_template(path=core.DataManager.get_guide_data(), target_transform_name=joint_name)
                elif guideType == "Curve":
                    guide_transform = create_curve_guide(name=joint_name)
                cmds.parent(guide_transform, guide_grp)

                transforms_chain_export.append(guide_transform)
                if moduleName != "Child":
                        cmds.addAttr(guide_transform, longName="moduleName", attributeType="enum", enumName=moduleName, keyable=False)
                if prefix != "Child":
                        cmds.addAttr(guide_transform, longName="prefix", attributeType="enum", enumName=prefix, keyable=False)
                if guideType == "NurbsSurface":
                        cmds.addAttr(guide_transform, longName="guideType", attributeType="enum", enumName=guideType, keyable=False)


                final_path = core.DataManager.get_guide_data()

                with open(final_path, "r") as infile:
                    guides_data = json.load(infile)

                guide_set_name = next(iter(guides_data))
                parent_map = {joint: data.get("parent") for joint, data in guides_data[guide_set_name].items()}
                transforms_chain = []
                processing_queue = [joint for joint, parent in parent_map.items() if parent == joint_name]

                while processing_queue:
                        joint = processing_queue.pop(0)
                        if "Settings" in joint:
                                continue
                        cmds.select(clear=True)
                        world_position, parent, moduleName, prefix, guideType, world_rotation = get_data(joint, module_name=True)


                        if guideType == "Guide" or guideType == "Transform":
                            imported_transform = cmds.createNode('transform', name=joint)
                            position = guides_data[guide_set_name][joint]["worldPosition"]
                            rotation = guides_data[guide_set_name][joint]["worldRotation"]
                            if useGuideRotation:
                                cmds.xform(imported_transform, ws=True, ro=rotation)
                            cmds.xform(imported_transform, ws=True, t=position)
                        elif guideType == "NurbsSurface":
                            imported_transform=curve_tool.build_surfaces_from_template(path=core.DataManager.get_guide_data(), target_transform_name=joint)

                        elif guideType == "Curve":
                            imported_transform = create_curve_guide(name=joint)

                        parent = parent_map[joint]

                        if parent and parent != "C_root_JNT":
                                        cmds.parent(imported_transform, parent)
                        transforms_chain.append(joint)
                        children = [child for child, p in parent_map.items() if p == joint]
                        processing_queue.extend(children)
                        transforms_chain_export.append(imported_transform)
                                                    
        else:


            world_position, parent, moduleName, prefix, guideType, world_rotation = get_data(joint_name, module_name=True)

            if guideType == "Guide" or guideType == "Transform":
                guide_transform = cmds.createNode('transform', name=joint_name)
                cmds.xform(guide_transform, ws=True, t=world_position)
                if useGuideRotation:
                    cmds.xform(guide_transform, ws=True, ro=world_rotation)
            elif guideType == "NurbsSurface":
                guide_transform=curve_tool.build_surfaces_from_template(path=core.DataManager.get_guide_data(), target_transform_name=joint_name)

            elif guideType == "Curve":
                guide_transform = create_curve_guide(name=joint_name)



            cmds.parent(guide_transform, guide_grp)
            transforms_chain_export.append(guide_transform)
            if moduleName != "Child":
                    cmds.addAttr(guide_transform, longName="moduleName", attributeType="enum", enumName=moduleName, keyable=False)
            if prefix != "Child":
                    cmds.addAttr(guide_transform, longName="prefix", attributeType="enum", enumName=prefix, keyable=False)

        return transforms_chain_export

def add_module_to_guide():
    """
    Adds a module to the guide creation process.
    """


    project_manager.load_asset_configuration(asset_name = "varyndor")

    load_guides()
    guides_trn = "guides_GRP"
    buffers_trn = "buffers_GRP"
    # EyebrowGuideCreation(side="C", input_name="C_centerBrow").create_guides(guides_trn, buffers_trn)
    # NoseGuideCreation(side="C",).create_guides(guides_trn, buffers_trn)
    # CheekBoneGuideCreation(side="L",input_name="lowerEyeSocket01").create_guides(guides_trn, buffers_trn)
    # CheekBoneGuideCreation(side="R",input_name="lowerEyeSocket01").create_guides(guides_trn, buffers_trn)
    # CheekBoneGuideCreation(side="L",input_name="lowerEyeSocket01").create_guides(guides_trn, buffers_trn)
    # CheekBoneGuideCreation(side="R",input_name="lowerEyeSocket01").create_guides(guides_trn, buffers_trn)
    # CheekGuideCreation(side="L", limb_name="cheek").create_guides(guides_trn, buffers_trn)
    # CheekGuideCreation(side="R", limb_name="cheek").create_guides(guides_trn, buffers_trn)
    # CheekBoneGuideCreation(side="L",input_name="cheekBone01").create_guides(guides_trn, buffers_trn)
    # CheekBoneGuideCreation(side="R",input_name="cheekBone01").create_guides(guides_trn, buffers_trn)
    TongueGuideCreation(side="C", twist_joints=10, type="tongue").create_guides(guides_trn, buffers_trn)


    # SpikesGuideCreation(side="L", limb_name="upperSpikes", prefix=False).create_guides(guides_trn, buffers_trn)
    # SpikesGuideCreation(side="R", limb_name="upperSpikes", prefix=False).create_guides(guides_trn, buffers_trn)
    # FkFingersGuideCreation(side="R", limb_name="footFinger", prefix=False, controller_number=2).create_guides(guides_trn, buffers_trn)
    # FkFingersGuideCreation(side="L", limb_name="footFinger", prefix=False, controller_number=2).create_guides(guides_trn, buffers_trn)

# add_module_to_guide()

""" --- Debug code for maya

from importlib import reload
from elmoTools.utils import core
from elmoTools.utils import data_export
from elmoTools.utils import guide_creation
reload(guide_creation)

core.DataManager.set_guide_data("P:/VFX_Project_20/PUIASTRE_PRODUCTIONS/00_Pipeline/puiastre_tools/guides/AYCHEDRAL_015.guides")
core.DataManager.set_asset_name("Dragon")
core.DataManager.set_mesh_data("Puiastre")


# guide_creation.load_guides()

guide_creation.guide_import("C_lipsTransform_GUIDE", all_descendents=True)

guide_creation.guides_export()
"""

