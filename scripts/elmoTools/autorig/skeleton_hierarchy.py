#Python libraries import
from maya import cmds
from importlib import reload
import os
import json
import maya.api.OpenMaya as om

# Tools / utils import
from elmoTools.utils import data_export
from elmoTools.utils import core
from elmoTools.utils import space_switch

reload(core)


def parented_chain(skinning_joints, parent, hand_value=False):

    data_exporter = data_export.DataExport()

    skelHierarchy_grp = data_exporter.get_data("basic_structure", "skeletonHierarchy_GRP")

    try:
        env_replace = parent.replace("_JNT", "_ENV")
        if cmds.objExists(env_replace):
            parent = env_replace
    except Exception as e:
        parent = parent

    complete_chain = []

    if hand_value:
        def get_finger_key(joint):
            name = joint.split("_", 1)[1]
            name = name.replace("metacarpal", "")
            name = ''.join([c for c in name if not c.isdigit()])
            name = name.replace("JNT", "")
            return name.lower()

        finger_chains = {}
        for joint in skinning_joints:
            key = get_finger_key(joint)
            if key not in finger_chains:
                finger_chains[key] = []
            finger_chains[key].append(joint)

        complete_chain = [finger_chains[key] for key in finger_chains]
    else:
        complete_chain = [skinning_joints]

    end_joints = []
    for index, chain in enumerate(complete_chain):
        joints = []
        for joint in chain:
            joint_env = cmds.createNode("joint", n=joint.replace("_JNT", "_ENV"), ss=True)
            # cmds.setAttr(joint_env + ".inheritsTransform", 0)


            if "localHip" in joint_env:
                cmds.parent(joint_env, joints[0])
                joints.append(joint_env)
                end_joints.append(joint_env)

                continue

            if joints:

                cmds.parent(joint_env, joints[-1])

            elif parent:
                cmds.parent(joint_env, parent)

            elif parent is None:
                cmds.parent(joint_env, skelHierarchy_grp)

            inverse_scale_attr = a = cmds.listConnections( f'{joint_env}.inverseScale', d=False, s=True, p=True )
            if inverse_scale_attr:
                cmds.disconnectAttr( inverse_scale_attr[0], f'{joint_env}.inverseScale' )

            
            
            joints.append(joint_env)
            end_joints.append(joint_env)

        for i, joint in enumerate(joints):
            
            if parent is None and i == 0:
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", joint + ".offsetParentMatrix", force=True)
            
            elif parent:
                mult_matrix = cmds.createNode("multMatrix", n=joint.replace("_ENV", "Envelop_MMX"), ss=True)
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
                cmds.connectAttr(parent + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)

                decompose = cmds.createNode("decomposeMatrix", n=joint.replace("_ENV", "Envelop_DCM"))
                cmds.connectAttr(f"{mult_matrix}.matrixSum", decompose + ".inputMatrix", force=True)

                cmds.connectAttr(decompose + ".outputTranslate", joint + ".translate", force=True)
                cmds.connectAttr(decompose + ".outputRotate", joint + ".rotate", force=True)
                cmds.connectAttr(decompose + ".outputScale", joint + ".scale", force=True)
                cmds.connectAttr(decompose + ".outputShear", joint + ".shear", force=True)


              
            if "localHip" in joint:
                mult_matrix = cmds.createNode("multMatrix", n=joint.replace("_ENV", "Envelop_MMX"), ss=True)
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
                cmds.connectAttr(joints[0] + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)

                decompose = cmds.createNode("decomposeMatrix", n=joint.replace("_ENV", "Envelop_DCM"))
                cmds.connectAttr(f"{mult_matrix}.matrixSum", decompose + ".inputMatrix", force=True)

                cmds.connectAttr(decompose + ".outputTranslate", joint + ".translate", force=True)
                cmds.connectAttr(decompose + ".outputRotate", joint + ".rotate", force=True)
                cmds.connectAttr(decompose + ".outputScale", joint + ".scale", force=True)
                cmds.connectAttr(decompose + ".outputShear", joint + ".shear", force=True)

            elif i != 0:
                mult_matrix = cmds.createNode("multMatrix", n=joint.replace("_ENV", "Envelop_MMX"), ss=True)
                cmds.connectAttr(complete_chain[index][i] + ".worldMatrix[0]", mult_matrix + ".matrixIn[0]", force=True)
                cmds.connectAttr(joints[i-1] + ".worldInverseMatrix[0]", mult_matrix + ".matrixIn[1]", force=True)

                decompose = cmds.createNode("decomposeMatrix", n=joint.replace("_ENV", "Envelop_DCM"))
                cmds.connectAttr(f"{mult_matrix}.matrixSum", decompose + ".inputMatrix", force=True)

                cmds.connectAttr(decompose + ".outputTranslate", joint + ".translate", force=True)
                cmds.connectAttr(decompose + ".outputRotate", joint + ".rotate", force=True)
                cmds.connectAttr(decompose + ".outputScale", joint + ".scale", force=True)
                cmds.connectAttr(decompose + ".outputShear", joint + ".shear", force=True)

            cmds.setAttr(joint + ".jointOrient", 0, 0, 0, type="double3")

    return end_joints

