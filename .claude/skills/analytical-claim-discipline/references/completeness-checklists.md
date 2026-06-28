# Completeness checklists by domain

The SKILL.md's "check the claims as a set" step requires naming what a complete
answer needs and flagging what is missing. The missing claims are domain-specific.
Read the row matching the claim's domain; if none matches, derive the missing-claims
list from first principles (what, if absent, would let the conclusion fail while the
present claims look fine).

## Quantitative finance / trading signals
A claim that a statistic implies a tradeable signal is usually missing:
- look-ahead: did the computation use only information available at each point in time
- half-life of mean reversion vs the intended holding horizon
- out-of-sample / walk-forward result, not in-sample only
- transaction costs / slippage vs the spread's typical excursion
- regime stability: does the relationship hold across sub-periods

## Backtest / strategy performance
A claim that a strategy "beat" a baseline is usually missing:
- statistical significance of the performance gap (is it inside the noise band)
- out-of-sample confirmation
- multiple-testing / selection: how many variants were tried before this one
- capacity: does the result survive realistic position sizing

## Causal / historical claims
A claim that X caused Y is usually missing:
- the counterfactual: cases where X occurred without Y
- confounders: a third factor driving both
- the competing mechanism the field already proposes
- temporal order and dose-response, where applicable

## Empirical measurement claims
A claim reporting a measured value is usually missing:
- the sample window and whether it is comparable across compared series
- the definition of the measured quantity (see methodological, below)
- measurement error / revision risk for the source series

## Methodological / definitional claims
A claim that a metric is meaningful or that a method is correct is usually missing:
- the operational definition (e.g. what "engagement" counts: DAU/MAU, sessions, feature use)
- robustness to a defensible alternative definition or sample choice
- whether the apparatus determines the result rather than the data

## Recommendation / normative claims
A claim that some action should be taken is usually missing:
- the objective / value under which the recommendation follows (and whether it is stated)
- who bears the cost and who gets the benefit
- the alternative actions not considered
