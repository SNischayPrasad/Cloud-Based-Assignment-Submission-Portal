import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Alert, EmptyState, Loading, PageHeader } from '../components/ui';
import { getErrorMessage } from '../services/api';
import { assignmentService } from '../services/assignmentService';
import { courseService } from '../services/courseService';
import { FILE_TYPE_OPTIONS } from '../utils/constants';
import { fromLocalInputValue, toLocalInputValue, userTimeZone } from '../utils/format';

const EMPTY = {
  course_id: '',
  title: '',
  description: '',
  deadline: '',
  max_marks: 20,
  allowed_file_types: ['pdf'],
  max_file_size_mb: 10,
  allow_late_submission: true,
  allow_resubmission: true,
};

function validate(form) {
  if (!form.course_id) return 'Choose a course.';
  if (form.title.trim().length < 3) return 'The title needs at least 3 characters.';
  if (!form.deadline) return 'Set a deadline.';
  if (new Date(form.deadline) <= new Date()) return 'The deadline must be in the future.';
  const marks = Number(form.max_marks);
  if (!(marks > 0 && marks <= 1000)) return 'Maximum marks must be between 1 and 1000.';
  if (form.allowed_file_types.length === 0) return 'Allow at least one file type.';
  const size = Number(form.max_file_size_mb);
  if (!(Number.isInteger(size) && size >= 1 && size <= 100)) return 'Maximum file size must be a whole number of MB (1–100).';
  return '';
}

export default function AssignmentFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const list = await courseService.list();
        setCourses(list);
        if (editing) {
          const a = await assignmentService.get(id);
          setForm({
            course_id: String(a.course_id),
            title: a.title,
            description: a.description,
            deadline: toLocalInputValue(a.deadline),
            max_marks: a.max_marks,
            allowed_file_types: a.allowed_file_types,
            max_file_size_mb: a.max_file_size_mb,
            allow_late_submission: a.allow_late_submission,
            allow_resubmission: a.allow_resubmission,
          });
        } else if (list.length === 1) {
          setForm((f) => ({ ...f, course_id: String(list[0].course_id) }));
        }
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, editing]);

  const set = (field) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [field]: value }));
  };

  const toggleType = (type) =>
    setForm((f) => ({
      ...f,
      allowed_file_types: f.allowed_file_types.includes(type)
        ? f.allowed_file_types.filter((t) => t !== type)
        : [...f.allowed_file_types, type],
    }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    const problem = validate(form);
    if (problem) return setError(problem);
    setError('');
    setSaving(true);
    const payload = {
      title: form.title.trim(),
      description: form.description,
      deadline: fromLocalInputValue(form.deadline), // sent as UTC
      max_marks: Number(form.max_marks),
      allowed_file_types: form.allowed_file_types,
      max_file_size_mb: Number(form.max_file_size_mb),
      allow_late_submission: form.allow_late_submission,
      allow_resubmission: form.allow_resubmission,
    };
    try {
      const saved = editing
        ? await assignmentService.update(id, payload)
        : await assignmentService.create({ ...payload, course_id: Number(form.course_id) });
      navigate(`/assignments/${saved.assignment_id}`, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the assignment.'));
      setSaving(false);
    }
  };

  if (loading) return <Loading />;
  if (!editing && courses.length === 0) {
    return (
      <EmptyState title="Create a course first" action={<Link className="btn btn--primary" to="/courses">Go to courses</Link>}>
        Assignments belong to a course.
      </EmptyState>
    );
  }

  return (
    <>
      <PageHeader eyebrow={editing ? 'Edit assignment' : 'New assignment'} title={editing ? form.title || 'Edit assignment' : 'Set an assignment'} />
      <form className="card form form--wide" onSubmit={handleSubmit} noValidate>
        <Alert>{error}</Alert>

        <div className="form-grid">
          <label className="field">
            <span className="field__label">Course</span>
            <select value={form.course_id} onChange={set('course_id')} disabled={editing} required>
              <option value="">Choose a course</option>
              {courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>{c.course_code} · {c.course_name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field__label">Deadline</span>
            <input type="datetime-local" value={form.deadline} onChange={set('deadline')} required />
            <span className="field__hint">Your time zone ({userTimeZone}). Stored in UTC.</span>
          </label>
        </div>

        <label className="field">
          <span className="field__label">Title</span>
          <input value={form.title} onChange={set('title')} maxLength={200} required />
        </label>
        <label className="field">
          <span className="field__label">Instructions</span>
          <textarea rows={6} value={form.description} onChange={set('description')} maxLength={10000} />
        </label>

        <div className="form-grid">
          <label className="field">
            <span className="field__label">Maximum marks</span>
            <input type="number" min="1" max="1000" step="0.5" value={form.max_marks} onChange={set('max_marks')} />
          </label>
          <label className="field">
            <span className="field__label">Maximum file size (MB)</span>
            <input type="number" min="1" max="100" value={form.max_file_size_mb} onChange={set('max_file_size_mb')} />
          </label>
        </div>

        <fieldset className="field">
          <legend className="field__label">Accepted file types</legend>
          <div className="chips">
            {FILE_TYPE_OPTIONS.map((type) => (
              <label key={type} className={`chip${form.allowed_file_types.includes(type) ? ' is-on' : ''}`}>
                <input type="checkbox" checked={form.allowed_file_types.includes(type)} onChange={() => toggleType(type)} />
                .{type}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="form-grid">
          <label className="check">
            <input type="checkbox" checked={form.allow_late_submission} onChange={set('allow_late_submission')} />
            <span>Accept late work <span className="muted">(recorded as LATE)</span></span>
          </label>
          <label className="check">
            <input type="checkbox" checked={form.allow_resubmission} onChange={set('allow_resubmission')} />
            <span>Allow resubmission <span className="muted">(until graded)</span></span>
          </label>
        </div>

        <div className="button-row">
          <button type="submit" className="btn btn--primary" disabled={saving}>
            {saving ? 'Saving…' : editing ? 'Save changes' : 'Publish assignment'}
          </button>
          <Link className="btn btn--ghost" to={editing ? `/assignments/${id}` : '/assignments'}>Cancel</Link>
        </div>
      </form>
    </>
  );
}
