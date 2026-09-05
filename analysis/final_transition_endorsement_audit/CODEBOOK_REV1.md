# Final-transition endorsement audit codebook — rev.1

Frozen after the completed 18-row pilot on 2026-08-21. The four formal review
rounds must use this version until the Round 1 checkpoint has been completed.

## Unit and scope

Each row is one independent stage output. Judge only the answer slot requested
by the original question.

- An incorrect intermediate hop does not change either axis when the output
  still supplies and ultimately endorses the correct value in the asked slot.
- Record intermediate-hop errors in `reviewer_notes` if useful, but do not use
  them to override the two answer-slot labels.
- Do not use outside knowledge to repair a missing entity-to-option mapping or
  comparison relation.

## Discovery

`C` means that at least one readable statement directly states or
unambiguously entails a reference answer in the requested entity, relation and
granularity. Later rejection, replacement or refusal does not erase discovery.

`W` means that no statement supplies the reference answer in the requested
slot. A string match alone is insufficient when the gold appears incidentally
or under another relation.

`U` is reserved for genuine semantic ambiguity, malformed questions or text
that cannot be judged reliably.

Every Discovery `C` requires a verbatim evidence substring from `stage_output`.

## Endorsement

`C` means that the output's final asserted, selected or supported answer is
semantically equivalent to a reference answer.

`W` includes a final wrong answer, refusal, unresolved contradiction,
unresolved choice or absence of a committed answer. Fill
`ultimately_endorsed_answer` unless the reason is `refusal` or
`no_committed_answer`.

Every Endorsement `C` requires a verbatim evidence substring from
`stage_output`.

## Reason codes

Use the most specific applicable code.

- `exact_or_alias`: the accepted answer is exact or a listed alias.
- `semantic_equivalent`: the answer is correct by unambiguous paraphrase or
  entailment.
- `absent`: no reference answer or semantic equivalent is asserted or entailed
  in the asked relation. Primarily a Discovery-W code.
- `incidental_mention`: the reference string occurs only as background,
  quotation, candidate, title or unrelated mention, not as an answer-bearing
  statement. Primarily a Discovery-W code.
- `wrong_relation`: the reference string appears, but is attached to a
  different entity, relation, time, comparison or answer slot. This differs
  from `absent` because the gold string is present.
- `wrong_entity`: the final committed value in the asked slot is wrong,
  including a wrong named entity or reversed yes/no polarity. It is the general
  Endorsement-W wrong-value class.
- `wrong_number_or_date`: a more specific subtype of `wrong_entity`; use this
  instead when the final wrong value is numeric or a date.
- `insufficient_granularity`: a broader or partial value does not uniquely
  satisfy all required gold components.
- `contradiction`: mutually incompatible final answers remain unresolved.
- `refusal`: the output explicitly refuses or says the answer cannot be
  determined.
- `unresolved_multiple_answers`: alternatives remain open and no answer is
  selected. A conjunctive answer that jointly asserts the gold and additional
  entities in the same relation is not automatically unresolved.
- `no_committed_answer`: only conditional, hypothetical or modal suggestions
  are given without a final assertion.
- `other`: use only when none of the above applies; explain in notes.

## Special forms frozen from the pilot

- Comparison questions require a readable statement chain that establishes
  the entity-to-option mapping and the comparison conclusion.
- A yes/no question may be answered by naming a unique shared country or other
  entity when that answer unambiguously entails `yes`.
- Granularity is directional: a more specific answer containing the gold is
  accepted; a partial answer missing a required gold component is rejected. A
  broader name is accepted only when the requested slot's referent is unchanged
  and unique.
- A conjunction containing the gold may be correct when all conjuncts are
  asserted as answers in the same relation. An unresolved disjunction is W.
- For truncation, use the last readable committed answer before the cut. If the
  cut occurs inside the answer and its content cannot be recovered reliably,
  label Endorsement U and record `truncation` in notes.

## Provisional rules requiring a Round 1 checkpoint

The pilot contained no empirical examples of the following:

1. Discovery C and Endorsement W (discovered then rejected/replaced).
2. Modal or conditional-only candidate answers.
3. Unresolved alternative answers.
4. Either axis labelled U.

After Round 1, list every observed `blind_stage_id` for these forms and decide
whether rev.1 remains adequate before starting Round 2. Do not retrospectively
change Round 1 labels without recording the codebook revision and affected IDs.
