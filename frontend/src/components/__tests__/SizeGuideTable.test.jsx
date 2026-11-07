import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SizeGuideTable } from '../SizeGuideTable';
import { sizeLabelParts, sizesFromProduct, sizesPayload, sizesTotal, splitSizeRow } from '../../utils/productSizes';

let language = 'fa';
vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key, fallback) => fallback || key, i18n: { language } }),
}));

const guide = {
  title_fa: 'راهنمای سایز زانوبند',
  how_to_measure_fa: 'دور ران را اندازه بگیرید.\nدور ساق را اندازه بگیرید.',
  how_to_measure_en: 'Measure the thigh.',
  image: null,
  columns: [{ label_fa: 'دور ران', label_en: 'Thigh', unit: 'cm' }],
  rows: [{ size: 'S', values: ['38-41'] }, { size: 'M', values: ['41-44'] }],
};

describe('SizeGuideTable', () => {
  it('shows the Persian table with Persian digits and highlights the chosen size', () => {
    language = 'fa';
    const { container } = render(<SizeGuideTable guide={guide} highlight="m" />);
    expect(screen.getByText('دور ران')).toBeInTheDocument();
    expect(screen.getByText('۳۸-۴۱')).toBeInTheDocument();
    expect(screen.getAllByText(/اندازه بگیرید/)).toHaveLength(2); // one paragraph per line
    expect(container.querySelector('tr.is-picked th').textContent).toBe('M');
  });

  it('uses the English texts in English', () => {
    language = 'en';
    render(<SizeGuideTable guide={guide} />);
    expect(screen.getByText('Thigh')).toBeInTheDocument();
    expect(screen.getByText('38-41')).toBeInTheDocument();
    expect(screen.getByText('Measure the thigh.')).toBeInTheDocument();
  });
});

describe('product size form helpers', () => {
  const rows = [
    { id: 1, label: ' S ', stock: '۳', sku: '', is_active: true },
    { label: 'M', stock: '4', sku: ' HZ-M ', is_active: true },
    { label: 'L', stock: '9', sku: '', is_active: false },
    { label: '  ', stock: '5', sku: '', is_active: true }, // empty row is ignored
  ];

  it('builds the API payload: trims, converts Persian digits, keeps order and ids', () => {
    expect(sizesPayload(rows)).toEqual([
      { id: 1, label: 'S', stock: 3, sku: '', is_active: true, sort_order: 0 },
      { label: 'M', stock: 4, sku: 'HZ-M', is_active: true, sort_order: 1 },
      { label: 'L', stock: 9, sku: '', is_active: false, sort_order: 2 },
    ]);
  });

  it('totals only active, named sizes', () => {
    expect(sizesTotal(rows)).toBe(7);
  });

  it('turns API sizes into form rows', () => {
    expect(sizesFromProduct({ sizes: [{ id: 2, label: 'XL', stock: 0, sku: null, is_active: true }] })).toEqual([
      { id: 2, label: 'XL', stock: '0', sku: '', is_active: true },
    ]);
  });
});

describe('splitting a label that holds several sizes', () => {
  it('finds the sizes in "M L", "M, L", "M/L" and "M، L", but keeps a range whole', () => {
    expect(sizeLabelParts('M L')).toEqual(['M', 'L']);
    expect(sizeLabelParts(' M,  L ')).toEqual(['M', 'L']);
    expect(sizeLabelParts('M/L/XL')).toEqual(['M', 'L', 'XL']);
    expect(sizeLabelParts('M، L')).toEqual(['M', 'L']);
    expect(sizeLabelParts('39-41')).toEqual(['39-41']);
  });

  it('replaces the row with one row per size, keeping the id and splitting the stock', () => {
    const rows = [
      { id: 7, label: 'M L', stock: '۵', sku: 'X', is_active: true },
      { id: 8, label: 'XL', stock: '2', sku: '', is_active: true },
    ];
    const out = splitSizeRow(rows, 0);
    expect(out.map((r) => [r.id, r.label, r.stock])).toEqual([[7, 'M', '3'], [undefined, 'L', '2'], [8, 'XL', '2']]);
    expect(out[1].sku).toBe('');
  });

  it('skips sizes the product already has and leaves single sizes alone', () => {
    const rows = [{ label: 'M XL', stock: '4', sku: '', is_active: true }, { label: 'XL', stock: '1', sku: '', is_active: true }];
    expect(splitSizeRow(rows, 0).map((r) => [r.label, r.stock])).toEqual([['M', '4'], ['XL', '1']]); // XL exists
    expect(splitSizeRow(rows, 1)).toBe(rows);
  });
});
