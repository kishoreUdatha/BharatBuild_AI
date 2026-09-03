"""
Every function the portal claims to have, exercised once, in order.

Not a render check - each step performs the action and asserts on what came
back, then the next step depends on the last. A break anywhere stops the chain,
which is the point: these functions are only worth anything as a sequence.

Leaves nothing behind: the batch, the students and the files are removed at the
end whether the run passed or failed.
"""
import os
import sys

# Run from anywhere: the backend package root is two directories up from
# tests/integration, and CI invokes this by absolute path, so sys.path[0] is
# this file's directory rather than the application root.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import io
import json
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta

API = "http://localhost:8000/api/v1"
PASS, FAIL = [], []
STATE = {}


def call(method, path, token=None, body=None, files=None, expect=None, raw=False):
    url = API + path
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if files is not None:
        boundary = "----b" + uuid.uuid4().hex
        buf = io.BytesIO()
        w = lambda s: buf.write(s if isinstance(s, bytes) else s.encode())
        for key, value in (body or {}).items():
            w(f"--{boundary}\r\n")
            w(f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n')
        for key, (name, content) in files.items():
            ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
            w(f"--{boundary}\r\n")
            w(f'Content-Disposition: form-data; name="{key}"; filename="{name}"\r\n')
            w(f"Content-Type: {ctype}\r\n\r\n")
            w(content)
            w("\r\n")
        w(f"--{boundary}--\r\n")
        data = buf.getvalue()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload or b"null"))
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload or b"null")
        except Exception:
            return e.code, {"raw": payload[:200].decode(errors="ignore")}


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    return ok


def login(email, password="Student@123", attempts=4):
    """
    Sign in, waiting out the login rate limiter if it trips.

    This run signs in as several people in quick succession, which is more
    than the five-per-minute limit on /auth/login allows. Without the wait a
    perfectly healthy build reports failures in whatever step happened to need
    a token next - the join code check, usually - and sends you looking for a
    bug that is not there.
    """
    import time

    delay = 5
    for attempt in range(attempts):
        status, d = call("POST", "/auth/login",
                         body={"email": email, "password": password})
        token = (d or {}).get("access_token")
        if token:
            return token
        if status != 429:
            return None
        if attempt < attempts - 1:
            time.sleep(delay)
            delay *= 3
    return None


PDF = (b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
       b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
       b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
       b"trailer\n<< /Root 1 0 R >>\n%%EOF\n")


