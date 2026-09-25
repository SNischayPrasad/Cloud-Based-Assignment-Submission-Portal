import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="status-page">
      <span className="stamp stamp--not-submitted stamp--big">404 · Not found</span>
      <h1 className="page-title">There is nothing at this address.</h1>
      <Link className="btn btn--primary" to="/">
        Back to dashboard
      </Link>
    </div>
  );
}
