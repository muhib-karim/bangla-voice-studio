export let locale = localStorage.getItem('bvs-language') === 'en' ? 'en' : 'bn';
const messages = {
  skip: ['মূল অংশে যান', 'Skip to content'], navigation: ['পাতার তালিকা', 'Navigation'],
  speak: ['বলুন', 'Speak'], clone: ['কণ্ঠ অনুকরণ', 'Clone'], transcribe: ['প্রতিলিপি', 'Transcribe'],
  audiobook: ['অডিওবই', 'Audiobook'], engines: ['ইঞ্জিন', 'Engines'], text: ['লেখা', 'Text'],
  dark: ['গাঢ় রং', 'Dark theme'], light: ['হালকা রং', 'Light theme'],
  local: ['লেখা ও অডিও এই কম্পিউটারেই থাকে।', 'Text and audio stay on this computer.'],
  demo: ['ডেমো: পরীক্ষার সুর ও নমুনা প্রতিলিপি।', 'Demo mode: generated tones and sample transcripts.'],
  engine: ['ইঞ্জিন', 'Engine'], description: ['কণ্ঠের বর্ণনা', 'Voice description'],
  preview: ['পড়ার রূপ দেখুন', 'Preview reading'], create: ['অডিও তৈরি করুন', 'Create audio'],
  createBook: ['অডিওবই তৈরি করুন', 'Create audiobook'], createTranscript: ['প্রতিলিপি তৈরি করুন', 'Create transcript'],
  chapters: ['অধ্যায় দেখুন', 'Preview chapters'], title: ['শিরোনাম', 'Title'], author: ['লেখক', 'Author'],
  audio: ['অডিও ফাইল', 'Audio file'], reference: ['রেফারেন্স অডিও', 'Reference audio'],
  referenceText: ['রেফারেন্সের কথা', 'Reference transcript'], permission: ['অনুমতি আছে এমন কণ্ঠ ব্যবহার করুন।', 'Use a voice you have permission to use.'],
  wavHelp: ['মনো PCM16 WAV ফাইল দিন।', 'Upload a mono PCM16 WAV file.'],
  referenceHelp: ['৩–৩০ সেকেন্ড, সর্বোচ্চ ২০ MB।', '3–30 seconds, at most 20 MB.'],
  language: ['ভাষা', 'Language'], advanced: ['অতিরিক্ত সেটিং', 'Advanced settings'],
  normalize: ['সংখ্যা ও তারিখের পড়ার রূপ ব্যবহার করুন', 'Normalize numbers and dates'],
  seed: ['সিড', 'Seed'], maxChars: ['প্রতি অংশে সর্বোচ্চ অক্ষর', 'Maximum characters per chunk'],
  pause: ['অধ্যায়ের বিরতি (মিলিসেকেন্ড)', 'Chapter pause (milliseconds)'],
  wordTimes: ['শব্দের সময় রাখুন', 'Word timestamps'], captions: ['সাবটাইটেল', 'Captions'],
  results: ['ফলাফল', 'Results'], noResult: ['কাজ শেষ হলে অডিও ও ফাইল এখানে পাবেন।', 'Audio and files appear here when the job finishes.'],
  cancel: ['বাতিল করুন', 'Cancel job'], resume: ['আবার চালান', 'Resume audiobook'],
  retry: ['আবার দেখুন', 'Reconnect'], error: ['সমস্যা ঠিক করে আবার চেষ্টা করুন', 'Check these fields and try again'],
  required: ['এই ঘরটি পূরণ করুন।', 'Complete this field.'], noEngine: ['প্রথমে ইঞ্জিন প্রস্তুত করুন।', 'Prepare an engine on the Engines page first.'],
  setup: ['ইঞ্জিন প্রস্তুত করুন', 'Set up engines'], job: ['কাজের অবস্থা', 'Job status'],
  useReference: ['রেফারেন্স কণ্ঠ ব্যবহার করুন', 'Use a reference voice'],
  offline: ['মডেল ডাউনলোড বন্ধ', 'Model downloads disabled'], online: ['শুধু অনুরোধ করলে মডেল ডাউনলোড হবে', 'Models download only on explicit request'],
  noFfmpeg: ['কয়েকটি কাজের জন্য ffmpeg ইনস্টল করুন।', 'Install ffmpeg for multi-unit audio, references and books.'],
  source: ['মূল লেখা', 'Original text'], spoken: ['পড়ার রূপ', 'Spoken text'],
  bookFile: ['বইয়ের ফাইল (ঐচ্ছিক)', 'Book file (optional)'],
  bookHelp: ['লেখা দিন অথবা UTF-8 .txt/.md ফাইল বাছুন, সর্বোচ্চ ১ MB।', 'Paste text or choose a UTF-8 .txt/.md file, at most 1 MB.'],
  download: ['মডেল ডাউনলোড করুন', 'Download model'], planned: ['এখনও প্রকাশিত হয়নি', 'Not published yet'],
  install: ['ইনস্টল কমান্ড', 'Install command'], status: ['অবস্থা', 'Status'], license: ['লাইসেন্স', 'License'],
  capability: ['সুবিধা', 'Capabilities'], size: ['মডেলের আকার', 'Model size'], unknown: ['অজানা', 'Unknown'],
  emptyTranscript: ['কথা শনাক্ত হয়নি।', 'No speech detected.'],
  formats: ['এই সংস্করণে WAV অডিও, SRT ও VTT আছে। MP3/M4B পরে যোগ হবে।', 'This version exports WAV, SRT and VTT. MP3/M4B are deferred.'],
  cacheHits: ['আগের যাচাই করা ক্যাশ অংশ পুনর্ব্যবহার', 'Reused cached chunks'],
  remove: ['অডিও সরান', 'Remove audio'], loading: ['লোড হচ্ছে…', 'Loading…'],
};
export function t(key) { return messages[key]?.[locale === 'en' ? 1 : 0] ?? key; }
export function label(node, key) { node.dataset.i18n = key; translate(node); return node; }
export function translate(root = document) {
  const nodes = root instanceof Element && root.dataset.i18n ? [root, ...root.querySelectorAll('[data-i18n]')] : root.querySelectorAll('[data-i18n]');
  for (const node of nodes) {
    const pair = messages[node.dataset.i18n];
    if (!pair) continue;
    node.replaceChildren(document.createTextNode(pair[locale === 'en' ? 1 : 0]));
    if (locale === 'bn') {
      const secondary = document.createElement('span'); secondary.lang = 'en'; secondary.textContent = pair[1]; node.append(secondary);
    }
  }
}
export function changeLocale() {
  locale = locale === 'bn' ? 'en' : 'bn';
  localStorage.setItem('bvs-language', locale);
  document.documentElement.lang = locale;
  document.querySelector('#language').textContent = locale === 'bn' ? 'English' : 'বাংলা';
  translate();
}
