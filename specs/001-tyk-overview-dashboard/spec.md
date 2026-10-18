# Feature Specification: Tyk Overview Dashboard

**Feature Branch**: `001-tyk-overview-dashboard`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "An overview dashboard showing API type, authentication, and organization breakdowns across all Tyk API definitions, with drill-down to the matching APIs"

## Clarifications

### Session 2026-10-18

- Q: Should the dashboard count inactive API definitions alongside active ones? → A: Count all definitions, offer active/inactive as a filter, and show the state on each API.
- Q: Should drill-down selections across dimensions combine? → A: Yes. Selections across API type, authentication, organization and active state combine (AND), and all breakdowns update to match.
- Q: How should organizations be labelled in the organization breakdown? → A: Organization names come from the source's separate organizations collection, matched to API definitions by organization identifier. An API whose organization is not recorded goes in "Not set"; one whose identifier has no matching organization shows the identifier under an "unmatched" label.
- Q: What are the Tyk API types? (correction) → A: Per Tyk's documentation and your guidance the types are REST (classic), REST (OpenAPI), GraphQL (proxy-only), Universal Data Graph (UDG), Federation, MCP, TCP and Streaming. TLS is not a type: it is a setting of a TCP API and is shown as a detail, not a category. This supersedes the GraphQL "mode" split and the TLS type in the previous entry.
- Q: What does "API type" mean? → A: A single API type dimension (superseding an earlier split into protocol kind and definition style). Every API has exactly one type; the type list is given in the entry above.
- Q: Should there be a "TCP APIs: TLS" filter? → A: No. Remove it. TLS stays visible only as a detail on each TCP API.
- Q: How should optional middleware be shown? (investigated in the local database: classic and OpenAPI definitions store it differently) → A: Two multi-value breakdowns, "Global middleware" (API-wide settings) and "Per-endpoint middleware" (settings attached to individual endpoints). An API counts once per middleware in each, so counts may exceed the total. Each middleware is a selectable category that filters the table, and classic and OpenAPI definitions map to the same names. This supersedes the earlier exclusion of middleware from scope.
- Q: Which database settings count as optional middleware? → A: Everything the database stores as an explicitly enabled optional setting, including settings that are not strictly middleware: strip listen path, override target and custom domain. Global ones go in the global breakdown, endpoint-level ones in the per-endpoint breakdown. Fields that are always present with empty values do not count.
- Q: Should the charts be pie charts instead of bars, and how should many-slice or overlapping breakdowns be handled? → A: API type, Active state and Organization become pie charts; Organization shows its top 8 plus an "Other" slice, and a selector still reaches every organization. Authentication, Global middleware and Per-endpoint middleware stay bar charts, because an API can count in several of their categories and shares of a whole would mislead. Clicking a slice or bar filters exactly as before.
- Q: How should the page be laid out, with the organization filter at the top? → A: Organization is a full-width multiselect directly under the summary, above the selection chips and the charts. The charts follow in two aligned rows of three equal-height charts: pies (API type, Active state, Organization) then bars (Authentication, Global middleware, Per-endpoint middleware), then the table. The Organization pie stays, and the multiselect replaces its separate "Find another" selector.
- Q: Should the Organization pie remain, and should Authentication be a pie? → A: The Organization pie is removed; organization is filtered only through the multiselect at the top. Authentication becomes a pie (a user decision; slices count APIs per method and may add up to more than the total, with the existing note). Row 1 is three equal pies (API type, Active state, Authentication); row 2 is the Global and Per-endpoint middleware bars, side by side at half width each. This supersedes the earlier Organization pie and the "two rows of three" layout.
- Q: What should stay visible in a smaller, sticky top bar? → A: One compact bar pinned to the top of the page while scrolling, in a single row: a small title, the Refresh button with "Data loaded at...", the Organization dropdown and "Clear all". The selection chips appear on a second thin line inside the bar only when something is selected. The summary numbers (total, active, inactive, unclassified) become one small line of text under the title that scrolls away with the page.
- Q: The sticky bar looks bad (white box, controls not next to each other): what changes? → A: The bar background MUST follow the active theme (no white box in dark mode), and the title, organization filter, Refresh and Clear all MUST sit in one row with the same top edge. The load time moves under the title. The UI is verified in a real browser in both themes (tests/ui).
- Q: Which authentication methods should the breakdown distinguish? → A: Derived from the local Tyk database rather than asked: none (keyless), API key (auth token), JWT, Basic, OAuth 2.0, OpenID Connect, mutual TLS and request signature checking, plus "not set" and "not understood". Classic and OpenAPI-based definitions store authentication differently, so both must be classified.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See how Tyk is used at a glance (Priority: P1)

