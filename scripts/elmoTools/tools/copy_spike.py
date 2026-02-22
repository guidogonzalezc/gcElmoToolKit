import maya.cmds as cmds
import maya.api.OpenMaya as om


# =============================================================
#  UTILITY HELPERS
# =============================================================

def get_dag_path(node):
    """Return MDagPath from a string."""
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def get_mesh_fn(mesh):
    """Return MFnMesh for a mesh transform or shape."""
    dag = get_dag_path(mesh)
    # ensure we point at the shape
    if dag.apiType() != om.MFn.kMesh:
        dag.extendToShape()
    return om.MFnMesh(dag)


def get_curve_fn(curve):
    """Return MFnNurbsCurve for a curve transform or shape."""
    dag = get_dag_path(curve)
    dag.extendToShape()
    return om.MFnNurbsCurve(dag)


def get_skin_cluster(mesh):
    """Return the skinCluster node and its influences."""
    history = cmds.listHistory(mesh, pdo=True) or []
    for h in history:
        if cmds.nodeType(h) == "skinCluster":
            inf = cmds.skinCluster(h, q=True, inf=True)
            return h, inf
    return None, None


def get_vertex_positions(mesh):
    """ReturnNx3 listof world-space vertex positions."""
    mfn = get_mesh_fn(mesh)
    pts = mfn.getPoints(om.MSpace.kWorld)
    return [[p[0], p[1], p[2]] for p in pts]


def build_adjacency_list(mesh):
    """Build adjacency list of connected vertices."""
    mfn = get_mesh_fn(mesh)
    counts, connects = mfn.getVertices()

    faces = []
    index = 0
    for c in counts:
        faces.append(connects[index:index + c])
        index += c

    from collections import defaultdict
    adj = defaultdict(set)

    for f in faces:
        for a in f:
            for b in f:
                if a != b:
                    adj[a].add(b)

    return adj


def get_island_sets(mesh):
    """Return list of vertex islands."""
    adj = build_adjacency_list(mesh)
    visited = set()
    islands = []

    from collections import deque

    for v in adj:
        if v not in visited:
            q = deque([v])
            cluster = []
            while q:
                x = q.popleft()
                if x in visited:
                    continue
                visited.add(x)
                cluster.append(x)
                q.extend(adj[x])
            islands.append(cluster)

    return islands


def build_mean_curve(islands, positions):
    """Create a linear NURBS curve through mean of each island."""
    means = []

    for isl in islands:
        xs = [positions[i][0] for i in isl]
        ys = [positions[i][1] for i in isl]
        zs = [positions[i][2] for i in isl]
        means.append(om.MPoint(sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs)))

    # Maya needs at least 2 CVs for a curve
    if len(means) == 1:
        means.append(om.MPoint(means[0]))

    pts = om.MPointArray(means)
    knots = om.MDoubleArray([0] * len(means))

    fn_curve = om.MFnNurbsCurve()
    curve_obj = fn_curve.create(
        pts, knots, 1,
        om.MFnNurbsCurve.kOpen,
        False, False
    )

    return om.MFnDagNode(curve_obj).fullPathName()


def find_closest_vertex(mesh, world_point):
    """Return the index of the TRUE closest vertex on the mesh."""
    mfn = get_mesh_fn(mesh)

    if not isinstance(world_point, om.MPoint):
        world_point = om.MPoint(*world_point)

    verts = mfn.getPoints(om.MSpace.kWorld)

    min_dist = float('inf')
    closest = 0

    for i, v in enumerate(verts):
        d = (v - world_point).length()
        if d < min_dist:
            min_dist = d
            closest = i

    return closest



# =============================================================
#  MAIN TRANSFER LOGIC (SPIKES MODE)
# =============================================================

def transferSkinClusterSpikes(source_mesh, target_mesh):
    """
    Transfer weights from source to target using a simplified
    'spikes' island-to-curve projection method.
    """

    # --------------------------------------
    # 1. Collect skinClusters
    # --------------------------------------
    src_skin, src_infs = get_skin_cluster(source_mesh)
    if not src_skin:
        raise RuntimeError("Source mesh has no skinCluster.")

    tgt_skin, tgt_infs = get_skin_cluster(target_mesh)
    if not tgt_skin:
        # auto-create new skinCluster for target
        tgt_skin = cmds.skinCluster(src_infs, target_mesh, tsb=True)[0]

    # --------------------------------------
    # 2. Gather mesh topology + islands
    # --------------------------------------
    src_positions = get_vertex_positions(source_mesh)
    tgt_positions = get_vertex_positions(target_mesh)
    islands = get_island_sets(target_mesh)

    # --------------------------------------
    # 3. Read all source weights properly
    # --------------------------------------
    src_weights = []
    for i in range(len(src_positions)):
        w = cmds.skinPercent(
            src_skin,
            "%s.vtx[%d]" % (source_mesh, i),
            q=True,
            v=True
        )
        src_weights.append(w)

    # --------------------------------------
    # 4. Build island-mean curve
    # --------------------------------------
    curve = build_mean_curve(islands, tgt_positions)
    curve_fn = get_curve_fn(curve)

    # --------------------------------------
    # 5. Prepare result array
    # --------------------------------------
    new_weights = [[] for _ in tgt_positions]

    # --------------------------------------
    # 6. For each island:
    #       • Compute mean position
    #       • Project onto curve
    #       • Find nearest source vertex
    #       • Copy its weights to entire island
    # --------------------------------------
    for isl in islands:

        # compute island mean
        mean = [sum(tgt_positions[i][k] for i in isl)/len(isl) for k in range(3)]
        mean_point = om.MPoint(mean)

        closest_curve = curve_fn.closestPoint(
            mean_point,
            tolerance=1e-4,
            space=om.MSpace.kWorld
        )

        # Some Maya versions return (MPoint, param)
        if isinstance(closest_curve, tuple):
            closest_curve_pt = closest_curve[0]
        else:
            closest_curve_pt = closest_curve

        # nearest vertex on source mesh
        donor_index = find_closest_vertex(
        source_mesh,
        [closest_curve_pt.x, closest_curve_pt.y, closest_curve_pt.z]  # <-- convert to list
        )


        # copy weights
        donor_weights = src_weights[donor_index]
        for v in isl:
            new_weights[v] = donor_weights[:]

    # --------------------------------------
    # 7. Apply weights back onto target skin
    # --------------------------------------
    for vtx_id, w in enumerate(new_weights):
        cmds.skinPercent(
            tgt_skin,
            "%s.vtx[%d]" % (target_mesh, vtx_id),
            tv=list(zip(src_infs, w))
        )

    # cleanup
    cmds.delete(curve)

    print("=== Spike-weight transfer complete ===")


# =============================================================
# HOW TO USE
# =============================================================
# Example:
transferSkinClusterSpikes("pSphere1", "pCone1")
#
# NOTE:
# Pass the *transform name* OR shape name — both work.
# =============================================================