def build_complete_hierarchy():
    """
    Reads the build and guide files, interprets the desired hierarchy, and
    constructs it in Maya by parenting the corresponding skinning groups.
    Uses file locations relative to the current script.
    """
    data_exporter = data_export.DataExport()
    try:
        complete_path = os.path.realpath(__file__)
        relative_path = complete_path.split("scripts")[0]
        build_path = os.path.join(relative_path, "build", "build_cache.cache")
        
        with open(build_path, "r") as f:
            build_data = json.load(f)

        guides_path = core.DataManager.get_guide_data()
        
        with open(guides_path, "r") as f:
            guides_data = json.load(f)

    except IOError as e:
        om.MGlobal.displayError(f"File error: Could not find or read a data file. {e}")
        return
    except json.JSONDecodeError as e:
        om.MGlobal.displayError(f"JSON error: The file is malformed. {e}")
        return
    except Exception as e:
        om.MGlobal.displayError(f"Unexpected error while loading files: {e}")
        return

    skelHierarchy_grp = data_exporter.get_data("basic_structure", "skeletonHierarchy_GRP")

    freeze_joint = cmds.createNode("joint", n="C_freeze_JNT", ss=True, parent=skelHierarchy_grp)

    skel_grps = []
    skinning_joints = []
    modules_name = []
    for module, data in build_data.items():
        for value in data.items():
            if "skinning_transform" in value:
                    joints = cmds.listRelatives(value[1], allDescendents=True, type="joint")
                    skel_grps.append((value[1]))
                    skinning_joints.append(joints)
                    modules_name.append(module)
    spine_index = next((i for i, grp in enumerate(skel_grps) if "spine" in grp.lower()), None)
    l_arm_index = next((i for i, grp in enumerate(skel_grps) if "L_arm" in grp), None)
    r_arm_index = next((i for i, grp in enumerate(skel_grps) if "R_arm" in grp), None)
    neck_index =  next((i for i, grp in enumerate(skel_grps) if "neck" in grp.lower()), None)


    arm_joints = []
    leg_joints = []

    complete_arm_chain = []
    if spine_index:
        spine_joints = parented_chain(skinning_joints=skinning_joints[spine_index], parent=None, hand_value=False)

    facial_joints_list = []
    head_joint= None

    for i, skinning_joint_list in enumerate(skinning_joints):
        if i != spine_index:
            if "Facial" in skel_grps[i] or "spikes" in skel_grps[i].lower():    
                parented_chain(skinning_joints=skinning_joint_list, parent=None, hand_value=False)
            elif "backLeg" in skinning_joint_list[0] or "tail" in skinning_joint_list[0] or "leg" in skinning_joint_list[0]:
                joints = parented_chain(skinning_joints=skinning_joint_list, parent=spine_joints[-1], hand_value=False)
                leg_joints.append(joints[-1])
            elif "Finger" in skinning_joint_list[0] or "Membran" in skinning_joint_list[0] or "thumb01" in skinning_joint_list[0].split("_", 1)[1].lower() or "Metacarpal" in skinning_joint_list[0] or "handThumb" in skinning_joint_list[0]:
                pass
            elif "Scapula" in skinning_joint_list[0]:
                joints = parented_chain(skinning_joints=[skinning_joint_list[0], skinning_joint_list[1]], parent=spine_joints[-2], hand_value=False)
                joints = parented_chain(skinning_joints=skinning_joint_list[2:], parent=spine_joints[-2], hand_value=False)
                leg_joints.append(joints[-1])
                continue     
            
                

                #facial_joints_list.append(skinning_joint_list)
            else:
                if len(skinning_joint_list) >= 2:
                    joints = parented_chain(skinning_joints=skinning_joint_list, parent=spine_joints[-2], hand_value=False)
                    if "clavicle" in skinning_joint_list[0]:
                        arm_joints.append(joints[-1])
                        complete_arm_chain.extend(skinning_joint_list)
                    if "neck" in skinning_joint_list[0]:
                        head_joint = joints[-1]

    """

    if head_joint:
        for list in facial_joints_list:
            joints = parented_chain(skinning_joints=list, parent=head_joint, hand_value=False)
    """

    hand_settings_value = None
    for i, skinning_joint_list in enumerate(skinning_joints):
        if "thumbMetacarpal" in skinning_joint_list[0] or "handThumb" in skinning_joint_list[0]:
            side = skinning_joint_list[0].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if f"{side}_" in j), None)

            child_joints = []
            for item in skinning_joint_list:
                if "Metacarpal" in item:
                    parented_chain(skinning_joints=child_joints, parent=parent_joint, hand_value=False)
                    child_joints = []
                    child_joints.append(item)
                else:
                    child_joints.append(item)
            if child_joints:                    
                parented_chain(skinning_joints=child_joints, parent=parent_joint, hand_value=False)

            attributes = data_exporter.get_data(f"{side}_FkFingersModule", "attributes_ctl")
            # try:
            #     space_switch.fk_switch(target = attributes, sources= [parent_joint], sources_names=["Wrist"])
            # except:
            #     pass
            


        elif "thumb01" in skinning_joint_list[0].split("_", 1)[1].lower():
            side = skinning_joint_list[0].split("_")[0]

            if "back" in skinning_joint_list[0].lower():
                for joint in leg_joints:
                    if f"{side}_" in joint and "back" in joint.lower():
                        parent_joint = joint
            elif "front" in skinning_joint_list[0].lower():
                for joint in leg_joints:
                    if f"{side}_" in joint and "front" in joint.lower():
                        parent_joint = joint 
            else:
               for joint in leg_joints:
                    if f"{side}_" in joint:
                        parent_joint = joint
                        
            for index in range(0, 12, 3):
                joint_list = skinning_joint_list[index:index+3]
                parented_chain(skinning_joints=joint_list, parent=parent_joint, hand_value=False)

        
        elif "Finger" in skinning_joint_list[0]:
            side = skinning_joint_list[0].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if f"{side}_" in j), None)
            parented_chain(skinning_joints=skinning_joint_list, parent=parent_joint, hand_value=False)


        if "Membran" in skinning_joint_list[0]:
            side = skinning_joint_list[0].split("_")[0]

            parent_joint = None

            for joint_arm in arm_joints:
                side_arm = joint_arm.split("_")[0]
                if side == side_arm:
                    parent_joint = joint_arm
                    break

            membrane_groups = []
            current_group = []

            for index, joint in enumerate(skinning_joint_list):
                if "Membrane01" in joint and not "PrimaryMembrane01" in joint:
                    current_group = [joint, skinning_joint_list[index + 1], skinning_joint_list[index + 2], skinning_joint_list[index + 3]]
                    membrane_groups.append(current_group)


                elif "PrimaryMembrane01" in joint:
                    current_group = [joint, skinning_joint_list[index + 1]]#, skinning_joint_list[index + 2]]
                    membrane_groups.append(current_group)                

            for joint_list in membrane_groups:
                if joint_list:
                    if "PrimaryMembrane01" in joint_list[0]:
                        closest01 = core.get_closest_transform(joint_list[0], complete_arm_chain)
                        parented_chain(skinning_joints=joint_list, parent=closest01, hand_value=False)
                    else:
                        parented_chain(skinning_joints=joint_list, parent=parent_joint, hand_value=True)



        # ===== SPACE SWITCHES ===== #
        if "fkFingers" in skel_grps[i]:
            continue

        if "backLeg" in skel_grps[i] or "leg" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")

            parents = [data_exporter.get_data("C_spineModule", "localHip"), data_exporter.get_data("C_spineModule", "body_ctl")]

            space_switch.fk_switch(target = fk, sources= parents, sources_names=["LocalHip", "Body"])
            space_switch.fk_switch(target = root, sources= parents, sources_names=["LocalHip", "Body"])
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0, sources_names=["LocalHip", "Body"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["AnkleIK", "LocalHip", "Body"], pv=True)

        if "frontLeg" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            scapula = data_exporter.get_data(modules_name[i], "scapula_ctl")
            first_bendy = data_exporter.get_data(modules_name[i], "first_bendy_joints")
            scapula_end = data_exporter.get_data(modules_name[i], "scapula_end_ctl")
            scapula_master = data_exporter.get_data(modules_name[i], "scapula_master_ctl")

            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]

            parents.insert(0, scapula_master)
            space_switch.fk_switch(target = fk, sources= parents, sources_names=["ScapulaMaster", "LocalChest", "SpineEnd"])
            parents.pop(0)
            space_switch.fk_switch(target = root, sources= [scapula_master], sources_names=["ScapulaMaster"])

            root_grp = root.replace("CTL", "GRP")
            root_connection = cmds.listConnections(root_grp + ".offsetParentMatrix", destination=True, source=True)

            # if root_connection:
            #     pick_matrix = cmds.createNode("pickMatrix", n=root_grp.replace("GRP", "PM"))
            #     cmds.setAttr(pick_matrix + ".useRotate", 0)
            #     cmds.connectAttr(root_connection[0] + ".outputMatrix", pick_matrix + ".inputMatrix")
            #     cmds.connectAttr(pick_matrix + ".outputMatrix", root_grp + ".offsetParentMatrix", force=True)
            space_switch.fk_switch(target = scapula_master, sources= parents, sources_names=["LocalChest", "SpineEnd"])
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0, sources_names=["LocalChest", "SpineEnd"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["AnkleIK", "LocalChest", "SpineEnd"], pv=True)

        if "tail" in skel_grps[i] and not "spikes" in skel_grps[i].lower():
            main_ctl= data_exporter.get_data(modules_name[i], "main_ctl")
            parents = [data_exporter.get_data("C_spineModule", "localHip"), data_exporter.get_data("C_spineModule", "body_ctl")]
            space_switch.fk_switch(target = main_ctl, sources= parents, sources_names=["LocalHip", "Body"])

        if "neck" in skel_grps[i] and len(skinning_joints[i]) >= 2:
            main_ctl= data_exporter.get_data(modules_name[i], "neck_ctl")
            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]
            space_switch.fk_switch(target = main_ctl, sources= parents, sources_names=["LocalChest", "SpineEnd"])

        if "arm" in skel_grps[i]:
            fk = data_exporter.get_data(modules_name[i], "fk_ctl")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            scapula = data_exporter.get_data(modules_name[i], "scapula_ctl")

            parents = [data_exporter.get_data("C_spineModule", "localChest"), data_exporter.get_data("C_spineModule", "end_main_ctl")]

            space_switch.fk_switch(target = scapula, sources= parents, sources_names=["LocalChest", "SpineEnd"])
            parents.insert(0, scapula)


            space_switch.fk_switch(target = fk, sources= parents, sources_names=["Scapula", "LocalChest", "SpineEnd"])
            space_switch.fk_switch(target = root, sources= parents, sources_names=["Scapula", "LocalChest", "SpineEnd"])
            space_switch.fk_switch(target = ik, sources= parents, default_rotate=0, default_translate=0, sources_names=["Scapula", "LocalChest", "SpineEnd"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= parents, sources_names=["WristIK", "Scapula", "LocalChest", "SpineEnd"], pv=True)


        if "Finger00" in skel_grps[i]:

            fk = data_exporter.get_data(modules_name[i], "fk_ctls")[0]
            pv = data_exporter.get_data(modules_name[i], "pv_ctl")
            root = data_exporter.get_data(modules_name[i], "root_ctl")
            ik = data_exporter.get_data(modules_name[i], "end_ik")
            metacarpal = data_exporter.get_data(modules_name[i], "metacarpal_ctl")


            side = skel_grps[i].split("_")[0]
            index = l_arm_index if side == "L" else r_arm_index
            parent_joint = next((j for j in arm_joints if f"{side}_" in j), None)
            hand_settings = data_exporter.get_data(modules_name[i], "settings_ctl")

            if hand_settings_value is None or hand_settings_value != modules_name[i].split("_")[0]:
                space_switch.fk_switch(target = hand_settings, sources=[parent_joint])
                hand_settings_value = modules_name[i].split("_")[0]
            parents = [parent_joint]

            space_switch.fk_switch(target = metacarpal, sources= parents, sources_names=["Hand"])

            space_switch.fk_switch(target = fk, sources= [metacarpal], sources_names=["Metacarpal"])
            space_switch.fk_switch(target = root, sources= [metacarpal], sources_names=["Metacarpal"])
            space_switch.fk_switch(target = ik, sources= [metacarpal], default_rotate=1, default_translate=1, sources_names=[ "Metacarpal"])
            parents.insert(0, ik)
            space_switch.fk_switch(target = pv, sources= [metacarpal, ik], sources_names=["fingerIK", "Wrist"], pv=True)

        # ===== SCAPULA SPACES ===== #

        if "scapula" in skel_grps[i]:
            scapula_ctl = data_exporter.get_data(modules_name[i], "scapula_ctl")
            spine_end = data_exporter.get_data("C_spineModule", "end_main_ctl")
            local_chest = data_exporter.get_data("C_spineModule", "localChest")
            front_leg = data_exporter.get_data("C_dragonFrontLegModule", "root_ctl")

            space_switch.fk_switch(target = scapula_ctl, sources= [front_leg, local_chest, spine_end], sources_names=["Front Leg", "LocalChest", "SpineEnd"])
