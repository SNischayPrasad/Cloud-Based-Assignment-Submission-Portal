import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './context/AuthContext';
import AdminPage from './pages/AdminPage';
import AssignmentDetailPage from './pages/AssignmentDetailPage';
import AssignmentFormPage from './pages/AssignmentFormPage';
import AssignmentsPage from './pages/AssignmentsPage';
import CoursesPage from './pages/CoursesPage';
import LoginPage from './pages/LoginPage';
import MySubmissionsPage from './pages/MySubmissionsPage';
import NotFoundPage from './pages/NotFoundPage';
import RegisterPage from './pages/RegisterPage';
import StudentDashboard from './pages/StudentDashboard';
import SubmissionPage from './pages/SubmissionPage';
import TeacherDashboard from './pages/TeacherDashboard';
import { ROLE_HOME } from './utils/constants';

const TEACHING = ['teacher', 'admin'];

function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? ROLE_HOME[user.role] : '/login'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<HomeRedirect />} />
        <Route path="/student" element={<ProtectedRoute roles={['student']}><StudentDashboard /></ProtectedRoute>} />
        <Route path="/teacher" element={<ProtectedRoute roles={TEACHING}><TeacherDashboard /></ProtectedRoute>} />
        <Route path="/assignments" element={<AssignmentsPage />} />
        <Route path="/assignments/new" element={<ProtectedRoute roles={TEACHING}><AssignmentFormPage /></ProtectedRoute>} />
        <Route path="/assignments/:id" element={<AssignmentDetailPage />} />
        <Route path="/assignments/:id/edit" element={<ProtectedRoute roles={TEACHING}><AssignmentFormPage /></ProtectedRoute>} />
        <Route path="/submissions" element={<ProtectedRoute roles={['student']}><MySubmissionsPage /></ProtectedRoute>} />
        <Route path="/submissions/:id" element={<SubmissionPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminPage /></ProtectedRoute>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
