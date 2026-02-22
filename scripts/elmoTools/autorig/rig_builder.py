

# Tools / utils import
from elmoTools.utils import basic_structure
from elmoTools.utils import data_export
from elmoTools.utils import core
from elmoTools.ui import project_manager

# ---- RIG MODULES IMPORT ----

# Body modules import
from elmoTools.autorig.body import limb_module_matrix as lbm
from elmoTools.autorig.body import dragon_falanges as dfl
from elmoTools.autorig.body import dragon_leg_matrix as dlm
from elmoTools.autorig.body import neck_quad as nkq
from elmoTools.autorig.body import neck_biped as nkb
from elmoTools.autorig.body import spine_quad as spq
from elmoTools.autorig.body import spine_biped as spb
from elmoTools.autorig.body import tail_module_matrix as tmm
from elmoTools.autorig.body import membran_module as mm
from elmoTools.autorig.body import finger_module as fm
from elmoTools.autorig.body import fkFingers as fkf
from elmoTools.autorig.body import spikes_module_matrix as spm

# Skeleton hierarchy import
from elmoTools.autorig import skeleton_hierarchy as skh

# Facial modules import
from elmoTools.autorig.facial import eye_module as em
from elmoTools.autorig.facial import jaw_module_matrix as jmm
from elmoTools.autorig.facial import jaw_module_matrix_old as jmm_old
from elmoTools.autorig.facial import eyebrow_module as ebm
from elmoTools.autorig.facial import eyelid_module as elm
from elmoTools.autorig.facial import nose_module as nm
from elmoTools.autorig.facial import cheek_module as cm
from elmoTools.autorig.facial import cheekbone as cb
from elmoTools.autorig.facial import tongue_module as tm
import elmoTools.tools.skincluster_manager as skt

# Python libraries import
import maya.cmds as cmds
from importlib import reload
import json
import maya.api.OpenMaya as om
import os

reload(basic_structure)
reload(core)
reload(data_export)
reload(lbm)
reload(dfl)
reload(dlm)
reload(nkq)
reload(nkb)
reload(spq)
reload(tmm)
reload(skh)
reload(mm)
reload(fm)
reload(em)
reload(spb)
reload(fkf)
reload(jmm)
reload(ebm)
reload(elm)
reload(nm)
reload(cm)
reload(spm)
reload(skt)
reload(project_manager)
reload(cb)
reload(tm)
reload(jmm_old)

def rename_ctl_shapes():
    """
    Rename all shapes in the scene to follow a specific naming convention.
    This function finds all nurbsCurve shapes in the scene, retrieves their parent transform, and renames the shape to match the parent's name with "Shape" appended.
    """
    
    obj = cmds.ls(type="nurbsCurve")

    for shapes in obj:
        parentName = cmds.listRelatives(shapes, parent=True)[0]
        cmds.rename(shapes, f"{parentName}Shape")

def setIsHistoricallyInteresting(value=2):
    cmds.select(r=True, allDependencyNodes=True)
    allNodes = cmds.ls(sl=True)
    allNodes.extend(cmds.ls(shapes=True))

    failed = []
    for node in allNodes:
        if cmds.nodeType(node) == "skinCluster":
            continue
        else:
            plug = '{}.ihi'.format(node)
            if cmds.objExists(plug):
                try:
                    cmds.setAttr(plug, value)
                except:
                    failed.append(node)
    if failed:
        print("Skipped the following nodes {}".format(failed))


def joint_label():
    """
    Set attributes for all joints in the scene to label them according to their side and type.
    This function iterates through all joints, checks their names for side indicators (L_, R_, C_), and sets the 'side' and 'type' attributes accordingly.
    """

    for jnt in cmds.ls(type="joint"):
        if "L_" in jnt:
            cmds.setAttr(jnt + ".side", 1)
        if "R_" in jnt:
            cmds.setAttr(jnt + ".side", 2)
        if "C_" in jnt:
            cmds.setAttr(jnt + ".side", 0)
        cmds.setAttr(jnt + ".type", 18)
        cmds.setAttr(jnt + ".otherType", jnt.split("_")[1], type= "string")

