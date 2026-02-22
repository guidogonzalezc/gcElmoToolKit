import os
import re
import maya.cmds as cmds

 
 
def connect_csv_to_simplex():
 
    attributes = [
    {"EyeBlinkLeft": "eyeClosed"},
    {"EyeSquintLeft": "lidTightener"},
    {"BrowInnerUp": "innerBrowRaiser"},
    {"BrowOuterUpLeft": "outerBrowRaiser"},
    {"BrowDownLeft": "browLowerer"},
    {"CheekSquintLeft": "cheekRaiser"},
    {"MouthSmileLeft": "lipCornerPuller"},
    {"MouthFrownLeft": "lipCornerDepressor"},
    {"MouthUpperUpLeft": "upperLipRaiser"},
    {"MouthLowerDownLeft": "lowerLipDepressor"},
    {"MouthShrugLower": "chinRaiser"},
    {"MouthShrugLower": "lipsTogether"}
    ]

    for attribute in attributes:
        for a, b in attribute.items():
            cmds.connectAttr(f"animSlate03:ARKit_BS.{a}", f"face_CTRL.{b}", f=True)

def set_attribute_value(ctl, export_dir, value=1, attribute="ty"):

    """
    Sets the specified attribute(s) to the given value and returns the file path for export.
    
    Args:
        attribute (str or list): The attribute name or list of attribute names to set.
        export_dir (str): The directory where the exported file will be saved.
        value (int): The value to set for the attribute(s).

    Returns:
        str: The file path for the exported OBJ file.
    """
    attribute_end_name = f"{attribute}Negate" if value == -1 else attribute

    if isinstance(ctl, list):
        for attr in ctl:
            cmds.setAttr(f"{attr}.{attribute}", value)
            cmds.setAttr(f"{attr.replace('CTRL_R_', 'CTRL_L_')}.{attribute}", value)
        name = ctl[0].replace("CTRL_R_","").replace("CTRL_C_", "") if ctl else "unknown"
    else:
        cmds.setAttr(f"{ctl}.{attribute}", value)
        cmds.setAttr(f"{ctl.replace('CTRL_R_', 'CTRL_L_')}.{attribute}", value)
        name = ctl.replace("CTRL_R_","").replace("CTRL_C_", "") if ctl else "unknown"    

    file_path = os.path.join(export_dir, f"{name}_{attribute_end_name}.obj")

    if value == 1:
        return  file_path

def anim_export():

    """
    Exports the head mesh with different attribute values to OBJ files in a structured directory.
    """

    # Get the current scene path and ensure it's saved
    scene_path = cmds.file(query=True, sceneName=True)
    if not scene_path:
        cmds.error("Scene is not saved. Please save the file to establish a working directory.")
        return

    scene_dir = os.path.dirname(scene_path)
    shapes_dir = os.path.join(scene_dir, "shapes")

    # Create root 'shapes' folder if it doesn't exist
    if not os.path.exists(shapes_dir):
        os.makedirs(shapes_dir)

    # Check for existing versioned folders and determine the next version number
    existing_folders = [f for f in os.listdir(shapes_dir) if os.path.isdir(os.path.join(shapes_dir, f))]
    
    highest_version = 0
    for folder in existing_folders:
        match = re.search(r'shapes_(\d+)', folder)
        if match:
            version = int(match.group(1))
            if version > highest_version:
                highest_version = version
                
    # Increment padding
    next_version = highest_version + 1
    new_folder_name = "shapes_{:03d}".format(next_version)
    export_dir = os.path.join(shapes_dir, new_folder_name)
    
    os.makedirs(export_dir)

    export_options = "groups=1;ptgroups=0;materials=0;smoothing=0;normals=1"

    # Default head and controllers metahuman names, adjust if necessary
    mesh_name = "head_lod0_mesh"

    controllers = ["CTRL_R_mouth_cornerDepress", 
                  "CTRL_R_mouth_upperLipRaise", 
                  "CTRL_R_mouth_cornerPull", 
                  ["CTRL_C_jaw", "CTRL_C_jaw_openExtreme"], 
                  "CTRL_R_nose", 
                  "CTRL_R_eye_cheekRaise", 
                  "CTRL_R_eye_blink",
                  "CTRL_R_eye_squintInner",
                  "CTRL_R_brow_lateral",
                  "CTRL_R_brow_down",
                  "CTRL_R_brow_raiseIn",
                  "CTRL_R_brow_raiseOut",
                  "CTRL_R_mouth_dimple",
                  "CTRL_R_mouth_suckBlow",
                  "CTRL_R_jaw_ChinRaiseU",
                  ["CTRL_R_jaw_ChinRaiseD", "CTRL_R_jaw_ChinRaiseU"]]
    
    # Export neutral shape
    neutral_path = os.path.join(export_dir, "_neutral.obj")

    duplicate_nodes = cmds.duplicate(mesh_name, returnRootsOnly=True, name=f"_neutral")
    if cmds.listRelatives(duplicate_nodes[0], parent=True):
        duplicate_nodes = cmds.parent(duplicate_nodes[0], world=True)[0]

    cmds.select(duplicate_nodes, replace=True)
    
    cmds.file(
            neutral_path,
            force=True,
            options=export_options,
            type="OBJexport",
            preserveReferences=True,
            exportSelected=True,
            defaultNamespace=False
        )

    cmds.delete(duplicate_nodes)    

    # Loop through attributes, set them to 1, export, then reset to 0
    for controller in controllers:
        file_path = set_attribute_value(controller, export_dir)
        
        duplicate_nodes = cmds.duplicate(mesh_name, returnRootsOnly=True, name=f"{os.path.basename(file_path).replace('.obj', '')}")[0]

        cmds.select(duplicate_nodes, replace=True)

        cmds.file(
            file_path,
            force=True,
            options=export_options,
            type="OBJexport",
            preserveReferences=True,
            exportSelected=True,
        )
        print("Exported: {}".format(file_path))

        set_attribute_value(controller, export_dir, 0)
        cmds.delete(duplicate_nodes)

    # # Extra attributes that depend on percentages or other direrctions, adjust if necessary 
    # extra_eyes_move = "CTRL_C_eye"

    # for attribute, value in zip(["tx","tx","ty", "tz"],[1,-1,1,-1]):

    #     file_path = set_attribute_value(extra_eyes_move, attribute=attribute, export_dir=export_dir, value=value)
    #     cmds.setAttr(f"{extra_eyes_move}.{attribute}", value)
    #     cmds.file(
    #         file_path,
    #         force=True,
    #         options=export_options,
    #         type="OBJexport",
    #         preserveReferences=True,
    #         exportSelected=True,
    #         # groupName=os.path.splitext(os.path.basename(file_path))[0]
    #     )
    #     print("Exported: {}".format(file_path))
    #     set_attribute_value(extra_eyes_move, attribute=attribute, export_dir=export_dir, value=0)

anim_export()