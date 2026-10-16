"""Original fold-family activity and smooth overlap ownership.

Scores use the actual authored PCHIP radial/axial vector request, including
exact source warp, angular support, terminal window and bridge multiplier.
They are not broad search-corridor masks. SOURCE face eligibility remains the
caller's actual topology/lineage mask and is never inferred from these scores.
"""
from pathlib import Path
import importlib.util

import numpy as np

HERE=Path(__file__).resolve().parent
EVENT_PATH=HERE/'original_fold_events.py'
_spec=importlib.util.spec_from_file_location('original_contribution_ownership',EVENT_PATH)
original=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(original)


def helper_paths():
    return list(dict.fromkeys([EVENT_PATH,*original.helper_paths()]))


def score(theta,t,event):
    """Nonnegative original-family vector magnitude at material samples."""
    theta,t=np.broadcast_arrays(np.asarray(theta,dtype=float),np.asarray(t,dtype=float))
    if not(np.isfinite(theta).all() and np.isfinite(t).all()):
        raise ValueError('Finite actual material theta/t required.')
    descriptor=original._descriptor(event)
    if 'profile' not in descriptor:
        raise ValueError('Exact original event profile descriptor required.')
    vector=original.bank.evaluate_event(descriptor,t,theta)
    return np.linalg.norm(vector,axis=-1)


def score_events(theta,t,events):
    """Return scores with event axis first; inputs and events stay unchanged."""
    theta,t=np.broadcast_arrays(np.asarray(theta,dtype=float),np.asarray(t,dtype=float))
    if not events:return np.empty((0,*theta.shape))
    return np.stack([score(theta,t,event) for event in events],axis=0)


def partition_weights(theta,t,events,*,normalization_floor=1e-12):
    """Normalize only real source-family activity; all-zero regions stay zero.

    Inside overlap the weights are continuous magnitude ratios, not an argmax
    partition. The small denominator floor keeps exact inactive boundaries
    finite. The caller must retain its separate true SOURCE topology mask.
    """
    if not np.isfinite(normalization_floor) or normalization_floor<=0:
        raise ValueError('Positive finite normalization floor required.')
    scores=score_events(theta,t,events)
    if not len(scores):return scores
    total=scores.sum(axis=0)
    return scores/np.maximum(total,normalization_floor)[None,...]


def select_parent(theta,t,events,available_family_ids=None):
    """Select strongest measured family on supplied actual material samples.

    Returns ``(family_id,diagnostics)``. ``available_family_ids`` may restrict
    selection to families with a real measured rail in an existing next state.
    The query set can be native samples or already verified diagnostic hits;
    its aggregate is not a surface-area measurement or an aesthetic score.
    """
    scores=score_events(theta,t,events)
    if not len(scores):return None,dict(status='NO_ORIGINAL_FAMILY',families=[])
    flat=scores.reshape(len(events),-1)
    mean=flat.mean(axis=1)
    allowed=set(range(len(events))) if available_family_ids is None else {int(i) for i in available_family_ids}
    candidates=[i for i in range(len(events)) if i in allowed and mean[i]>1e-12]
    weights=partition_weights(theta,t,events).reshape(len(events),-1)
    families=[dict(family_id=i,bank_id=event.get('bank_id',event.get('id')),
        mean_original_request=float(mean[i]),maximum_original_request=float(flat[i].max(initial=0.)),
        mean_overlap_weight=float(weights[i].mean()),available_measured_parent=i in allowed)
        for i,event in enumerate(events)]
    selected=max(candidates,key=lambda i:(mean[i],-i)) if candidates else None
    total=flat.sum(axis=0)
    dominant=np.argmax(flat,axis=0).astype(int)
    dominant[total<=1e-12]=-1
    info=dict(status='SELECTED_ORIGINAL_CONTRIBUTION' if selected is not None else 'NO_ACTIVE_MEASURED_PARENT',
        selected_family_id=selected,
        selected_bank_id=None if selected is None else events[selected].get('bank_id',events[selected].get('id')),
        families=families,sample_scores=flat.tolist(),sample_partition_weights=weights.tolist(),
        dominant_family_per_sample=dominant.tolist(),
        score_equation='norm(actual original radial/axial PCHIP vector evaluated at exact source u(theta,t), including angular wave, source axial window and amplitude_multiplier).',
        ownership='Continuous score_i/sum(score_j) where any original family is active; zero where none is active. True SOURCE incidence mask is independent and must still be enforced.',
        limitation='Source-family request magnitude, not an exact additive decomposition of mature geometry. G0 initial memory/valley retention, later finite-field movement, WALL redevelopment and subdivision are not inverted by this score. Selection on supplied samples does not certify aesthetic quality.')
    return selected,info


normalized_scores=partition_weights
