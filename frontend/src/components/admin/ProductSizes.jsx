import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import Icon from '../Icon';
import { SizeGuideTable } from '../SizeGuideTable';
import { toEnglishDigits } from '../../utils/digits';
import { sizesTotal } from '../../utils/productSizes';
import { toPersianNumber } from '../../hooks/useLanguage';

const PRESETS = [
  ['S', 'M', 'L', 'XL'],
  ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
  ['1', '2', '3', '4', '5', '6', '7'],
];


/** The product's sizes: one row per size customers choose, each with its own stock. */
export function SizesFieldset({ rows, onChange }) {
  const { t, i18n } = useTranslation();
  const num = (n) => (i18n.language === 'fa' ? toPersianNumber(n) : String(n));
  const update = (i, patch) => onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const move = (i, dir) => {
    const next = [...rows];
    [next[i], next[i + dir]] = [next[i + dir], next[i]];
    onChange(next);
  };
  const addPreset = (labels) => {
    const have = new Set(rows.map((r) => r.label.trim().toLowerCase()));
    onChange([...rows, ...labels.filter((l) => !have.has(l.toLowerCase())).map((label) => ({ label, stock: '0', sku: '', is_active: true }))]);
  };
  const labels = rows.map((r) => r.label.trim().toLowerCase()).filter(Boolean);
  const duplicates = new Set(labels.filter((l, i) => labels.indexOf(l) !== i));

  return (
    <fieldset className="sizes-fieldset">
      <legend>{t('admin.sizesTitle', 'سایزها و موجودی هر سایز')}</legend>
      <p className="field-hint">
        {t('admin.sizesHint', 'اگر محصول چند سایز دارد، هر سایز را با موجودی‌اش اضافه کنید تا مشتری هنگام خرید سایز را انتخاب کند. برای محصول تک‌سایز این بخش را خالی بگذارید.')}
      </p>

      {rows.length > 0 && (
        <div className="sizes-table" role="table" aria-label={t('admin.sizesTitle', 'سایزها و موجودی هر سایز')}>
          <div className="sizes-row sizes-head" role="row">
            <span role="columnheader">{t('product.size')}</span>
            <span role="columnheader">{t('admin.stock', 'موجودی')}</span>
            <span role="columnheader">{t('admin.sku', 'کد انبار (اختیاری)')}</span>
            <span role="columnheader">{t('admin.active', 'فعال')}</span>
            <span role="columnheader" className="sr-only">{t('admin.actions', 'عملیات')}</span>
          </div>
          {rows.map((r, i) => (
            <div className={`sizes-row ${r.is_active ? '' : 'is-muted'}`} role="row" key={r.id || `new-${i}`}>
              <input
                className={`form-input ${duplicates.has(r.label.trim().toLowerCase()) ? 'is-invalid' : ''}`}
                value={r.label}
                maxLength={20}
                dir="ltr"
                placeholder="M"
                aria-label={t('product.size')}
                onChange={(e) => update(i, { label: e.target.value })}
              />
              <input
                className="form-input"
                type="text"
                inputMode="numeric"
                dir="ltr"
                value={r.stock}
                aria-label={t('admin.stock', 'موجودی')}
                onChange={(e) => update(i, { stock: e.target.value.replace(/[^0-9۰-۹]/g, '') })}
              />
              <input
                className="form-input"
                value={r.sku}
                maxLength={64}
                dir="ltr"
                aria-label={t('admin.sku', 'کد انبار (اختیاری)')}
                onChange={(e) => update(i, { sku: e.target.value })}
              />
              <input type="checkbox" checked={r.is_active} aria-label={t('admin.active', 'فعال')} onChange={(e) => update(i, { is_active: e.target.checked })} />
              <div className="row-actions">
                <button type="button" className="icon-btn" disabled={i === 0} onClick={() => move(i, -1)} aria-label={t('admin.moveUp', 'بالاتر')}>
                  <Icon name="chevronUp" size={16} />
                </button>
                <button type="button" className="icon-btn" disabled={i === rows.length - 1} onClick={() => move(i, 1)} aria-label={t('admin.moveDown', 'پایین‌تر')}>
                  <Icon name="chevronDown" size={16} />
                </button>
                <button type="button" className="icon-btn danger-btn" onClick={() => onChange(rows.filter((_, j) => j !== i))} aria-label={t('admin.removeSize', 'حذف سایز')}>
                  <Icon name="trash" size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {duplicates.size > 0 && <p className="field-error">{t('admin.duplicateSize', 'هر سایز فقط یک بار می‌تواند بیاید.')}</p>}

      <div className="sizes-actions">
        <button type="button" className="btn btn-outline btn-sm" onClick={() => onChange([...rows, { label: '', stock: '0', sku: '', is_active: true }])}>
          <Icon name="plus" size={16} /> {t('admin.addSize', 'افزودن سایز')}
        </button>
        {PRESETS.map((preset) => (
          <button type="button" key={preset.join()} className="chip" onClick={() => addPreset(preset)} dir="ltr">
            {preset[0]}–{preset[preset.length - 1]}
          </button>
        ))}
        {rows.length > 0 && (
          <span className="sizes-total">{t('admin.sizesTotal', 'موجودی کل: {{count}}', { count: num(sizesTotal(rows)) })}</span>
        )}
      </div>
    </fieldset>
  );
}

const EMPTY_GUIDE = {
  name: '', title_fa: '', title_en: '', how_to_measure_fa: '', how_to_measure_en: '',
  columns: [{ label_fa: '', label_en: '', unit: 'cm' }],
  rows: [],
};

/** راهنمای سایز: pick a shared size guide for the product, or create / edit one. */
export function SizeGuideFieldset({ guides, value, onChange, onGuideSaved, sizeLabels }) {
  const { t, i18n } = useTranslation();
  const num = (n) => (i18n.language === 'fa' ? toPersianNumber(n) : String(n));
  const [editingGuide, setEditingGuide] = useState(null); // null = closed
  const current = guides.find((g) => String(g.id) === String(value));

  return (
    <fieldset className="size-guide-fieldset">
      <legend>{t('product.sizeGuide')}</legend>
      <p className="field-hint">{t('admin.sizeGuideHint', 'جدول اندازه‌گیری که مشتری کنار انتخاب سایز می‌بیند. یک راهنما را می‌توان برای چند محصول مشابه استفاده کرد.')}</p>
      <div className="size-guide-pick">
        <select className="form-select" value={value ?? ''} onChange={(e) => onChange(e.target.value)} aria-label={t('product.sizeGuide')}>
          <option value="">{t('admin.noSizeGuide', 'بدون راهنمای سایز')}</option>
          {guides.map((g) => (
            <option key={g.id} value={g.id}>
              {g.title_fa || g.name} {g.product_count ? `(${t('admin.usedBy', '{{count}} محصول', { count: num(g.product_count) })})` : ''}
            </option>
          ))}
        </select>
        {current && (
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setEditingGuide(current)}>
            <Icon name="edit" size={16} /> {t('admin.editGuide', 'ویرایش راهنما')}
          </button>
        )}
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={() => setEditingGuide({ ...EMPTY_GUIDE, rows: sizeLabels.map((size) => ({ size, values: [''] })) })}
        >
          <Icon name="plus" size={16} /> {t('admin.newGuide', 'راهنمای جدید')}
        </button>
      </div>
      {current && (
        <details className="size-guide-preview">
          <summary>{t('admin.previewGuide', 'پیش‌نمایش برای مشتری')}</summary>
          <SizeGuideTable guide={current} />
        </details>
      )}
      {editingGuide && (
        <SizeGuideEditor
          guide={editingGuide}
          sizeLabels={sizeLabels}
          onClose={() => setEditingGuide(null)}
          onSaved={(saved) => {
            setEditingGuide(null);
            onGuideSaved(saved);
          }}
        />
      )}
    </fieldset>
  );
}

function SizeGuideEditor({ guide, sizeLabels, onClose, onSaved }) {
  const { t } = useTranslation();
  const { success } = useToast();
  const [form, setForm] = useState(() => ({
    ...EMPTY_GUIDE,
    ...guide,
    columns: guide.columns?.length ? guide.columns.map((c) => ({ label_fa: '', label_en: '', unit: '', ...c })) : EMPTY_GUIDE.columns,
    rows: (guide.rows || []).map((r) => ({ size: r.size, values: [...r.values] })),
  }));
  const [image, setImage] = useState(null);
  const [removeImage, setRemoveImage] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(false);

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const setColumn = (i, patch) => set({ columns: form.columns.map((c, j) => (j === i ? { ...c, ...patch } : c)) });
  const addColumn = () =>
    set({ columns: [...form.columns, { label_fa: '', label_en: '', unit: 'cm' }], rows: form.rows.map((r) => ({ ...r, values: [...r.values, ''] })) });
  const removeColumn = (i) =>
    set({ columns: form.columns.filter((_, j) => j !== i), rows: form.rows.map((r) => ({ ...r, values: r.values.filter((_, j) => j !== i) })) });
  const setRow = (i, patch) => set({ rows: form.rows.map((r, j) => (j === i ? { ...r, ...patch } : r)) });
  const setCell = (i, c, value) => setRow(i, { values: form.rows[i].values.map((v, j) => (j === c ? value : v)) });
  const addRow = (size = '') => set({ rows: [...form.rows, { size, values: form.columns.map(() => '') }] });
  const rowsFromSizes = () => {
    const have = new Set(form.rows.map((r) => r.size.trim().toLowerCase()));
    set({ rows: [...form.rows, ...sizeLabels.filter((s) => !have.has(s.toLowerCase())).map((size) => ({ size, values: form.columns.map(() => '') }))] });
  };

  const cleaned = () => ({
    ...form,
    columns: form.columns.map((c) => ({ label_fa: c.label_fa.trim(), label_en: c.label_en.trim(), unit: c.unit.trim() })),
    rows: form.rows
      .filter((r) => r.size.trim())
      .map((r) => ({ size: r.size.trim(), values: r.values.map((v) => toEnglishDigits(String(v)).trim()) })),
  });

  const save = async () => {
    setSaving(true);
    setError('');
    const data = cleaned();
    const fields = ['name', 'title_fa', 'title_en', 'how_to_measure_fa', 'how_to_measure_en'];
    let body;
    if (image || removeImage) {
      // A diagram goes in a multipart form; the table travels as JSON text.
      body = new FormData();
      fields.forEach((f) => body.append(f, data[f] || ''));
      body.append('columns', JSON.stringify(data.columns));
      body.append('rows', JSON.stringify(data.rows));
      body.append('image', image || '');
    } else {
      body = Object.fromEntries(fields.map((f) => [f, data[f] || '']));
      body.columns = data.columns;
      body.rows = data.rows;
    }
    try {
      const res = guide.id
        ? await apiClient.patch(ENDPOINTS.adminSizeGuide(guide.id), body)
        : await apiClient.post(ENDPOINTS.adminSizeGuides, body);
      success(t('admin.guideSaved', 'راهنمای سایز ذخیره شد'));
      onSaved(res.data);
    } catch (err) {
      const d = err.response?.data;
      setError(
        d && typeof d === 'object'
          ? Object.values(d).flat().join(' ')
          : t('admin.saveFailed', 'ذخیره انجام نشد'),
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay nested" onClick={onClose}>
      <div className="modal modal-lg" role="dialog" aria-modal="true" aria-labelledby="guide-form-title" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 id="guide-form-title">{guide.id ? t('admin.editGuide', 'ویرایش راهنما') : t('admin.newGuide', 'راهنمای جدید')}</h2>
          <button type="button" onClick={onClose} className="icon-btn" aria-label={t('common.close', 'بستن')}><Icon name="close" /></button>
        </div>
        <div className="admin-form">
          {error && <p className="form-alert">{error}</p>}
          {guide.id && guide.product_count > 1 && (
            <p className="field-hint">{t('admin.guideShared', 'این راهنما در {{count}} محصول استفاده شده و تغییرات در همه آن‌ها دیده می‌شود.', { count: guide.product_count })}</p>
          )}
          <div className="form-grid two">
            <div className="form-group">
              <label className="form-label" htmlFor="g-title-fa">{t('admin.guideTitleFa', 'عنوان (فارسی)')}</label>
              <input id="g-title-fa" className="form-input" value={form.title_fa} placeholder="راهنمای سایز زانوبند" onChange={(e) => set({ title_fa: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="g-name">{t('admin.guideName', 'نام داخلی (یکتا)')}</label>
              <input id="g-name" className="form-input" value={form.name} required maxLength={100} onChange={(e) => set({ name: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="g-how-fa">{t('admin.howToMeasureFa', 'نحوه اندازه‌گیری (فارسی)')}</label>
              <textarea id="g-how-fa" className="form-textarea" rows={4} value={form.how_to_measure_fa} onChange={(e) => set({ how_to_measure_fa: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="g-how-en">{t('admin.howToMeasureEn', 'نحوه اندازه‌گیری (انگلیسی)')}</label>
              <textarea id="g-how-en" className="form-textarea" rows={4} dir="ltr" value={form.how_to_measure_en} onChange={(e) => set({ how_to_measure_en: e.target.value })} />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="g-image">{t('admin.guideImage', 'تصویر راهنمای اندازه‌گیری (اختیاری)')}</label>
            <input id="g-image" type="file" accept="image/*" onChange={(e) => { setImage(e.target.files[0] || null); setRemoveImage(false); }} />
            {guide.image && !image && (
              <label className="check-inline">
                <input type="checkbox" checked={removeImage} onChange={(e) => setRemoveImage(e.target.checked)} /> {t('admin.removeImage', 'حذف تصویر فعلی')}
              </label>
            )}
          </div>

          <h3 className="size-guide-section">{t('admin.guideTable', 'جدول اندازه‌ها')}</h3>
          <div className="size-guide-grid-wrap">
            <table className="size-guide-grid">
              <thead>
                <tr>
                  <th>{t('product.size')}</th>
                  {form.columns.map((c, i) => (
                    <th key={i}>
                      <input className="form-input" value={c.label_fa} placeholder={t('admin.columnFa', 'مثلاً دور ران')} aria-label={t('admin.columnFa', 'مثلاً دور ران')} onChange={(e) => setColumn(i, { label_fa: e.target.value })} />
                      <input className="form-input" value={c.label_en} dir="ltr" placeholder="Thigh" aria-label={t('admin.columnEn', 'نام انگلیسی ستون')} onChange={(e) => setColumn(i, { label_en: e.target.value })} />
                      <div className="size-guide-col-foot">
                        <input className="form-input" value={c.unit} dir="ltr" placeholder="cm" aria-label={t('admin.unit', 'واحد')} onChange={(e) => setColumn(i, { unit: e.target.value })} />
                        {form.columns.length > 1 && (
                          <button type="button" className="icon-btn danger-btn" onClick={() => removeColumn(i)} aria-label={t('admin.removeColumn', 'حذف ستون')}>
                            <Icon name="trash" size={14} />
                          </button>
                        )}
                      </div>
                    </th>
                  ))}
                  <th aria-hidden="true" />
                </tr>
              </thead>
              <tbody>
                {form.rows.map((r, i) => (
                  <tr key={i}>
                    <td><input className="form-input" value={r.size} dir="ltr" maxLength={20} aria-label={t('product.size')} onChange={(e) => setRow(i, { size: e.target.value })} /></td>
                    {r.values.map((v, c) => (
                      <td key={c}><input className="form-input" value={v} dir="ltr" maxLength={40} placeholder="38-41" aria-label={form.columns[c]?.label_fa || t('admin.value', 'مقدار')} onChange={(e) => setCell(i, c, e.target.value)} /></td>
                    ))}
                    <td>
                      <button type="button" className="icon-btn danger-btn" onClick={() => set({ rows: form.rows.filter((_, j) => j !== i) })} aria-label={t('admin.removeRow', 'حذف ردیف')}>
                        <Icon name="trash" size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sizes-actions">
            <button type="button" className="btn btn-outline btn-sm" onClick={() => addRow()}><Icon name="plus" size={16} /> {t('admin.addRow', 'افزودن ردیف')}</button>
            {form.columns.length < 6 && (
              <button type="button" className="btn btn-outline btn-sm" onClick={addColumn}><Icon name="plus" size={16} /> {t('admin.addColumn', 'افزودن ستون')}</button>
            )}
            {sizeLabels.length > 0 && (
              <button type="button" className="btn btn-outline btn-sm" onClick={rowsFromSizes}>{t('admin.rowsFromSizes', 'ردیف برای سایزهای محصول')}</button>
            )}
            <button type="button" className="text-btn" onClick={() => setPreview((p) => !p)}>{t('admin.previewGuide', 'پیش‌نمایش برای مشتری')}</button>
          </div>
          {preview && <div className="size-guide-preview"><SizeGuideTable guide={cleaned()} /></div>}

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn btn-outline">{t('admin.cancel', 'انصراف')}</button>
            <button type="button" disabled={saving} onClick={save} className="btn btn-primary">{saving ? t('common.loading') : t('admin.saveGuide', 'ذخیره راهنما')}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
