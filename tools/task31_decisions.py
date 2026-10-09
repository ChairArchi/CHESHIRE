"""Write evidence-based decisions after inspecting the actual images."""
import copy,sys
from task31_study import ROOT,REPO,read,write,file_hash,basic_gate
from task30_views import sheet


def stageA():
    v=read(ROOT/'definitions/task31_variant_definitions.json')['StageA'];lookup={d['id']:d for d in v}
    whole=read(ROOT/'renders/cube1/manifest.json')['records']+read(ROOT/'renders/cube2_complete/manifest.json')['records']
    assert len(whole)==19
    sheet(whole,ROOT/'renders/TASK31_cube_variants.png',4,1000)
    detail=read(ROOT/'renders/detail/manifest.json')['records']
    visibility=[dict(label=r['label'],pixels=r['enclosed_background_pixels'],largest=r['largest_background_component'],area=r['enclosed_background_area']) for r in detail]
    write(ROOT/'analysis/stageA_visibility.json',dict(records=visibility,meaning='Actual rendered background inside foreground silhouette; not genus inferred from shading. Crops may clip outer silhouette; compare identical frames.',
        limits='Raster visibility confirms particular rays; does not prove all walls free from self intersections.'))
    observations={
        'AX_P4':'Directional regional contrast: calmer upper/right zones beside a folded front; modest amplitude.',
        'AX_P8':'Strong rough/front versus quiet/upper regional differentiation; parts of it are smoothing/suppression.',
        'AX_R4':'Similar to persistent .4 in whole view; weak evidence that axis memory itself adds visual identity.',
        'AX_R8':'Similar to persistent .8, so no claim that memory alone solves the design bottleneck.',
        'FOLD_P4':'Fold-based distinctions modest; shared macro lobes remain.',
        'FOLD_P8':'Quiet central neck/bulb beside folded neighbours; more localized contrast than dominant axes.',
        'DEPTH_1_3':'Inset without regional wall controls is visually weak in final G8.',
        'DEPTH_2_3':'Two inset rings alone do not produce convincing persistent nested concavity.',
        'DEPTH_2_6':'Deeper two-ring edit alone is mostly concealed in G8; retained as negative.',
        'OPEN_35':'Combinatorial handle exists, but no meaningful exposed opening in oblique whole view.',
        'OPEN_60':'Combinatorial handle exists; tested opening-only family remains visually weak.',
        'OPEN_85':'G8 front crop has no exposed through background; adjacency change alone is insufficient.',
        'AXIS_OPEN_60':'Channel-mode walls combine with differentiated exterior; finer aperture than .85.',
        'AXIS_OPEN_85':'Clearly exposed front opening with recessed collar/wall; broad directional contrast.',
        'FOLD_OPEN_60':'Localized exterior identity plus channel protection; smaller aperture.',
        'FOLD_OPEN_85':'Selected cube lead: exposed front opening, recessed lip and quiet neck/bulb beside folded neighbours.',
        'AXIS_DEPTH':'Visible recessed nested collar only with channel-mode response; no exposed through opening expected.',
        'AXIS_BORN1':'Earlier birth does not produce stronger hierarchy; no extra timing search justified.'}
    records=[]
    for d in v:
        r=read(ROOT/'analysis/runs/cube'/(d['id']+'.json'));r['visual_assessment']=observations[d['id']];records.append(r)
    write(ROOT/'analysis/targeted_experiment_log.json',dict(StageA=records,new_cube_variants=18,unchanged_cube_controls=1,StageB=[],
        main_directions=['persistent regional controls','early bounded control-mesh recess/tunnel'],
        failed_render_attempt=dict(tag='cube2',reason='Renderer reached a G8 NPZ still being written; EOFError, no geometry loss.',recovery='All stages completed; complete rerender cube2_complete retained; failed logs preserved.')))
    chosen=lookup['FOLD_OPEN_85'];write(ROOT/'definitions/task31_lead_pipeline.json',dict(cube=chosen,base=read(ROOT/'definitions/task30_retained_baseline.json'),gate=None))
    text='''PARTIAL — meaningful StageA improvement; gate transfer required.

All18 actual cube G8 whole views and the unchanged Task30 control were inspected.
Matched900-unit front/oblique crops inspected Task30, AX_P8, FOLD_P8, OPEN_85,
AXIS_OPEN_85, FOLD_OPEN_85, DEPTH_2_6 and AXIS_DEPTH. Same flat clay/light,
no smoothing, unknown reference camera not falsely matched.

Persistent regional controls produce quiet neck/bulb and folded neighbouring regions.
Dominant-axis memory and per-step remeasurement look similar; memory alone is NOT
proved superior. Large quiet areas partly suppress detail, not new ornament hierarchy.
Fold descriptor localizes the contrast better, so FOLD_OPEN_85 is the cube lead.

The geometric edit is one explicit G2 front/rear annulus tunnel, aperture .85.
New collar/walls get persistent CHANNEL membership and nonzero quiet/negative normal
controls. Tunnel-only OPEN_85 remains genus1, but its mouth is visually occluded atG8.
The combined modes maintain actual background-visible front rays and a recessed collar.
AXIS_DEPTH gives a readable nested recess; depth-only edits are largely concealed.
See stageA_visibility.json for actual hit/background counts, not a shading claim.

This is meaningful spatial improvement beyond Task30's dense skin: an exposed
through opening and localized contrasting development on the SAME actual prefix.
It is not a recovery of Hansmeyer's generator, automatic porosity or non-repeating
micro growth. The opening was deliberately created; self-intersection-free embedding
and fabrication safety remain unproved. Overall provisional verdict PARTIAL.

StageB is authorized and mandatory: actual gate_input('RECT',False), same74V/80F,
Task30 full schedule control with the necessary polygon compatibility enabler,
plus4 targeted transfers: FOLD_P8, AXIS_OPEN_85, FOLD_OPEN_60, FOLD_OPEN_85.
No semantic body/neck/shoulder construction. Mouths selected geometrically near
the original lintel midpoint. Full G0..G8 retained, measured RAM guard only.
'''
    (ROOT/'analysis/stageA_decision.md').write_text(text,encoding='utf-8')
    variants=[dict(id='TASK30_GATE',descriptor=None,memory='persistent',contrast=0,edit=None,born=2,onset=3)]
    variants += [lookup[n] for n in ('FOLD_P8','AXIS_OPEN_85','FOLD_OPEN_60','FOLD_OPEN_85')]
    m=basic_gate();write(ROOT/'definitions/gate_specimen_definition.json',dict(source='src/cheshire/progressive_gates.py:gate_input(RECT,False)',
        source_sha256=file_hash(REPO/'src/cheshire/progressive_gates.py'),input_vertices=m.xyz.tolist(),input_faces=m.faces.tolist(),
        vertex_count=len(m.xyz),face_count=len(m.faces),frame='Original X=-400.036865234375/Y=-18.533447265625/Z-up, unscaled',
        weights='Identical full Task30 schedule for control and all treatments before declared regional blend',
        compatibility='Complete polygon DS needed for original foot-centre valence8 and edited valence5; neutral cosine n>4, no w1 there.',
        variants=variants,transfer_variant_count=4,control_count=1))
    print('StageA decision and mandatory4-case gate transfer definition saved.')


