import { submit } from '../api.js';
import { label, t } from '../i18n.js';
import { jobPanel } from '../jobs.js';
import { button, el, heading } from '../ui.js';

export function build(engines, health) {
  const panel = jobPanel(), root = el('section', {}, heading(1, 'engines'));
  root.append(label(el('p', { class: 'notice' }), health.offline ? 'offline' : 'online'));
  for (const engine of engines) {
    const row = el('section', { class: 'engine-row' }, el('h2', { text: engine.display_name }));
    const data = el('dl');
    const cap = engine.capabilities;
    for (const [key, value] of [
      ['status', engine.availability === 'planned' ? t('planned') : engine.availability],
      ['capability', `${cap.languages.join(', ')}; cloning: ${cap.cloning}; description: ${cap.voice_description}; ${cap.sample_rate_hz ?? t('unknown')} Hz`],
      ['size', engine.model_bytes_on_disk == null ? t('unknown') : `${engine.model_bytes_on_disk} bytes`],
      ['license', `${engine.license.identifier}; ${engine.license.commercial_use}`],
    ]) data.append(label(el('dt'), key), el('dd', { text: value }));
    row.append(data);
    if (engine.model_id) row.append(el('a', { href: 'https://huggingface.co/' + encodeURI(engine.model_id), target: '_blank', rel: 'noopener noreferrer', text: engine.model_id }));
    for (const warning of engine.readiness_warnings) row.append(el('p', { class: 'notice', text: warning }));
    if (engine.install_hint) row.append(heading(3, 'install'), el('code', { text: engine.install_hint }));
    const download = button('download', { disabled: health.offline || !engine.installed || !['mms', 'faster-whisper'].includes(engine.id) || engine.availability === 'ready' });
    const message = el('p', { role: 'status' });
    download.onclick = async () => {
      download.disabled = true;
      try { const job = await submit(download, '/engines/' + engine.id + '/downloads', {}); panel.watch(job.id); }
      catch (error) { message.textContent = error.message; download.disabled = false; }
    };
    row.append(el('div', { class: 'actions' }, download), message); root.append(row);
  }
  root.append(panel.element);
  return { element: root, panel };
}
