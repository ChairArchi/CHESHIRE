"""Task23 capability contacts and design eligibility; old policies unchanged."""


def contact_band(count, cap_reached=False):
    if type(count) is not int or count < 0:
        raise ValueError('Nonnegative sampled contact count required.')
    if cap_reached:
        return '256+' if count >= 256 else 'CAPPED'
    if count == 0:
        return 'CLEAN_SAMPLE'
    if count <= 10:
        return 'LOW_CONTACT'
    if count <= 30:
        return '11-30'
    if count <= 100:
        return '31-100'
    if count <= 256:
        return '101-256'
    return '256+'


def assess_contact_policy(count, *, cap_reached=False, valid=True, catastrophic=False,
                          stages_after_cap=0, mode='EXPLORATION'):
    if mode not in ('EXPLORATION', 'DESIGN') or type(stages_after_cap) is not int or stages_after_cap < 0:
        raise ValueError('Explicit contact policy and counted post-cap stages required.')
    band = contact_band(count, cap_reached)
    hard = not valid or catastrophic
    eligible = not hard and not cap_reached and count <= 10
    # User's Task23 policy override: counts and the sampler cap are diagnostic.
    # Cleanliness remains available for final preference, never a growth veto.
    stop = hard
    return dict(contact_band=band, design_eligible=eligible, hard_stop=hard, stop=stop,
        capability_usable=not hard,
        capability_state='SELF_INTERSECTING_CAPABILITY' if count or cap_reached else 'CLEAN_SAMPLE',
        additional_requested_stage_allowed=not hard,
        policy='User override: contact count/cap never stops evolution; finite/topology/operator/resource conditions govern. No collision certificate.')
