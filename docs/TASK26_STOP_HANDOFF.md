# Task26 stop and preservation handoff

Reason: the user supplied Task27 and requested direction reconsideration.
This is not an algorithm-failure determination.

At Task27's initial safe-start check, HEAD was still Task25
`b4000cf85bc0768821976bab4b454ca35b8ccca3`, Task26 code was uncommitted, and
this stop handoff did not exist. The Task27 instruction says:

> Task26이 아직 실행 중이거나 안전한 보존 상태를 확인할 수 없으면
> 새 실험을 시작하지 말고 그 사실만 알려줘.

Accordingly, **Task27 experiments did not start**. No Task27 branch, output
root, input cage or model was created. Only the preceding Task26 work was
safely preserved. No new Task26 geometry generations were started after this
check. Original branches, user files, inputs, previous attempts and superseded
captures were retained; no reset, clean, push, merge or publish was performed.

The existing generation/native/capture workers had already exited successfully.
A scoped process check found no running progressive-gate workers. Existing-file
checkpoint verification and preservation packaging are separate from design
generation and have their own logs. Read external `release.json` and the actual
log exit statuses to confirm the final snapshot rather than treating this
statement as proof that an unlogged operation succeeded.

The final full checkpoint reread passed (all OBJ XYZ/oriented faces, continuation
coverage and constructive symmetry); ten saved-geometry comparisons passed.
The first inefficient validator was explicitly stopped and retained as an
interrupted attempt, then the corrected validation exited 0 with no RAM stop.
Its correction changes only validation lookup cost, not generated meshes.

Preservation branch: `experiment/task26-progressive-gates`.
Preservation commit: recorded below after the actual local commit is created.
The metadata follow-up can be a descendant; it does not change generated meshes.
Verify with `git show`, `git merge-base --is-ancestor` and `git status --porcelain`.

Retained lead: `LEAD_BALANCED_G7`, actual attempt_002, 1,245,184 quads.
Actual OBJ, full geometry/state/operator checkpoints and native 3DM are under
`E:/CHESHIRE_DATA/task26`. Read `TASK26_RESULTS.md` and `TASK26_HANDOFF.md` for
exact paths, executed tests, resource records and limitations. The design status
is PARTIAL for fine-fold hierarchy; bulk, export and real depth captures exist.

Task26 code may be reused selectively. It still uses a continuous swept U and
global fold stencils with physical support; its auxiliary input profile is not
the selected lead. Task27's required profile-first body/neck/seat/lintel and
part-specific continuation are not implemented by relabeling these results.

The next Task27 run must read this file, the actual preservation commit and
current Git state before choosing a separate branch/worktree. Do not silently
start from Task25 or assume current HEAD is correct. Do not treat this user-
requested direction change as evidence that all prior algorithms failed.
