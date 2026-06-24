# Feature Specification: AI Trend Intelligence Platform

**Feature Branch**: `001-ai-trend-intelligence`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Design and implement a complete production-ready AI Trend Intelligence Platform that automatically generates premium technology research reports — discovering trending technologies, collecting and validating information from multiple sources, analyzing them with multiple AI agents, and producing premium Markdown and PDF reports stored as historical intelligence. Runs locally via Docker and n8n."

## Clarifications

### Session 2026-06-24

- Q: Acceptable time budget for one full report run (synchronous vs. background job)? → A: Run as a tracked background job optimized for speed; prioritize accuracy and built-in error detection. By default a single configurable OpenRouter model is shared across all agent roles (still independently overridable per role).
- Q: How should the system decide that two discovered entries are the same tool? → A: Normalized + fuzzy matching (name normalization plus similarity scoring and URL/domain matching).
- Q: Which dimensions feed each tool's ranking score? → A: All four — popularity signals, momentum/growth rate, technical merit, and source credibility & breadth.
- Q: When the Quality Reviewer Agent flags problems, what happens? → A: Bounded auto-revise then re-review loop — reviewer feedback triggers a Report Writer revision, capped at a maximum number of attempts, then the report is finalized.

## User Scenarios & Testing *(mandatory)*

<!--
  User stories are prioritized as independently testable journeys.
  Each delivers a viable slice of value on its own.
-->

### User Story 1 - Automated End-to-End Report Generation (Priority: P1)

A research operator wants a premium technology research report produced automatically without manual writing. They trigger a run (or wait for the scheduled trigger); the platform discovers trending technologies, analyzes them, and delivers a polished, professionally formatted PDF report along with its Markdown source. The operator opens the PDF and finds it indistinguishable in quality from a paid industry analyst report.

**Why this priority**: This is the core product promise and the minimum viable product. Even with a single discovery source and a reduced agent set, an operator who can press "run" and receive a premium report has received the central value. Everything else deepens or broadens this loop.

**Independent Test**: Trigger a single report run end-to-end and confirm a complete PDF report (with cover page, executive summary, table of contents, trend analysis, tool profiles, rankings, recommendations, and conclusions) plus its Markdown source are produced and saved, with no manual authoring required.

**Acceptance Scenarios**:

1. **Given** the platform is configured and running, **When** the operator triggers a report run, **Then** a complete premium PDF report and its Markdown source are generated and stored within the expected time window.
2. **Given** a report run has completed, **When** the operator opens the PDF, **Then** it contains all required sections in order: cover page, executive summary, table of contents, trend analysis, tool profiles, rankings, recommendations, and conclusions.
3. **Given** a report run is in progress, **When** any single step fails, **Then** the run records the failure with a clear reason and does not produce a partial report presented as complete.

---

### User Story 2 - Multi-Source Discovery & Validation (Priority: P2)

The operator wants reports to reflect what is genuinely trending across the technology ecosystem, not a single feed. The platform discovers candidate tools and technologies from multiple sources, removes duplicates, filters out low-quality or unverifiable items, and confirms each item is genuinely popular before it reaches analysis.

**Why this priority**: Breadth and trustworthiness of inputs are what separate a credible intelligence report from a noisy aggregation. This directly determines whether the report's conclusions can be trusted, but it builds on the P1 loop rather than being independently valuable without it.

**Independent Test**: Run discovery against the configured sources and confirm the output is a deduplicated, validated list of trending tools where each entry traces back to at least one verifiable source and meets the configured popularity threshold.

**Acceptance Scenarios**:

1. **Given** multiple discovery sources are configured, **When** discovery runs, **Then** candidate tools are collected from each available source and combined into a single candidate set.
2. **Given** the same tool appears in more than one source, **When** validation runs, **Then** it appears only once in the validated list with its sources merged.
3. **Given** a candidate that fails quality, popularity, or source-verification checks, **When** validation runs, **Then** it is excluded from the validated list and the exclusion reason is recorded.
4. **Given** one discovery source is unavailable, **When** discovery runs, **Then** the run continues using the remaining sources and records which source was skipped.

---

### User Story 3 - Multi-Agent Deep Analysis & Ranking (Priority: P3)

The operator wants each validated tool examined from several expert angles — what it is, why it is trending, its technical strengths and weaknesses, how it compares to competitors, and an objective score — so the report carries analytical depth rather than surface summaries.

**Why this priority**: This is what makes the report "premium" rather than a list. It depends on having a validated set of tools (P2) and a working report pipeline (P1), so it is layered on top.

