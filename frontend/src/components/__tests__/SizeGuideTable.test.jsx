import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SizeGuideModal, { SizeGuideTable } from '../SizeGuideTable';
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

  it('puts the size table before the measuring photo and instructions', () => {
    language = 'fa';
    const { container } = render(<SizeGuideTable guide={{ ...guide, image: '/media/guide.jpg' }} />);
    const table = container.querySelector('.size-table-wrap');
    const how = container.querySelector('.size-guide-how');
    expect(how.querySelector('img')).toBeTruthy();
    expect(table.compareDocumentPosition(how) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('uses the English texts in English', () => {
    language = 'en';
    render(<SizeGuideTable guide={guide} />);
    expect(screen.getByText('Thigh')).toBeInTheDocument();
    expect(screen.getByText('38-41')).toBeInTheDocument();
    expect(screen.getByText('Measure the thigh.')).toBeInTheDocument();
  });
});

describe('a size table wider than its box', () => {
  const widths = (scrollWidth, clientWidth) => {
    const original = {
      scrollWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollWidth'),
      clientWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth'),
    };
    Object.defineProperty(HTMLElement.prototype, 'scrollWidth', { configurable: true, get: () => scrollWidth });
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, get: () => clientWidth });
    return () => {
      for (const [name, descriptor] of Object.entries(original)) {
        if (descriptor) Object.defineProperty(HTMLElement.prototype, name, descriptor);
        else delete HTMLElement.prototype[name];
      }
    };
  };

  it('says it scrolls sideways and can be focused; a table that fits says nothing', () => {
    language = 'fa';
    let restore = widths(540, 326);
    const wide = render(<SizeGuideTable guide={guide} />);
    expect(wide.container.querySelector('.size-table-hint')).toBeTruthy();
    expect(wide.container.querySelector('.size-table-wrap').getAttribute('tabindex')).toBe('0');
    wide.unmount();
    restore();

    restore = widths(326, 326);
    const fits = render(<SizeGuideTable guide={guide} />);
    expect(fits.container.querySelector('.size-table-hint')).toBeNull();
    expect(fits.container.querySelector('.size-table-wrap').hasAttribute('tabindex')).toBe(false);
    restore();
  });

  it('keeps the text direction off the size cell so it can stay pinned in Persian', () => {
    const { container } = render(<SizeGuideTable guide={guide} />);
    const cell = container.querySelector('tbody th');
    expect(cell.hasAttribute('dir')).toBe(false);
    expect(cell.querySelector('bdi').getAttribute('dir')).toBe('ltr');
  });
});

describe('SizeGuideModal', () => {
  it('locks the page while open, and closes on Escape, the X and the backdrop but not on its content', () => {
    language = 'fa';
    const onClose = vi.fn();
    const { container, unmount } = render(<SizeGuideModal guide={guide} onClose={onClose} />);
    expect(document.body.style.overflow).toBe('hidden');
    expect(screen.getByRole('dialog').className).toContain('modal-sheet');

    fireEvent.click(container.querySelector('.size-table'));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: 'Escape' });
    fireEvent.click(container.querySelector('.modal-header .icon-btn'));
    fireEvent.click(container.querySelector('.modal-overlay'));
    expect(onClose).toHaveBeenCalledTimes(3);

    unmount();
    expect(document.body.style.overflow).toBe('');
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
