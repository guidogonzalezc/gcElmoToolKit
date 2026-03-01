import elmoTools.utils.core as core
import maya.cmds as cmds
from elmoTools.utils import data_export
import json
import os
import maya.api.OpenMaya as om

def _get_settings_transforms():

    data_exporter = data_export.DataExport()

    build_path = data_exporter.build_path
    try:
        
        with open(build_path, "r") as f:
            build_data = json.load(f)

    except IOError as e:
        om.MGlobal.displayError(f"File error: Could not find or read a data file. {e}")
        return
    except json.JSONDecodeError as e:
        om.MGlobal.displayError(f"JSON error: The file is malformed. {e}")
        return
    except Exception as e:
        om.MGlobal.displayError(f"Unexpected error while loading files: {e}")
        return


    settings_trn = []
    for module, data in build_data.items():
        if data.get("settings_transform"):
            settings_trn.append(data["settings_transform"])

    return settings_trn

def export_settings():  
    core.load_data()
    extra_attrs_path = core.DataManager.get_extra_data_path()

    settings_trn = _get_settings_transforms()

    dict_to_export = {}

    for trn in settings_trn:
        if not cmds.objExists(trn):
            om.MGlobal.displayWarning(f"Settings transform not found in scene: {trn}. Skipping.")
            continue

        dict_to_export[trn] = {}

        keyable_attrs = cmds.listAttr(trn, keyable=True) or []

        for attr in keyable_attrs:
            attr_plug = f"{trn}.{attr}"
            
            try:
                val = cmds.getAttr(attr_plug)
                
                dict_to_export[trn][attr] = val
                
            except Exception as e:
                om.MGlobal.displayWarning(f"Could not read {attr_plug}: {e}")
    with open(extra_attrs_path, "w") as f:
        json.dump(dict_to_export, f, indent=4)

    om.MGlobal.displayInfo("Settings export complete.")


def import_settings():
    """
    Reads a nested dictionary of {transform: {attribute: value}} and applies
    the values to the scene, safely bypassing locked or connected attributes.
    """

    extra_attrs_path = core.DataManager.get_extra_data_path()

    with open(extra_attrs_path, "r") as f:
        settings_dict = json.load(f)


    if not settings_dict:
        om.MGlobal.displayWarning("Provided settings dictionary is empty.")
        return

    for trn, attrs in settings_dict.items():
        # 1. Check if the transform exists in the current scene
        if not cmds.objExists(trn):
            om.MGlobal.displayWarning(f"Transform not found: {trn}. Skipping.")
            continue
            
        # 2. Iterate through the saved attributes
        for attr, value in attrs.items():
            plug = '{}.{}'.format(trn, attr)
            
            # Check if the specific attribute exists on the node
            if not cmds.objExists(plug):
                om.MGlobal.displayWarning(f'Attribute not found: "{plug}". Skipping.')
                continue
                
            # 3. DG Safety Checks: Is it locked or connected?
            is_locked = cmds.getAttr(plug, lock=True)
            is_connected = cmds.listConnections(plug, source=True, destination=False)
            
            if is_locked:
                om.MGlobal.displayWarning(f'Cannot set "{plug}". It is locked.' )
                continue
                
            if is_connected:
                om.MGlobal.displayWarning(f'Cannot set "{plug}". It has incoming connections.')
                continue
                
            # 4. Safely apply the value based on data type
            try:
                # Maya requires the type flag for string attributes
                if isinstance(value, str):
                    cmds.setAttr(plug, value, type="string")
                else:
                    cmds.setAttr(plug, value)
                    
            except Exception as e:
                # Catch complex data type mismatches (e.g., matrices or arrays)
                om.MGlobal.displayWarning(f'Failed to set "{plug}" to {value}: {e}')

    om.MGlobal.displayInfo("Settings import complete.")

def mirror_settings_attributes():
    """
    Finds the symmetrical counterpart of a transform (L_ <-> R_) and mirrors 
    its Channel Box attributes by multiplying their values by -1.
    """

    settings_trn = _get_settings_transforms()

    for source_trn in settings_trn:
        if not cmds.objExists(source_trn):
            om.MGlobal.displayWarning(f"Source transform does not exist: {source_trn}")
            return

        parts = source_trn.split("_")
        if parts[0] == "L":
            parts[0] = "R"
        else:
            om.MGlobal.displayWarning(f"Transform {source_trn} isnt L. Cannot mirror.")
            continue

        target_trn = "_".join(parts)

        # 2. Check if the mirror target exists
        if not cmds.objExists(target_trn):
            om.MGlobal.displayWarning(f"Mirror target does not exist: {target_trn}")
            return

        # 3. Gather attributes from the source
        keyable_attrs = cmds.listAttr(source_trn, keyable=True) or []

        # 4. Loop through and apply to target
        for attr in keyable_attrs:
            src_plug = f'{source_trn}.{attr}'
            tgt_plug = f'{target_trn}.{attr}'

            # Check if attribute exists on target
            if not cmds.objExists(tgt_plug):
                om.MGlobal.displayWarning(f'Attribute not found on mirror: "{tgt_plug}"')
                continue

            # Check DG State on target
            if cmds.getAttr(tgt_plug, lock=True):
                om.MGlobal.displayWarning(f'Cannot set "{tgt_plug}". It is locked.')
                continue
                
            if cmds.listConnections(tgt_plug, source=True, destination=False):
                om.MGlobal.displayWarning(f'Cannot set "{tgt_plug}". It has incoming connections.')
                continue

            # Query source value
            value = cmds.getAttr(src_plug)

            try:
                # 5. Type checking: Only multiply numbers (avoid strings, booleans, enums if possible)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    mirrored_value = value * -1
                    cmds.setAttr(tgt_plug, mirrored_value)
                
                elif isinstance(value, str):
                    # Strings cannot be multiplied by -1, just copy them
                    cmds.setAttr(tgt_plug, value, type="string")
                    
                else:
                    # Booleans or unhandled types, just copy them to avoid breaking logic
                    cmds.setAttr(tgt_plug, value)

            except Exception as e:
                om.MGlobal.displayWarning(f'Failed to mirror "{tgt_plug}" to {value}: {e}')

        om.MGlobal.displayInfo(f'Successfully mirrored attributes from "{source_trn}" to "{target_trn}".')

#mirror_settings_attributes()
# export_settings()