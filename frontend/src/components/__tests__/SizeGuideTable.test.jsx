import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SizeGuideTable } from '../SizeGuideTable';
import { sizesFromProduct, sizesPayload, sizesTotal } from '../../utils/productSizes';

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
