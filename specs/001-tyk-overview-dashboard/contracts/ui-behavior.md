# Contract: Dashboard Behavior

The only external interface is the web page. This defines what it must show and how it reacts.

## Layout (top to bottom)

1. **Sticky top bar** (FR-006e, FR-006i, FR-006j), pinned while scrolling, two rows on a
   theme-matching background. Row 1: small title with "Data loaded at <UTC time>" under it,
   **Refresh**, and **Clear all** (disabled when nothing is selected). Row 2: five equal dropdown
   buttons (Organization, API type, Authentication, Global middleware, Per-endpoint middleware),
   each showing a summary of its selection ("All API types", "TCP", "2 selected"). Opening one shows
   a **Clear** button (no "All") above a scrollable list with a checkbox on every line, "<name>
   (<count>)", every category in a fixed order, ticked ones included (FR-006n). Counts follow the other
   dropdowns' selections (a dropdown ignores its own) and show "(0)" when nothing matches. There is
   no chip line: selections are shown in the dropdowns. The bar never covers the first chart.
2. **Summary line**: one small line of text under the bar: total APIs, unclassified count, and the
   coverage indicator ("N of M APIs have unclassified settings" with a reasons popover). It scrolls
   with the page.
3. **Two tabs** (FR-006l) under the top bar and the summary line: **Overview** and **APIs**. Filters
   are shared and kept when switching tabs.
   - **Overview tab, breakdown charts**: row 1 two equal-height pies at half width (API type, Authentication) whose slices carry the
   category name; a wrapping row of "Name · count" chips under each pie lists every category and is
   the filter control (slices are not clickable; hover adds the percentage);
   row 2 two equal-height horizontal bar charts at half width each (Global middleware,
   Per-endpoint middleware) (FR-006c, FR-006d). Authentication and both middleware charts carry the
   note "An API can use several methods, so counts may exceed the total." (middleware charts:
   "...several middleware...")
   - **APIs tab, table and detail side by side** (FR-006k): "Showing N of M" above both columns; left
   (about two thirds) the table with name, API type, authentication and organization (no TLS column),
   using the available screen height; right (about one third) the **API detail** panel, which stays in view while the table scrolls.
   Selecting a row fills the panel with the API's name and ID, API type, organization, any
   unclassified warnings and the evidence behind each classification (the raw field values used),
   not the full document. With no row selected it shows a short hint. On a narrow screen the panel
   moves below the table.

## Interactions

| Action | Result |
|---|---|
| Open page | Load snapshot (spinner while loading) |
| Click Refresh | Reload from MongoDB; replace snapshot and load time |
| Click slice(s) or bar(s) in a chart | Set that dimension's selection; table and all other charts re-filter |
| Select in a second dimension | AND with existing selections |
| Click chip / Clear all | Remove selection(s) |
| Select table row | Show evidence panel |

## States

| State | Display |
|---|---|
| Loading | Spinner, no stale numbers |
| Read failure | Error banner with a redacted reason and a Retry (Refresh) button; no charts |
| Zero APIs | "No Tyk API definitions found in the configured source." |
| Selections match nothing | "No matching APIs" with Clear all |
| Unclassified present | Coverage indicator highlighted; categories "Not set", "Not understood", "unmatched" shown as ordinary bars |

## Invariants

- Chart counts, table rows and totals always come from the same snapshot (FR-011).
- Count shown for a bar equals rows listed after selecting it with the current other selections
  (FR-007).
- Nothing on the page can issue a free-form query (FR-015).
