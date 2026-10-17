# SciModel — Phase 0 Scope Brief

**Status:** Draft — complete this brief before starting implementation  
**Owner:**  
**Reviewer:**  
**Date:**  

## Scientific problem

- **Scientific domain:** `[choose one domain]`
- **Research question:** `[what relationship, parameter, prediction, or behavior are we studying?]`
- **Target user:** `[who will run the workflow?]`
- **Why this problem matters:** `[practical or scientific motivation]`

## Data

- **Input file/source:** `[file or dataset name]`
- **Permission to use:** `[synthetic / public / permission confirmed / pending]`
- **Independent variables and units:** `[list]`
- **Outcome variable and units:** `[list]`
- **Number and structure of observations:** `[rows, repeats, batches, time ordering]`
- **Known data-quality issues:** `[missing values, duplicates, measurement limits, etc.]`
- **Expected data transformations:** `[none or list; no silent transformations]`

## Modeling plan

- **Baseline model:** `[model name and reason it is defensible]`
- **Optional comparison model:** `[leave empty if not needed]`
- **Model assumptions:** `[list assumptions that can be checked or reported]`
- **Constraints or physical rules:** `[units, bounds, conservation, monotonicity, etc.]`
- **Expected parameter/result behavior:** `[known values, signs, ranges, or qualitative behavior]`

## Reference analysis and acceptance criteria

Describe how an expert would inspect the data, choose the model, fit it, diagnose it, and interpret the result. Include the expected failure modes.

### Numerical acceptance

- **Known-answer values:** `[values or reference output]`
- **Allowed parameter error:** `[tolerance]`
- **Allowed prediction/error metric:** `[tolerance]`
- **Expected convergence behavior:** `[criteria]`
- **Runtime/memory expectation:** `[criteria]`

### Required report contents

- [ ] Input summary and data-quality warnings
- [ ] Model, assumptions, and configuration
- [ ] Parameter estimates/results and units
- [ ] Metrics and diagnostics
- [ ] Uncertainty, where justified
- [ ] Limitations and unsupported conclusions
- [ ] Reproduction instructions and software metadata

## Unsupported cases

List cases the first version must reject or clearly mark as unsupported:

- `[case]`

## Approval gate

Do not begin Phase 1 until the domain, dataset, model, reference analysis, and acceptance criteria are complete and reviewed.

- **Approved by:**  
- **Approval date:**  
- **Related issue/decision:**  
