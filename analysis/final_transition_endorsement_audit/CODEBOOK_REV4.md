# Final-transition endorsement audit codebook — rev.4

Frozen after the completed Round 3 audit on 2026-08-21. Rounds 1, 2 and 3
remain immutable under rev.1, rev.2 and rev.3 respectively. Round 4 uses rev.4.
This prospective revision does not alter earlier labels or raw reason codes.

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
unresolved choice, modal-only candidate, auxiliary step without a verdict, or
an option-label reference with no recoverable answer content.

- Normally record the final answer in `ultimately_endorsed_answer`.
- For `unresolved_multiple_answers`, `no_committed_answer`,
  `partial_step_no_verdict` and `contentless_option_reference`, begin that field
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
- `wrong_relation`: the reference string is attached to a different entity,
  predicate, time, comparison or answer slot, or the output clearly fills a
  different slot type from the one requested.
- `wrong_entity`: the output attempts the requested slot type but gives the
  wrong value, including a wrong named entity or reversed yes/no polarity.
- `wrong_number_or_date`: use only when the requested answer slot itself is a
  number, rank, quantity or date and the output gives the wrong numeric/date
  value.
- `insufficient_granularity`: a broader or partial value does not uniquely
  satisfy all components required by the asked slot.
- `contradiction`: mutually incompatible final answers remain unresolved.
- `refusal`: the output explicitly refuses or says the answer cannot be
  determined.
- `unresolved_multiple_answers`: substantive alternatives for the asked slot
  remain open and no answer is selected.
- `no_committed_answer`: the output gives one or more asked-slot candidates only
  conditionally, hypothetically or modally, without a final assertion.
- `partial_step_no_verdict`: the output gives substantive information for an
  auxiliary subproblem or another answer slot but never answers, selects or
  compares values for the original asked slot.
- `contentless_option_reference`: the output contains only option labels or
  references such as `Answer A`, `Answer B` or `Improved Answer`, with no
  recoverable answer content in the same output. Use this whether one label is
  selected or multiple labels are merely listed. The act of selecting a label
  does not supply semantic answer content.
- `other`: use only when none of the above applies; explain in notes.

## Executable rules

- Comparison questions require a readable statement chain that establishes
  the entity-to-option mapping and the comparison conclusion. Merely naming a
  director, date or other intermediate fact is `partial_step_no_verdict` when
  no comparison verdict is given.
- In coordinated or conjunctive clauses, predicate–argument relations are
  local. An entity attached to `owns` cannot be transferred to `works at`.
- A yes/no question may be answered by naming a unique shared country or other
  entity when that answer unambiguously entails `yes`.
- Granularity is evaluated in the asked slot. A more specific answer containing
  the gold is accepted. A gold-span modifier outside the requested slot is not
  required, but modifiers needed to identify the requested value remain
  required.
- A conjunction containing the gold may be correct only when the gold is
  asserted under the asked relation. An unresolved disjunction is W.
- A trailing `Answer:` line that clearly answers a different auxiliary slot
  does not override an earlier supported answer to the original asked slot. A
  later statement that explicitly replaces the original asked-slot value does
  override it for Endorsement, but not for Discovery.
- A substring or name prefix inside a different longer entity is not an exact
  match or alias unless the output establishes referential identity.

## Truncation decision rule

Truncation alone does not imply U. First locate the cut relative to an
answer-bearing statement:

1. If the cut occurs after a readable committed answer, evaluate that answer.
2. If the cut occurs in background exposition, critique or setup before an
   answer assertion, label W using the applicable reason (`no_committed_answer`,
   `partial_step_no_verdict`, `refusal`, etc.).
3. Use U only when the cut interrupts an answer-bearing statement and the
   intended answer content cannot be recovered reliably.

Record `REV4:TRUNCATION_BACKGROUND` for case 2 and
`REV4:TRUNCATION_ANSWER` for case 3.

## Revision audit trail

- `FTS-0218` motivates `contentless_option_reference`: it selects `Answer B`
  without reproducing any answer content and remains raw `other` in Round 3.
- Round 1 `FTS-0211` lists `Answer A` and `Answer B` without content and remains
  raw `unresolved_multiple_answers`. Under a derived rev.4 harmonization, both
  cases map to `contentless_option_reference`.
- `FTS-0213` motivates the truncation clarification. Its cut occurs in setup,
  not inside an asserted answer, so its frozen Round 3 label is W with
  `no_committed_answer`, not U.

For cross-round reason-code summaries, preserve the raw source reason and add a
separate derived `harmonized_reason_rev4`. Never silently overwrite completed
workbooks.

## Round 4 final check

After Round 4, review every case of:

1. `contentless_option_reference`;
2. `no_committed_answer`, `partial_step_no_verdict` and either-axis U;
3. both truncation-position tags;
4. `Endorsement C` with Discovery not C, which should remain zero or be fully
   adjudicated.

Only after Round 4 and this final check are complete may the four rounds be
joined to the private key for agreement and transition analysis.
