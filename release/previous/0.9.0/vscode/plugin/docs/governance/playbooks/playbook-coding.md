# Coding Playbook

## 1. Safe Types
Use safe types to ensure variables are managed, initialized, and never implicitly null or non-existent without checking. Have a class manage the underlying value to ensure once it is set or called, there is a valid state attached to it. This means we will be checking for `null`, as opposed to checking if it exists.

- **Safe String:** A string wrapper/class that is never null or non-existent.
- **Safe Number:** A number wrapper/class providing state guarantees.
- **Safe Array:** An array wrapper/class ensuring safe access and manipulation.

## 2. Architecture & Design
- **SOA Specifications:** Always build to Service-Oriented Architecture (SOA) specifications. Ensure services remain decoupled and independently deployable.
- **Dependency Injection:** Utilize Dependency Injection (DI) to maintain separation of concerns between your API, EDGE, and DB layers.
- **Immutability:** Prefer immutable data structures, especially when manipulating UI state or utilizing a `Safe Array`, to prevent unintended side effects.

## 3. Asynchronous Operations
- **Asynchronous Connections:** Always make connections asynchronous (ASync).
- **Error Handling & Fallbacks:** Always define standard ways to handle network timeouts, failed promises, and service unavailability (e.g., graceful degradation or circuit breakers).

## 4. Rule Adherence & Quality Gates
- **Canonical Rules:** Always adhere to canonical rules.
- **CLI Rules:** Always adhere to CLI rules (e.g., invoking `hath0r` CLI for connections, workflows, and missing capabilities).
- **Quality Gates:** Code must pass the mandatory SonarCloud Quality Gate before being merged. Do not attempt to bypass these automated checks.
