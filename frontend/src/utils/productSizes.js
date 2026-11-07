import { toEnglishDigits } from './digits';

// Admin form rows keep stock as typed text; the API takes numbers.
export const sizesFromProduct = (p) =>
  (p.sizes || []).map((s) => ({ id: s.id, label: s.label, stock: String(s.stock), sku: s.sku || '', is_active: s.is_active }));

export const sizesPayload = (rows) =>
  rows
    .filter((r) => r.label.trim())
    .map((r, i) => ({
      ...(r.id ? { id: r.id } : {}),
      label: r.label.trim(),
      stock: parseInt(toEnglishDigits(r.stock), 10) || 0,
      sku: r.sku.trim(),
      is_active: r.is_active,
      sort_order: i,
    }));

// A label must hold one size: "M L", "M, L" or "M/L" are several (the API and database refuse them).
const SIZE_SEPARATORS = /[\s,،/]+/;
export const sizeLabelParts = (label) => label.trim().split(SIZE_SEPARATORS).filter(Boolean);

// Replace row `index` ("M L") with one row per size; the first keeps its id, stock is split evenly.
export const splitSizeRow = (rows, index) => {
  const row = rows[index];
  const taken = new Set(rows.filter((_, i) => i !== index).map((r) => r.label.trim().toLowerCase()));
  if (sizeLabelParts(row.label).length < 2) return rows;
  const parts = sizeLabelParts(row.label).filter((p, i, all) => !taken.has(p.toLowerCase()) && all.indexOf(p) === i);
  if (!parts.length) return rows; // every part is already a size of this product
  const stock = parseInt(toEnglishDigits(row.stock), 10) || 0;
  const share = Math.floor(stock / parts.length);
  const extra = stock % parts.length;
  const split = parts.map((label, i) => ({
    ...(i === 0 ? row : { sku: '', is_active: row.is_active }),
    label,
    stock: String(share + (i < extra ? 1 : 0)),
    ...(i === 0 ? {} : { id: undefined }),
  }));
  return [...rows.slice(0, index), ...split, ...rows.slice(index + 1)];
};

export const sizesTotal = (rows) =>
  rows.filter((r) => r.is_active && r.label.trim()).reduce((sum, r) => sum + (parseInt(toEnglishDigits(r.stock), 10) || 0), 0);
