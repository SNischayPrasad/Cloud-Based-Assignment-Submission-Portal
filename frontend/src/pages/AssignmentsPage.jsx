import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, CourseTag, DeadlineText, EmptyState, Loading, PageHeader, StatusStamp } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import useLoad from '../hooks/useLoad';
import { assignmentService } from '../services/assignmentService';
import { courseTone } from '../utils/format';

export default function AssignmentsPage() {
  const { user } = useAuth();
  const isStudent = user.role === 'student';
  const { data: assignments, error, loading } = useLoad(() => assignmentService.list(), []);
  const [query, setQuery] = useState('');
  const [course, setCourse] = useState('all');
  const [status, setStatus] = useState('all');

  const courses = useMemo(
    () => [...new Set((assignments || []).map((a) => a.course_code))].sort(),
    [assignments],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (assignments || []).filter(
      (a) =>
        (course === 'all' || a.course_code === course) &&
        (status === 'all' || a.my_status === status) &&
        (!q || a.title.toLowerCase().includes(q)),
    );
  }, [assignments, query, course, status]);

  return (
    <>
      <PageHeader
        eyebrow={isStudent ? 'Your coursework' : 'Coursework you set'}
        title="Assignments"
        actions={!isStudent && <Link className="btn btn--primary" to="/assignments/new">New assignment</Link>}
      />

      <div className="toolbar">
        <input
          type="search"
          className="toolbar__search"
          placeholder="Search by title"
          aria-label="Search assignments by title"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select aria-label="Filter by course" value={course} onChange={(e) => setCourse(e.target.value)}>
          <option value="all">All courses</option>
          {courses.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {isStudent && (
          <select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="all">Any status</option>
            <option value="NOT_SUBMITTED">Not submitted</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="LATE">Late</option>
            <option value="GRADED">Graded</option>
          </select>
        )}
      </div>

      {loading && <Loading />}
      <Alert>{error}</Alert>

      {!loading && !error && visible.length === 0 && (
        <EmptyState
          title={assignments?.length ? 'No assignments match these filters' : 'No assignments yet'}
          action={
            !assignments?.length &&
            (isStudent ? <Link to="/courses">Join a course</Link> : <Link to="/assignments/new">Create the first one</Link>)
          }
        />
      )}

      <ul className="cards">
        {visible.map((a) => (
          <li key={a.assignment_id}>
            <Link to={`/assignments/${a.assignment_id}`} className={`assignment-card has-tab ${courseTone(a.course_code)}`}>
              <div className="assignment-card__main">
                <span className="assignment-card__course">
                  <CourseTag code={a.course_code} tone={courseTone(a.course_code)} /> {a.course_name}
                </span>
                <span className="assignment-card__title">{a.title}</span>
                <DeadlineText deadline={a.deadline} done={isStudent && a.my_status !== 'NOT_SUBMITTED'} />
              </div>
              <div className="assignment-card__side">
                {isStudent ? (
                  <StatusStamp status={a.my_status} />
                ) : (
                  <span className="count-badge">
                    <strong>{a.submission_count}</strong>/{a.enrolled_count} submitted
                  </span>
                )}
                <span className="muted small">{a.max_marks} marks</span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
