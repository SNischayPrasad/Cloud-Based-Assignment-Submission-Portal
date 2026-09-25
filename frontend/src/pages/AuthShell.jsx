/**
 * Two-column frame shared by the login and registration pages.
 * The left column shows a "submission slip" - what students get back
 * after every upload.
 */
export default function AuthShell({ children }) {
  return (
    <div className="auth">
      <section className="auth__intro" aria-label="About Handin">
        <p className="brand brand--large">
          <span className="brand__mark" aria-hidden="true">✓</span>
          <span className="brand__name">Handin</span>
        </p>
        <h1 className="auth__headline">Hand in work. Get it back marked.</h1>
        <p className="auth__lede">
          Assignments, deadlines, uploads and teacher feedback in one place, reachable from any device.
        </p>

        <figure className="slip" aria-label="Example submission receipt">
          <div className="slip__head">
            <span className="slip__course">CC401 · Cloud Computing</span>
            <span className="stamp stamp--submitted slip__stamp">Received</span>
          </div>
          <p className="slip__title">Design a Three-Tier Cloud Architecture</p>
          <dl className="slip__rows">
            <div><dt>File</dt><dd>architecture_report.pdf · 1.2 MB</dd></div>
            <div><dt>Stored at</dt><dd className="mono">assignments/assignment_001/student_003/…pdf</dd></div>
            <div><dt>Received</dt><dd className="mono">2026-09-25 10:15 UTC · on time</dd></div>
          </dl>
          <div className="slip__grade">
            <span className="grade grade--md"><span className="grade__score">18</span><span className="grade__max">/20</span></span>
            <span className="slip__note">“Clear diagram. Explain your autoscaling trigger.”</span>
          </div>
        </figure>
      </section>
      <section className="auth__form">{children}</section>
    </div>
  );
}