def stageB():
    definitions=read(ROOT/'definitions/gate_specimen_definition.json')['variants'];chosen=next(d for d in definitions if d['id']=='FOLD_OPEN_85')
    lead=read(ROOT/'definitions/task31_lead_pipeline.json');lead['gate']=chosen;write(ROOT/'definitions/task31_lead_pipeline.json',lead)
    detail=read(ROOT/'renders/gate_detail/manifest.json')['records']
    visibility=[dict(label=r['label'],pixels=r['enclosed_background_pixels'],largest=r['largest_background_component'],area=r['enclosed_background_area']) for r in detail]
    write(ROOT/'analysis/stageB_visibility.json',dict(records=visibility,render_frame='Actual1400px/1800-unit lintel crops, same flat material/light.',
        limitation='Only front rays expose the aperture here; oblique view is occluded by the depth of the tunnel.'))
    observations=dict(TASK30_GATE='Control: a dense broadly similar folded skin across whole carrier; portal remains.',
        FOLD_P8='Clear quiet bulb/neck zones beside angular bands and deeper lintel layering; some smooth suppression, no additional topological tunnel.',
        AXIS_OPEN_85='Visible extra front aperture; axis scheme leaves more folded exterior than fold descriptor, useful matched transfer control.',
        FOLD_OPEN_60='Regional layering plus exposed smaller front aperture; 12999 visible interior-background pixels.',
        FOLD_OPEN_85='Selected gate lead: same fold-based differentiation, larger exposed front aperture25727pixels, recessed lip/wall, main portal preserved.')
    log=read(ROOT/'analysis/targeted_experiment_log.json');records=[]
    for d in definitions:
        r=read(ROOT/'analysis/runs/gate'/(d['id']+'.json'));r['visual_assessment']=observations[d['id']];records.append(r)
    log.update(StageB=records,new_gate_transfers=4,gate_control_count=1);write(ROOT/'analysis/targeted_experiment_log.json',log)
    text='''PARTIAL — meaningful gate transfer achieved, target aesthetic hierarchy incomplete.

Exact existing basic RECT unprofiled gate,74V/80F, full actual G0..G8.
Task30-schedule control and4 transfers all completed without a RAM stop.
No ALICE, recreated architecture or semantic body/neck/shoulder pipeline.

All5 actual G8 whole views and10 matched lintel front/oblique crops were inspected.
FOLD_P8 visibly differentiates quiet neck/bulb volumes, folded bands and nested lintel
layers compared with the control's more uniform dense folded skin. This is actual
flat-normal geometry, but part of the contrast is detail suppression.

FOLD_OPEN_85 is selected: same .8 persistent fold mixture, one explicit G2 annulus
tunnel, aperture .85, protected nonzero CHANNEL wall controls. Front crop has25727
interior background pixels, projected area42528.3061 original-unit squared. Matched
Task30_GATE and FOLD_P8 have0. FOLD_OPEN_60 has12999; AXIS_OPEN_85 has23127.
These are particular visible rays, not a fabrication/solid certificate.
Oblique crops show a recessed wall/lip but have0 through-background pixels due to
tunnel depth. Do not imply an opening is visible from every direction.

The main U-carrier portal remains. Extra source mouths are actualG2 faces490/412,
centroids(-627.62549,-298.28765,2767.75142) and
(-627.62549,261.22075,2767.75142): left of the original X=-400.03687 centreline.
This one-pair bounded experiment is intentionally asymmetric; no automatic mirror
or symmetry claim. Same geometric selection on cube chooses faces35/71.

Gate leadG8 is5021696V/5021696quadF, closed oriented incidence, Euler0. ControlG8
is4980738V/4980736quadF, Euler2. Counts are not the reason for selection.
This demonstrates that the mechanism transfers to the original basic gate and
increases its local spatial potential. It does not establish independent non-repeating
small motifs or multi-generation automatic porosity. Layered concavity is clearer,
but arbitrary increasing nested complexity is not proved by the two-ring recess test.
'''
    (ROOT/'analysis/stageB_gate_transfer_decision.md').write_text(text,encoding='utf-8')
    final='''PARTIAL

Selected cube and gate lead: FOLD_OPEN_85, actualG0..G8 plusG2_post_edit.
Keep Task30 U_67_LOCK_END4 as immutable canonical control; all Task31 modes are opt-in.

Primary Task30 diagnosis C is retained but narrowed after the experiment: the
remaining weakness is coordinated multi-scale motif hierarchy and relational design
identity, not raw lack of different numerical controls. Geometry-derived persistent
regions now produce differentiated response, and protected walls maintain real exposed
negative space on cube AND the same existing basic gate. Tests and density alone
are not the improvement: matched flat crops show it and actual visibility quantifies it.

Main technical direction: persistent four-mode memberships with actual multi-parent
inheritance, coupled to one early bounded control-mesh tunnel/recess. Strongest selected
birth descriptor is signed normal-relative neighbour displacement on actualG2 faces,
tertiles give convex/neutral/concave intended modes. Descriptor uses geometry, not IDs.
CC exact parent, DS equal mean of complete supports; walls are explicitly CHANNEL.
Blend .8 with original Task30 resolved controls and local current scales. Existing
schedule, finite locks, modified DS and final nonzero CC remain declared in fullprecision.

Initial prompt assumptions were partially superseded: current intrinsic weights alone
were not required to discover both topology and identity. R1p78 tags justify differentiated
controls; R3 separates coarse control topology from refinement. The bounded annulus is
more interpretable than hidden late self-intersections and permits independent topology,
visibility and wall-response ablations. It is our implementation, not R3's reflection/union
code or recovered Digital Grotesque source. Standard cosine DS for extraordinary polygons
is a compatibility enabler, not an extra design search or invented modified n-gon equation.

Task30 comparison: cube now has an exposed front aperture and localized quiet neck/bulb
beside folded regions. Gate has clearer regional lobes, necks and lintel bands/layering,
plus an additional front-visible opening while retaining the main portal. Cube opening-only
negative stays Euler0 yet is visually occluded and has tangled sampled sections. CHANNEL
response maintains a clearer open interval. Axis persistent versus remeasured comparison
looks similar, so memory alone is NOT proved superior. Fold locality is the limited
advantage selected from this bounded study. Larger quiet areas partly suppress detail.

18 StageA variants plus1 control;4 gate transfers plus1 control. All actual steps saved.
Cube selected front900-unit crop:13419 interior-background pixels versus Task30/open-only0.
Gate selected front1800-unit crop:25727 versus Task30/identity-only0. Oblique through
visibility is0 for both leads; deep tunnels occlude their opposite mouths from that angle.
Actual topology was deliberately edited atG2; this is designed genus, not emergent porosity.
Deeper recessed walls/lintels improve local spatial reading; persistent independent nested
fine development, non-repeating motif families and intersection-free embedding remain
unproved. This prevents a SUCCESS claim for the full reference-grounded aesthetic target.

Both selected leads require exact full replay, actualG7 continuation, OBJ and native3DM
reread; validation_summary.json records completed evidence. No push/merge/Task32.
Optional image-led atlas deferred with a concrete source/grouping follow-up plan.
'''
    (ROOT/'analysis/final_decision.md').write_text(final,encoding='utf-8')
    reassess=ROOT/'analysis/primary_bottleneck_reassessment.md'
    reassess.write_text(reassess.read_text(encoding='utf-8')+'\n\nPost-experiment: keep C, narrow to coordinated multi-scale motif hierarchy and relational design identity. Regional controls and exposed protected negative space now work, but independent non-repeating fine growth is unproved. See final_decision.md.\n',encoding='utf-8')
    print('StageB selection and final PARTIAL decision saved.',flush=True)


if __name__=='__main__':stageB() if len(sys.argv)>1 and sys.argv[1]=='stageB' else stageA()
