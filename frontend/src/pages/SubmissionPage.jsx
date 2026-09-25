import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert, CourseTag, GradeMark, Loading, PageHeader, StatusStamp } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import useLoad from '../hooks/useLoad';
import { getErrorMessage } from '../services/api';
import { openSubmissionFile, submissionService } from '../services/submissionService';
import { courseTone, formatBytes, formatDateTime, formatMarks, relativeTime } from '../utils/format';

/** One submission: file + metadata, and either the grading form (teacher) or the feedback (student). */
export default function SubmissionPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: submission, error, loading, setData } = useLoad(() => submissionService.get(id), [id]);
  const [fileError, setFileError] = useState('');

  if (loading && !submission) return <Loading />;
  if (error) return <Alert>{error}</Alert>;

  const isStudent = user.role === 'student';
  const open = (disposition) => {
    setFileError('');
    openSubmissionFile(submission.submission_id, disposition).catch((err) => setFileError(getErrorMessage(err)));
  };
  const lateBy = submission.is_late ? relativeTime(submission.deadline).replace('ago', 'late') : null;

  return (
    <>
      <PageHeader
        eyebrow={<><CourseTag code={submission.course_code} tone={courseTone(submission.course_code)} /> Submission #{submission.submission_id}</>}
        title={submission.assignment_title}
        actions={<Link className="btn btn--ghost" to={`/assignments/${submission.assignment_id}`}>Back to assignment</Link>}
      >
        {isStudent ? 'Your submission' : `Submitted by ${submission.student_name} (${submission.student_email})`}
      </PageHeader>

      <div className="columns columns--wide-left">
        <section className="card stack">
          <div className="receipt__row">
            <StatusStamp status={submission.submission_status} late={submission.is_late} />
            <span className="receipt__file">{submission.file_name}</span>
          </div>
          <div className="button-row">
            <button type="button" className="btn btn--primary btn--sm" onClick={() => open('inline')}>Open file</button>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => open('attachment')}>Download</button>
          </div>
          <Alert>{fileError}</Alert>

          <dl className="facts facts--mono">
            <div><dt>Received</dt><dd>{formatDateTime(submission.submitted_at)}{submission.is_late && ` · ${lateBy}`}</dd></div>
            <div><dt>Deadline</dt><dd>{formatDateTime(submission.deadline)}</dd></div>
            <div><dt>Attempt</dt><dd>{submission.attempt_number}</dd></div>
            <div><dt>Size / type</dt><dd>{formatBytes(submission.file_size)} · {submission.content_type}</dd></div>
            <div><dt>Object key</dt><dd className="break">{submission.storage_path}</dd></div>
            <div><dt>Storage URI</dt><dd className="break">{submission.file_url}</dd></div>
            <div><dt>SHA-256</dt><dd className="break">{submission.checksum_sha256}</dd></div>
          </dl>
          <p className="muted small">
            Files are kept in private object storage. “Open” and “Download” use a signed link that expires after a few minutes.
          </p>
        </section>

        {isStudent ? <FeedbackView submission={submission} /> : <GradeForm submission={submission} onSaved={setData} />}
      </div>
    </>
  );
}

function FeedbackView({ submission }) {
  const { data: feedback, error, loading } = useLoad(() => submissionService.feedback(submission.submission_id), [submission.submission_id]);
  if (loading) return <section className="card"><Loading /></section>;
  if (error) return <section className="card"><Alert>{error}</Alert></section>;

  return (
    <section className="card">
      <h2 className="section-title">Marks & feedback</h2>
      {feedback.marks == null ? (
        <p className="muted">Not graded yet. You will see your marks and your teacher’s comments here.</p>
      ) : (
        <div className="feedback-box">
          <GradeMark marks={feedback.marks} max={feedback.max_marks} size="lg" />
          <p className="margin-note margin-note--large">{feedback.feedback || 'No written feedback.'}</p>
          <p className="muted small">Marked by {feedback.graded_by_name} · {formatDateTime(feedback.graded_at)}</p>
        </div>
      )}
    </section>
  );
}

function GradeForm({ submission, onSaved }) {
  const [marks, setMarks] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setMarks(submission.marks ?? '');
    setFeedback(submission.feedback ?? '');
  }, [submission.submission_id, submission.marks, submission.feedback]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const value = Number(marks);
    if (marks === '' || Number.isNaN(value)) return setError('Enter the marks awarded.');
    if (value < 0 || value > submission.max_marks) {
      return setError(`Marks must be between 0 and ${formatMarks(submission.max_marks)}.`);
    }
    setError('');
    setSaving(true);
    try {
      const saved = await submissionService.grade(submission.submission_id, value, feedback);
      onSaved(saved);
      setNotice('Grade saved. The student can see it now.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the grade.'));
    } finally {
      setSaving(false);
    }
  };

  const graded = submission.marks != null;
  return (
    <form className="card form grade-form" onSubmit={handleSubmit} noValidate>
      <h2 className="section-title">{graded ? 'Update grade' : 'Mark this submission'}</h2>
      {graded && <GradeMark marks={submission.marks} max={submission.max_marks} size="lg" />}
      <Alert kind="success" onClose={() => setNotice('')}>{notice}</Alert>
      <Alert>{error}</Alert>
      <label className="field">
        <span className="field__label">Marks (out of {formatMarks(submission.max_marks)})</span>
        <input
          type="number"
          min="0"
          max={submission.max_marks}
          step="0.5"
          value={marks}
          onChange={(e) => setMarks(e.target.value)}
          className="input--marks"
        />
      </label>
      <label className="field">
        <span className="field__label">Written feedback</span>
        <textarea rows={7} maxLength={5000} value={feedback} onChange={(e) => setFeedback(e.target.value)}
          placeholder="What was done well, and what to improve next time." />
        <span className="field__hint">{feedback.length}/5000</span>
      </label>
      <button type="submit" className="btn btn--primary" disabled={saving}>
        {saving ? 'Saving…' : graded ? 'Save new grade' : 'Save grade'}
      </button>
    </form>
  );
}