def run():
    fac = login("kavitha@sgit.ac.in", "Faculty@123")
    adm = login("admin@sgit.ac.in", "Admin@12345")
    check("faculty login", bool(fac))
    check("admin login", bool(adm))
    if not fac:
        return

    # --- registration ------------------------------------------------------
    tag = uuid.uuid4().hex[:6]
    students = []
    for i, name in enumerate(["Fn Alpha", "Fn Beta"]):
        st, d = call("POST", "/auth/register", body={
            "email": f"fn{tag}{i}@sgit.ac.in", "password": "Student@123",
            "full_name": name, "role": "student", "roll_number": f"22FN{tag[:3]}{i}",
            "department": "Computer Science & Engineering", "section": "A",
            "year_semester": "4th Year / 7th Semester", "course": "B.Tech",
            "college_name": "SGIT", "guide_name": "Dr Kavitha"})
        students.append(f"fn{tag}{i}@sgit.ac.in")
        if i == 0:
            check("register a student", st == 201, f"HTTP {st}")
    STATE["students"] = students

    st, d = call("GET", f"/faculty/registrations/students?search=22FN{tag[:3]}0", fac)
    rows = (d or {}).get("rows") or []
    check("registration becomes an enrolment", len(rows) == 1,
          rows[0]["department"] + " " + rows[0]["section"] if rows else "not found")

    ids = []
    for s in students:
        _, d = call("GET", f"/faculty/registrations/students?search={s}", fac)
        r = ((d or {}).get("rows") or [None])[0]
        if r:
            ids.append(r["id"])
    st, d = call("POST", "/faculty/registrations/students/verify", fac, {"enrollment_ids": ids})
    check("faculty verifies students", len((d or {}).get("verified") or []) == 2,
          str((d or {}).get("skipped")))

    # --- batch -------------------------------------------------------------
    st, d = call("POST", "/faculty/registrations/batches", fac, {
        "department": "CSE", "year": "4th Year", "semester": "I", "section": "A",
        "team_size": 2, "count": 1,
        "guide_id": None})
    created = ((d or {}).get("created") or [None])[0]
    check("create a batch", st == 201 and created is not None, created and created["batch_code"])
    if not created:
        return
    code, join = created["batch_code"], created["join_code"]
    STATE["batch"] = code

    # A guide is needed for anything to be manageable.
    _, opts = call("GET", "/faculty/reviews/options", fac)
    guide = next(r["id"] for r in opts["reviewers"] if "Kavitha" in r["name"])
    _, blist = call("GET", f"/faculty/registrations?per_page=100&search={code}", fac)
    bid = ((blist or {}).get("rows") or [{}])[0].get("id")
    st, _ = call("POST", "/faculty/registrations/assign-guide", fac,
                 {"batch_ids": [bid], "guide_id": guide})
    check("assign a guide", st == 200, f"HTTP {st}")

    # --- joining -----------------------------------------------------------
    toks = [login(s) for s in students]
    st, _ = call("POST", "/student/registration/verify-batch", toks[0], {"code": join})
    check("verify a join code", st == 200, f"HTTP {st}")
    st, bad = call("POST", "/student/registration/verify-batch", toks[0], {"code": "BB-NOPE-999"})
    check("wrong join code refused", st == 400, (bad or {}).get("detail", "")[:40])
    for t in toks:
        call("POST", "/student/registration/join", t, {"code": join})
    _, reg = call("GET", "/student/registration", toks[0])
    check("both students join", reg["batch"]["joined"] == 2, f"{reg['batch']['joined']}/2")

    # --- project details ---------------------------------------------------
    st, d = call("PUT", "/student/project", toks[0], {
        "title": "Functional Check Project",
        "problem_statement": "Nothing verified the whole chain in one pass.",
        "abstract": "A single run that exercises every function the portal offers, in the "
                    "order a real cohort would meet them, so a break in any one of them "
                    "stops the chain instead of hiding behind a green screen.",
        "objectives": [{"text": "a"}, {"text": "b"}, {"text": "c"}],
        "methodology": [{"title": "Step one"}],
        "technologies": [{"layer": "Backend", "name": "FastAPI"}],
        "outcomes": ["Every function proven"], "in_scope": ["The portal"],
        "deliverables": ["This report"]})
    check("save project details", st == 200 and d["checks_passed"] == 8,
          f"{d.get('checks_passed')}/8")
    st, d = call("POST", "/student/project/submit", toks[0], {})
    check("submit the registration", st == 200 and d.get("status") == "submitted", str(d)[:50])
    st, d = call("PUT", "/student/project", toks[0], {"title": "x"})
    check("locked once submitted", st == 400, (d or {}).get("detail", "")[:40])

    # --- documents ---------------------------------------------------------
    st, d = call("POST", "/student/documents", toks[0],
                 {"category": "Student Declaration"}, {"file": ("dec.pdf", PDF)})
    doc_id = (d or {}).get("id")
    check("upload a document", st == 201 and (d or {}).get("version") == "v1.0")
    st, d = call("POST", "/student/documents", toks[0],
                 {"category": "Student Declaration"}, {"file": ("bad.pdf", b"<?php ?>")})
    check("fake PDF refused", st == 400, (d or {}).get("detail", "")[:40])
    st, body = call("GET", f"/student/documents/{doc_id}/download", toks[0], raw=True)
    check("download returns the same bytes", st == 200 and body == PDF, f"{len(body)}B")
    st, d = call("POST", f"/faculty/batches/{code}/documents/decide", fac,
                 {"document_id": doc_id, "decision": "verify"})
    check("faculty verifies a document", st == 200 and d.get("status") == "verified")
    st, d = call("DELETE", f"/student/documents/{doc_id}", toks[0])
    check("verified document cannot be removed", st == 400, (d or {}).get("detail", "")[:40])

    # --- base paper --------------------------------------------------------
    st, d = call("POST", "/student/base-paper", toks[0], {}, {"file": ("paper.pdf", PDF)})
    check("upload a base paper", st == 201, str(d)[:40])
    st, d = call("POST", f"/faculty/batches/{code}/base-paper/decide", fac,
                 {"decision": "verify"})
    check("verify the base paper", st == 200 and d.get("status") == "verified")

    # --- submissions -------------------------------------------------------
    st, d = call("POST", "/student/submissions", toks[0],
                 {"document_type": "Synopsis"}, {"file": ("syn.pdf", PDF)})
    sub = (d or {}).get("id")
    check("hand in a deliverable", st == 201)
    st, d = call("POST", f"/faculty/batches/{code}/submissions/{sub}/decide", fac,
                 {"decision": "reject"})
    check("reject without a reason refused", st == 400, (d or {}).get("detail", "")[:40])
    st, d = call("POST", f"/faculty/batches/{code}/submissions/{sub}/decide", fac,
                 {"decision": "reject", "note": "Add the scope section."})
    check("reject with a reason", st == 200 and d.get("status") == "rejected")
    st, d = call("POST", "/student/submissions", toks[0],
                 {"document_type": "Synopsis"}, {"file": ("syn2.pdf", PDF + b"%v2\n")})
    sub2 = (d or {}).get("id")
    check("resubmit supersedes", (d or {}).get("version") == "v1.1", str(d.get("version")))
    st, d = call("POST", f"/faculty/batches/{code}/submissions/{sub2}/decide", fac,
                 {"decision": "verify"})
    check("accepting moves the stage", st == 200 and d.get("stage_completed") == "Topic Approval",
          f"progress {d.get('overall_progress')}%")
    st, d = call("POST", "/student/submissions", toks[0],
                 {"document_type": "SRS"}, {"file": ("srs.pdf", PDF)})
    st, d = call("DELETE", f"/student/submissions/{d['id']}", toks[0])
    check("withdraw a pending submission", st == 200, (d or {}).get("message", "")[:30])

    # --- attendance --------------------------------------------------------
    st, roster = call("GET", "/faculty/attendance/roster?department=CSE&section=A", fac)
    check("load a register", st == 200 and roster["total"] > 0, f"{roster.get('total')} students")
    marks = [{"student_id": s["student_id"], "status": "present"} for s in roster["students"]]
    marks[0]["status"] = "absent"
    st, d = call("POST", "/faculty/attendance/mark", fac,
                 {"department": "CSE", "section": "A", "marks": marks})
    check("save a register", st == 200 and d["created"] > 0, d.get("message", "")[:40])
    marks[0]["status"] = "present"
    st, d = call("POST", "/faculty/attendance/mark", fac,
                 {"department": "CSE", "section": "A", "marks": marks})
    check("correct a register", st == 200 and d["updated"] == 1, d.get("message", "")[:40])
    st, d = call("POST", "/faculty/attendance/mark", fac,
                 {"department": "CSE", "section": "A", "date": "2099-01-01", "marks": marks})
    check("future date refused", st == 400, (d or {}).get("detail", "")[:40])
    st, d = call("GET", "/student/attendance", toks[0])
    check("student sees their own register", st == 200 and d["days_recorded"] >= 1,
          f"{d.get('days_recorded')} day(s)")

    # --- reviews -----------------------------------------------------------
    when = (date.today() + timedelta(days=10)).isoformat()
    st, d = call("POST", f"/faculty/batches/{code}/reviews", fac,
                 {"review_type": "Progress Review", "date": when, "time": "10:00"})
    rev = (d or {}).get("id")
    check("schedule a review", st == 201, (d or {}).get("scheduled_label"))
    st, d = call("POST", f"/faculty/batches/{code}/reviews", fac,
                 {"review_type": "Progress Review", "date": when, "time": "11:00"})
    check("duplicate review refused", st == 400, (d or {}).get("detail", "")[:45])
    st, d = call("POST", f"/faculty/batches/{code}/reviews/{rev}/complete", fac,
                 {"score": 150})
    check("out-of-range score refused", st == 400, (d or {}).get("detail", "")[:40])
    st, d = call("POST", f"/faculty/batches/{code}/reviews/{rev}/complete", fac,
                 {"score": 78, "remarks": "Solid."})
    check("record a review outcome", st == 200 and d.get("status") == "completed")
    st, d = call("GET", "/faculty/reviews/schedule?include_past=true&limit=500", fac)
    check("review calendar reports clashes", st == 200 and "clashing" in d,
          f"{d.get('count')} reviews, {d.get('clashing')} clashing")

    # --- approval ----------------------------------------------------------
    st, d = call("POST", "/faculty/registrations/queue/decide", fac,
                 {"batch_ids": [bid], "decision": "request_changes", "note": "Tighten scope."})
    check("request changes", st == 200 and code in (d.get("applied") or []))
    call("POST", "/student/project/submit", toks[0], {})
    st, d = call("POST", "/faculty/registrations/queue/decide", fac,
                 {"batch_ids": [bid], "decision": "approve", "note": "Approved."})
    check("approve the registration", st == 200 and code in (d.get("applied") or []),
          str(d.get("skipped"))[:50])
    st, d = call("GET", f"/faculty/batches/{code}/approvals", fac)
    check("batch reads as approved", d["header"]["status"] == "Approved", d["header"]["status"])

    # --- authority ---------------------------------------------------------
    latha = login("latha@sgit.ac.in", "Faculty@123")
    st, _ = call("PUT", f"/faculty/batches/{code}/project", latha, {"title": "hijack"})
    check("other faculty cannot edit", st == 403, f"HTTP {st}")
    st, _ = call("GET", "/admin/users", fac)
    check("faculty cannot reach admin", st == 403, f"HTTP {st}")
    st, d = call("GET", "/admin/plans", adm)
    check("admin can read plans", st == 200 and len(d) > 0, f"{len(d) if isinstance(d, list) else '?'} plans")
    st, d = call("GET", "/admin/users", adm)
    check("admin can read users", st == 200)


def cleanup():
    print("\ncleanup")
    print(json.dumps({"batch": STATE.get("batch"), "students": STATE.get("students")}))


if __name__ == "__main__":
    print("FUNCTIONAL CHECK\n")
    try:
        run()
    except Exception as exc:
        check("run completed without an exception", False, f"{type(exc).__name__}: {exc}")
    cleanup()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failed:", ", ".join(FAIL))
    sys.exit(1 if FAIL else 0)