A team member opens the dashboard and immediately sees summary breakdowns of all Tyk API definitions: how many APIs exist, how they are distributed by API type, by authentication method, and by organization. They do not need to open individual API definitions to answer common questions such as "how many of our APIs have no authentication?" or "which organization owns the most APIs?".

**Why this priority**: This is the core value of the product: high-level visibility into Tyk usage. Without it nothing else is useful.

**Independent Test**: Load the dashboard against a source containing a known set of API definitions and verify that the total count and each breakdown match the known data.

**Acceptance Scenarios**:

1. **Given** a source with API definitions of several types, **When** the user opens the dashboard, **Then** a total API count and a breakdown by API type is shown, and the category counts sum to the total.
2. **Given** API definitions using different authentication methods, **When** the user views the authentication breakdown, **Then** each method (and "no authentication") appears with its API count.
3. **Given** API definitions belonging to multiple organizations, **When** the user views the organization breakdown, **Then** each organization appears with its API count.
4. **Given** an API definition whose type, authentication, or organization is missing or not recognized, **When** the breakdowns are shown, **Then** it appears in a distinct "not set" or "not understood" category instead of being merged into a known category.

---

### User Story 2 - Drill down from a category to the matching APIs (Priority: P1)

A user selects a category in any breakdown (for example, one authentication method or one organization) and sees the list of API definitions that fall into it, along with the key configuration details that explain why each one was counted there.

**Why this priority**: Drill-down makes the numbers verifiable and actionable. A summary the user cannot trace back to specific APIs is not trustworthy.

**Independent Test**: Select each category in a breakdown and verify the listed APIs match exactly the count shown and the known data.

**Acceptance Scenarios**:

1. **Given** a breakdown showing N APIs in a category, **When** the user selects that category, **Then** exactly N matching APIs are listed.
2. **Given** a listed API, **When** the user inspects it, **Then** the relevant configuration details behind its API type, authentication, and organization classification are visible.
3. **Given** a drill-down list, **When** the user clears the selection, **Then** the dashboard returns to the full overview.
4. **Given** a category is already selected in one dimension, **When** the user selects a category in another dimension, **Then** only APIs matching both are listed and every breakdown reflects that combination.

---

### User Story 3 - Refresh to see current data and understand coverage (Priority: P2)

A user refreshes the dashboard to load the latest API definitions and sees when the data was loaded. The dashboard also indicates how much of the configuration it could classify, so the user knows the limits of what is shown.

**Why this priority**: Trust in the numbers depends on freshness and on knowing what was not analyzed, but the dashboard is already useful without it.

**Independent Test**: Change the source data, trigger a refresh, and verify the dashboard reflects the change and shows an updated load time and coverage indicator.

**Acceptance Scenarios**:

1. **Given** the source data has changed since the dashboard was loaded, **When** the user triggers a refresh, **Then** all breakdowns and drill-down lists reflect the current data.
2. **Given** some API definitions contain settings the dashboard does not classify, **When** the dashboard is shown, **Then** a concise coverage indicator states how many APIs have unclassified values.
3. **Given** the data source is unreachable or the read is incomplete, **When** the user opens or refreshes the dashboard, **Then** a clear error is shown and no stale data is presented as current.

