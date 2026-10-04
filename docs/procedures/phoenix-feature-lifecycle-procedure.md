# Procedure: Phoenix Observability & Evaluation Feature Lifecycle

> **Procedural Standard** · Part of `CR-CLI-FEATURE-STANDARD-001`

## 1. Procedure Steps

1. **Service Registration**: Ensure `1n-phoenix` is declared in ATC compose and edge routing.
2. **CLI Command Binding**: Verify `hath0r phoenix status` and `hath0r phoenix evals` pass in CLI tests.
3. **Bot Integration**: Wire consumer services to wrap steps in `PhoenixTracer`.
4. **Benchmark Verification**: Execute evaluation suite and assert pass rates before PR submission.
