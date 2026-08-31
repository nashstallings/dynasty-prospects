/**
 * Column sorting for the prospect table.
 *
 * Ported from nfl-2026-projections/web/js/sort.js, unchanged -- the same two
 * decisions apply here: missing values (a prospect with no scouting rank, no
 * combine number) sort last in *both* directions, and a click on a new column
 * starts descending for numbers, ascending for text.
 */

function compare(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

function isMissing(value) {
  return value === null || value === undefined || value === "" || Number.isNaN(value);
}

/**
 * Sort a copy of `rows` by `key`. Never mutates the input.
 *
 * Ties keep their previous order, so sorting by position leaves each
 * position's players in whatever order the last sort put them.
 */
export function sortRows(rows, key, direction = "desc") {
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((left, right) => {
    const a = left[key];
    const b = right[key];
    const aMissing = isMissing(a);
    const bMissing = isMissing(b);
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;
    return sign * compare(a, b);
  });
}

/**
 * The direction a click should produce.
 *
 * Clicking the column already sorted reverses it. Clicking a new one starts
 * from the end of that column people usually want.
 */
export function nextDirection(current, key, type = "number") {
  if (current?.key === key) return current.direction === "asc" ? "desc" : "asc";
  return type === "text" ? "asc" : "desc";
}

/** The `aria-sort` value for a header, so the sort is announced, not just drawn. */
export function ariaSort(current, key) {
  if (current?.key !== key) return "none";
  return current.direction === "asc" ? "ascending" : "descending";
}
