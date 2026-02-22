import maya.cmds as cmds
from elmoTools.utils.curve_tool import controller_creator
from elmoTools.utils import data_export

def get_structure_config(adonis_setup=0):
    """
    Returns the hierarchy dictionary based on the setup type.
    Key = Parent Group
    Value = List of children (Transforms or Controllers)
    """
    hierarchy = {
        "controls_GRP": [
            "C_characterNode",
            "C_masterWalk",
            "C_preferences"
        ],
        "rig_GRP": [
            "modules_GRP",
            "skel_GRP",
            "geoLayering_GRP",
            "skeletonHierarchy_GRP",
            "guides_GRP",
        ],
        "model_GRP": [
        ],
        "groom_GRP": [],
        "clothSim_GRP": [],
    }

    if adonis_setup:
        hierarchy["muscleLocators_GRP"] = []
        hierarchy["muscleSystems_GRP"] = []
        hierarchy["adonis_GRP"] = []
        
        hierarchy["model_GRP"] = ["SKELETON", "MUSCLES", "PROXY", "SKINNED_MODEL","MODEL"]
    
    return hierarchy

def create_basic_structure(asset_name="assetName", adonis_setup=0):
    """
    Create basic asset structure using a robust dictionary lookup system.
    """
    structure_map = get_structure_config(adonis_setup)
    
    nodes = {} 
    
    ordered_ctls = []

    main_transform = cmds.createNode("transform", name=asset_name, ss=True)
    nodes[asset_name] = main_transform

    for parent_grp, children in structure_map.items():
        
        parent_node = cmds.createNode("transform", name=parent_grp, parent=main_transform, ss=True)
        nodes[parent_grp] = parent_node
        
        children = sorted(list(children))
        
        for child in children:
            
            if child.startswith("C_"):
                lock_attrs = ["sx", "sy", "sz", "v"]
                ro = True
                
                if "preferences" in child:
                    lock_attrs += ["tx", "ty", "tz", "rx", "ry", "rz"]
                    ro = False 

                ctl, grp = controller_creator(child, ["GRP", "ANM"], lock=lock_attrs, ro=ro)
                
                cmds.setAttr(f"{ctl}.overrideEnabled", 1)
                
                if ordered_ctls:
                    cmds.parent(grp[0], ordered_ctls[-1])
                else:
                    cmds.parent(grp[0], parent_node)
                
                ordered_ctls.append(ctl)
                nodes[child] = ctl
                
            else:
                child_node = cmds.createNode("transform", name=child, parent=parent_node, ss=True)
                nodes[child] = child_node


    pref_ctl = nodes.get("C_preferences") 
    walk_ctl = nodes.get("C_masterWalk")

    export_data = {
        "modules_GRP": nodes.get("modules_GRP"),
        "skel_GRP": nodes.get("skel_GRP"),
        "masterWalk_CTL": walk_ctl,
        "guides_GRP": nodes.get("guides_GRP"),
        "skeletonHierarchy_GRP": nodes.get("skeletonHierarchy_GRP"),
        "model_GRP": nodes.get("SKINNED_MODEL") if nodes.get("SKINNED_MODEL") else nodes.get("model_GRP"),
        "skelModel_GRP": nodes.get("SKELETON") if adonis_setup and nodes.get("SKELETON") else None,
        "muscleModel_GRP": nodes.get("MUSCLES") if adonis_setup and nodes.get("MUSCLES") else None,
    }
    
    if adonis_setup:
        export_data["muscleLocators_GRP"] = nodes.get("muscleLocators_GRP")
        export_data["adonis_GRP"] = nodes.get("adonis_GRP")
        cmds.setAttr(f"{export_data['muscleLocators_GRP']}.visibility", 0)

    data_exporter = data_export.DataExport()
    data_exporter.append_data("basic_structure", export_data)

    if pref_ctl:
        cmds.addAttr(pref_ctl, shortName="extraAttr", niceName="Extra Attributes  ———", enumName="———", attributeType="enum", keyable=False)
        cmds.setAttr(f"{pref_ctl}.extraAttr", channelBox=True)
        
        cmds.addAttr(pref_ctl, shortName="reference", niceName="Reference", attributeType="bool", keyable=False, defaultValue=True)
        cmds.setAttr(f"{pref_ctl}.reference", channelBox=True)
        
        if nodes.get("model_GRP"):
            cmds.setAttr(f"{nodes['model_GRP']}.overrideDisplayType", 2)
            cmds.connectAttr(f"{pref_ctl}.reference", f"{nodes['model_GRP']}.overrideEnabled")

        # Hide on Playback
        cmds.addAttr(pref_ctl, shortName="hideControllersOnPlayblast", niceName="Hide Controllers On Playblast", attributeType="bool", keyable=False, defaultValue=False)
        cmds.setAttr(f"{pref_ctl}.hideControllersOnPlayblast", channelBox=True)
        if nodes.get("controls_GRP"):
            cmds.connectAttr(f"{pref_ctl}.hideControllersOnPlayblast", f"{nodes['controls_GRP']}.hideOnPlayback")

        # Visibilities
        cmds.addAttr(pref_ctl, shortName="extraVisibility", niceName="Extra Visibility  ———", enumName="———", attributeType="enum", keyable=False)
        cmds.setAttr(f"{pref_ctl}.extraVisibility", channelBox=True)


        
        toggles = [
            ("showModules", "modules_GRP"),
            ("showSkeleton", "skeletonHierarchy_GRP"),
            ("showOutJoints", "skel_GRP")
        ]
        
        for attr, grp in toggles:
            cmds.addAttr(pref_ctl, shortName=attr, niceName=attr, attributeType="bool", keyable=False, defaultValue=False)
            cmds.setAttr(f"{pref_ctl}.{attr}", channelBox=True)
            if nodes.get(grp):
                cmds.connectAttr(f"{pref_ctl}.{attr}", f"{nodes[grp]}.visibility")

    
    if adonis_setup:
        if "SKELETON" in nodes and nodes["SKELETON"]:
            cmds.select(nodes["SKELETON"]) 
            display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_SKELETON", empty=False, num=1)
            cmds.setAttr(display_layer + ".color", 13)
            cmds.setAttr(display_layer + ".visibility", 0)
            cmds.setAttr(display_layer + ".displayType", 2)

        if "MUSCLES" in nodes and nodes["MUSCLES"]:
            cmds.select(nodes["MUSCLES"]) 
            display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_MUSCLES", empty=False, num=1)
            cmds.setAttr(display_layer + ".color", 16)
            cmds.setAttr(display_layer + ".visibility", 0)
            cmds.setAttr(display_layer + ".displayType", 2)

        if "PROXY" in nodes and nodes["PROXY"]:
            cmds.select(nodes["PROXY"]) 
            display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_PROXY", empty=False, num=1)
            cmds.setAttr(display_layer + ".color", 14)
            cmds.setAttr(display_layer + ".visibility", 0)
            cmds.setAttr(display_layer + ".displayType", 2)

        if "SKINNED_MODEL" in nodes and nodes["SKINNED_MODEL"]:
            cmds.select(nodes["SKINNED_MODEL"]) 
            display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_SKINNED_MODEL", empty=False, num=1)
            cmds.setAttr(display_layer + ".color", 15)
            cmds.setAttr(display_layer + ".visibility", 1)
            cmds.setAttr(display_layer + ".displayType", 2)

        if "MODEL" in nodes and nodes["MODEL"]:
            cmds.select(nodes["MODEL"]) 
            display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_MODEL", empty=False, num=1)
            cmds.setAttr(display_layer + ".color", 18)
            cmds.setAttr(display_layer + ".visibility", 0)
            cmds.setAttr(display_layer + ".displayType", 2)

        if "muscleLocators_GRP" in nodes and nodes["muscleLocators_GRP"]:
            cmds.select(nodes["muscleLocators_GRP"]) 
            display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_LOCATORS", empty=False, num=1)
            cmds.setAttr(display_layer + ".color", 12)
            cmds.setAttr(display_layer + ".visibility", 0)
            cmds.setAttr(display_layer + ".displayType", 2)


    elif "model_GRP" in nodes and nodes["model_GRP"]:
        cmds.select(nodes["model_GRP"]) 
        display_layer = cmds.createDisplayLayer(name=f"{asset_name.upper()}_MODEL", empty=False, num=1)
        cmds.setAttr(display_layer + ".color", 17)
        cmds.setAttr(display_layer + ".displayType", 2)

    if walk_ctl:
        cmds.addAttr(walk_ctl, shortName="extraAttributesSep", niceName="Extra Attributes  ———", enumName="———", attributeType="enum", keyable=True)
        cmds.setAttr(f"{walk_ctl}.extraAttributesSep", channelBox=True, lock=True)
        
        cmds.addAttr(walk_ctl, shortName="globalScale", niceName="Global Scale", minValue=0.001, defaultValue=1, keyable=True)

        for attr in ["sx", "sy", "sz"]:
            cmds.setAttr(f"{walk_ctl}.{attr}", keyable=False, channelBox=False, lock=False)
            cmds.connectAttr(f"{walk_ctl}.globalScale", f"{walk_ctl}.{attr}", force=True)
            cmds.setAttr(f"{walk_ctl}.{attr}", keyable=False, channelBox=False, lock=True)


    if nodes.get("guides_GRP"): cmds.setAttr(f"{nodes['guides_GRP']}.visibility", 0)

    cmds.select(clear=True)
    

# create_basic_structure("varyndor", 0)

""""

    SETS WIP


    sets = {         
        f"{asset_name}_RIG_SET": {
            "__EXPORT__SET": {
                "__EXPORT__GEO_SET": {
                    secondary_transforms[4],
                    secondary_transforms[3],
                    secondary_transforms[2],
                },
                "__EXPORT__LOCATORS_SET": {},
                "__EXPORT__SKELETON_HIERARCHY_SET": {
                    rig_transforms[3]
                }

            },
            "CONTROLS_SET": {
                ctls[0],
                ctls[1],
                ctls[2],
            }
        }
    }

    set_node = cmds.sets(name=f"{asset_name}_RIG_SET", empty=True)
    for set_name, contents in sets[f"{asset_name}_RIG_SET"].items():
        secondary_set = cmds.sets(name=set_name, empty=True)
        cmds.sets(secondary_set, add=set_node)
        for item, inside in contents.items():
            print(item)
            print(inside)
            if item == "__EXPORT__SET":
                export_set = cmds.sets(name=item, empty=True)
                cmds.sets(export_set, add=secondary_set)

            else:
                cmds.sets(item, add=secondary_set)

         
"""



