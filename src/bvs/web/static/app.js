import { api } from './api.js';
import { changeLocale, label, locale, t, translate } from './i18n.js';
import { el } from './ui.js';
import { build as speak } from './pages/speak.js';
import { build as clone } from './pages/clone.js';
import { build as transcribe } from './pages/transcribe.js';
import { build as audiobook } from './pages/audiobook.js';
import { build as engines } from './pages/engines.js';

const builders = { speak, clone, transcribe, audiobook, engines };
const pages = new Map();
let current, health, catalog;
const theme = document.querySelector('#theme');
let dark = localStorage.getItem('bvs-theme') === 'dark' || (!localStorage.getItem('bvs-theme') && matchMedia('(prefers-color-scheme: dark)').matches);
function paintTheme() { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; label(theme, dark ? 'light' : 'dark'); }
paintTheme(); theme.onclick = () => { dark = !dark; localStorage.setItem('bvs-theme', dark ? 'dark' : 'light'); paintTheme(); };
document.documentElement.lang = locale;
document.querySelector('#language').textContent = locale === 'bn' ? 'English' : 'বাংলা';
document.querySelector('#language').onclick = changeLocale;
const navToggle = document.querySelector('#nav-toggle'), nav = document.querySelector('#navigation');
navToggle.onclick = () => { nav.hidden = !nav.hidden; navToggle.setAttribute('aria-expanded', String(!nav.hidden)); };
translate();

function navigate(path, { push = false, focus = false } = {}) {
  const url = new URL(path, location.origin);
  const name = url.pathname.replace(/^\//, '') || 'speak';
  if (!builders[name]) return;
  const previous = current;
  current?.panel.stop();
  if (!pages.has(name)) pages.set(name, builders[name](catalog, health));
  current = pages.get(name);
  if (name === 'clone' && previous?.text && current.text && !current.text.value) current.text.value = previous.text.value;
  document.querySelector('#page').replaceChildren(current.element);
  document.querySelectorAll('nav a').forEach(a => { if (a.pathname === '/' + name) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  if (push) history.pushState({}, '', url.pathname + url.search);
  const job = url.searchParams.get('job');
  if (job && /^[0-9a-f-]{36}$/.test(job)) current.panel.watch(job, false);
  translate(); document.title = `${t(name)} · Bangla Voice Studio`;
  if (focus) document.querySelector('#main').focus();
}
try {
  health = await api('/health'); catalog = (await api('/engines?limit=100')).items;
  document.querySelector('#demo-banner').hidden = !health.test_mode;
  document.querySelector('#status-strip').textContent = t(health.offline ? 'offline' : 'online') + (health.ffmpeg_available ? '' : ' · ' + t('noFfmpeg'));
  navigate(location.href);
  document.addEventListener('click', event => {
    const anchor = event.target.closest('a');
    if (!anchor || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    if (anchor.origin === location.origin && builders[anchor.pathname.slice(1)] && !anchor.hash) { event.preventDefault(); navigate(anchor.href, { push: true, focus: true }); }
  });
  addEventListener('popstate', () => navigate(location.href, { focus: true }));
} catch (error) { document.querySelector('#page').replaceChildren(el('p', { role: 'alert', class: 'notice', text: error.message })); }
