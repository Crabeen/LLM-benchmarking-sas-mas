# Final-transition endorsement audit codebook — rev.2

Frozen after the completed Round 1 checkpoint on 2026-08-21. Round 1 remains
an immutable rev.1 annotation round. Rounds 2–4 use rev.2; no Round 1 label is
retrospectively changed by this revision.

## Unit and scope

Each row is one independent stage output. Judge only the answer slot requested
by the original question.

- An incorrect intermediate hop does not change either axis when the output
  still supplies and ultimately endorses the correct value in the asked slot.
- Record intermediate-hop errors in `reviewer_notes` if useful, but do not use
  them to override the two answer-slot labels.
- Do not use outside knowledge to repair a missing entity-to-option mapping,
  comparison relation or reasoning premise.

## Discovery

`C` means that at least one readable statement directly states or
unambiguously entails a reference answer in the requested entity, relation and
granularity. Later rejection, replacement or refusal does not erase discovery.

An entailment may combine multiple statements in the same output only when all
required premises are explicit, readable assertions. It must not rely on facts
outside the output. A presupposition, hypothetical, quoted candidate or merely
mentioned string is not by itself an asserted premise.

`W` means that no statement supplies the reference answer in the requested
slot. A string match alone is insufficient when the gold appears incidentally,
under another relation, or only as a prefix/substring of a different entity.

`U` is reserved for genuine semantic ambiguity, malformed questions or text
that cannot be judged reliably.

Every Discovery `C` requires a verbatim evidence substring from `stage_output`.

## Endorsement

`C` means that the output's final asserted, selected or supported answer to the
original asked slot is semantically equivalent to a reference answer.

`W` includes a final wrong answer, refusal, unresolved contradiction,
unresolved choice or absence of a committed answer.

- Normally record the final answer in `ultimately_endorsed_answer`.
- For `unresolved_multiple_answers` and `no_committed_answer`, begin that field
  with the literal `(none stated)`; any explanation belongs after it or in
  `reviewer_notes`.
- For `refusal`, the field may be blank.

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
  satisfy all components required by the asked slot.
- `contradiction`: mutually incompatible final answers remain unresolved.
- `refusal`: the output explicitly refuses or says the answer cannot be
  determined.
- `unresolved_multiple_answers`: alternatives remain open and no answer is
  selected. A conjunctive answer that jointly asserts the gold and additional
  entities in the same relation is not automatically unresolved.
- `no_committed_answer`: only conditional, hypothetical or modal suggestions
  are given without a final assertion.
- `other`: use only when none of the above applies; explain in notes.

## Executable rules

- Comparison questions require a readable statement chain that establishes
  the entity-to-option mapping and the comparison conclusion.
- A yes/no question may be answered by naming a unique shared country or other
  entity when that answer unambiguously entails `yes`.
- Granularity is evaluated in the asked slot. A more specific answer containing
  the gold is accepted. A gold-span modifier outside the requested slot is not
  required—for example, when the question asks for a wood type, `teak` can fill
  that slot even if the benchmark span is `75% of the world's teak`. Modifiers
  needed to identify the requested value remain required.
- A conjunction containing the gold may be correct when all conjuncts are
  asserted as answers in the same relation. An unresolved disjunction is W.
- A trailing `Answer:` line that clearly answers a different auxiliary slot
  does not override an earlier supported answer to the original asked slot. A
  later statement that explicitly replaces the original asked-slot value does
  override it for Endorsement, but not for Discovery.
- A substring or name prefix inside a different longer entity is not an exact
  match or alias unless the output establishes referential identity.
- For truncation, use the last readable committed answer before the cut. If the
  cut occurs inside the answer and its content cannot be recovered reliably,
  label Endorsement U and record `truncation` in notes.

## Round 2 watchlist

Round 1 empirically observed Discovery-C/Endorsement-W and unresolved-choice
cases. The following still require targeted review after Round 2:

1. modal or conditional-only candidate answers;
2. either axis labelled U;
3. disagreements over multi-statement compositional entailment;
4. the asked-slot granularity and trailing-other-slot rules added in rev.2.

Zero observed examples must be reported as “not empirically tested,” not as
validation of the rule.
