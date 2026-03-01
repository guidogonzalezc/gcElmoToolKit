import maya.cmds as cmds
from maya.api import OpenMaya as om
from elmoTools.utils import core

OPEN = 'open'
PERIODIC = 'periodic'
AXIS_VECTOR = {'x': (1, 0, 0), '-x': (-1, 0, 0), 'y': (0, 1, 0), '-y': (0, -1, 0), 'z': (0, 0, 1), '-z': (0, 0, -1)}
KNOT_TO_FORM_INDEX = {OPEN: om.MFnNurbsCurve.kOpen, PERIODIC: om.MFnNurbsCurve.kPeriodic}

def get_open_uniform_kv(n, d):
    """
    Get open uniform knot vector

    Attributes:
        n (int): the number of control vertices
        d (int): degree of outputs

    Returns:
        list: open uniform knot vector
    """

    return [0] * (d + 1) + [(i - d) / (n - d) for i in range(d + 1, n)] + [1] * (d + 1)


def get_periodic_uniform_kv(n, d):
    """
    Get periodic uniform knot vector.  Append d values to the start and end

    Returns:
        list: periodic uniform knot vector with d additional values at the start and end
    """

    i = 1.0 / (n + d)
    return  [-i * a for a in range(d, 0, -1)] + [i * a for a in range(n + d + 1)] + [i * a + 1 for a in range(1, d + 1)]


def knot_vector(kv_type, cvs, d):
    """
    Convenience function for creating knot vectors and editing cv/joint/controls/etc lists

    Attributes:
        kv_type (str): knot vector type to be created
        cvs (list): list of objects to be associated with the knot vector
        d (int): degree of outputs

    Returns:
        tuple: knot vector and (modified) cvs list
    """

    cvs_copy = cvs[:]

    if kv_type == 'open':

        kv = get_open_uniform_kv(len(cvs), d)

    else:

        kv = get_periodic_uniform_kv(len(cvs), d)

        for i in range(d):
            cvs_copy.insert(0, cvs[len(cvs) - i - 1])
            cvs_copy.append(cvs[i])

    return kv, cvs_copy


def de_boor(n, d, t, kv, tol=0.000001):
    """
    Attributes:
        n (integer): number of control vertices
        d (integer): degree of the resulting curve
        t (float): parametric value along the curve that we use to query the value
        kv (list or tuple): represents the knot vector which is used to calculate the basis function weights

    Returns:
        list: contains float values between 0 and 1
    """

    if t + tol > 1:
        return [0.0 if i != n - 1 else 1.0 for i in range(n)]

    weights = [1.0 if kv[i] <= t < kv[i + 1] else 0.0 for i in range(n + d)]

    basis_width = n + d - 1

    for degree in range(1, d + 1):

        for i in range(basis_width):

            if weights[i] == 0 and weights[i + 1] == 0:
                continue

            a_denom = kv[i + degree] - kv[i]
            b_denom = kv[i + degree + 1] - kv[i + 1]
            a = (t - kv[i]) * weights[i] / a_denom if a_denom != 0 else 0.0
            b = (kv[i + degree + 1] - t) * weights[i + 1] / b_denom if b_denom != 0 else 0.0

            weights[i] = a + b

        basis_width -= 1

    return weights[:n]

def get_offset_matrix(child, parent):
    """
    Calculate the offset matrix between a child and parent transform in Maya.
    Args:
        child (str): The name of the child transform.
        parent (str): The name of the parent transform. 
    Returns:
        om.MMatrix: The offset matrix that transforms the child into the parent's space.
    """
    child_dag = om.MSelectionList().add(child).getDagPath(0)
    parent_dag = om.MSelectionList().add(parent).getDagPath(0)
    
    child_world_matrix = child_dag.inclusiveMatrix()
    parent_world_matrix = parent_dag.inclusiveMatrix()
    
    offset_matrix = child_world_matrix * parent_world_matrix.inverse()

    return offset_matrix

