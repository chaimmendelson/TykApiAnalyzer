# Contract: Dashboard Behavior

The only external interface is the web page. This defines what it must show and how it reacts.

## Layout (top to bottom)

1. **Sticky top bar** (FR-006e, FR-006i), pinned while scrolling: row 1 with a shared top edge and
   a theme-matching background: small title with "Data loaded at <UTC time>" under it, the
   **Organization** multiselect of every organization (FR-006d; the only way to select an organization),
   **Refresh**, and **Clear all** (disabled when nothing is
   selected). A second thin line inside the bar shows one chip per selected category with a remove
   control; it is absent when nothing is selected. The bar never covers the first chart at the top.
2. **Summary line**: one small line of text under the bar: total APIs, unclassified count, and the
   coverage indicator ("N of M APIs have unclassified settings" with a reasons popover). It scrolls
   with the page.
3. **Breakdown charts**: row 1 two equal-height pies at half width (API type, Authentication) whose slices carry the
   category name; a wrapping row of "Name · count" chips under each pie lists every category and is
   the filter control (slices are not clickable; hover adds the percentage);
   row 2 two equal-height horizontal bar charts at half width each (Global middleware,
   Per-endpoint middleware) (FR-006c, FR-006d). Authentication and both middleware charts carry the
   note "An API can use several methods, so counts may exceed the total." (middleware charts:
   "...several middleware...")
4. **Matching APIs table**: name, API type, authentication, organization, TLS (for
   TCP). Selecting a middleware bar filters on that middleware. Shows "Showing N of M".
6. **API detail**: selecting a row shows the evidence behind each classification (the raw field
   values used), not the full document.

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
