import { Link } from 'react-router-dom';
import { Alert, CourseTag, DeadlineText, EmptyState, Ledger, Loading, PageHeader, StatusStamp } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import useLoad from '../hooks/useLoad';
import { dashboardService } from '../services/dashboardService';
import { courseTone, relativeTime } from '../utils/format';

export default function TeacherDashboard() {
  const { user } = useAuth();
  const { data, error, loading } = useLoad(() => dashboardService.teacher(), []);

  if (loading) return <Loading />;
  if (error) return <Alert>{error}</Alert>;

  const { stats, recent_uploads: uploads, upcoming_deadlines: upcoming } = data;
  const isAdmin = user.role === 'admin';

  return (
    <>
      <PageHeader
        eyebrow={isAdmin ? 'Portal overview' : 'Teacher dashboard'}
        title={isAdmin ? 'All courses' : `Welcome, ${data.teacher_name}`}
        actions={!isAdmin && <Link className="btn btn--primary" to="/assignments/new">New assignment</Link>}
      >
        {stats.pending_reviews > 0
          ? `${stats.pending_reviews} submission${stats.pending_reviews === 1 ? '' : 's'} waiting for marks.`
          : 'No submissions are waiting for marks.'}
      </PageHeader>

      <Ledger
        items={[
          { label: 'Assignments', value: stats.total_assignments },
          { label: 'Students', value: stats.total_students },
          { label: 'Submissions', value: stats.total_submissions },
          { label: 'Pending review', value: stats.pending_reviews, tone: stats.pending_reviews ? 'warn' : '' },
          { label: 'Late', value: stats.late_submissions, tone: stats.late_submissions ? 'late' : '' },
          { label: 'Graded', value: stats.graded_submissions, tone: 'graded' },
        ]}
      />

      <div className="columns columns--wide-left">
        <section className="card">
          <h2 className="section-title">Recent uploads</h2>
          {uploads.length === 0 ? (
            <EmptyState title="No uploads yet">Student submissions show up here the moment they are stored.</EmptyState>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>Student</th><th>Assignment</th><th>Received</th><th>Status</th><th /></tr>
                </thead>
                <tbody>
                  {uploads.map((u) => (
                    <tr key={u.submission_id}>
                      <td>{u.student_name}</td>
                      <td>
                        <span className="cell-title">{u.assignment_title}</span>
                        <span className="cell-sub"><CourseTag code={u.course_code} tone={courseTone(u.course_code)} /> {u.file_name}</span>
                      </td>
                      <td className="nowrap">{relativeTime(u.submitted_at)}</td>
                      <td><StatusStamp status={u.submission_status} late={u.is_late} /></td>
                      <td className="align-right">
                        <Link className="btn btn--ghost btn--sm" to={`/submissions/${u.submission_id}`}>
                          {u.submission_status === 'GRADED' ? 'View' : 'Mark'}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card">
          <h2 className="section-title">Upcoming deadlines</h2>
          {upcoming.length === 0 ? (
            <EmptyState title="No open assignments" action={!isAdmin && <Link to="/assignments/new">Create one</Link>} />
          ) : (
            <ul className="list">
              {upcoming.map((a) => {
                const pct = a.enrolled ? Math.round((a.submissions / a.enrolled) * 100) : 0;
                return (
                  <li key={a.assignment_id} className={`list__item list__item--stack has-tab ${courseTone(a.course_code)}`}>
                    <Link to={`/assignments/${a.assignment_id}`} className="list__title">{a.title}</Link>
                    <DeadlineText deadline={a.deadline} />
                    <div className="progress" aria-label={`${a.submissions} of ${a.enrolled} submitted`}>
                      <span className="progress__bar" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="list__meta">{a.submissions} of {a.enrolled} students submitted</span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
