"""Read-only C0 descendant-landmark monitor; never a constraint or budget."""
from math import dist, hypot
from statistics import mean, median

from .validation import inspect_mesh


class GateIntegrityMonitor:
    """Observe primary-corner descendant clouds, not exact aperture clearance.

    Initial groups are explicit C0 landmarks. CC carries retained corner
    identities; DS carries source-corner construction descendants. Unassociated
    CC edge/face points remain unassociated rather than inventing anchor tags.
    All metrics stay separate; no score, threshold, selection or intervention.
    """

    def __init__(self,source):
        self.xyz={v:list(source.vertex_coordinates(v)) for v in source.vertices()}
        self.dimensions=inspect_mesh(source)["bounding_box"]
        self.diagonal=hypot(*self.dimensions)
        x_center=(min(p[0] for p in self.xyz.values())+max(p[0] for p in self.xyz.values()))/2
        ground=min(p[2] for p in self.xyz.values())
        self.ground=ground
        # C0 fixed opening: +/-1100 from center, head at floor+2600. No
        # generated coordinates determine groups or subdivision families.
        def group(predicate): return sorted(v for v,p in self.xyz.items() if predicate(p))
        self.groups=dict(opening_left=group(lambda p:p[0]==x_center-1100 and p[2]<=ground+2600),
            opening_right=group(lambda p:p[0]==x_center+1100 and p[2]<=ground+2600),
            opening_head=group(lambda p:abs(p[0]-x_center)==1100 and p[2]==ground+2600),
            opening_foot=group(lambda p:abs(p[0]-x_center)==1100 and p[2]==ground),
            left_support=group(lambda p:p[0]<x_center and p[2]<=ground+2600),
            right_support=group(lambda p:p[0]>x_center and p[2]<=ground+2600),
            lintel=group(lambda p:p[2]>=ground+2600),
            support_base=group(lambda p:p[2]==ground))
        if any(not keys for keys in self.groups.values()):
            raise ValueError("GateIntegrityMonitor requires the explicit C0 opening/support landmarks.")
        self.reference=self.evaluate(source,{v:v for v in source.vertices()},generation=0,normalize=False)

    def evaluate(self,mesh,anchors,*,generation,normalize=True):
        clouds={v:[] for v in self.xyz}
        for v,source in anchors.items():
            if source in clouds and mesh.has_vertex(v):
                clouds[source].append(mesh.vertex_coordinates(v))
        centroids={v:[mean(p[i] for p in points) for i in range(3)] for v,points in clouds.items() if points}
        # Each original landmark contributes equally, independent of how many
        # descendants it has. Cloud spread exposes the approximation's limits.
        points={name:[centroids[v] for v in keys if v in centroids] for name,keys in self.groups.items()}
        def average(name,axis):
            return mean(p[axis] for p in points[name]) if points[name] else None
        left,right=average("opening_left",0),average("opening_right",0)
        head,foot=average("opening_head",2),average("opening_foot",2)
        opening=dict(width=None if left is None or right is None else right-left,
            height=None if head is None or foot is None else head-foot,
            center_x=None if left is None or right is None else (left+right)/2,
            center_z=None if head is None or foot is None else (head+foot)/2)
        statistics=inspect_mesh(mesh)
        dimensions=dict(zip(("width","depth","height"),statistics["bounding_box"]))
        relations={}
        if points["left_support"] and points["right_support"] and points["lintel"]:
            lx=median(p[0] for p in points["left_support"]); rx=median(p[0] for p in points["right_support"])
            lz=median(p[2] for p in points["left_support"]); rz=median(p[2] for p in points["right_support"])
            top=median(p[2] for p in points["lintel"])
            relations=dict(left_median_x=lx,right_median_x=rx,lintel_median_z=top,
                left_median_left_of_right=lx<rx,
                fraction_left_landmarks_left_of_right_median=mean(p[0]<rx for p in points["left_support"]),
                fraction_right_landmarks_right_of_left_median=mean(p[0]>lx for p in points["right_support"]),
                lintel_median_above_support_medians=top>max(lz,rz),
                fraction_lintel_landmarks_above_opening_center=None if opening["center_z"] is None else mean(p[2]>opening["center_z"] for p in points["lintel"]))
        base=[p[2]-self.ground for p in points["support_base"]]
        result=dict(generation=generation,opening=opening,dimensions=dimensions,macro_relations=relations,
            tracked_vertex_count=sum(len(c) for c in clouds.values()),total_vertex_count=mesh.number_of_vertices(),
            missing_source_anchor_ids=sorted(set(self.xyz)-set(centroids)),
            disappeared_macro_regions=[name for name in ("left_support","right_support","lintel") if not points[name]],
            macro_region_anchor_counts={name:len(points[name]) for name in ("left_support","right_support","lintel")},
            support_base_displacement=dict(mean=mean(base) if base else None,min=min(base) if base else None,max=max(base) if base else None,
                mean_over_source_height=mean(base)/self.dimensions[2] if base else None),
            anchors=[dict(source_id=v,descendant_count=len(clouds[v]),mean_xyz=centroids.get(v),
                normalized_mean_displacement=dist(centroids[v],self.xyz[v])/self.diagonal if v in centroids else None,
                maximum_descendant_distance_over_source_diagonal=max(dist(p,self.xyz[v]) for p in clouds[v])/self.diagonal if clouds[v] else None) for v in sorted(self.xyz)],
            topology=dict(components=len(mesh.connected_vertices()),boundary_edges=statistics["boundary_edge_count"],
                is_manifold=statistics["is_manifold"],is_closed=statistics["is_closed"]),
            note="Read-only primary-corner descendant landmark approximation, equal source-anchor influence. Not exact free opening clearance, semantic inheritance or a gate score; never used by recursion.")
        if normalize:
            result["opening_normalized"]={name:(value/self.reference["opening"][name] if self.reference["opening"][name] else None) if value is not None else None for name,value in opening.items()}
            result["opening_center_drift_over_source_width_height"]=dict(x=None if opening["center_x"] is None else (opening["center_x"]-self.reference["opening"]["center_x"])/self.dimensions[0],
                z=None if opening["center_z"] is None else (opening["center_z"]-self.reference["opening"]["center_z"])/self.dimensions[2])
            result["dimensions_drift_percent"]={name:100*(value/self.reference["dimensions"][name]-1) for name,value in dimensions.items()}
        return result