**Independent Test**: Feed a validated tool through the analysis stage and confirm each analytical perspective (research summary, trend rationale, technical evaluation, competitor comparison, and numeric score) is produced and attached to that tool.

**Acceptance Scenarios**:

1. **Given** a validated tool, **When** analysis runs, **Then** a research summary, trend rationale, technical strengths/weaknesses, competitor comparison, and a numeric ranking score are produced for it.
2. **Given** all analyzed tools, **When** ranking runs, **Then** tools are ordered by a consistent, reproducible scoring method and the score components are recorded.
3. **Given** the analyzed and ranked tools, **When** the report is assembled, **Then** an independent quality review evaluates the draft and flags issues before the report is finalized.
4. **Given** an AI analysis step fails for one tool, **When** the run continues, **Then** the failure is isolated to that tool and does not abort analysis of the others.

---

### User Story 4 - Historical Intelligence & Trend Evolution (Priority: P4)

The operator wants every report, ranking, and tool profile retained over time so they can see how trends evolve, when tools first appeared, how rankings shift between reports, and compare any two reports.

**Why this priority**: Historical comparison turns a series of one-off reports into an intelligence asset. It is highly valuable but only meaningful once reports are being produced regularly (P1–P3).

**Independent Test**: Produce two reports on different dates and confirm both are retained, each tool's appearance history is queryable, and the change in a tool's ranking between the two reports can be retrieved.

**Acceptance Scenarios**:

1. **Given** a completed report, **When** it is finalized, **Then** the report, its rankings, and its tool profiles are persisted and retrievable later.
2. **Given** two reports from different dates, **When** the operator compares them, **Then** the platform shows which tools are new, which dropped off, and how rankings changed.
3. **Given** a specific tool, **When** the operator views its history, **Then** every report in which it appeared and its score in each are shown.

---

### User Story 5 - Configurable Models & Future Expansion (Priority: P5)

The operator wants to change which AI model powers each agent, adjust thresholds, and add new discovery sources or report sections later without re-architecting the platform.

**Why this priority**: Configurability protects the investment as models, costs, and sources change, but the platform delivers value before this flexibility is exercised.

**Independent Test**: Change the configured model for an agent and add a new discovery source through configuration, then run a report and confirm the new model and source are used without code changes to unrelated components.

**Acceptance Scenarios**:

1. **Given** a configured model assignment for an agent, **When** the operator changes it, **Then** subsequent runs use the new model without altering other agents.
2. **Given** a new discovery source definition, **When** it is added through configuration, **Then** it participates in discovery without changes to validation or analysis logic.
3. **Given** configurable thresholds (popularity, number of tools per report), **When** the operator adjusts them, **Then** subsequent runs honor the new values.

---

### Edge Cases

- **No tools discovered**: When discovery returns nothing (all sources empty or unavailable), the run ends with a clear "no qualifying trends found" outcome rather than producing an empty report presented as complete.
- **All candidates fail validation**: When every discovered candidate is filtered out, the run records why and does not proceed to analysis with an empty set.
- **AI provider unavailable or rate-limited**: When the AI provider cannot be reached or rejects requests, affected steps retry within limits and, if still failing, the run is marked failed with a clear reason rather than hanging indefinitely.
- **Partial agent success**: When some analysis perspectives succeed and others fail for a tool, the report either includes the tool with clearly marked gaps or excludes it per the configured policy — never silently presenting incomplete analysis as complete.
- **Duplicate near-matches**: When two entries refer to the same tool under slightly different names, deduplication treats them as one.
- **PDF generation failure**: When the Markdown report is produced but PDF rendering fails, the Markdown is retained and the run reports the PDF failure rather than losing all output.
- **Long-running source**: When a single source is slow, it does not block the entire run beyond a bounded wait.
- **Re-run on the same day**: When a report is triggered while a recent one exists, the platform produces a distinct, separately stored report rather than overwriting prior history.

## Requirements *(mandatory)*

### Functional Requirements

**Discovery**

- **FR-001**: System MUST discover candidate trending tools and technologies from multiple independent sources within a single run.
- **FR-002**: System MUST continue a run using remaining sources when one or more sources are unavailable, recording which sources were skipped.
- **FR-003**: System MUST capture, for each discovered candidate, the source(s) it came from and a reference back to the originating item.

**Validation**

- **FR-004**: System MUST merge candidates that refer to the same tool into a single entry, preserving all contributing sources. Sameness MUST be determined by normalized + fuzzy matching: name normalization (case, spacing, punctuation, common suffixes such as ".ai"/".io"/"-app"), similarity scoring above a configurable threshold, and matching of canonical URL/domain.
- **FR-005**: System MUST exclude candidates that fail quality, popularity, or source-verification checks, and MUST record the reason for each exclusion.
- **FR-006**: System MUST apply a configurable popularity threshold when deciding whether a candidate qualifies.