def de_boor_ribbon(cvs, aim_axis='x', up_axis='y', num_joints=5, tangent_offset=0.001, d=None, kv_type=OPEN,
                   param_from_length=True, tol=0.000001, name='ribbon', use_position=True, use_tangent=True,
                   use_up=True, use_scale=True, custom_parm = [], parent=None, axis_change=False, negate_secundary=False, align=False):
    """
    Use controls and de_boor function to get position, tangent and up values for joints.  The param_from_length can
    be used to get the parameter values using a fraction of the curve length, otherwise the parameter values will be
    equally spaced

    To optimize the setup we change the nodes and connections if different combinations of position, tangent and up are
    used:
        use_position=True, use_tangent=True, use_up=True
            create 3 wtAddMatrix nodes and connect to aimMatrix

        use_position=False, use_tangent=True, use_up=True
            wtAddMatrix for tangent only created if use_position=True
            use wts and tangent_wts to set matrix values for aimMatrix
            create wtAddMatrix for up and connect to aimMatrix

        use_position=True, use_tangent=False, use_up=True
            create offset matrices in the aim direction for each joint
            use offset matrices to set the primaryTargetMatrix of aimMatrix
            create wtAddMatrix nodes for position and up and connect to aimMatrix

        use_position=True, use_tangent=True, use_up=False
            use module group matrix as the secondaryTargetMatrix of aimMatrix
            create wtAddMatrix nodes for position and tangent and connect to aimMatrix

        use_position=False, use_tangent=False, use_up=True
            same as use_position=False, use_tangent=True, use_up=True

        use_position=False, use_tangent=True, use_up=False
            translation and rotation of joints set

        use_position=True, use_tangent=False, use_up=False
            no aimMatrix needed, connect the wtAddMatrix for translation to the joints

        use_position=False, use_tangent=False, use_up=False
            translation and rotation of joints set

        aimMatrix not created when use_tangent=False and use_up=False, otherwise it is

    """

    if not parent:
        jnts_grp = cmds.createNode('transform', n=f'{name}_GRP', ss=True)
    else:
        jnts_grp = parent

    ctls = []
    new_cvs = []

    for cv in cvs:
        if len(cv.split(".")) > 1:
            ctls.append(cv)
            new_cvs.append(cv.split(".")[0])
        else:
            new_cvs.append(cv)
            ctls.append(f"{cv}.worldMatrix[0]")

    cvs = new_cvs

    num_cvs = len(cvs)
    original_cvs = cvs[:]

    d = num_cvs - 1 if d is None else d

    if kv_type == OPEN:

        kv, _ = knot_vector(OPEN, cvs, d)

        m_kv = kv[1:-1]
        # m_cvs = cvs[:]
        m_cvs = []

        for i, cv in enumerate(cvs):
            if cmds.objectType(cv) != "transform":
                temp = cmds.createNode("transform", n=f"{cv}_temp")
                cmds.connectAttr(ctls[i], temp + ".offsetParentMatrix")
                m_cvs.append(temp)
            else:
                m_cvs.append(cv)


    else:  # kv_type is PERIODIC

        m_cvs = [cvs[i - 1 % len(cvs)] for i in range(len(cvs))]
        for i in range(d):
            m_cvs.append(m_cvs[i])

        m_kv_len = len(m_cvs) + d - 1
        m_kv_interval = 1 / (m_kv_len - 2 * (d - 1) - 1)
        m_kv = [-m_kv_interval * (d - 1) * (1 - t / (m_kv_len - 1)) +
                (1 + m_kv_interval * (d - 1)) * t / (m_kv_len - 1) for t in range(m_kv_len)]

        kv, cvs = knot_vector(PERIODIC, cvs, d)

    m_cv_poss = om.MPointArray([cmds.xform(obj, q=True, ws=True, t=True) for obj in m_cvs])
    form = KNOT_TO_FORM_INDEX[kv_type]
    is_2d = False
    rational = True
    data_creator = om.MFnNurbsCurveData()
    parent = data_creator.create()

    crv_fn = om.MFnNurbsCurve()
    crv_fn.create(m_cv_poss, m_kv, d, form, is_2d, rational, parent)

    if param_from_length:

        crv_len = crv_fn.length()
        params = []

        for i in range(num_joints):

            sample_len = crv_len * i / (num_joints - 1)

            if kv_type == PERIODIC:
                t = crv_fn.findParamFromLength((sample_len + crv_len * m_kv[2] * 0.5) % crv_len)
                params.append(t - m_kv[2] * 0.5)
            else:
                t = crv_fn.findParamFromLength(sample_len)
                params.append(t)

    else:
        params = [i / (num_joints - 1) for i in range(num_joints)]

    params = custom_parm if custom_parm else params


    if kv_type == PERIODIC:

        params = [(kv[d + 1] * (d * 0.5 + 0.5)) * (1 - t) + t * (1 - kv[d + 1] * (d * 0.5 - 0.5))
                  for i, t in enumerate(params)]

    par_off_plugs = []
    trans_off_plugs = []
    sca_off_plugs = []

    for i, ctl in enumerate(ctls):

        par_off_plugs.append(ctl)

        trans_off = cmds.createNode('pickMatrix', n=f'{name}Translation0{i}_PM', ss=True)
        cmds.connectAttr(ctl, f'{trans_off}.inputMatrix')
        for attr in 'useRotate', 'useScale', 'useShear':
            cmds.setAttr(f'{trans_off}.{attr}', False)

        trans_off_plugs.append(f'{trans_off}.outputMatrix')

        if use_scale and use_tangent or use_up:

            sca_off = cmds.createNode('pickMatrix', n=f'{name}ScaleOffset0{i}_PM', ss=True)
            cmds.connectAttr(ctl, f'{sca_off}.inputMatrix')
            for attr in 'useRotate', 'useShear', 'useTranslate':
                cmds.setAttr(f'{sca_off}.{attr}', False)

            sca_off_plugs.append(f'{sca_off}.outputMatrix')

    jnts = []
    up_offsets =[]
    aim_matrices = []
    positions_plugs = []
    for i, param in enumerate(params):

        jnt = cmds.createNode("joint", n=f'{name}0{i}_JNT', ss=True, parent=jnts_grp)
        cmds.setAttr(f'{jnt}.jo', 0, 0, 0)
        cmds.xform(jnt, m=om.MMatrix.kIdentity)

        jnts.append(jnt)

        wts = de_boor(len(cvs), d, param, kv, tol=tol)
        if kv_type == PERIODIC:
            wts = get_consolidated_wts(wts, original_cvs, cvs)

        tangent_param = param + tangent_offset
        aim_vector = om.MVector(AXIS_VECTOR[aim_axis])
        if tangent_param > 1:
            tangent_param = param - 2 * tangent_offset
            aim_vector *= -1

        tangent_wts = de_boor(len(cvs), d, tangent_param, kv, tol=tol)
        if kv_type == PERIODIC:
            tangent_wts = get_consolidated_wts(tangent_wts, original_cvs, cvs)

        position_plug = None
        tangent_plug = None

        # ----- position setup
        if use_position:

            position = create_wt_add_matrix(trans_off_plugs, wts, f'{name}Position0{i}_WAM', tol=tol)
            position_plug = f'{position}.matrixSum'
        

            if not use_tangent and not use_up:  # no aimMatrix necessary, connect wtAddMatrix to joint

                cmds.connectAttr(position_plug, f'{jnt}.offsetParentMatrix')

                if use_scale:

                    for trans_off_plug in trans_off_plugs:

                        trans_off = trans_off_plug.split('.')[0]
                        cmds.setAttr(f'{trans_off}.useScale', True)

                continue

            # ----- tangent setup
            if use_tangent:

                tangent = create_wt_add_matrix(trans_off_plugs, tangent_wts, f'{name}Tangent0{i}_WAM', tol=tol)
                tangent_plug = f'{tangent}.matrixSum'

        # ----- up setup
        if use_up:
            # if float(param) < 0.9 or float(param) > 0.99: 
            temp = cmds.createNode('transform', ss=True)
            ori_con = cmds.orientConstraint(m_cvs, temp)[0]
            cmds.setAttr(f'{ori_con}.interpType', 2)
            for j, wt in enumerate(wts):
                cmds.setAttr(f'{ori_con}.{m_cvs[j]}W{j}', wt)

            up = create_wt_add_matrix(par_off_plugs, wts, f'{name}Up0{i}_WAM', tol=tol)

            up_off = cmds.createNode('multMatrix', n=f'{name}UpOffset0{i}_MM', ss=True)


            if axis_change:
                blend_up = cmds.createNode('blendMatrix', n=f'{name}UpAxisChange0{i}_BM', ss=True)
                cmds.connectAttr(f'{up}.matrixSum', f'{blend_up}.inputMatrix')
                cmds.connectAttr(f'{cvs[0]}.outputMatrix', f'{blend_up}.target[0].targetMatrix')
                cmds.setAttr(f'{blend_up}.target[0].translateWeight', 0)

                parent_matrix = cmds.createNode("parentMatrix", n=f"{name}ParentMatrix0{i}_PM", ss=True)
                cmds.connectAttr(f'{blend_up}.outputMatrix', f'{parent_matrix}.inputMatrix')
                cmds.connectAttr(f'{up}.matrixSum', f'{parent_matrix}.target[0].targetMatrix')

                parent_matrix_offset_axis = parent_matrix
                up_offset_axis = up
                blend_up_axis = blend_up
                cmds.setAttr(f"{parent_matrix_offset_axis}.target[0].offsetMatrix", core.get_offset_matrix(f'{up_offset_axis}.matrixSum', f'{blend_up_axis}.outputMatrix'), type='matrix')
            
                # inverse_parent = cmds.createNode("inverseMatrix", n=f"{name}InverseParent0{i}_IM", ss=True)
                # mult_offset = cmds.createNode('multMatrix', n=f'{name}UpOffset0{i}_MM', ss=True)
                # cmds.connectAttr(f'{up}.matrixSum', f'{inverse_parent}.inputMatrix')
                # cmds.connectAttr(f'{inverse_parent}.outputMatrix', f'{mult_offset}.matrixIn[1]')
                # cmds.connectAttr(f'{blend_up}.outputMatrix', f'{mult_offset}.matrixIn[0]')
                # cmds.connectAttr(f'{mult_offset}.matrixSum', f'{parent_matrix}.target[0].offsetMatrix')



                cmds.connectAttr(f'{parent_matrix}.outputMatrix', f'{up_off}.matrixIn[1]')

            else:
                cmds.connectAttr(f'{up}.matrixSum', f'{up_off}.matrixIn[1]')

            fourbyfour = cmds.createNode('fourByFourMatrix', n=f'{name}UpFourByFour0{i}_FBF', ss=True)

            if up_axis == 'x' or up_axis == '-x':
                cmds.setAttr(f'{fourbyfour}.in30', 10)
            elif up_axis == 'y' or up_axis == '-y':
                cmds.setAttr(f'{fourbyfour}.in31', 10)
            elif up_axis == 'z' or up_axis == '-z':
                cmds.setAttr(f'{fourbyfour}.in32', 10)


            cmds.connectAttr(f'{fourbyfour}.output', f'{up_off}.matrixIn[0]')


            up_plug = f'{up_off}.matrixSum'
            up_offsets.append(up_off)

            cmds.delete(temp)

            secondaryMode = 2
            # else:
            #     up_plug = f'{up_offsets[-1]}.matrixSum'

            #     secondaryMode = 1


        aim = cmds.createNode('aimMatrix', n=f'{name}PointOnCurve0{i}_AM', ss=True)

        if position_plug:
            cmds.connectAttr(position_plug, f'{aim}.inputMatrix')
        else:
            matrices = [om.MMatrix(cmds.getAttr(top)) for top in trans_off_plugs]
            trans_wt_mat = get_weighted_translation_matrix(matrices, wts)
            cmds.setAttr(f'{aim}.inputMatrix', trans_wt_mat, type='matrix')

        # if tangent_plug:
        #     cmds.connectAttr(f'{tangent}.matrixSum', f'{aim}.primaryTargetMatrix')
        # else:
        #     matrices = [om.MMatrix(cmds.getAttr(top)) for top in trans_off_plugs]
        #     trans_wt_mat = get_weighted_translation_matrix(matrices, tangent_wts)

        #     if position_plug:

        #         position_m = om.MMatrix(cmds.getAttr(position_plug))
        #         tangent_offset_val = trans_wt_mat * position_m.inverse()

        #         tangent_off = cmds.createNode('multMatrix', n=f'{name}TangentOffset0{i}_MM', ss=True)
        #         cmds.setAttr(f'{tangent_off}.matrixIn[0]', tangent_offset_val, type='matrix')
        #         cmds.connectAttr(position_plug, f'{tangent_off}.matrixIn[1]')

        #         cmds.connectAttr(f'{tangent_off}.matrixSum', f'{aim}.primaryTargetMatrix')

        #     else:

        #         cmds.setAttr(f'{aim}.primaryTargetMatrix', trans_wt_mat, type='matrix')

        if aim_matrices:
            cmds.connectAttr(position_plug, f'{aim_matrices[-1]}.primaryTargetMatrix')
            cmds.setAttr(f'{aim}.primaryInputAxis', *aim_vector)

            if i == len(params) - 1:
                next_aim = positions_plugs[-1]
                cmds.connectAttr(next_aim, f'{aim}.primaryTargetMatrix')
                a= om.MVector(AXIS_VECTOR[aim_axis])
                b = [-a for a in AXIS_VECTOR[aim_axis]]
                cmds.setAttr(f'{aim}.primaryInputAxis', b[0],b[1],b[2], type='double3') #*AXIS_VECTOR[aim_axis]*-1
            

        aim_matrices.append(aim)
        positions_plugs.append(position_plug)


        cmds.connectAttr(up_plug, f'{aim}.secondaryTargetMatrix')

        output_plug = f'{aim}.outputMatrix'

        if negate_secundary:
            cmds.setAttr(f'{aim}.secondaryInputAxis', *[-a for a in AXIS_VECTOR[up_axis]], type='double3') # *AXIS_VECTOR[up_axis]*-1
            cmds.setAttr(f'{aim}.secondaryTargetVector', *[-a for a in AXIS_VECTOR[up_axis]], type='double3') #*AXIS_VECTOR[up_axis]*-1
        # else:
            # cmds.setAttr(f'{aim}.secondaryInputAxis', *AXIS_VECTOR[up_axis], type='double3')
            # cmds.setAttr(f'{aim}.secondaryTargetVector', *AXIS_VECTOR[up_axis], type='double3')
        if not align:
            cmds.setAttr(f'{aim}.secondaryMode', 1)

        else: 
            cmds.setAttr(f'{aim}.secondaryMode', 2)

        if use_scale:
            scale_wam = create_wt_add_matrix(sca_off_plugs, wts, f'{name}Scale0{i}_WAM', tol=tol)

            scale_mm = cmds.createNode('multMatrix', n=f'{name}Scale0{i}_MM', ss=True)
            cmds.connectAttr(f'{scale_wam}.matrixSum', f'{scale_mm}.matrixIn[0]')
            cmds.connectAttr(output_plug, f'{scale_mm}.matrixIn[1]')

            output_plug = f'{scale_mm}.matrixSum'

        cmds.connectAttr(output_plug, f'{jnt}.offsetParentMatrix')

        if axis_change:

            cmds.setAttr(f"{parent_matrix_offset_axis}.target[0].offsetMatrix", core.get_offset_matrix(f'{blend_up_axis}.outputMatrix', f'{up_offset_axis}.matrixSum'), type='matrix')


    for i, cv_temp in enumerate(m_cvs):
        if cv_temp != original_cvs[i]:
            cmds.delete(cv_temp)

    return jnts


def get_consolidated_wts(wts, original_cvs, cvs):

    consolidated_wts = {cv: 0 for cv in original_cvs}
    for j, wt in enumerate(wts):
        consolidated_wts[cvs[j]] += wt

    return [consolidated_wts[cv] for cv in original_cvs]


def create_wt_add_matrix(matrix_attrs, wts, name, tol=0.000001):

    wam = cmds.createNode('wtAddMatrix', n=name, ss=True)

    for matrix_attr, wt, i in zip(matrix_attrs, wts, range(len(matrix_attrs))):

        if wt < tol:
            continue
        cmds.connectAttr(matrix_attr, f'{wam}.wtMatrix[{i}].matrixIn')
        cmds.setAttr(f'{wam}.wtMatrix[{i}].weightIn', wt)

    return wam

def get_weighted_translation_matrix(matrices, wts):

    translation_m = om.MMatrix(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

    for m, wt in zip(matrices, wts):
        for i in 12, 13, 14:
            translation_m[i] += m[i] * wt

    return translation_m
