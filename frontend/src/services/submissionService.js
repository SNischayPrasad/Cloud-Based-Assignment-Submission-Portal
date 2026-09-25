import api from './api';

export const submissionService = {
  /**
   * Upload a file for an assignment.
   * `idempotencyKey` stays the same when the student retries the same file,
   * so a retry after a dropped connection never creates a duplicate.
   */
  submit: (assignmentId, file, idempotencyKey, onProgress) => {
    const form = new FormData();
    form.append('file', file);
    return api
      .post(`/assignments/${assignmentId}/submit`, form, {
        headers: { 'Idempotency-Key': idempotencyKey },
        timeout: 120000,
        onUploadProgress: (event) => {
          if (onProgress && event.total) onProgress(Math.round((event.loaded / event.total) * 100));
        },
      })
      .then((r) => r.data);
  },
  mine: () => api.get('/submissions/me').then((r) => r.data),
  get: (id) => api.get(`/submissions/${id}`).then((r) => r.data),
  feedback: (id) => api.get(`/submissions/${id}/feedback`).then((r) => r.data),
  grade: (id, marks, feedback) => api.post(`/submissions/${id}/grade`, { marks, feedback }).then((r) => r.data),
  /** Ask the API for a short-lived signed URL, then open it. */
  signedUrl: (id, disposition = 'attachment') =>
    api.get(`/submissions/${id}/download`, { params: { disposition } }).then((r) => r.data),
};

/**
 * Open a submission file. The blank tab is opened synchronously (inside the
 * click handler) so pop-up blockers allow it; it is pointed at the signed
 * URL once the API returns it.
 */
export async function openSubmissionFile(id, disposition = 'inline') {
  const tab = disposition === 'inline' ? window.open('', '_blank') : null;
  try {
    const { url } = await submissionService.signedUrl(id, disposition);
    if (tab) tab.location.href = url;
    else window.location.assign(url); // attachment -> browser downloads, page stays
  } catch (error) {
    if (tab) tab.close();
    throw error;
  }
}
