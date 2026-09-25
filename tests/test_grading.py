"""TC-16..TC-20: teacher review, grading, feedback visibility, grading authorization."""

from tests.conftest import upload


def _submit(client, people, make_assignment, pdf_bytes):
    assignment = make_assignment(max_marks=20)
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    return assignment, response.json()["submission"]["submission_id"]


def test_tc16_teacher_views_submissions(client, people, make_assignment, pdf_bytes):
    assignment, _ = _submit(client, people, make_assignment, pdf_bytes)
    response = client.get(f"/api/assignments/{assignment['assignment_id']}/submissions", headers=people["teacher"])
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["enrolled"] == 2
    assert body["summary"]["submitted"] == 1
    assert body["summary"]["not_submitted"] == 1
    statuses = sorted(e["status"] for e in body["entries"])
    assert statuses == ["NOT_SUBMITTED", "SUBMITTED"]


def test_other_teacher_cannot_view_submissions(client, people, make_assignment, pdf_bytes):
    assignment, submission_id = _submit(client, people, make_assignment, pdf_bytes)
    assert client.get(f"/api/assignments/{assignment['assignment_id']}/submissions", headers=people["other_teacher"]).status_code == 403
    assert client.get(f"/api/submissions/{submission_id}", headers=people["other_teacher"]).status_code == 403


def test_tc17_teacher_grades_and_tc19_student_views_feedback(client, people, make_assignment, pdf_bytes):
    _, submission_id = _submit(client, people, make_assignment, pdf_bytes)
    graded = client.post(
        f"/api/submissions/{submission_id}/grade",
        json={"marks": 17.5, "feedback": "  Good architecture diagram. Explain autoscaling triggers.  "},
        headers=people["teacher"],
    )
    assert graded.status_code == 200
    assert graded.json()["submission_status"] == "GRADED"
    assert graded.json()["marks"] == 17.5

    feedback = client.get(f"/api/submissions/{submission_id}/feedback", headers=people["student"])
    assert feedback.status_code == 200
    body = feedback.json()
    assert body["marks"] == 17.5
    assert body["max_marks"] == 20
    assert body["feedback"] == "Good architecture diagram. Explain autoscaling triggers."
    assert body["graded_by_name"] == "Dr. Test Teacher"


def test_tc18_marks_above_maximum_rejected(client, people, make_assignment, pdf_bytes):
    _, submission_id = _submit(client, people, make_assignment, pdf_bytes)
    response = client.post(f"/api/submissions/{submission_id}/grade", json={"marks": 25, "feedback": ""}, headers=people["teacher"])
    assert response.status_code == 400
    assert response.json()["code"] == "MARKS_EXCEED_MAXIMUM"
    negative = client.post(f"/api/submissions/{submission_id}/grade", json={"marks": -1}, headers=people["teacher"])
    assert negative.status_code == 422


def test_tc20_unauthorized_grading_rejected(client, people, make_assignment, pdf_bytes):
    _, submission_id = _submit(client, people, make_assignment, pdf_bytes)
    by_student = client.post(f"/api/submissions/{submission_id}/grade", json={"marks": 20}, headers=people["student"])
    by_other_teacher = client.post(f"/api/submissions/{submission_id}/grade", json={"marks": 20}, headers=people["other_teacher"])
    assert by_student.status_code == 403
    assert by_other_teacher.status_code == 403
    # Nothing changed
    feedback = client.get(f"/api/submissions/{submission_id}/feedback", headers=people["student"]).json()
    assert feedback["marks"] is None


def test_graded_submission_cannot_be_replaced(client, people, make_assignment, pdf_bytes):
    assignment, submission_id = _submit(client, people, make_assignment, pdf_bytes)
    client.post(f"/api/submissions/{submission_id}/grade", json={"marks": 10}, headers=people["teacher"])
    response = upload(client, assignment["assignment_id"], people["student"], pdf_bytes)
    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_GRADED"


def test_late_flag_survives_grading(client, people, make_assignment, pdf_bytes, shift_clock):
    assignment = make_assignment()
    shift_clock(hours=48)
    submission_id = upload(client, assignment["assignment_id"], people["student"], pdf_bytes).json()["submission"]["submission_id"]
    client.post(f"/api/submissions/{submission_id}/grade", json={"marks": 12}, headers=people["teacher"])
    detail = client.get(f"/api/submissions/{submission_id}", headers=people["student"]).json()
    assert detail["submission_status"] == "GRADED"
    assert detail["is_late"] is True


def test_admin_can_grade_any_course(client, people, make_assignment, pdf_bytes):
    _, submission_id = _submit(client, people, make_assignment, pdf_bytes)
    response = client.post(f"/api/submissions/{submission_id}/grade", json={"marks": 15}, headers=people["admin"])
    assert response.status_code == 200
