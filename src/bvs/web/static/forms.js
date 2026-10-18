import { api, submit, upload } from './api.js';
import { label, t } from './i18n.js';
import { jobPanel } from './jobs.js';
import { button, checkbox, clearErrors, el, field, formShell, heading, showError, validate } from './ui.js';

export function workspace(kind, engines, health) {
  const form = formShell(kind);
  const panel = jobPanel();
  const root = el('section', {}, heading(1, kind));
  const layout = el('div', { class: 'workspace' }, form, panel.element); root.append(layout);
  const isASR = kind === 'transcribe', isBook = kind === 'audiobook', isClone = kind === 'clone';
  if (isBook) {
    field(form, 'title', 'title', 'input', { required: true, maxlength: 200 });
    field(form, 'author', 'author', 'input', { maxlength: 200 });
  }
  const text = !isASR ? field(form, 'text', 'text', 'textarea', { required: !isBook, maxlength: isBook ? 1000000 : 10000, lang: 'bn' }) : null;
  const sourceFile = isASR || isBook ? field(form, 'file', isASR ? 'audio' : 'bookFile', 'input', { type: 'file', accept: isASR ? '.wav' : '.txt,.md', required: isASR }) : null;
  if (sourceFile) form.append(label(el('p', { class: 'help' }), isASR ? 'wavHelp' : 'bookHelp'));
  const engineSelect = field(form, 'engine_id', 'engine', 'select', { required: true });
  const choices = engines.filter(e => e.kind === (isASR ? 'asr' : 'tts') && (!isClone || e.capabilities.cloning) && (health.test_mode || e.maturity !== 'test-only') && (!e.capabilities.reference_required || isClone));
  engineSelect.append(el('option', { value: '', text: t('noEngine') }));
  for (const engine of choices) {
    engineSelect.append(el('option', { value: engine.id, disabled: engine.availability !== 'ready', text: `${engine.display_name} · ${engine.license.identifier} · ${engine.availability}` }));
  }
  const preferred = choices.find(e => e.availability === 'ready' && (health.test_mode ? e.maturity === 'test-only' : true));
  if (preferred) engineSelect.value = preferred.id;
  form.append(label(el('a', { href: '/engines' }), 'setup'));
  if (!isClone && !isASR) form.append(label(el('a', { href: '/clone', class: 'button' }), 'useReference'));
  let reference, referenceText;
  if (isClone) {
    form.append(label(el('p', { class: 'notice' }), 'permission'));
    reference = field(form, 'reference', 'reference', 'input', { type: 'file', accept: '.wav', required: true });
    form.append(label(el('p', { class: 'help' }), 'referenceHelp'));
    referenceText = field(form, 'transcript', 'referenceText', 'textarea', { required: true, maxlength: 1000 });
  }
  const language = field(form, 'language', 'language', 'select');
  for (const [value, title] of [['bn', 'বাংলা / Bangla'], ['en', 'English'], ...(isASR ? [['auto', 'স্বয়ংক্রিয় / Auto']] : [])]) language.append(el('option', { value, text: title }));
  const description = !isASR ? field(form, 'voice_description', 'description', 'input', { maxlength: 1000 }) : null;
  const advanced = el('details', {}, label(el('summary'), 'advanced'));
  const options = el('div'); options.id = form.id + '-options'; advanced.append(options); form.append(advanced);
  const normalized = !isASR ? checkbox(options, 'normalize', 'normalize') : null;
  const words = isASR ? checkbox(options, 'word_timestamps', 'wordTimes') : null;
  const seed = !isASR ? field(options, 'seed', 'seed', 'input', { type: 'number', min: 0, max: 4294967295, value: 0 }) : null;
  const maxChars = isBook ? field(options, 'max_chars', 'maxChars', 'input', { type: 'number', min: 50, max: 1000, value: 300 }) : null;
  const pause = isBook ? field(options, 'chapter_pause_ms', 'pause', 'input', { type: 'number', min: 0, max: 5000, value: 750 }) : null;
  const captionSet = el('fieldset', {}, label(el('legend'), 'captions')); captionSet.id = form.id + '-captions'; options.append(captionSet);
  const srt = checkbox(captionSet, 'srt', 'SRT'), vtt = checkbox(captionSet, 'vtt', 'VTT');
  let mp3 = null, m4b = null;
  if (!isASR) {
    const formatSet = el('fieldset', {}, label(el('legend'), 'audioFormats')); formatSet.id = form.id + '-formats'; form.append(formatSet);
    checkbox(formatSet, 'wav', 'WAV').disabled = true;
    mp3 = checkbox(formatSet, 'mp3', isBook ? 'mp3Chapters' : 'MP3', isBook && !!health.ffmpeg_available);
    m4b = isBook ? checkbox(formatSet, 'm4b', 'm4bBook', !!health.ffmpeg_available) : null;
    if (!health.ffmpeg_available) for (const control of [mp3, m4b].filter(Boolean)) control.disabled = true;
  }
  form.append(label(el('p', { class: 'help' }), 'formats'));
  const preview = el('section', { 'data-testid': 'preview', hidden: true, 'aria-live': 'polite' });
  const previewButton = !isASR ? button(isBook ? 'chapters' : 'preview') : null;
  const create = button(isBook ? 'createBook' : isASR ? 'createTranscript' : 'create', { type: 'submit', class: 'primary' });
  form.append(el('div', { class: 'actions' }, ...[previewButton, create].filter(Boolean)), preview);
  const audioInput = reference ?? (isASR ? sourceFile : null);
  if (audioInput) {
    const player = el('audio', { controls: true, hidden: true, 'aria-label': 'Playback' });
    const remove = button('remove', { hidden: true });
    audioInput.after(player, remove);
    let objectURL;
    audioInput.onchange = () => {
      if (objectURL) URL.revokeObjectURL(objectURL);
      player.hidden = remove.hidden = !audioInput.files.length;
      if (audioInput.files.length) { objectURL = URL.createObjectURL(audioInput.files[0]); player.src = objectURL; }
      else player.removeAttribute('src');
    };
    remove.onclick = () => { audioInput.value = ''; audioInput.onchange(); };
  }
  engineSelect.onchange = () => {
    const engine = choices.find(e => e.id === engineSelect.value);
    if (description) { description.parentElement.hidden = !engine?.capabilities.voice_description; description.disabled = !engine?.capabilities.voice_description; }
    if (words) { words.disabled = !engine?.capabilities.word_timestamps; words.checked = !words.disabled; }
    for (const option of language.options) option.disabled = option.value !== 'auto' && !engine?.capabilities.languages.includes(option.value);
    if (language.selectedOptions[0]?.disabled) language.value = 'bn';
    create.disabled = !engine;
  }; engineSelect.onchange();
  async function bookSource() {
    const file = sourceFile.files[0];
    if (!!text.value.trim() === !!file) throw new Error(t('bookHelp'));
    if (file) return { upload_id: (await upload(file, 'book')).id };
    return { text: text.value };
  }
  if (previewButton) previewButton.onclick = async () => {
    clearErrors(form); previewButton.disabled = true;
    try {
      const data = isBook ? { ...await bookSource(), max_chars: Number(maxChars.value), normalize: normalized.checked } : { text: text.value };
      const result = await api(isBook ? '/audiobooks/previews' : '/normalizations', { method: 'POST', body: data });
      preview.replaceChildren(heading(2, isBook ? 'chapters' : 'preview'));
      if (isBook) for (const chapter of result.chapters) preview.append(el('p', { text: `${chapter.title} · ${chapter.chunk_count} chunks` }));
      else preview.append(heading(3, 'source'), el('p', { class: 'preview-text', text: text.value }), heading(3, 'spoken'), el('p', { class: 'preview-text', text: result.text }));
      for (const warning of result.warnings) preview.append(el('p', { class: 'notice', text: warning }));
      preview.hidden = false;
    } catch (error) { showError(form, error); }
    finally { previewButton.disabled = false; }
  };
  form.onsubmit = async event => {
    event.preventDefault(); if (!validate(form)) return; create.disabled = true;
    try {
      const data = { engine_id: engineSelect.value, language: language.value === 'auto' ? null : language.value, captions: [srt.checked && 'srt', vtt.checked && 'vtt'].filter(Boolean) };
      if (isASR) Object.assign(data, { upload_id: (await upload(sourceFile.files[0], 'transcription')).id, word_timestamps: words.checked });
      else {
        Object.assign(data, { text: text.value, normalize: normalized.checked, seed: Number(seed.value), formats: ['wav', mp3?.checked && 'mp3', m4b?.checked && 'm4b'].filter(Boolean) });
        if (!description.disabled && description.value.trim()) data.voice_description = description.value;
        if (isClone) data.reference = { upload_id: (await upload(reference.files[0], 'reference')).id, transcript: referenceText.value, language: language.value };
        if (isBook) { delete data.text; Object.assign(data, await bookSource(), { title: form.elements.title.value, author: form.elements.author.value, max_chars: Number(maxChars.value), chapter_pause_ms: Number(pause.value) }); }
      }
      const path = isBook ? '/audiobooks' : isASR ? '/transcriptions' : isClone ? '/clones' : '/syntheses';
      const job = await submit(form, path, data); panel.watch(job.id);
    } catch (error) { showError(form, error); }
    finally { create.disabled = !engineSelect.value; }
  };
  return { element: root, panel, text };
}
