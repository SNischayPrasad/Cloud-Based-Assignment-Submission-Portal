/**
 * Client-side file checks. These only give instant feedback - the server
 * repeats every check (plus a content check) because browsers can be bypassed.
 */
export function getExtension(filename) {
  const dot = filename.lastIndexOf('.');
  return dot === -1 ? '' : filename.slice(dot + 1).toLowerCase();
}

export function validateFile(file, allowedTypes, maxMb) {
  if (!file) return 'Choose a file to upload.';
  const ext = getExtension(file.name);
  if (!allowedTypes.includes(ext)) {
    return `.${ext || '?'} files are not accepted. Upload one of: ${allowedTypes.map((t) => `.${t}`).join(', ')}.`;
  }
  if (file.size === 0) return 'This file is empty.';
  if (file.size > maxMb * 1024 * 1024) return `This file is larger than the ${maxMb} MB limit.`;
  return null;
}

export function newIdempotencyKey() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
