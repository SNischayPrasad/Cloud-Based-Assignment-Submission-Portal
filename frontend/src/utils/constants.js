// File types a teacher can allow (must be a subset of the backend ALLOWED_FILE_TYPES).
export const FILE_TYPE_OPTIONS = ['pdf', 'docx', 'pptx', 'zip', 'png', 'jpg', 'jpeg', 'txt', 'py', 'ipynb'];

export const STATUS_LABELS = {
  NOT_SUBMITTED: 'Not submitted',
  SUBMITTED: 'Submitted',
  LATE: 'Late',
  GRADED: 'Graded',
};

// Where each role lands after logging in.
export const ROLE_HOME = {
  student: '/student',
  teacher: '/teacher',
  admin: '/teacher',
};

export const ROLE_LABELS = { student: 'Student', teacher: 'Teacher', admin: 'Admin' };
