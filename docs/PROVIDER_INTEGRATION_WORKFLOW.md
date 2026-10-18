# Provider Integration Workflow

This workflow governs adding a local or hosted language model to SciModel.
Each gate must pass before the next gate begins.

## Objective

Use a language model for request interpretation, planning, explanation, and
recommendations while keeping scientific computation deterministic, validated,
auditable, and independent of the language model.

## Non-negotiable boundaries

- The provider may propose plans but may not execute tools directly.
- Only registered tools may be called.
- Scientific algorithms remain outside the language model.
- Provider output must be structured and schema-validated.
- Invalid, unsafe, or incomplete plans must fail honestly.
- The deterministic planner remains an available fallback.
- Production code and scientific methods never change automatically from feedback.

## Gates

### Gate 0 — Baseline freeze

Record the current deterministic baseline:

- Test count and coverage
- Benchmark score
- Tool-selection behavior
- Scientific accuracy
- Runtime and memory
- Recommendation behavior

Exit condition: the baseline evaluation report is saved and reproducible.

### Gate 1 — Provider selection

Record:

- Provider and model name
- Model version or revision
- License and usage terms
- Runtime method
- Required RAM/VRAM/storage
- Privacy and network behavior
- Quantization, if applicable

No model is downloaded until this information is reviewed.

### Gate 2 — Provider adapter

Implement the provider behind `AssistantProvider`.

Required outputs:

- Provider name
- Provider version
- Structured plan
- Assumptions
- Missing-information questions
- Provider errors and timing

Exit condition: valid and invalid provider responses are tested.

### Gate 3 — Plan and permission validation

Validate:

- JSON structure
- Tool names
- Tool arguments
- Required verification steps
- Context permissions
- Approval requirements
- Secret redaction

Exit condition: the provider cannot invoke an unregistered or unauthorized tool.

### Gate 4 — Private benchmark

Run the provider against the same benchmark suite as the deterministic planner.
Measure:

- Plan correctness
- Tool selection
- Task completion
- Verification accuracy
- Error honesty
- Recommendation quality
- Latency and resource use

Exit condition: the provider meets the declared acceptance thresholds without
reducing scientific reliability.

### Gate 5 — Shadow mode

Run the provider beside the deterministic planner without allowing it to change
the authoritative result. Compare plans and recommendations.

Exit condition: disagreements are reviewable and no provider result is silently
treated as authoritative.

### Gate 6 — Limited activation

Enable the provider only for approved tasks and synthetic/public datasets.
Keep deterministic fallback and audit every provider decision.

Exit condition: a private human review approves the behavior.

### Gate 7 — Controlled improvement

Store reviewed corrections and outcomes. Use them to improve prompts, routing,
tools, or evaluation cases. Run regression tests before accepting changes.

Fine-tuning is considered only after enough reviewed examples exist and a held-
out evaluation set is protected from training.

## Current position

- Gate 0: baseline frozen at 78 tests, 85.63% coverage, and a benchmark score
  of 1.0.
- Gate 1: provider choice and machine requirements are intentionally not yet
  recorded; no model is downloaded.
- Gate 2: provider contract and controlled JSON-plan adapter are implemented
  and tested.
- Gates 3–7: pending provider selection and private evaluation.

## Immediate next action

Choose one provider candidate and record its hardware, license, runtime, and
privacy requirements. Then implement only that provider adapter and test it
against the existing deterministic benchmark.
