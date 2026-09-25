import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import FileDropzone from '../components/FileDropzone';
import {
  Alert, CourseTag, DeadlineText, EmptyState, GradeMark, Ledger, Loading, PageHeader, StatusStamp,
} from '../components/ui';
import { useAuth } from '../context/AuthContext';
import useLoad from '../hooks/useLoad';
import { getErrorMessage } from '../services/api';
import { assignmentService } from '../services/assignmentService';
import { openSubmissionFile, submissionService } from '../services/submissionService';
import { newIdempotencyKey, validateFile } from '../utils/fileValidation';
import { courseTone, formatBytes, formatDateTime, formatMarks } from '../utils/format';

export default function AssignmentDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { data: assignment, error, loading, reload } = useLoad(() => assignmentService.get(id), [id]);

  if (loading && !assignment) return <Loading />;
  if (error) return <Alert>{error}</Alert>;

  const isStudent = user.role === 'student';
  return (
    <>
      <PageHeader
        eyebrow={<><CourseTag code={assignment.course_code} tone={courseTone(assignment.course_code)} /> {assignment.course_name}</>}
        title={assignment.title}
        actions={!isStudent && <TeacherActions assignment={assignment} />}
      >
        <DeadlineText deadline={assignment.deadline} />
      </PageHeader>

      <div className="columns columns--wide-left">
        <section className="card">
          <h2 className="section-title">Instructions</h2>
          <p className="prose">{assignment.description || 'No written instructions.'}</p>
        </section>
        <section className="card">
          <h2 className="section-title">Rules</h2>
          <dl className="facts">
            <div><dt>Maximum marks</dt><dd>{formatMarks(assignment.max_marks)}</dd></div>
            <div><dt>File types</dt><dd>{assignment.allowed_file_types.map((t) => `.${t}`).join(' ')}</dd></div>
            <div><dt>Max file size</dt><dd>{assignment.max_file_size_mb} MB</dd></div>
            <div><dt>Late work</dt><dd>{assignment.allow_late_submission ? 'Accepted, marked late' : 'Not accepted'}</dd></div>
            <div><dt>Resubmission</dt><dd>{assignment.allow_resubmission ? 'Allowed until graded' : 'One upload only'}</dd></div>
          </dl>
        </section>
      </div>

      {isStudent ? <StudentSubmissionPanel assignment={assignment} onChange={reload} /> : <TeacherSubmissionsPanel assignment={assignment} />}
    </>
  );
}

