import { label, t } from './i18n.js';
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value === true ? '' : value);
  }
  node.append(...children); return node;
}
export const heading = (level, key) => label(el('h' + level), key);
export const button = (key, props = {}) => label(el('button', { type: 'button', ...props }), key);
export function field(form, name, key, tag = 'input', props = {}) {
  const id = form.id + '-' + name;
  const control = el(tag, { id, name, ...props });
  const wrapper = el('div', { class: 'field' }, label(el('label', { for: id }), key), control);
  form.append(wrapper); return control;
}
export function checkbox(form, name, key, checked = true) {
  const id = form.id + '-' + name;
  const control = el('input', { id, name, type: 'checkbox' }); control.checked = checked;
  form.append(el('div', { class: 'check' }, control, label(el('label', { for: id }), key)));
  return control;
}
export function clearErrors(form) {
  form.querySelectorAll('.field-error').forEach(n => n.remove());
  form.querySelectorAll('[aria-invalid]').forEach(n => { n.removeAttribute('aria-invalid'); n.removeAttribute('aria-describedby'); });
  const summary = form.querySelector('.error-summary'); summary.hidden = true; summary.replaceChildren();
}
export function showError(form, error) {
  const summary = form.querySelector('.error-summary'); summary.replaceChildren(heading(2, 'error'));
  const list = el('ul');
  for (const detail of error.details ?? []) {
    const name = detail.field.replace(/^body\./, '').split('.').pop();
    const control = form.elements.namedItem(name);
    if (control instanceof HTMLElement) {
      const id = control.id + '-error';
      control.setAttribute('aria-invalid', 'true'); control.setAttribute('aria-describedby', id);
      control.after(el('p', { id, class: 'field-error', text: detail.message }));
      list.append(el('li', {}, el('a', { href: '#' + control.id, text: detail.message })));
    }
  }
  summary.append(el('p', { text: error.message }), list); summary.hidden = false; summary.focus();
}
export function validate(form) {
  clearErrors(form);
  const details = [...form.elements].filter(c => c.willValidate && (!c.checkValidity() || (c.required && typeof c.value === 'string' && !c.value.trim())))
    .map(c => ({ field: c.name, message: t('required') }));
  if (details.length) { const error = new Error(t('required')); error.details = details; showError(form, error); return false; }
  return true;
}
export function formShell(kind) {
  const form = el('form', { id: kind + '-form', novalidate: true });
  form.append(el('div', { class: 'error-summary', role: 'alert', tabindex: '-1', hidden: true }));
  return form;
}