---

### Edge Cases

- Combined selections match no APIs: the dashboard shows an explicit "no matching APIs" state and a way to clear selections.
- The source contains no API definitions: the dashboard shows an explicit empty state rather than blank or zero-filled charts.
- An API definition has several authentication methods enabled: it is counted in each applicable method, and the dashboard makes clear that categories may overlap.
- An API definition is malformed or missing expected fields: it is still counted, placed in a "not set" or "not understood" category, and does not break the dashboard.
- A very large number of organizations exist: the breakdown stays readable and all organizations remain reachable.
- The source is slow to respond: the user sees a loading indication rather than a frozen page.
- Credentials or connection details are wrong: the error message does not reveal secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show a total count of all Tyk API definitions in the configured source, including inactive ones.
- **FR-001a**: Users MUST be able to filter the overview and drill-down lists by active or inactive state, and the active/inactive state MUST be visible on each listed API.
- **FR-002**: The system MUST show a breakdown of API definitions by API type: REST (classic), REST (OpenAPI), GraphQL (proxy-only), Universal Data Graph (UDG), Federation, MCP, TCP and Streaming.
- **FR-002a**: TLS MUST NOT be an API type. Whether a TCP API uses TLS MUST be shown as a detail on that API. There is no separate TLS filter or breakdown.
- **FR-002b**: Each API definition MUST be assigned exactly one API type, so API type counts sum to the total. A type-related setting that is present but switched off (for example GraphQL disabled) MUST NOT cause an API to be counted under that type.
- **FR-002c**: An API definition that matches no known API type MUST appear under "not understood" and count toward the coverage indicator.
- **FR-003**: The system MUST show a breakdown of API definitions by authentication method (none, API key, JWT, Basic, OAuth 2.0, OpenID Connect, mutual TLS, request signature checking), including a category for APIs with no authentication.
- **FR-003a**: Authentication MUST be classified correctly for both classic and OpenAPI-based definitions, so the same method is counted in the same category regardless of definition style.
- **FR-004**: The system MUST show a breakdown of API definitions by organization, labelling each organization by the name stored in the source's organizations collection, matched via the organization identifier on the API definition.
- **FR-004a**: An API definition with no organization identifier MUST appear under "Not set". One whose identifier matches no stored organization MUST appear under its identifier with an "unmatched" label and MUST count toward the coverage indicator.
- **FR-005**: The system MUST distinguish enabled, disabled, absent, and unrecognized states and MUST NOT merge missing or unrecognized values into a known category.
- **FR-003b**: The system MUST show two breakdowns of optional middleware, "Global middleware" and "Per-endpoint middleware", for both classic and OpenAPI definitions. A middleware counts only when explicitly enabled, and this includes settings that are not strictly middleware (strip listen path, override target, custom domain), an API counts once per middleware, and the same middleware has the same name regardless of definition style.
- **FR-006c**: API type, active state and authentication MUST be shown as pie charts, and global and per-endpoint middleware as bar charts, because middleware has many categories. There is no organization chart: organization is shown only as the filter in FR-006d. Pie slices show counts, and authentication and middleware carry a note that counts may exceed the total when an API falls in several categories.
- **FR-006d**: The organization filter MUST be a multiselect listing every organization, part of the sticky top bar (FR-006e) above the charts. The charts MUST be laid out as a row of three equal-height pies (API type, active state, authentication) followed by a row of two equal-height bar charts, each half the page width.
- **FR-006e**: The title, refresh control with load time, organization filter and "Clear all" MUST be one compact row pinned to the top of the page while scrolling. The selection chips MUST appear on a second line inside that bar only when a selection exists. The summary figures MUST be one small line of text outside the bar that scrolls with the page. The bar MUST NOT cover the first chart or table row when the page is at the top, MUST use the active theme's background, and its controls MUST share one top edge.
- **FR-006**: Users MUST be able to select any category in any breakdown and see the list of matching API definitions.
- **FR-006a**: Selections in different dimensions (API type, authentication, organization, active state) MUST combine with AND, and all breakdowns and the total MUST update to reflect the combined selection.
- **FR-007**: The count shown for a category MUST equal the number of APIs listed when that category is selected, given any other active selections.
- **FR-008**: Users MUST be able to inspect, for each listed API, the configuration details relevant to its API type, authentication, and organization classification, without exposing the full raw stored document.
- **FR-009**: Users MUST be able to clear a selection and return to the full overview.
- **FR-010**: Every explicit refresh MUST load current data from the source, and the dashboard MUST display when the data was last loaded.
- **FR-011**: All breakdowns and drill-down lists shown for one refresh MUST be consistent with each other.
- **FR-012**: The system MUST display a coverage indicator stating how many API definitions contain settings that were not classified.
- **FR-013**: The system MUST show a clear error when the source is unreachable or the read is incomplete, and MUST NOT present previously loaded data as current in that case.
- **FR-014**: The system MUST show an explicit empty state when no API definitions exist.
- **FR-015**: The system MUST NOT modify any source data, and MUST NOT offer arbitrary queries or a generic raw-document browser.
- **FR-016**: The system MUST NOT display credentials or other secrets in the interface, errors, or logs.