/* ---------------------------------------------------------------- student */
function StudentSubmissionPanel({ assignment, onChange }) {
  const submissionId = assignment.my_submission_id;
  const { data: submission, loading, setData } = useLoad(
    () => (submissionId ? submissionService.get(submissionId) : Promise.resolve(null)),
    [submissionId],
  );
  const [file, setFile] = useState(null);
  const [key, setKey] = useState('');
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  if (loading && !submission) return <Loading />;

  const windowOpen = !assignment.is_past_deadline || assignment.allow_late_submission;
  const canUpload = submission ? submission.can_resubmit : windowOpen;

  const chooseFile = (picked) => {
    setNotice('');
    const problem = validateFile(picked, assignment.allowed_file_types, assignment.max_file_size_mb);
    setError(problem || '');
    setFile(problem ? null : picked);
    setKey(newIdempotencyKey()); // same key if this exact attempt is retried
  };

  const upload = async () => {
    setBusy(true);
    setError('');
    setProgress(0);
    try {
      const result = await submissionService.submit(assignment.assignment_id, file, key, setProgress);
      setData(result.submission);
      setNotice(result.message);
      setFile(null);
      onChange();
    } catch (err) {
      setError(`${getErrorMessage(err, 'Upload failed.')} Your file is still selected - press Upload to retry.`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card submission-panel">
      <h2 className="section-title">Your submission</h2>
      <Alert kind="success" onClose={() => setNotice('')}>{notice}</Alert>

      {submission ? (
        <SubmissionSummary submission={submission} />
      ) : (
        <p className="muted">You have not handed this in yet.</p>
      )}

      {canUpload ? (
        <div className="upload">
          {assignment.is_past_deadline && (
            <Alert kind="warn">The deadline has passed. Anything you upload now is recorded as late.</Alert>
          )}
          <FileDropzone
            allowedTypes={assignment.allowed_file_types}
            maxMb={assignment.max_file_size_mb}
            file={file}
            onFile={chooseFile}
            disabled={busy}
          />
          <Alert>{error}</Alert>
          {busy && (
            <div className="progress progress--upload" aria-label={`Uploading ${progress}%`}>
              <span className="progress__bar" style={{ width: `${progress}%` }} />
            </div>
          )}
          <button type="button" className="btn btn--primary" disabled={!file || busy} onClick={upload}>
            {busy ? `Uploading… ${progress}%` : submission ? 'Upload replacement' : 'Upload submission'}
          </button>
        </div>
      ) : (
        !submission && <Alert kind="warn">The deadline has passed and this assignment no longer accepts uploads.</Alert>
      )}
    </section>
  );
}

function SubmissionSummary({ submission }) {
  const [error, setError] = useState('');
  const open = (disposition) => openSubmissionFile(submission.submission_id, disposition).catch((err) => setError(getErrorMessage(err)));

  return (
    <div className="receipt">
      <div className="receipt__row">
        <StatusStamp status={submission.submission_status} late={submission.is_late} />
        <span className="receipt__file">{submission.file_name}</span>
        <span className="muted small">{formatBytes(submission.file_size)} · attempt {submission.attempt_number}</span>
      </div>
      <p className="muted small">Received {formatDateTime(submission.submitted_at)}</p>
      <div className="button-row">
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => open('inline')}>Open</button>
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => open('attachment')}>Download</button>
        <Link className="btn btn--ghost btn--sm" to={`/submissions/${submission.submission_id}`}>Details</Link>
      </div>
      <Alert>{error}</Alert>
      {submission.submission_status === 'GRADED' && (
        <div className="feedback-box">
          <GradeMark marks={submission.marks} max={submission.max_marks} size="lg" />
          <p className="margin-note margin-note--large">{submission.feedback || 'No written feedback.'}</p>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- teacher */
function TeacherActions({ assignment }) {
  const navigate = useNavigate();
  const [error, setError] = useState('');

  const remove = async () => {
    const hasWork = assignment.submission_count > 0;
    const question = hasWork
      ? `Delete "${assignment.title}" and its ${assignment.submission_count} submission file(s)? This cannot be undone.`
      : `Delete "${assignment.title}"?`;
    if (!window.confirm(question)) return;
    try {
      await assignmentService.remove(assignment.assignment_id, hasWork);
      navigate('/assignments', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="button-row">
      <Link className="btn btn--ghost" to={`/assignments/${assignment.assignment_id}/edit`}>Edit</Link>
      <button type="button" className="btn btn--danger" onClick={remove}>Delete</button>
      <Alert>{error}</Alert>
    </div>
  );
}

function TeacherSubmissionsPanel({ assignment }) {
  const { data, error, loading } = useLoad(() => assignmentService.submissions(assignment.assignment_id), [assignment.assignment_id]);

  if (loading) return <Loading />;
  if (error) return <Alert>{error}</Alert>;
  const { summary, entries } = data;

  return (
    <section className="card">
      <h2 className="section-title">Submissions</h2>
      <Ledger
        items={[
          { label: 'Enrolled', value: summary.enrolled },
          { label: 'Submitted', value: summary.submitted },
          { label: 'Missing', value: summary.not_submitted, tone: summary.not_submitted ? 'warn' : '' },
          { label: 'Late', value: summary.late, tone: summary.late ? 'late' : '' },
          { label: 'To mark', value: summary.pending_review },
          { label: 'Graded', value: summary.graded, tone: 'graded' },
        ]}
      />
      {entries.length === 0 ? (
        <EmptyState title="No students enrolled">Share the course join code from the Courses page.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Student</th><th>Status</th><th>Received</th><th>File</th><th>Marks</th><th /></tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.student_id}>
                  <td><span className="cell-title">{e.student_name}</span><span className="cell-sub">{e.student_email}</span></td>
                  <td><StatusStamp status={e.status} late={e.submission?.is_late} /></td>
                  <td className="nowrap">{e.submission ? formatDateTime(e.submission.submitted_at) : '—'}</td>
                  <td>{e.submission ? <span className="mono small">{e.submission.file_name}</span> : '—'}</td>
                  <td>{e.submission?.marks != null ? `${formatMarks(e.submission.marks)} / ${formatMarks(assignment.max_marks)}` : '—'}</td>
                  <td className="align-right">
                    {e.submission && (
                      <Link className="btn btn--ghost btn--sm" to={`/submissions/${e.submission.submission_id}`}>
                        {e.status === 'GRADED' ? 'Review' : 'Mark'}
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
