# Independent review of Goals A, B and D

Reviewed baseline: `9497f47e6a44ac8ba076860ef846ea0e3a50a8bf`. Three separate reviewers received the documents and their lens instructions without the author's earlier conclusions. Review lenses: adversarial, edge-case hunter, editorial structure. These are planning findings, not a runtime certification. No forced finding count was used to pad the results.

## Adversarial findings and disposition

| Location | Trigger condition | Concrete guard | Consequence without guard | Disposition |
| --- | --- | --- | --- | --- |
| Behavior contract / execution; B / current state | A runs before the retention hold | Enforce a preservation prerequisite before further app/evaluation runs | Existing or new records can age out before B | Include minimal hold in A; advanced retention remains B |
| A / trace boundaries | Clarification question originates in LLM output | Use a deterministic question-kind code for that branch; never copy generated question text into trace | Trace requirement conflicts with no-generated-text rule | Add exact branch rule |
| A / fact symbols | User-reported, observed, conflicting and false values share symbols | Label all four evidence statuses; symbols indicate presence/conflict only | Checkmark looks like verified compliance | Add exhaustive mapping |
| A / sources | Retrieved candidates differ from citations actually returned | Populate sources from final validated citations; preserve available identity/date/passage metadata | Panel falsely claims supporting evidence | Add source rule |
| B / strict mirror | Required mirror URL is missing or invalid | Fail configuration/delivery closed; never silently use local-only storage | Strict mode loses durability on ephemeral host | Include minimal config guard in A prerequisite |
| Behavior contract / acceptance | Only selected tests run or counts use inconsistent units | All applicable A cases must pass locally; define live smoke separately and count claims consistently | Partial or incomparable acceptance evidence | Clarify checkpoints and metric units |
| D / selection | Halan lacks verified page evidence | Label as an insufficient-evidence control outside qualifying coverage | Five candidates mistaken for five verified dossiers | Correct proposal wording |
| A/B / signal capture | A strips router weights before B captures them | Preserve internal router signals in committed record in A | Early records permanently lose diagnostic data | Include minimal additive audit field in A |

## Edge-case findings and disposition

| Location | Trigger condition | Concrete guard | Consequence without guard | Disposition |
| --- | --- | --- | --- | --- |
| A / fact display | Supplied, false, or conflicting values | Explicit status labels and non-verdict symbols | False implies failed rule, assertion implies verification | Overlaps adversarial mapping finding; accepted |
| A / sources | Clarification precedes retrieval or retrieved source unused | Only final citation references; empty list where no sources used | False source-backed explanation | Overlaps adversarial citation finding; accepted |
| B / retention | Shared evidence referenced by a held record | Delete evidence only when no retained/archived/mirrored/held record references it | Preserved record loses reconstructibility | Add B reference protection |

## Structure findings and disposition

| Original structure | Recommended change | Disposition |
| --- | --- | --- |
| A scope extension appears after matrix | Move expanded scope directly after Intent | Accepted |
| Joint A+B case ownership unspecified | Define A as observable behavior and current safe trace; B as extended lifecycle/provenance, except A preservation prerequisites | Accepted; no behavior removed |
| B runtime gaps appear late | Move current-state gaps before implementation details | Accepted |
| D mixes Halan with qualifying candidates | Label four evidence-backed candidates plus one insufficient-evidence case | Accepted; all matches still need verification |
| All required cases versus selected deployed cases | Complete local acceptance first; explicit deployed smoke is additional evidence, not a replacement | Accepted |
| Preservation policy repeated across entry documents | Preserve short local statements and links | Accepted; no redundant rewrite |

## Machine-readable behavioral findings

```json
[
  {"lens":"adversarial","location":"behavior contract/execution; B/current state","trigger_condition":"A runs before hold","guard_snippet":"Enforce preservation prerequisite in A","potential_consequence":"POC evidence deleted"},
  {"lens":"adversarial","location":"A/trace boundaries","trigger_condition":"LLM-generated clarification","guard_snippet":"Use deterministic question-kind code","potential_consequence":"Generated text enters trace"},
  {"lens":"adversarial","location":"A/fact symbols","trigger_condition":"Four statuses mapped to three symbols","guard_snippet":"Label evidence status explicitly","potential_consequence":"Presence mistaken for compliance"},
  {"lens":"adversarial","location":"A/sources","trigger_condition":"Retrieved candidate not used","guard_snippet":"Final citation references only","potential_consequence":"False support claim"},
  {"lens":"adversarial","location":"B/strict mirror","trigger_condition":"Required URL absent or invalid","guard_snippet":"Fail closed","potential_consequence":"Durability bypass"},
  {"lens":"adversarial","location":"behavior contract/acceptance","trigger_condition":"Selected subset or variable counting unit","guard_snippet":"All applicable A cases and fixed rubric","potential_consequence":"Incomparable acceptance"},
  {"lens":"adversarial","location":"D/selection","trigger_condition":"Halan counted as qualified","guard_snippet":"Separate negative control","potential_consequence":"Inflated coverage"},
  {"lens":"adversarial","location":"A/B/signal capture","trigger_condition":"Public signals removed before internal capture","guard_snippet":"Add internal audit capture in A","potential_consequence":"Diagnostic evidence lost"},
  {"lens":"edge-case-hunter","location":"A/fact display","trigger_condition":"Reported/conflicting/false fact","guard_snippet":"Explicit evidence labels","potential_consequence":"Misleading symbols"},
  {"lens":"edge-case-hunter","location":"A/sources","trigger_condition":"No retrieval or unused chunk","guard_snippet":"Only actual citation references","potential_consequence":"Unsupported trace attribution"},
  {"lens":"edge-case-hunter","location":"B/retention","trigger_condition":"Shared source still referenced","guard_snippet":"Reference-aware evidence preservation","potential_consequence":"Protected history unreconstructible"}
]
```

The author checked these findings against the current source, including the strict-mirror fallback and router metadata assignments. The review does not establish that all 16 behavior cases already pass. Implementation and case-level evidence remain required.
