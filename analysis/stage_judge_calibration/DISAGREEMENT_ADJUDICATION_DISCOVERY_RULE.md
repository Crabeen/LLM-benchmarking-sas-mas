# Disagreement Adjudication — Semantic Discovery Rule

## User-defined rule

A stage is `correct` when the gold answer occurs in a readable,
understandable sentence whose relation fits the question. If a later sentence
overturns the gold answer but that overturning statement does not fit the
question, a human may ignore the overturning statement. This is therefore a
semantic **discovery** label, not a final-answer endorsement label.

Incidental string occurrence is still insufficient: a place mentioned only as
a burial site, neighbouring county, language adjective, or location where a
person grew up does not answer a birthplace/death-place/county question.

## Decisions

| blind_id | human | Mistral | discovery adjudication | rationale under the discovery rule |
|---|---|---|---|---|
| STG-0004 | incorrect | correct | **incorrect** | Sweden appears only as birthplace and is explicitly contrasted with the claimed nationality American. |
| STG-0005 | correct | incorrect | **correct** | “Mario Andretti” is a readable direct answer to who won the race. |
| STG-0006 | correct | incorrect | **incorrect** | Richland County never appears before truncation. |
| STG-0008 | correct | incorrect | **correct** | The text says Yesugei was likely born in the Khamag Mongol region. |
| STG-0010 | correct | incorrect | **incorrect** | Only South Carolina appears; the requested county is absent. |
| STG-0026 | correct | incorrect | **incorrect** | London is absent; Westminster Abbey is mentioned only as a burial site. |
| STG-0030 | incorrect | correct | **correct** | “The correct answer for the embassy is Paraguay” directly fits the where-question. |
| STG-0041 | correct | incorrect | **correct** | British/United Kingdom is asserted as the father's country-level identity. |
| STG-0044 | incorrect | correct | **correct** | The sentence “It produced 75% of the world's teak” contains the complete gold fact and fits the product question. |
| STG-0050 | correct | incorrect | **incorrect** | Hinkins's dates alone do not state or establish who lived longer because Harpur is never compared. |
| STG-0060 | incorrect | correct | **correct** | The text clearly identifies East Germany (GDR) as the country with the Deutsche Grenzpolizei; the later FRG resolution is the faulty overturn. |
| STG-0064 | incorrect | correct | **correct** | It explicitly states that San Diego is the third-largest urban area. |
| STG-0069 | correct | incorrect | **correct** | The sentence linking “Mranma” to 1235 is readable and relevant to the name-history question; the later 1989 answer is the overturn. |
| STG-0070 | correct | incorrect | **incorrect** | “French” modifies noble names; no sentence says the wife was born in France/French territory. |
| STG-0071 | correct | incorrect | **incorrect** | London never appears; a burial site is not a death-place answer. |
| STG-0089 | correct | incorrect | **correct** | The text says Forest Acres is in Richland County, the correct city–county relation; the later Darlington answer is the faulty overturn. |
| STG-0092 | correct | incorrect | **incorrect** | Athens never appears; the only proposed birthplace is Corfu. |
| STG-0094 | incorrect | correct | **correct** | The text states that Confederate General John Bell Hood ordered Atlanta's destruction. |
| STG-0095 | correct | incorrect | **correct** | The death-date discussion explicitly presents 662 as a candidate date before later dismissing it. |
| STG-0098 | correct | incorrect | **incorrect** | Wittenberg is supplied, but Saxony-Anhalt never appears. |
| STG-0116 | incorrect | correct | **incorrect** | The film Dodging the Dole is absent and the two named directors are not mapped back to the films. |
| STG-0123 | correct | incorrect | **incorrect** | “French” describes naming conventions, not the wife's birthplace. |
| STG-0124 | correct | incorrect | **correct** | The text explicitly says formal political unification occurred in 1932. |
| STG-0125 | correct | incorrect | **correct** | “Springfield, Illinois became the capitol of Illinois in 1839” is a complete sentence containing the intended answer; “not applicable” is the later overturn. |
| STG-0127 | correct | incorrect | **incorrect** | London is absent and the text only supplies the Westminster Abbey burial site. |
| STG-0132 | incorrect | correct | **incorrect** | Kingdom of Sicily appears only in a sentence distinguishing it from the asserted Italian answer. |
| STG-0133 | correct | incorrect | **correct** | The text directly states that Constantine I was born in Athens, Greece. |
| STG-0144 | correct | incorrect | **correct** | The sentence “Springfield, Illinois became the capitol of Illinois in 1839” contains the intended answer despite the later objection. |
| STG-0152 | correct | incorrect | **incorrect** | London is asserted as the burial site's location, while the text explicitly does not connect it to the place of death. |
| STG-0155 | correct | incorrect | **correct** | The parenthetical explicitly states that Scotto died in Los Angeles; the later “unknown” conclusion can be ignored under the discovery rule. |
| STG-0157 | correct | incorrect | **correct** | It explicitly states that San Diego is the third-largest urban area before introducing a conflicting fourth-place claim. |
| STG-0160 | correct | incorrect | **correct** | It states that Yugoslavia used “Slavs” in its anthem during 1943–1992, which is the required country–date relation. |
| STG-0161 | correct | incorrect | **correct** | The death-date sentence explicitly includes 662 before the later “before 679” preference. |
| STG-0170 | incorrect | correct | **incorrect** | Richland County is mentioned only as the county bordering Lexington; the text answers Lexington County. |
| STG-0171 | correct | incorrect | **correct** | “The Restored Toungoo Dynasty in Myanmar defeated the Portuguese in 1613” provides the required defeat relation. |
| STG-0176 | correct | incorrect | **incorrect** | Richland County appears only as the place Sumter allegedly borders; no sentence places the requested city in Richland County. |
| STG-0180 | incorrect | correct | **incorrect** | The stage repeatedly supplies 1932; 1930 occurs only in the judge's extracted field, not in the stage text. |
| STG-0182 | correct | incorrect | **incorrect** | “English noblewoman” is a nationality description and the same sentence says the birthplace is unknown. |
| STG-0196 | correct | incorrect | **incorrect** | Paris appears only as the metropolitan reference for where the director grew up; the asserted birthplace answer is France. |

## Summary of label changes

- Discovery-correct disagreements: 20.
- Discovery-incorrect disagreements: 19.
- Change 14 original human labels from `correct` to `incorrect`.
- Change 5 original human labels from `incorrect` to `correct`.
- If the 161 agreement rows remain unchanged, the resulting human label balance
  is 115 `correct` and 85 `incorrect`.

## Provisional Mistral result

Assuming the 161 original agreement rows remain unchanged, Mistral's confusion
matrix becomes TP=100, TN=80, FP=5, FN=15. This corresponds to accuracy 0.900,
precision 0.952, recall 0.870, F1 0.909, specificity 0.941, and Cohen's kappa
about 0.798.

This rule changes the target construct. Mistral's remaining false negatives are
mostly cases where a correct fact is mentioned and later rejected. That is a
problem for a semantic-discovery judge, even if the same behaviour would be
reasonable for a final-answer-correctness judge.
