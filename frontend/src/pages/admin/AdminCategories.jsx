import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import Icon from '../../components/Icon';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

const EMPTY = { name: '', name_fa: '', slug: '', description: '', description_fa: '', is_active: true };

export default function AdminCategories() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { success, error: showError } = useToast();
  const [categories, setCategories] = useState(null);
  const [editing, setEditing] = useState(null); // null closed, {} new, category = edit
  const [form, setForm] = useState(EMPTY);
  const [imageFile, setImageFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  usePageMeta({ title: t('admin.categories', 'دسته‌بندی‌ها'), noindex: true });

  const load = useCallback(() => {
    apiClient
      .get(ENDPOINTS.adminCategories)
      .then((res) => setCategories(res.data.results || res.data))
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => () => preview.startsWith('blob:') && URL.revokeObjectURL(preview), [preview]);

  const open = (c) => {
    setForm(c ? Object.fromEntries(Object.keys(EMPTY).map((k) => [k, c[k] ?? EMPTY[k]])) : EMPTY);
    setImageFile(null);
    setPreview(c?.image || '');
    setFormError('');
    setEditing(c || {});
  };

  const setField = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  const pickImage = (file) => {
    if (!file) return;
    setImageFile(file);
    setPreview(URL.createObjectURL(file));
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    const body = new FormData();
    Object.entries(form).forEach(([k, v]) => {
      if (k === 'slug' && !v) return;
      body.append(k, typeof v === 'boolean' ? String(v) : v);
    });
    if (imageFile) body.append('image', imageFile);
    try {
      if (editing.slug) await apiClient.patch(ENDPOINTS.adminCategory(editing.slug), body);
      else await apiClient.post(ENDPOINTS.adminCategories, body);
      success(t('admin.categorySaved', 'دسته‌بندی ذخیره شد'));
      setEditing(null);
      load();
    } catch (err) {
      const data = err.response?.data;
      setFormError(
        data?.error ||
          (data && typeof data === 'object'
            ? Object.entries(data).map(([f, m]) => `${f}: ${[].concat(m).join(' ')}`).join(' — ')
            : t('admin.saveFailed', 'ذخیره انجام نشد')),
      );
    } finally {
      setSaving(false);
    }
  };

  const remove = async (c) => {
    if (!window.confirm(t('admin.deleteCategoryConfirm', 'دسته «{{name}}» حذف شود؟', { name: c.name_fa || c.name }))) return;
    try {
      await apiClient.delete(ENDPOINTS.adminCategory(c.slug));
      success(t('admin.categoryDeleted', 'دسته‌بندی حذف شد'));
      load();
    } catch (err) {
      showError(err.response?.data?.error || t('admin.deleteFailed', 'حذف انجام نشد'));
    }
  };

  const toggleActive = async (c) => {
    try {
      await apiClient.patch(ENDPOINTS.adminCategory(c.slug), { is_active: !c.is_active });
      setCategories((list) => list.map((x) => (x.id === c.id ? { ...x, is_active: !c.is_active } : x)));
    } catch {
      showError(t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    }
  };

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <div>
          <h1>{t('admin.categories', 'دسته‌بندی‌ها')}</h1>
          <p className="muted">{t('admin.categoriesHint2', 'نام، توضیحات، تصویر و نمایش دسته‌ها را مدیریت کنید.')}</p>
        </div>
        <button onClick={() => open(null)} className="btn btn-primary">
          <Icon name="plus" size={18} /> {t('admin.addCategory', 'دسته‌بندی جدید')}
        </button>
      </header>

      {categories === null ? (
        <div className="loading"><div className="spinner" /></div>
      ) : (
        <div className="admin-tile-grid">
          {categories.map((c) => (
            <article key={c.id} className={`admin-tile ${c.is_active ? '' : 'is-muted'}`}>
              <div className="admin-tile-img">
                {c.image ? <img src={c.image} alt="" loading="lazy" /> : <span className="no-image"><Icon name="image" size={28} /> {t('admin.noImage', 'بدون تصویر')}</span>}
                {!c.is_active && <span className="status-pill tone-bad tile-flag">{t('admin.inactive', 'غیرفعال')}</span>}
              </div>
              <div className="admin-tile-body">
                <h3>{c.name_fa || c.name}</h3>
                <span className="muted" dir="ltr">{c.name}</span>
                <span className="muted">{t('products.productsCount', { count: num(c.product_count) })}</span>
              </div>
              <div className="admin-tile-actions">
                <button onClick={() => open(c)} className="btn btn-outline btn-sm">
                  <Icon name="edit" size={16} /> {t('admin.edit', 'ویرایش')}
                </button>
                <button onClick={() => toggleActive(c)} className="btn btn-ghost btn-sm">
                  {c.is_active ? t('admin.hide', 'پنهان کردن') : t('admin.show', 'نمایش')}
                </button>
                <Link to={`/products?category=${c.slug}`} className="icon-btn" aria-label={t('admin.viewInShop', 'نمایش در فروشگاه')} title={t('admin.viewInShop', 'نمایش در فروشگاه')}>
                  <Icon name="search" size={16} />
                </Link>
                {c.product_count === 0 && (
                  <button onClick={() => remove(c)} className="icon-btn danger-btn" aria-label={t('admin.delete', 'حذف')} title={t('admin.delete', 'حذف')}>
                    <Icon name="trash" size={16} />
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {editing && (
        <div className="modal-overlay" onClick={() => setEditing(null)}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="cat-form-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 id="cat-form-title">{editing.slug ? t('admin.editCategory', 'ویرایش دسته‌بندی') : t('admin.addCategory', 'دسته‌بندی جدید')}</h2>
              <button onClick={() => setEditing(null)} className="icon-btn" aria-label={t('common.close', 'بستن')}><Icon name="close" /></button>
            </div>
            <form onSubmit={save} className="admin-form">
              {formError && <p className="form-alert">{formError}</p>}
              <label className="image-drop">
                {preview ? <img src={preview} alt="" /> : <span><Icon name="upload" size={28} /> {t('admin.chooseImage', 'انتخاب تصویر')}</span>}
                <input type="file" accept="image/*" onChange={(e) => pickImage(e.target.files?.[0])} />
              </label>
              <div className="form-grid two">
                <div className="form-group">
                  <label className="form-label" htmlFor="c-name-fa">{t('admin.nameFa', 'نام فارسی')}</label>
                  <input id="c-name-fa" className="form-input" value={form.name_fa} onChange={(e) => setField('name_fa', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="c-name">{t('admin.nameEn', 'نام انگلیسی')}</label>
                  <input id="c-name" className="form-input" dir="ltr" value={form.name} onChange={(e) => setField('name', e.target.value)} required />
                </div>
              </div>
              {!editing.slug && (
                <div className="form-group">
                  <label className="form-label" htmlFor="c-slug">{t('admin.slug', 'نامک (آدرس)')} <span className="optional">({t('checkout.optional', 'اختیاری')})</span></label>
                  <input id="c-slug" className="form-input" dir="ltr" value={form.slug} onChange={(e) => setField('slug', e.target.value)} placeholder="knee-braces" />
                </div>
              )}
              <div className="form-group">
                <label className="form-label" htmlFor="c-desc-fa">{t('admin.descFa', 'توضیحات فارسی')}</label>
                <textarea id="c-desc-fa" className="form-textarea" rows={3} value={form.description_fa} onChange={(e) => setField('description_fa', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="c-desc">{t('admin.descEn', 'توضیحات انگلیسی')}</label>
                <textarea id="c-desc" className="form-textarea" rows={2} dir="ltr" value={form.description} onChange={(e) => setField('description', e.target.value)} />
              </div>
              <label className="check-inline">
                <input type="checkbox" checked={form.is_active} onChange={(e) => setField('is_active', e.target.checked)} />
                {t('admin.activeHint', 'نمایش در فروشگاه')}
              </label>
              <div className="modal-actions">
                <button type="button" onClick={() => setEditing(null)} className="btn btn-outline">{t('admin.cancel', 'انصراف')}</button>
                <button type="submit" disabled={saving} className="btn btn-primary">{saving ? t('common.loading') : t('admin.save', 'ذخیره')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
