<!--
Sync Impact Report (temporary; remove before committing)
- Version change: 1.0.0-draft → 1.0.0
- Modified principles: none renamed. Wording tightened (lowercase "must"/"should" → MUST/SHOULD)
  in I, III, IV, XI.
- Added sections: Development Workflow (moved repository-conduct bullets out of Implementation
  Guidance); Governance now includes versioning policy and compliance review expectations.
- Removed sections: none. "Status: Draft pending review" line removed (draft is ratified).
- Ratification: 2026-10-18 (adopted via this amendment; previously "Pending").
- Follow-up TODOs: none.
-->

# Tyk Configuration Analytics Dashboard Constitution

## Purpose and Scope

This project provides an internal dashboard for understanding how Tyk is used across API
definitions stored in MongoDB. It is an analytics and visibility tool, not a Tyk management
interface. It analyzes all relevant Tyk API definitions regardless of the technology used by their
upstream services.

## Core Principles

### I. Read-Only by Design

The application MUST never create, update, or delete Tyk configurations or other source records.
MongoDB access MUST use read-only credentials and permissions wherever supported. Read-only
behavior MUST be reflected in both application design and database authorization; it MUST NOT
depend solely on the application choosing not to write.

### II. Useful, High-Level Tyk Analytics

The primary experience MUST make common questions about Tyk usage easy to answer without requiring
users to inspect individual definitions. The overview SHOULD include useful default metrics such
as API type distribution, authentication methods, organization breakdowns, rate-limiting
configuration, versions, paths, upstream targets, and relevant security or middleware settings.

Metrics MUST be based on the actual stored configuration and MUST NOT use fabricated, hardcoded,
or illustrative values as live results. Metric names and categories SHOULD be understandable to
the intended technical team.

### III. Curated Semantics, Traceable Results

The application MUST interpret known Tyk settings into clear, documented categories where doing so
is meaningful. It MUST also make it possible to inspect the relevant configuration details behind
a metric or API so users can understand and validate the result. It does not need to expose full
raw MongoDB documents.

The implementation MUST distinguish materially different states, such as a setting being enabled,
disabled, absent, or not understood. It MUST NOT silently treat missing or unrecognized values as
equivalent to a known value.

### IV. Focused Exploration, Not a Generic Database Browser

The dashboard MUST provide curated, high-level analytics and a guided explorer for supported Tyk
configuration categories. Users SHOULD be able to filter, group, compare, and drill down into
results through the UI without code changes for supported dimensions.

The application MUST NOT expose arbitrary MongoDB queries, unrestricted field exploration, or a
generic raw-document browser. New analytics categories SHOULD be introduced through deliberate
metric definitions rather than unrestricted inspection of every stored field.

### V. Transparent Analytics Coverage

The dashboard MUST make material analytics limitations visible. Where configuration contains
settings that the application does not understand or classify, it SHOULD provide a concise
coverage indicator or equivalent explanation. Unsupported settings MUST NOT be silently presented
as fully analyzed.

### VI. Fresh Data on Refresh

MongoDB is the source of truth for the initial implementation. Each explicit dashboard refresh
MUST fetch current API-definition data from the configured source; the application MUST NOT rely
on a periodic cache or a separate analytics database as the source of truth.

Within one refresh, charts, summaries, filters, and drill-down results SHOULD use the same
in-memory data snapshot where practical, so related views are consistent and interactions do not
trigger unnecessary repeated database reads. The application MUST handle connection failures and
incomplete reads clearly rather than presenting stale data as fresh.

### VII. Simple Python-First Implementation

The initial application SHOULD remain a small, maintainable Python application using Streamlit for
the dashboard and Plotly for interactive visualizations, unless repository constraints or
demonstrated requirements justify another choice. The application SHOULD support interactive
charts, cross-filtering where useful, and drill-down from aggregate statistics to the matching
APIs.

