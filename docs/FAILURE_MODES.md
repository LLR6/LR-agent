# Known Failure Modes

| Failure | Detection | Recovery / containment |
|---|---|---|
| Shadow candidate leaks changes into source workspace | workspace hash / baseline mismatch | abort promotion; restore from snapshots |
| Real-workspace verification fails after promotion | non-zero verifier / invariant result | automatic restore of promoted files |
| Repository changed after tournament baseline | promotion conflict check | refuse overwrite; rerun from fresh baseline |
| Genome strategy appears useful only by chance | repeated treatment/control trials | keep quarantined / contested |
| ChronoForge future scenario is unrealistic | reality observations disagree | reduce calibration weight; do not treat forecast as fact |
| Research artifact is detached from experiment definition | missing/changed manifest hash | reject artifact provenance claim |
| Persisted run interrupted | interrupted state on restart | recover as interrupted; do not mark completed |

A failed experiment is still evidence. Do not delete negative or interrupted runs just to keep dashboards clean.
