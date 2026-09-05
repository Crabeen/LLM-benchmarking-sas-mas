# Discovery-v2 Residual Disagreement Adjudication

This audit applies the user-defined semantic-discovery rule to the 20 rows on
which the dual-label Mistral judge disagreed with the first adjudicated labels.

## Decisions

| blind_id | prior human discovery | Mistral discovery | final discovery adjudication | rationale |
|---|---|---|---|---|
| STG-0004 | incorrect | correct | **incorrect** | Sweden is asserted only as birthplace and explicitly contrasted with the claimed American nationality. |
| STG-0005 | correct | incorrect | **correct** | Mario Andretti is present as a direct, readable answer; the judge incorrectly selected Phoenix as evidence. |
| STG-0018 | incorrect | correct | **incorrect** | The stage contains 1932 and geological dates, but never 1930. |
| STG-0023 | incorrect | correct | **correct** | “The Kingdom of Saudi Arabia was founded in 1932” is a readable answer-bearing sentence relevant to the intended region-creation chain. |
| STG-0040 | incorrect | correct | **incorrect** | The sentence locates Columbia itself in Richland County; it does not locate the requested bordering city. |
| STG-0043 | correct | incorrect | **correct** | Chinese is a valid semantic nationality answer for the Qing emperor despite the benchmark's dynasty-form reference. |
| STG-0055 | incorrect | correct | **incorrect** | Louis Philippe II occurs only inside an explicit rejection; no sentence asserts him as the father-in-law. |
| STG-0059 | incorrect | correct | **incorrect** | Madhavrao Scindia never appears, and “a member of the Scindia family” is insufficient. |
| STG-0071 | incorrect | correct | **incorrect** | London is attached to the burial site while the death location is explicitly left unknown. |
| STG-0083 | incorrect | correct | **incorrect** | Richland County is mentioned as Columbia's county/neighbour, not as the county containing the incorrectly proposed Darlington. |
| STG-0125 | correct | incorrect | **correct** | The stage explicitly states that Springfield became Illinois's capital in 1839 before the later rejection. |
| STG-0129 | incorrect | correct | **correct** | “Forest Acres is in Richland County” supplies the correct city–county relation before later confused reasoning. |
| STG-0152 | incorrect | correct | **incorrect** | London is only the burial-site location; the death place remains unasserted. |
| STG-0157 | correct | incorrect | **correct** | The stage explicitly states San Diego is third-largest and maps both Papa Roach and Veoh to California/San Diego. |
| STG-0162 | incorrect | correct | **incorrect** | It names the earlier-born director but never maps that director to the requested film. |
| STG-0171 | correct | incorrect | **correct** | The sentence saying the Restored Toungoo Dynasty defeated the Portuguese supplies the required defeat relation. |
| STG-0177 | incorrect | correct | **incorrect** | It compares directors but never maps the later-born director to Saturn in Opposition. |
| STG-0180 | incorrect | correct | **incorrect** | The stage contains only 1932; the gold year 1930 is absent. |
| STG-0183 | incorrect | correct | **incorrect** | It compares directors but never maps Christine Pascal to the requested film. |
| STG-0192 | incorrect | correct | **incorrect** | The stage contains only 1932; the gold year 1930 is absent. |

## Main failure pattern

The residual false positives are not merely generous semantic matching. Several
rows contain fabricated `discovery_evidence` that is absent from the stage text
(for example STG-0005, STG-0055, STG-0071, STG-0083 and STG-0129). Before
full-scale use, the pipeline should deterministically verify that the returned
evidence is actually grounded in the stage output and route ungrounded evidence
to review or retry.
