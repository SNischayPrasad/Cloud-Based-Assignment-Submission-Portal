import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Alert, CourseTag, EmptyState, Loading, PageHeader } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import useLoad from '../hooks/useLoad';
import { getErrorMessage } from '../services/api';
import { courseService } from '../services/courseService';
import { courseTone, formatDateTime } from '../utils/format';

export default function CoursesPage() {
  const { user } = useAuth();
  const location = useLocation();
  const { data: courses, error, loading, reload } = useLoad(() => courseService.list(), []);
  const isStudent = user.role === 'student';

  return (
    <>
      <PageHeader eyebrow={isStudent ? 'Where your assignments come from' : 'Your classes'} title="Courses" />
      {location.state?.welcome && (
        <Alert kind="success">Account created. Enter the join code from your teacher to see your assignments.</Alert>
      )}
      {isStudent ? <JoinCourseForm onJoined={reload} /> : user.role === 'teacher' && <CreateCourseForm onCreated={reload} />}

      {loading && !courses && <Loading />}
      <Alert>{error}</Alert>
      {courses && courses.length === 0 && (
        <EmptyState title={isStudent ? 'You have not joined any course' : 'No courses yet'}>
          {isStudent ? 'Use the join code above.' : 'Create a course, then share its join code with students.'}
        </EmptyState>
      )}
      <ul className="course-grid">
        {courses?.map((course) => (
          <CourseCard key={course.course_id} course={course} manage={!isStudent} />
        ))}
      </ul>
    </>
  );
}

function CourseCard({ course, manage }) {
  const [open, setOpen] = useState(false);
  const tone = courseTone(course.course_code);
  return (
    <li className={`card course-card has-tab ${tone}`}>
      <div className="course-card__head">
        <CourseTag code={course.course_code} tone={tone} />
        {course.join_code && (
          <span className="join-code" title="Students enter this code to join">
            <span className="muted small">Join code</span> <strong className="mono">{course.join_code}</strong>
          </span>
        )}
      </div>
      <h2 className="course-card__name">{course.course_name}</h2>
      {course.description && <p className="muted small">{course.description}</p>}
      <p className="small">
        {course.teacher_name} · {course.student_count} students · {course.assignment_count} assignments
      </p>
      {manage && (
        <>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? 'Hide roster' : 'Show roster'}
          </button>
          {open && <Roster courseId={course.course_id} />}
        </>
      )}
    </li>
  );
}

function Roster({ courseId }) {
  const { data, error, loading, reload } = useLoad(() => courseService.roster(courseId), [courseId]);
  const [email, setEmail] = useState('');
  const [formError, setFormError] = useState('');

  const add = async (event) => {
    event.preventDefault();
    setFormError('');
    try {
      await courseService.enroll(courseId, email.trim());
      setEmail('');
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
    }
  };

  return (
    <div className="roster">
      {loading && !data && <Loading />}
      <Alert>{error}</Alert>
      {data && (
        <ul className="roster__list">
          {data.length === 0 && <li className="muted small">No students yet.</li>}
          {data.map((s) => (
            <li key={s.student_id}>
              <span>{s.name}</span>
              <span className="muted small">{s.email} · joined {formatDateTime(s.enrolled_at)}</span>
            </li>
          ))}
        </ul>
      )}
      <form className="inline-form" onSubmit={add}>
        <input type="email" placeholder="student@email" aria-label="Student email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <button type="submit" className="btn btn--ghost btn--sm">Add student</button>
      </form>
      <Alert>{formError}</Alert>
    </div>
  );
}

function JoinCourseForm({ onJoined }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const join = async (event) => {
    event.preventDefault();
    setError('');
    setNotice('');
    try {
      const course = await courseService.join(code.trim());
      setNotice(`Joined ${course.course_code} · ${course.course_name}.`);
      setCode('');
      onJoined();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form className="card inline-card" onSubmit={join}>
      <label className="field field--inline">
        <span className="field__label">Join a course</span>
        <input
          className="mono input--code"
          placeholder="e.g. CLOUD4"
          maxLength={12}
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          required
        />
      </label>
      <button type="submit" className="btn btn--primary" disabled={code.trim().length < 4}>Join course</button>
      <Alert kind="success">{notice}</Alert>
      <Alert>{error}</Alert>
    </form>
  );
}

function CreateCourseForm({ onCreated }) {
  const [form, setForm] = useState({ course_code: '', course_name: '', description: '' });
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    try {
      await courseService.create(form);
      setForm({ course_code: '', course_name: '', description: '' });
      setOpen(false);
      onCreated();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  if (!open) {
    return (
      <div className="button-row">
        <button type="button" className="btn btn--primary" onClick={() => setOpen(true)}>New course</button>
      </div>
    );
  }
  return (
    <form className="card form form--wide" onSubmit={submit}>
      <h2 className="section-title">New course</h2>
      <Alert>{error}</Alert>
      <div className="form-grid">
        <label className="field">
          <span className="field__label">Course code</span>
          <input className="mono" placeholder="CC401" value={form.course_code} maxLength={20}
            onChange={(e) => setForm({ ...form, course_code: e.target.value.toUpperCase() })} required />
        </label>
        <label className="field">
          <span className="field__label">Course name</span>
          <input value={form.course_name} maxLength={150} onChange={(e) => setForm({ ...form, course_name: e.target.value })} required />
        </label>
      </div>
      <label className="field">
        <span className="field__label">Description (optional)</span>
        <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </label>
      <div className="button-row">
        <button type="submit" className="btn btn--primary">Create course</button>
        <button type="button" className="btn btn--ghost" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}