### Key Entities *(include if feature involves data)*

- **API Definition**: A stored Tyk configuration for one API. Relevant attributes: name, identifier, active/inactive state, API type, authentication settings, owning organization.
- **API Type**: The kind of API a definition represents: REST (classic), REST (OpenAPI), GraphQL (proxy-only), Universal Data Graph (UDG: a GraphQL API composed from several data sources), Federation (a GraphQL API composed from federated subgraphs), MCP, TCP or Streaming, plus "not understood". Exactly one per API definition.
- **Authentication Method**: A category describing how an API definition authenticates callers (none, API key, JWT, Basic, OAuth 2.0, OpenID Connect, mutual TLS, request signature checking), plus "not set" and "not understood". An API definition may have more than one.
- **Organization**: A stored record, separate from API definitions, with an identifier and a name. API definitions reference it by identifier. Categories also include "Not set" and "unmatched".
- **Breakdown**: A set of categories with counts for one dimension (API type, authentication, organization), each traceable to its member API definitions.
- **Coverage Indicator**: A summary of how many API definitions contain unclassified settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can answer "how many APIs use authentication method X?" and "how many APIs belong to organization Y?" in under 30 seconds from opening the dashboard, without opening any individual API definition.
- **SC-002**: For a verification data set, 100% of breakdown counts match counts computed independently from the same data.
- **SC-003**: From any breakdown category, a user reaches the list of matching APIs in at most 2 interactions.
- **SC-004**: After a refresh, the dashboard fully reflects source changes with no stale values visible.
- **SC-005**: For a source of 10,000 API definitions, the dashboard shows the overview within 15 seconds of load or refresh.
- **SC-006**: 100% of API definitions in the source are accounted for in each breakdown, including those with missing or unrecognized values.

## Assumptions

- Users are members of the internal technical team, and access control is provided by the deployment environment, so no separate login is needed.
- A single data source holds all relevant Tyk API definitions in one collection and organizations in another; supporting additional sources is out of scope.
- Read access to the organizations collection is available alongside the API definitions.
- Only API type, authentication, organization and middleware breakdowns are in scope. Other analytics categories (versions, listen paths, upstream targets, access controls) are future features.
- The dashboard is read-only and does not create, edit, or delete API definitions.
- Data is loaded when the dashboard is opened and on each explicit refresh, with no background updates.
- An API definition with several authentication methods counts once in each method, so authentication category counts may exceed the total.
- Historical trends, exports, and alerting are out of scope.
- Access to the source is available using read-only credentials supplied at deployment.