def make():
    """
    Build a complete dragon rig in Maya by creating basic structure, modules, and setting up space switching for controllers.
    This function initializes various modules, creates the basic structure, and sets up controllers and constraints for the rig.
    It also sets the radius for all joints and displays a completion message.
    Args:
        model_path (str): The file path to the model to be imported. (full path)
        guides_path (str): The file path to the guides data. (full path)
        ctls_path (str): The file path to the controllers data. (full path)
    """
    core.load_data()

    asset_name = core.DataManager.get_asset_name()
    progress_window = cmds.progressWindow(title='Rig builder',
                                            progress=0,
                                            status=f"Loading data for {asset_name.capitalize()}",
                                            isInterruptable=True )

    # Create a new data export instance and generate build data
    model_path = core.DataManager.get_model_path()
    if model_path and os.path.exists(model_path):
        cmds.file(model_path, o=True, f=True)
        om.MGlobal.displayInfo(f"Imported model from {model_path}")
        file_objects = cmds.ls(assemblies=True)
        objects = []
        for item in file_objects:
            relative = cmds.listRelatives(item, shapes=True) or []
            if not relative and not cmds.objectType(item, isAType="camera"):
                objects.append(item)
    else:
        cmds.file(new=True, force=True)
        om.MGlobal.displayWarning(f"Model path is invalid or does not exist: {model_path}")

    data_exporter = data_export.DataExport()
    data_exporter.new_build()

    final_path = core.DataManager.get_guide_data()

    # Load guides data from the specified file
    try:
        with open(final_path, "r") as infile:
            guides_data = json.load(infile)

    except Exception as e:
        om.MGlobal.displayError(f"Error loading guides data: {e}")

    adonis = guides_data.get("adonis")
    if adonis is None:
        adonis = 0
    core.DataManager.set_adonis_data(adonis)

    # Set asset name and mesh data in DataManager
    core.DataManager.set_asset_name(list(guides_data.keys())[0])

    if core.DataManager.get_asset_name() != "oto" and core.DataManager.get_asset_name() != "baby":
        basic_structure.create_basic_structure(asset_name=core.DataManager.get_asset_name(), adonis_setup=adonis)

    else:
        data_exporter.append_data("basic_structure", {"modules_GRP": "setup",
                                    "skel_GRP": "setup_jnt_org",
                                    "masterWalk_CTL": "masterWalk",
                                    "guides_GRP": "guide",
                                    "skeletonHierarchy_GRP": "out_skel_facial",
                                    "muscleLocators_GRP": "muscleSystems_GRP",
                                    "adonis_GRP" : "adonis",
                                    })
        data_exporter.append_data("C_neckModule", {"skinning_transform": "C_neck4_JNT",
                                    "neck_ctl": "C_neck01_CTL",
                                    "head_ctl": "C_head_CTL"
                            })
        
        skel_out = cmds.createNode("transform", name="out_skel_facial", ss=True, parent = "jnt_org")
        setup_jnt_org = cmds.createNode("transform", name="setup_jnt_org", ss=True, parent = "setup")
        
    if objects:
        model_grp = data_exporter.get_data("basic_structure", "model_GRP")
        skelmodel_grp = data_exporter.get_data("basic_structure", "skelModel_GRP")
        musclemodel_grp = data_exporter.get_data("basic_structure", "muscleModel_GRP")
        if adonis:
            for item in objects:
                if "muscle" in item.lower() and "adonis" in item.lower() and musclemodel_grp and cmds.objExists(musclemodel_grp):                
                    cmds.parent(item, musclemodel_grp)
                elif "skel" in item.lower() and "adonis" in item.lower() and skelmodel_grp and cmds.objExists(skelmodel_grp):                
                    cmds.parent(item, skelmodel_grp)
                else:
                    cmds.parent(item, model_grp)
       
        elif model_grp and cmds.objExists(model_grp):                
            cmds.parent(item, model_grp)
        
            


    guide_amount = 0
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":
                guide_amount += 1


    step = 70/guide_amount
    current_val = 10

    def update_ui(module_name):
        nonlocal current_val # Allows us to modify the variable from the outer scope
        current_val += step
        
        cmds.progressWindow(
            progress_window, 
            edit=True, 
            progress=int(current_val),
            status=f"Building {module_name} module"
        )
        cmds.refresh()

    # Loop through guides data and create modules based on guide information
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "arm":
                    update_ui("arm")
                    lbm.ArmModule(guide_name).make()
                
                elif guide_info.get("moduleName") == "leg":
                    update_ui("leg")
                    lbm.LegModule(guide_name).make()

                elif guide_info.get("moduleName") == "backLeg":
                    update_ui("backLeg")
                    dlm.BackLegModule(guide_name).make()

                elif guide_info.get("moduleName") == "frontLeg":
                    update_ui("frontLeg")
                    dlm.FrontLegModule(guide_name).make()

                elif guide_info.get("moduleName") == "handQuad":
                    update_ui("handQuad")
                    dfl.FalangeModule().hand_distribution(guide_name=guide_name)

                elif guide_info.get("moduleName") == "spineQuad":
                    update_ui("spineQuad")
                    spq.SpineModule().make(guide_name)

                elif guide_info.get("moduleName") == "spine":
                    update_ui("spine")
                    spb.SpineModule().make(guide_name)

                elif guide_info.get("moduleName") == "neckQuad":
                    update_ui("neckQuad")
                    nkq.NeckModule().make(guide_name)
                
                elif guide_info.get("moduleName") == "neck":
                    update_ui("neck")
                    nkb.NeckModule().make(guide_name, num_joints=guide_info.get("jointTwist", 5))

                elif guide_info.get("moduleName") == "tail":
                    update_ui("tail")
                    tmm.TailModule().make(guide_name)
                


                
    # Additional modules who depends on others modules
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "spikes":
                    update_ui("spikes")
                    spm.SpikesModule().make(guide_name)

                if guide_info.get("moduleName") == "membran":
                    update_ui("membran")
                    mm.MembraneModule().make(guide_name)


                if guide_info.get("moduleName") == "backLegFoot" or guide_info.get("moduleName") == "footFront" or guide_info.get("moduleName") == "footBack" :
                    update_ui("foot")
                    fm.FingersModule().make(guide_name)

                if not core.DataManager.get_asset_name() in ["varyndor", "aychedral", "azhurean"]:
                    if guide_info.get("moduleName") == "mouth":
                        update_ui("jaw")
                        jmm.JawModule().make(guide_name)
                else:
                    if guide_info.get("moduleName") == "mouth":
                        update_ui("jaw")
                        jmm_old.JawModule().make(guide_name)


                if guide_info.get("moduleName") == "eyebrow":
                    update_ui("eyebrow")
                    ebm.EyebrowModule().make(guide_name)

                if guide_info.get("moduleName") == "eye":
                    update_ui("eye")
                    elm.EyelidModule().make(guide_name)

                if guide_info.get("moduleName") == "nose":
                    update_ui("nose")
                    nm.NoseModule().make(guide_name)
                
                if guide_info.get("moduleName") == "cheek":
                    update_ui("cheek")
                    cm.CheekModule().make(guide_name)
                    
                if guide_info.get("moduleName") == "cheekBone":
                    update_ui("cheekBone")
                    cb.CheekBoneModule().make(guide_name)

                
    
    # Additional modules who depends on others modules
    for template_name, guides in guides_data.items():
        if not isinstance(guides, dict):
            continue

        for guide_name, guide_info in guides.items():
            if guide_info.get("moduleName") != "Child":

                if guide_info.get("moduleName") == "fkFinger":
                    update_ui("fkFinger")

                    fkf.FingersModule().make(guide_name)

                if guide_info.get("moduleName") == "tongue":
                    update_ui("tongue")
                    tm.TongueModule().make(guide_name)

    # Create the skeleton hierarchy and spaces
    cmds.progressWindow(edit=True, progress=90, status=(f"Creating the skeleton hierarchy and spaces") )

    skeleton_hierarchy = skh.build_complete_hierarchy() 

    skinning_path = core.DataManager.get_skinning_data()
    if os.path.exists(skinning_path):
        cmds.progressWindow(edit=True, progress=90, status=(f"Importing skinning data") )
        skt.SkinIO().import_skins(file_path=skinning_path)
    else:
        om.MGlobal.displayWarning(f"Skinning file not found at {skinning_path}. Skipping skin import.")

    # End commands to clean the scene
    cmds.progressWindow(edit=True, progress=99, status=(f"Finalizing") )
    rename_ctl_shapes()
    joint_label()
    setIsHistoricallyInteresting(0)

    # End message
    cmds.inViewMessage(
    amg=f'Completed <hl> {core.DataManager.get_asset_name().capitalize()} RIG</hl> build.',
    pos='midCenter',
    fade=True,
    alpha=0.8)
    cmds.progressWindow(endProgress=True)
    cmds.select(clear=True)