**AI Analysis**

- **FR-007**: System MUST produce, for each validated tool, a research summary, a trend rationale (why it is trending), a technical evaluation of strengths and weaknesses, and a comparison against competitors.
- **FR-008**: System MUST compute a numeric ranking score for each validated tool using a consistent, reproducible, versioned method that combines four dimensions: (1) popularity signals (e.g., stars, upvotes, mentions), (2) momentum/growth rate (rate of change in popularity, not just absolute counts), (3) technical merit (capability, maturity, differentiation), and (4) source credibility & breadth (number and reputation of independent sources). System MUST retain the per-dimension components that contributed to each score.
- **FR-009**: System MUST order tools in the report by their ranking score.
- **FR-010**: System MUST perform an automated quality review of the assembled report before finalization. When the review flags problems, the system MUST trigger a bounded auto-revision loop — the Report Writer revises the flagged content and the reviewer re-evaluates — repeating up to a configurable maximum number of attempts, after which the report is finalized with any unresolved review notes recorded.
- **FR-011**: System MUST isolate failures of an individual analysis step to the affected tool so that analysis of other tools continues.

**Report Generation**

- **FR-012**: System MUST generate a report in a structured text (Markdown) form and retain it as the report's source.
- **FR-013**: System MUST generate a premium PDF report that includes, in order: cover page, executive summary, table of contents, trend analysis, tool profiles, rankings, recommendations, and conclusions.
- **FR-014**: System MUST retain the Markdown report even when PDF generation fails, and MUST surface the PDF failure.

**Orchestration**

- **FR-015**: System MUST run the full pipeline — discovery, validation, analysis dispatch, output aggregation, report generation, PDF export, and storage — as a single orchestrated workflow executed as a **tracked background job** (asynchronous), so that long-running AI analysis does not block the trigger and progress can be observed.
- **FR-016**: System MUST support both scheduled automatic triggering and on-demand manual triggering of a report run.
- **FR-017**: System MUST record the status and outcome of each run (succeeded, failed, partial) and the status of each individual step, with enough detail to diagnose failures and detect errors as early as the step in which they occur.
- **FR-017a**: System MUST use a single configurable AI model (via the OpenRouter API key) shared across all agent roles by default, while still allowing the model for any individual agent role to be overridden independently (see FR-022). Analysis MUST prioritize output accuracy, and the system MUST validate each agent's output for completeness/format and flag or retry malformed results rather than passing them downstream.

**Historical Intelligence**

- **FR-018**: System MUST persist each finalized report, its rankings, and its tool profiles for later retrieval.
- **FR-019**: System MUST retain the appearance history of each tool across reports, including its score in each report.
- **FR-020**: System MUST allow comparison of two reports, identifying newly appearing tools, dropped tools, and ranking changes.
- **FR-021**: System MUST store each report run as distinct history rather than overwriting prior reports.

**Configuration & Expansion**

- **FR-022**: System MUST allow the AI model used by each agent to be configured independently without changing other agents.
- **FR-023**: System MUST allow new discovery sources to be added through configuration without changes to validation or analysis logic.
- **FR-024**: System MUST allow operational thresholds — at minimum popularity threshold and number of tools per report — to be configured.

**Operational Integrity**

- **FR-025**: System MUST retry transient AI-provider and network failures within a bounded limit and fail the run with a clear reason if still unsuccessful, rather than hanging.
- **FR-026**: System MUST end a run with a clear "no qualifying trends found" outcome when discovery or validation yields no qualifying tools, rather than producing an empty report presented as complete.
- **FR-027**: System MUST protect configured secrets (such as third-party API credentials) so they are not exposed in reports, logs, or stored output.

### Key Entities *(include if feature involves data)*

