# Final-transition endorsement audit: next-step protocol

## Frozen design

- Sampling seed: `41`; presentation-round seed: `4104`.
- Frozen sample: 160 unique benchmark items.
- Analysis rows: 400; hidden intra-rater duplicates: 20; total annotations: 420.
- Four review rounds contain 105 rows each.
- Every item appears at most once in a given round.
- Every hidden duplicate is in a different round from its original.
- The machine sampling stratum is used only for sampling and must never be
  rewritten from the human labels.

## Step 1 — Complete the 18-row pilot

Use `outputs/final_transition_endorsement_audit/final_transition_endorsement_pilot_18.xlsx`.

1. Annotate both axes for all 18 rows.
2. Require an evidence quotation whenever either axis is `C`.
3. Fill `ultimately_endorsed_answer` unless the reason is `refusal` or
   `no_committed_answer`.
4. Resolve all seven questions in `Pilot Findings` as executable rules.
5. Confirm `Progress=100%` and `Endorsement C but Discovery not C=0`.
6. Save the completed pilot and freeze the resulting codebook version before
   opening any formal round. This pilot is complete and the frozen version is
   `CODEBOOK_REV1.md`.

The pilot is a codebook-development exercise, not an estimate of transition
frequencies. Its planned size was 20 stage rows, but the only eligible machine-
labelled Debate W→C item contributes three stages, so the feasible total is 18.

## Step 2 — Formal blind review

Open the four files in numerical order. Finish, save and close one round before
opening the next.

1. `final_transition_endorsement_round_1.xlsx`
2. `final_transition_endorsement_round_2.xlsx`
3. `final_transition_endorsement_round_3.xlsx`
4. `final_transition_endorsement_round_4.xlsx`

For every row:

- judge Discovery first and Endorsement second;
- do not infer one axis from the other;
- do not compare the question with remembered outputs from earlier rounds;
- use `U` only for genuine ambiguity;
- do not open `round_assignment_key.jsonl`, `final_transition_audit_key.jsonl`,
  `item_sample_160.jsonl` or the machine-labelled reports.

Rounds 1–3 are complete and remain frozen under `CODEBOOK_REV1.md`,
`CODEBOOK_REV2.md` and `CODEBOOK_REV3.md`. Round 4 uses `CODEBOOK_REV4.md`.
Revisions are prospective and do not alter earlier source labels or reason
codes.

Rev.4 adds `contentless_option_reference` for option labels without recoverable
answer content and clarifies that truncation produces U only when it interrupts
an answer-bearing statement whose content cannot be recovered. For cross-round
reason summaries, retain the raw reason and add a separate
`harmonized_reason_rev4` field.

After Round 4, review its `Rev.4 Final Check` sheet before unblinding.

Completion gate for every round:

- 105/105 rows show `Complete`;
- no blank label or reason-code cells remain;
- every `C` label has evidence;
- `Endorsement C but Discovery not C` is zero, or every exception has been
  explicitly re-audited and documented.

## Step 3 — Unblind only after all four rounds

Join completed rows to `round_assignment_key.jsonl` by `blind_stage_id`.

Compute, in this order:

1. intra-rater agreement on the 20 hidden duplicate pairs, separately for
   Discovery and Endorsement;
2. human–Mistral agreement and Cohen's kappa for each axis;
3. disagreement categories by architecture, stage position and machine stratum;
4. human transitions for Debate (`rev_A`, `rev_B` → final picker) and Sequential
   (last worker → final aggregator);
5. weighted population estimates using the frozen machine-stratum pool sizes;
6. sensitivity of conclusions to `U` handling and borderline codebook cases.

For a human transition category `t`, estimate its population count with

`N_hat(t) = sum_h N_h * y_h(t) / n_h`,

where `N_h` is the full machine-stratum pool size, `n_h` is the audited sample
size from that stratum, and `y_h(t)` is the number human-labelled as transition
`t`. Do not report raw proportions from the deliberately stratified 160-item
sample as population prevalence.

## Step 4 — Known judge-instability queue

Keep the 82 text-identical endorsement reuse conflicts outside the frozen
transition strata. After the formal codebook is frozen, adjudicate them as a
separate judge-reliability queue or report them as missing final endorsement
labels. Describe `82/2297 = 3.57%` as item-level conflict incidence, not judge
accuracy and not a pairwise disagreement rate.
