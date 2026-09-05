# Final-transition endorsement audit codebook — rev.3

Frozen after the completed Round 2 audit on 2026-08-21. Round 1 remains an
immutable rev.1 annotation round and Round 2 remains an immutable rev.2 round.
Rounds 3–4 use rev.3. This prospective revision does not alter earlier labels
or reason codes.

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
unresolved choice, modal-only candidate, or an output that only completes an
auxiliary step without giving a verdict for the asked slot.

- Normally record the final answer in `ultimately_endorsed_answer`.
- For `unresolved_multiple_answers`, `no_committed_answer` and
  `partial_step_no_verdict`, begin that field with the literal `(none stated)`;
  any explanation belongs after it or in `reviewer_notes`.
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
  value. A year offered where a film title was requested is `wrong_relation`,
  not `wrong_number_or_date`.
- `insufficient_granularity`: a broader or partial value does not uniquely
  satisfy all components required by the asked slot.
- `contradiction`: mutually incompatible final answers remain unresolved.
- `refusal`: the output explicitly refuses or says the answer cannot be
  determined.
- `unresolved_multiple_answers`: alternatives for the asked slot remain open
  and no answer is selected.
- `no_committed_answer`: the output gives one or more asked-slot candidates only
  conditionally, hypothetically or modally, without a final assertion.
- `partial_step_no_verdict`: the output gives substantive information for an
  auxiliary subproblem or another answer slot but never answers, selects or
  compares values for the original asked slot. This definition depends only on
  the text, not on knowing the architecture or stage identity.
- `other`: use only when none of the above applies; explain in notes.

## Executable rules

- Comparison questions require a readable statement chain that establishes
  the entity-to-option mapping and the comparison conclusion. Merely naming a
  director, date or other intermediate fact is `partial_step_no_verdict` when
  no comparison verdict is given.
- In coordinated or conjunctive clauses, predicate–argument relations are
  local. An entity attached to `owns` cannot be transferred to `works at`; a
  gold entity under the wrong predicate does not satisfy Discovery or
  Endorsement for the asked relation.
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
  match or alias unless the output establishes referential identity. Adding a
  surname to the same referent is acceptable; embedding the gold name in a
  different person's longer name is not.
- For truncation, use the last readable committed answer before the cut. If the
  cut occurs inside the answer and its content cannot be recovered reliably,
  label Endorsement U and record `truncation` in notes.

## Revision audit trail

Round 2 supplied the prospective examples motivating rev.3:

- `FTS-0260`, `FTS-0376`, `FTS-0387`, `FTS-0012` and `FTS-0417` are candidate
  `partial_step_no_verdict` cases; their frozen rev.2 source labels remain
  `wrong_relation`.
- `FTS-0200` motivates the local-predicate rule for mixed-relation conjunctions.
- `FTS-0140` remains `wrong_number_or_date` in the frozen rev.2 workbook, while
  rev.3 prospectively treats the year-for-film mismatch as `wrong_relation`.

For cross-round reason-code summaries, preserve the raw source reason and add a
separate derived harmonized reason under rev.3. Never silently overwrite the
completed workbooks.

## Round 3 watchlist

After Round 3, review every case of:

1. `partial_step_no_verdict`;
2. `no_committed_answer` and either-axis `U`, still unobserved in Rounds 1–2;
3. mixed-relation conjunctions;
4. wrong-slot-type answers;
5. trailing answers to another slot, still unobserved in Rounds 1–2.

Zero observed examples must be reported as “not empirically tested,” not as
validation of the rule.
