/**
 * Small presentational building blocks shared by every page.
 */
import { STATUS_LABELS } from '../utils/constants';
import { formatDateTime, formatMarks, hoursUntil, relativeTime } from '../utils/format';

/** Rubber-stamp status badge: SUBMITTED / LATE / GRADED / NOT SUBMITTED. */
export function StatusStamp({ status, late = false }) {
  const key = (status || 'NOT_SUBMITTED').toLowerCase().replace('_', '-');
  return (
    <span className="stamp-group">
      <span className={`stamp stamp--${key}`}>{STATUS_LABELS[status] || status}</span>
      {late && status === 'GRADED' && <span className="stamp stamp--late stamp--mini">Late</span>}
    </span>
  );
}

/** Red-pen grade, circled like on a marked paper. */
export function GradeMark({ marks, max, size = 'md' }) {
  if (marks == null) return <span className="grade grade--none">Not graded</span>;
  return (
    <span className={`grade grade--${size}`} aria-label={`${formatMarks(marks)} out of ${formatMarks(max)}`}>
      <span className="grade__score">{formatMarks(marks)}</span>
      <span className="grade__max">/{formatMarks(max)}</span>
    </span>
  );
}

export function DeadlineText({ deadline, done = false }) {
  const hours = hoursUntil(deadline);
  const tone = done ? '' : hours < 0 ? 'is-past' : hours < 48 ? 'is-soon' : '';
  return (
    <span className={`deadline ${tone}`}>
      <span className="deadline__abs">{formatDateTime(deadline)}</span>
      <span className="deadline__rel">{hours < 0 ? `closed ${relativeTime(deadline)}` : `due ${relativeTime(deadline)}`}</span>
    </span>
  );
}

export function Alert({ kind = 'error', children, onClose }) {
  if (!children) return null;
  return (
    <div className={`alert alert--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <span>{children}</span>
      {onClose && (
        <button type="button" className="alert__close" onClick={onClose} aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  );
}

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="loading" role="status">
      <span className="loading__dot" />
      {label}
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {children && <p className="empty__body">{children}</p>}
      {action}
    </div>
  );
}

export function PageHeader({ eyebrow, title, children, actions }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {children && <div className="page-header__meta">{children}</div>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </div>
  );
}

/** A row of counts, read left to right like a register. */
export function Ledger({ items }) {
  return (
    <dl className="ledger">
      {items.map((item) => (
        <div key={item.label} className={`ledger__item ${item.tone ? `ledger__item--${item.tone}` : ''}`}>
          <dt>{item.label}</dt>
          <dd>{item.value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

export function CourseTag({ code, tone }) {
  return <span className={`course-tag ${tone}`}>{code}</span>;
}
