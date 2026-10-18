import { api, submit } from './api.js';
import { label, t } from './i18n.js';
import { button, el, heading } from './ui.js';

export function jobPanel() {
  const panel = el('section', { class: 'result-pane', 'aria-label': t('results') }, heading(2, 'results'));
  const state = el('p', { 'data-testid': 'job-state', role: 'status', 'aria-live': 'polite' });
  const progress = el('progress', { 'aria-label': t('job'), hidden: true });
  const detail = el('p', { class: 'muted' });
  const result = el('div', { 'data-testid': 'results' }, label(el('p', { class: 'muted' }), 'noResult'));
  const cancel = button('cancel', { hidden: true });
  const resume = button('resume', { hidden: true });
  const retry = button('retry', { hidden: true });
  const controls = el('div', { class: 'actions' }, cancel, resume, retry);
  panel.append(state, progress, detail, controls, result);
  let timer, jobId, active = false, lastPhase = '', rendered = false;
  function stop() { active = false; clearTimeout(timer); }
  function files(artifacts) {
    const list = el('ul');
    for (const artifact of artifacts) {
      if (!/^\/api\/v1\/artifacts\/[0-9a-f-]+$/.test(artifact.download_url)) continue;
      list.append(el('li', {}, el('a', { href: artifact.download_url, download: artifact.name, text: artifact.name })));
    }
    return list;
  }
  function render(job) {
    result.replaceChildren();
    const data = job.result;
    if (!data) return;
    result.append(el('p', { class: 'muted', text: `${job.engine_id ?? ''} · ${job.model_revision ?? 'test / unpinned'}` }));
    for (const warning of data.warnings ?? []) result.append(el('p', { class: 'notice', text: warning }));
    if (data.type === 'transcript') {
      result.append(el('p', { class: 'preview-text', text: data.text || t('emptyTranscript') }));
      for (const segment of data.segments) result.append(el('p', { text: `${segment.start_seconds.toFixed(2)}–${segment.end_seconds.toFixed(2)} s: ${segment.text}` }));
    }
    const audio = (data.artifacts ?? []).find(a => a.media_type === 'audio/wav');
    if (audio) result.append(el('p', { text: `${audio.duration_seconds?.toFixed(2) ?? ''} s` }), el('audio', { controls: true, src: audio.download_url, preload: 'metadata', 'aria-label': audio.name }));
    result.append(files(data.artifacts ?? []));
    if (data.type === 'audiobook') result.append(el('p', { 'data-testid': 'cache-hits', text: `${t('cacheHits')}: ${data.cache_hits ?? 0}` }));
    for (const chapter of data.chapters ?? []) {
      result.append(el('h3', { text: chapter.title }), files(chapter.artifacts));
    }
    if (data.type === 'download') result.append(el('p', { text: `${data.engine_id}: ${data.verified ? 'verified' : 'incomplete'} · ${data.model_revision}` }));
  }
  async function poll() {
    if (!active) return;
    try {
      const job = await api('/jobs/' + encodeURIComponent(jobId));
      if (!active || job.id !== jobId) return;
      const phase = job.state + ': ' + job.progress.phase;
      if (phase !== lastPhase) { state.textContent = phase; lastPhase = phase; }
      const terminal = ['succeeded', 'failed', 'cancelled', 'interrupted'].includes(job.state);
      progress.hidden = terminal;
      if (job.progress.total > 0) { progress.max = job.progress.total; progress.value = job.progress.completed; }
      else progress.removeAttribute('value');
      const elapsed = Math.max(0, Math.round((Date.now() - Date.parse(job.created_at)) / 1000));
      detail.textContent = `${job.progress.message} · ${elapsed} s`;
      cancel.hidden = terminal; cancel.disabled = job.state === 'cancelling';
      resume.hidden = !(job.kind === 'audiobook' && ['failed', 'cancelled', 'interrupted'].includes(job.state));
      retry.hidden = true;
      if (job.error) result.replaceChildren(el('p', { class: 'notice', text: `${job.error.code}: ${job.error.message}` }));
      if (job.state === 'succeeded' && !rendered) { render(job); rendered = true; }
      if (!terminal) timer = setTimeout(poll, document.hidden ? 5000 : 1000);
    } catch (error) { state.textContent = error.message; retry.hidden = false; }
  }
  function watch(id, updateURL = true) {
    stop(); active = true; jobId = id; rendered = false; lastPhase = '';
    result.replaceChildren(label(el('p'), 'loading'));
    if (updateURL) history.replaceState({}, '', location.pathname + '?job=' + encodeURIComponent(id));
    poll();
  }
  cancel.onclick = async () => {
    cancel.disabled = true;
    try { await api('/jobs/' + jobId + '/cancellations', { method: 'POST', body: {} }); clearTimeout(timer); await poll(); }
    catch (error) { state.textContent = error.message; cancel.disabled = false; }
  };
  resume.onclick = async () => {
    resume.disabled = true;
    try { const job = await submit(resume, '/jobs/' + jobId + '/resumptions', {}); watch(job.id); }
    catch (error) { state.textContent = error.message; }
    finally { resume.disabled = false; }
  };
  retry.onclick = () => { clearTimeout(timer); poll(); };
  return { element: panel, watch, stop };
}