- **Discovery Source**: A configured origin of trending candidates (e.g., a community site, code-hosting trend feed, news aggregator, blog feed). Attributes: identifier, type, enabled state, configuration. Relationships: produces many Candidates.
- **Candidate**: A raw discovered item before validation. Attributes: name, originating source reference(s), raw signals (e.g., popularity indicators), discovery timestamp. Relationships: may merge into one validated Tool.
- **Tool**: A validated, deduplicated technology entity tracked over time. Attributes: canonical name, category, first-seen date, merged source references. Relationships: has many Tool Profiles (one per report), appears in many Reports.
- **Tool Profile**: The per-report analytical record for a tool. Attributes: research summary, trend rationale, technical strengths/weaknesses, competitor comparison, ranking score and score components. Relationships: belongs to one Report and one Tool.
- **Ranking**: The ordered scoring of tools within a report. Attributes: ordered tool references, score per tool, scoring-method version. Relationships: belongs to one Report.
- **Report**: A finalized intelligence deliverable. Attributes: title, generation date, status (succeeded/failed/partial), Markdown source reference, PDF reference, included sections. Relationships: contains many Tool Profiles and one Ranking.
- **Run**: A single execution of the pipeline. Attributes: trigger type (scheduled/manual), start/end time, status, per-step outcomes, skipped sources, failure reasons. Relationships: produces at most one Report.
- **Agent Configuration**: The configurable assignment of an AI model and parameters to each analytical agent role. Attributes: agent role, assigned model, parameters. Relationships: used by Runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can obtain a complete premium report (PDF plus Markdown source) from a single trigger with no manual authoring at any step.
- **SC-002**: A scheduled run completes end-to-end and produces a stored report without any human intervention.
- **SC-003**: Every finalized PDF report contains all eight required sections in the correct order, verified across at least 5 consecutive reports.
- **SC-004**: At least 95% of tools that reach the report carry all required analytical perspectives (research summary, trend rationale, technical evaluation, competitor comparison, and score).
- **SC-005**: No tool appears more than once in a finalized report (zero duplicates across the validated set).
- **SC-006**: 100% of tools in a finalized report trace back to at least one verifiable source and meet the configured popularity threshold.
- **SC-007**: When a single discovery source or a single tool's analysis fails, the overall run still completes and produces a report at least 90% of the time.
- **SC-008**: Two reports from different dates can be compared to show new tools, dropped tools, and ranking changes within seconds of the request.
- **SC-009**: An operator can change which AI model an agent uses and add a new discovery source entirely through configuration, with the change taking effect on the next run and no modification to unrelated components.
- **SC-010**: A run that cannot produce a valid report (no qualifying trends, or unrecoverable provider failure) ends in a clearly reported failure/empty outcome 100% of the time, never a silent partial result presented as complete.
- **SC-011**: Configured secrets never appear in any generated report, stored output, or operator-visible log.
- **SC-012**: Every agent output that is malformed or incomplete is detected and either retried or flagged before it reaches the report — zero malformed agent outputs are silently incorporated into a finalized report.
- **SC-013**: When a run fails, the operator can identify the specific failing step from the recorded run status without inspecting raw provider responses.

## Assumptions

- **Deployment model**: The platform runs locally as a self-hosted, single-operator system (not a multi-tenant public service). Multi-user accounts, public sign-up, and per-user access control are out of scope for the first version. *(Derived from "must run locally using Docker and n8n.")*
- **Trigger cadence**: In the absence of a specified schedule, a weekly automatic run is assumed as the default, with on-demand manual triggering always available. Cadence is configurable.
- **Report breadth**: In the absence of a specified count, each report covers a configurable top set of tools (default in the range of 10–20) selected by ranking score.
- **Distribution**: Reports are delivered by being stored locally and made retrievable; external delivery channels (email, messaging, web portal for external readers) are out of scope for the first version but the storage model should not preclude adding them.
- **AI provider**: A single configurable AI gateway (OpenRouter, accessed via API key) fronts multiple model providers. By default one model is shared across all agent roles, optimized for accuracy and speed; each agent role's model remains independently overridable as needs evolve.
- **Execution model**: A report run executes as an asynchronous, tracked background job rather than a blocking synchronous call, so multi-agent analysis can prioritize accuracy without trigger-side timeouts while still surfacing per-step progress and errors quickly. No fixed wall-clock SLA is fixed by this spec; speed is optimized subject to accuracy.
- **Source access**: Where a source requires credentials or has rate limits, valid credentials and acceptable-use compliance are assumed to be provided by the operator via configuration.
- **Content rights**: Collected source material is used for internal analysis and summarization; respecting each source's terms of use and robots/crawl policies is assumed to be an operational responsibility configured per source.
- **Language**: Reports are produced in English for the first version.
- **Scoring method**: A consistent, documented scoring formula exists and is versioned; its exact weighting is a configuration/planning detail, not fixed by this specification.

## Out of Scope (First Version)

- Multi-tenant access, public user accounts, and role-based permissions.
- External delivery channels (email/Slack/web portal for outside readers).
- Real-time/streaming trend monitoring (runs are batch/scheduled).
- Non-English report generation.
- Monetization, paywalling, or subscriber management.