The project MUST avoid unnecessary services, frontend frameworks, microservices, analytics
databases, and abstractions. Future support for additional data sources is a design
consideration, but MUST NOT justify speculative multi-source infrastructure in the first version.

### VIII. Secure Internal Deployment

The application is intended for internal team use. Access restriction is provided by the
deployment environment's existing network controls; the application does not need to implement a
separate login or SSO flow unless requirements change.

Database connection details and credentials MUST be supplied through runtime configuration or an
approved secrets mechanism, never hardcoded or committed. Logs and errors MUST NOT expose
credentials or other secrets. The MongoDB connection MUST use the least privileges required for
analytics.

### IX. Reproducible Docker Packaging

The application MUST be packaged for deployment as a Docker container. The image build and runtime
configuration SHOULD be reproducible, application configuration MUST be external to the image, and
the container SHOULD run as a non-root user where practical. The project MUST NOT assume a
particular orchestrator, CI/CD system, or additional infrastructure unless required by the target
environment.

### X. Testing, Correctness, and Maintainability

Meaningful behavior MUST be covered by appropriate tests, especially metric classification,
aggregation, missing or unrecognized settings, and read-only data access. Tests SHOULD use
representative fixtures and MUST NOT require access to production data or production credentials.

The application MUST handle malformed or unexpected configuration safely, explain failures
clearly, and avoid silently dropping data in ways that mislead users. Dependencies and
abstractions SHOULD be kept to what the project needs. Changes MUST remain focused and follow
established repository conventions.

### XI. Justified Exceptions

These principles are firm defaults, not a reason to ignore real constraints. A deviation is
acceptable when a concrete requirement or constraint justifies it, the impact is understood, and
material trade-offs are documented. The smallest exception that solves the problem SHOULD be
preferred. Repeated conflicts MUST prompt an intentional constitution update rather than silent
non-compliance.

## Implementation Guidance

- Analyze all relevant Tyk API definitions in the configured MongoDB source, regardless of
  upstream application language or framework.
- Treat the initial deployment as a single-source application. Keep source access sufficiently
  separated from analytics logic to allow additional sources later, but do not build a generalized
  ingestion platform prematurely.
- Keep metric definitions explicit and maintainable. Use Tyk-aware semantic interpretation for
  known settings; do not infer more than the stored configuration supports.
- A chart or summary SHOULD be traceable to the API definitions included in its result. Clicking
  or selecting a chart category SHOULD make it possible to inspect the corresponding API list and
  relevant details.
- Example overview categories include API type, authentication, organization, rate limiting,
  versions, listen paths, upstream targets, CORS, access controls, and middleware. This list is an
  initial guide, not a claim that every category is available in every Tyk version or
  configuration.
- Do not log full API definitions by default. Avoid exposing sensitive configuration details in
  the UI beyond what is needed for the dashboard's intended internal audience.

## Development Workflow

- Do not commit, push, create pull requests, or publish changes unless explicitly authorized.
- Specifications, plans, tasks, and reviews SHOULD identify the applicable principles and explain
  any material deviation (see Principle XI).
- Changes MUST stay focused on the stated requirement and follow established repository
  conventions.

## Governance

This constitution governs engineering decisions for this repository. Requirements, design plans,
implementation tasks, and reviews SHOULD identify applicable principles and explain material
deviations.

**Amendments**: Changes to this constitution MUST be intentional and reviewed alongside their
rationale and impact on existing specifications, plans, tasks, tests, and documentation. A
documented exception applies only to its stated scope. If instructions conflict, follow applicable
higher-priority instructions and security requirements, and surface unresolved conflicts.

**Versioning**: The constitution uses semantic versioning. MAJOR for backward-incompatible
removals or redefinitions of principles or governance; MINOR for a new principle or section, or
materially expanded guidance; PATCH for clarifications, wording, and typo fixes.

**Compliance review**: Plans and reviews MUST check proposed work against the Core Principles.
Unresolved violations MUST be documented as justified exceptions or corrected before work is
considered complete.

**Version**: 1.0.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18
