import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, CourseTag, EmptyState, Loading, PageHeader, StatusStamp } from '../components/ui';
import useLoad from '../hooks/useLoad';
import { getErrorMessage } from '../services/api';
import { openSubmissionFile, submissionService } from '../services/submissionService';
import { courseTone, formatBytes, formatDateTime, formatMarks } from '../utils/format';

export default function MySubmissionsPage() {
  const { data, error, loading } = useLoad(() => submissionService.mine(), []);
  const [actionError, setActionError] = useState('');

  const download = (id) => openSubmissionFile(id, 'attachment').catch((err) => setActionError(getErrorMessage(err)));

  return (
    <>
      <PageHeader eyebrow="Everything you have handed in" title="My submissions" />
      {loading && <Loading />}
      <Alert>{error || actionError}</Alert>
      {data && data.length === 0 && (
        <EmptyState title="No submissions yet" action={<Link className="btn btn--primary" to="/assignments">See assignments</Link>} />
      )}
      {data && data.length > 0 && (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr><th>Assignment</th><th>Received</th><th>Status</th><th>File</th><th>Marks</th><th /></tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.submission_id}>
                  <td>
                    <Link className="cell-title" to={`/assignments/${s.assignment_id}`}>{s.assignment_title}</Link>
                    <span className="cell-sub"><CourseTag code={s.course_code} tone={courseTone(s.course_code)} /> attempt {s.attempt_number}</span>
                  </td>
                  <td className="nowrap">{formatDateTime(s.submitted_at)}</td>
                  <td><StatusStamp status={s.submission_status} late={s.is_late} /></td>
                  <td><span className="mono small">{s.file_name}</span><span className="cell-sub">{formatBytes(s.file_size)}</span></td>
                  <td>{s.marks != null ? <span className="red-pen">{formatMarks(s.marks)}/{formatMarks(s.max_marks)}</span> : '—'}</td>
                  <td className="align-right nowrap">
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => download(s.submission_id)}>Download</button>{' '}
                    <Link className="btn btn--ghost btn--sm" to={`/submissions/${s.submission_id}`}>
                      {s.submission_status === 'GRADED' ? 'Feedback' : 'Details'}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
