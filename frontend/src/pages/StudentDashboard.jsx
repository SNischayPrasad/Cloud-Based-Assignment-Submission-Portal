import { Link } from 'react-router-dom';
import { Alert, CourseTag, DeadlineText, EmptyState, GradeMark, Ledger, Loading, PageHeader } from '../components/ui';
import useLoad from '../hooks/useLoad';
import { dashboardService } from '../services/dashboardService';
import { courseTone, formatDateTime } from '../utils/format';

export default function StudentDashboard() {
  const { data, error, loading } = useLoad(() => dashboardService.student(), []);

  if (loading) return <Loading />;
  if (error) return <Alert>{error}</Alert>;

  const { stats, upcoming_deadlines: upcoming, recent_feedback: feedback } = data;
  const firstName = data.student_name.split(' ')[0];

  return (
    <>
      <PageHeader eyebrow="Student dashboard" title={`Welcome, ${firstName}`}>
        {stats.courses === 0
          ? 'You are not in any course yet.'
          : `${stats.pending_assignments} of ${stats.total_assignments} assignments still to hand in.`}
      </PageHeader>

      {stats.courses === 0 ? (
        <EmptyState
          title="Join your first course"
          action={<Link className="btn btn--primary" to="/courses">Enter a join code</Link>}
        >
          Your teacher shares a six-character join code in class.
        </EmptyState>
      ) : (
        <>
          <Ledger
            items={[
              { label: 'Total assignments', value: stats.total_assignments },
              { label: 'Pending', value: stats.pending_assignments, tone: stats.pending_assignments ? 'warn' : '' },
              { label: 'Submitted', value: stats.submitted_assignments },
              { label: 'Late', value: stats.late_assignments, tone: stats.late_assignments ? 'late' : '' },
              { label: 'Graded', value: stats.graded_assignments, tone: 'graded' },
              { label: 'Average score', value: stats.average_percentage == null ? '—' : `${stats.average_percentage}%` },
            ]}
          />

          <div className="columns">
            <section className="card">
              <h2 className="section-title">Upcoming deadlines</h2>
              {upcoming.length === 0 ? (
                <EmptyState title="Nothing due">Every open assignment has been handed in.</EmptyState>
              ) : (
                <ul className="list">
                  {upcoming.map((a) => (
                    <li key={a.assignment_id} className={`list__item has-tab ${courseTone(a.course_code)}`}>
                      <div className="list__main">
                        <Link to={`/assignments/${a.assignment_id}`} className="list__title">{a.title}</Link>
                        <span className="list__meta"><CourseTag code={a.course_code} tone={courseTone(a.course_code)} /> · {a.max_marks} marks</span>
                      </div>
                      <DeadlineText deadline={a.deadline} />
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="card">
              <h2 className="section-title">Recent feedback</h2>
              {feedback.length === 0 ? (
                <EmptyState title="No marks yet">Feedback appears here as soon as a teacher grades your work.</EmptyState>
              ) : (
                <ul className="list">
                  {feedback.map((f) => (
                    <li key={f.submission_id} className="list__item list__item--feedback">
                      <GradeMark marks={f.marks} max={f.max_marks} />
                      <div className="list__main">
                        <Link to={`/submissions/${f.submission_id}`} className="list__title">{f.assignment_title}</Link>
                        {f.feedback_preview && <p className="margin-note">{f.feedback_preview}</p>}
                        <span className="list__meta">{f.course_code} · marked {formatDateTime(f.graded_at)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </>
  );
}
