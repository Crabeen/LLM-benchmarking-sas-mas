# Intermediate-Stage Judge Disagreement Adjudication

## Scope and rule

This document reviews the 39 rows where the blind human label and
Mistral-24B stage-judge label disagreed. It does not overwrite the original
blind labels.

Adjudication rule: a stage is `correct` only when it supplies the answer to the
question at the required semantic granularity. Merely mentioning the reference
answer while rejecting it, giving it only as an unsupported alternative, or
ending with a conflicting answer is not sufficient. A concise answer, a clear
equivalent, or a correct answer accompanied only by an epistemic caveat is
sufficient.

## Decisions

| blind_id | human | Mistral | adjudicated | concise rationale |
|---|---|---|---|---|
| STG-0004 | incorrect | correct | **incorrect** | Final answer is American; the reference nationality is Sweden. |
| STG-0005 | correct | incorrect | **correct** | Explicitly supplies Mario Andretti; the preceding Phoenix is supporting context. |
| STG-0006 | correct | incorrect | **incorrect** | Truncates during a methodological critique and never names Richland County. |
| STG-0008 | correct | incorrect | **correct** | Gives the Khamag Mongol region as the likely birthplace; no competing birthplace is supplied. |
| STG-0010 | correct | incorrect | **incorrect** | Answers South Carolina, a state, instead of Richland County. |
| STG-0026 | correct | incorrect | **incorrect** | Concludes that the death location is unspecified and never answers London. |
| STG-0030 | incorrect | correct | **correct** | Paraguay is a direct semantic equivalent of “Alfredo Stroessner's Paraguay” for a where-question. |
| STG-0041 | correct | incorrect | **correct** | United Kingdom is a valid country-level realization of British. |
| STG-0044 | incorrect | correct | **correct** | The question asks for the wood product; teak answers it, while 75% is an unnecessary quantity. |
| STG-0050 | correct | incorrect | **incorrect** | Gives only Hinkins's dates and never compares him with Charles Harpur. |
| STG-0060 | incorrect | correct | **incorrect** | Final answer is FRG, not GDR; merely mentioning GDR earlier does not rescue it. |
| STG-0064 | incorrect | correct | **correct** | Explicitly states that San Diego is the third-largest urban area; later caveats do not replace it with another rank. |
| STG-0069 | correct | incorrect | **incorrect** | Endorses 1989 and treats 1235 as a different historical reference. |
| STG-0070 | correct | incorrect | **incorrect** | Concludes that the birthplace cannot be determined; it does not answer French. |
| STG-0071 | correct | incorrect | **incorrect** | Discusses a London burial site but explicitly refuses to infer the place of death. |
| STG-0089 | correct | incorrect | **incorrect** | Final answer is Darlington County rather than Richland County. |
| STG-0092 | correct | incorrect | **incorrect** | Supplies Corfu and says the context is insufficient; the reference is Athens. |
| STG-0094 | incorrect | correct | **correct** | Explicitly identifies Confederate General John Bell Hood as ordering the destruction. |
| STG-0095 | correct | incorrect | **incorrect** | Endorses “before 679” and dismisses 662 as a possible error. |
| STG-0098 | correct | incorrect | **incorrect** | Answers Wittenberg rather than the containing region, Saxony-Anhalt. |
| STG-0116 | incorrect | correct | **incorrect** | Compares two people without mapping the earlier-born director to the requested film. |
| STG-0123 | correct | incorrect | **incorrect** | Explicitly concludes that the birthplace cannot be determined. |
| STG-0124 | correct | incorrect | **correct** | Clearly states that formal unification occurred in 1932 before the output truncates. |
| STG-0125 | correct | incorrect | **incorrect** | Mentions 1839 only while rejecting the question and ends with “not applicable.” |
| STG-0127 | correct | incorrect | **incorrect** | Gives a burial site but states that the death location is unspecified. |
| STG-0132 | incorrect | correct | **incorrect** | Final answer is Italian, not Kingdom of Sicily; these are not equivalent historical nationalities. |
| STG-0133 | correct | incorrect | **correct** | Explicitly states, as historical knowledge, that Constantine I was born in Athens; the caveat concerns source availability, not a competing birthplace. |
| STG-0144 | correct | incorrect | **incorrect** | Mentions 1839 but concludes that Springfield never became North Carolina's capital. |
| STG-0152 | correct | incorrect | **incorrect** | Says Westminster Abbey is in London but explicitly says the death location is unconfirmed. |
| STG-0155 | correct | incorrect | **incorrect** | Mentions Los Angeles only as external knowledge and concludes that the answer is unknown. |
| STG-0157 | correct | incorrect | **incorrect** | Gives incompatible third- and fourth-place rankings and truncates before resolving them. |
| STG-0160 | correct | incorrect | **incorrect** | Misidentifies the unprepared country as Czechoslovakia; the correct Yugoslavia interval is only listed amid unresolved reasoning. |
| STG-0161 | correct | incorrect | **incorrect** | Endorses “before 679,” not 662. |
| STG-0170 | incorrect | correct | **incorrect** | Answers Lexington County rather than Richland County. |
| STG-0171 | correct | incorrect | **incorrect** | Explicitly denies the reference event instead of answering how the Portuguese were defeated. |
| STG-0176 | correct | incorrect | **incorrect** | Supplies Sumter, not Richland County, and does not answer at county granularity. |
| STG-0180 | incorrect | correct | **incorrect** | Repeatedly endorses 1932; the judge's extracted 1930 does not occur as the answer in the stage text. |
| STG-0182 | correct | incorrect | **incorrect** | Says the birthplace is unspecified; “English noblewoman” is not an asserted birthplace. |
| STG-0196 | correct | incorrect | **incorrect** | Answers France rather than Paris and discusses Meaux as where the director grew up. |

## Summary

- Keep the original human label for 11 rows.
- Change the original human label for 28 rows: 24 from `correct` to
  `incorrect`, and 4 from `incorrect` to `correct`.
- After these adjudications, the 200-row human class balance would be 104
  `correct` and 96 `incorrect`.
- Assuming the 161 original human–Mistral agreements are retained, Mistral's
  provisional confusion matrix becomes TP=99, TN=90, FP=6, FN=5.
- The resulting provisional accuracy is 0.945 and Cohen's kappa is about 0.890.

## Interpretation and limitation

The original 0.805 accuracy substantially understated Mistral agreement because
the first-pass human labels often treated lexical presence as semantic
correctness. The adjudicated result would support promotion of the judge, but it
is not yet a defensible final calibration: the same clarified rule should be
applied to at least a stratified audit of the 161 agreement rows. An LLM-assisted
adjudication should be confirmed by the human researcher before it replaces the
blind human gold labels.
