# Explaining the project in an interview

## A 90-second explanation

> I wanted to investigate where weak public-transport connections coincide with high economic need and households without a car. I studied all 1,015 LSOA neighbourhoods across Leeds, Bradford and Wakefield, using Leeds and Bradford as the main study and Wakefield as a comparison.
>
> I first downloaded and inspected official DfT, Census, deprivation and ONS geography data. That changed an important decision: the main DfT score covers several destination purposes, so I call it public-transport connectivity rather than employment accessibility. I also found an ambiguous Business label in the public-transport columns and did not silently rename it.
>
> I built a reproducible Python pipeline with checksum-pinned inputs, validated one-to-one geographic joins and DuckDB district summaries. I used households for the no-car denominator and economically active adults, including active students, for unemployment. The dashboard shows all three constituent indicators alongside a transparent review score.
>
> Wakefield had lower median connectivity than Leeds and Bradford. Only three neighbourhoods fell into all three adverse quartiles under my baseline, but the count changed from one to 24 across sensitivity choices. Better-connected neighbourhoods often had more households without cars, so overlapping disadvantage was not as simple as I might have expected.
>
> The result is a defensible shortlist for further investigation, not proof that transport causes unemployment or an automatic funding recommendation. My most important learning was that definitions, denominators and geography can matter more than fitting a complicated model.

Adapt this to what you have personally understood and verified. The project was developed with AI assistance: be prepared to explain, inspect and modify the code yourself. Do not claim every implementation decision or learning experience as yours until you can demonstrate it.

## Decisions and trade-offs to defend

| Decision | Why it helps | What it costs |
|---|---|---|
| All eligible LSOAs | Prevents selection of convenient examples | More acquisition and join checks; maps need care |
| Public-transport overall score | Relevant when studying car non-availability | It is broader than employment access and depends on a model |
| Income domain only | Clear economic-need concept; avoids transport-related IMD overlap | Does not represent every form of deprivation |
| Transparent percentile score | Different units become comparable and ties are explicit | Loses magnitude information and depends on the reference group |
| Separate three-tail intersection | Requires all three conditions | Can omit important areas narrowly outside a threshold |
| Coarse peer groups | Understandable similarity comparison without unjustified ML | Broad groups and unsupported areas; no causal identification |
| DuckDB aggregation | SQL is useful for auditable ratio-of-sums and weighting | Adds a small dependency; it is not used merely for decoration |
| Pin source bytes | Reproduces the reviewed evidence and detects changes | A publisher revision can require deliberate review |
| Defer bus routing | Completes a reliable, manageable core | Cannot answer departure-time-specific reachable-job questions |

## A five-minute demonstration

1. Open the dashboard with all districts and identify the different source years.
2. Switch between connectivity, no-car and income maps. Explain why map area is not population and why a grey peer polygon is not a zero score.
3. Filter Wakefield. Confirm 215 neighbourhoods and explain that the display filter does not redefine pooled percentile standings.
4. Compare the connectivity distributions. Explain the distinction between neighbourhood medians, population-weighted access means and household ratios.
5. Open the priority tab, show only the three-tail areas, then change the reference group or threshold. Explain why the composite and intersection can disagree.
6. Open the quality/source evidence, then the SQL query and one denominator test. Show how the notebook and reports arise from the same pipeline.

## Learning exercises

- Calculate one area's no-car and unemployment rates by hand from the original CSV and compare with the output.
- Explain each term in the percentile score, then change a weight and predict the effect before running it.
- Find an unsupported peer comparison and inspect its group size and district coverage.
- Trace one source-register URL through its checksum, reviewed source column and derived dashboard value.
- Rebuild in an empty data directory using the pinned files. Understand why a changed checksum is a reason to investigate.

## Questions you should be able to answer

1. What exactly does DfT's primary score measure, and why is it not employment-only access?
2. Why does no-car availability use a household denominator? Why does unemployment use economically active residents instead of all adults?
3. How did you establish complete district coverage and stop duplicate keys from multiplying rows?
4. Why did you choose income deprivation instead of the overall IMD score?
5. How can a neighbourhood have a high review score but fail the all-three-tail rule?
6. Why do pooled, within-district and main-study-reference comparisons answer different questions?
7. What does a scenario frequency mean, and why is it not a probability that an area needs intervention?
8. What changes when you use population weighting instead of treating each LSOA equally?
9. What do the peer groups adjust descriptively, and which differences remain?
10. Why might greater connectivity be associated with more no-car households? Which explanations can this project test, and which can it only suggest?
11. What uncertainty remains despite having no missing core indicators?
12. What additional data and routing method would you need to estimate reachable jobs for a particular shift time, and how would you validate it?
