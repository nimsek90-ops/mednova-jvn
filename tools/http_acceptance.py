"""HTTP acceptance against the explicitly isolated localhost fixture server.

Run only after loading care.tests.Workflows into browser_acceptance.sqlite3.
Never target production: the origin is deliberately fixed to loopback.
"""
import re
import os
import uuid
from datetime import date, timedelta
import requests

ORIGIN = os.getenv('MEDNOVA_HTTP_ORIGIN', 'http://127.0.0.1:8000')
assert ORIGIN in ('http://127.0.0.1:8000','http://127.0.0.1:8002'), 'Only designated loopback rehearsal servers are allowed.'
PASSWORD = "Correct-Hospital-Pass12"  # Synthetic test fixture only.


def get(session, path):
    response = session.get(ORIGIN + path, timeout=10)
    response.raise_for_status()
    return response


def post(session, path, data):
    page = get(session, path)
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.text)
    assert token, "CSRF token missing"
    response = session.post(ORIGIN + path, data={**data, "csrfmiddlewaretoken": token[1]}, headers={"Origin": ORIGIN, "Referer": page.url}, timeout=10)
    response.raise_for_status()
    return response


def sign(email):
    session = requests.Session()
    response = post(session, "/login/", {"email": email, "password": PASSWORD})
    assert response.url.endswith("/dashboard/"), "Sign-in failed"
    return session


def main():
    sqlite_fixture = os.getenv('MEDNOVA_TESTING') == '1' and os.getenv('MEDNOVA_TEST_DB') == 'browser_acceptance.sqlite3'
    mysql_fixture = (os.getenv('MEDNOVA_HTTP_MYSQL') == '1' and os.getenv('MEDNOVA_DEMO') == '1' and os.getenv('MYSQL_HOST') == '127.0.0.1' and os.getenv('MYSQL_DATABASE') == 'mednova_local')
    postgres_fixture = (os.getenv('MEDNOVA_HTTP_POSTGRES') == '1' and os.getenv('MEDNOVA_DEMO') == '1' and os.getenv('PGHOST') == '127.0.0.1' and os.getenv('PGDATABASE') == 'mednova_pg_rehearsal')
    if os.getenv('APP_ENV') != 'local' or not (sqlite_fixture or mysql_fixture or postgres_fixture):
        raise SystemExit('Refusing mutations: use a designated isolated loopback fixture.')
    patient = requests.Session()
    email = f"synthetic-{uuid.uuid4().hex[:12]}@example.test"
    response = post(patient, "/register/", {"name": "Synthetic HTTP Patient", "email": email, "role": "patient", "password1": PASSWORD, "password2": PASSWORD, "consent": "on"})
    assert response.url.endswith("/dashboard/")
    post(patient, "/profile/", {"name": "Synthetic Updated Patient", "phone": ""})
    # Logout token is supplied by the authenticated layout on /profile/.
    page = get(patient, "/profile/")
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.text)[1]
    response = patient.post(ORIGIN + "/logout/", data={"csrfmiddlewaretoken": token}, headers={"Origin": ORIGIN}, timeout=10)
    assert response.url.endswith("/login/")
    patient = sign(email)
    assert "Synthetic Updated Patient" in get(patient, "/profile/").text
    print("PASS 1: registration, profile, logout, email login and persisted profile")

    doctor = sign("doctor@example.test")
    day = (date.today() + timedelta(days=5)).isoformat()
    post(doctor, "/availability/", {"date": day, "start": "11:00", "end": "11:24", "consultation_type": "in_person"})
    assert "11:00" in get(doctor, f"/availability/?date={day}&period=day").text
    print("PASS 2: approved doctor publishes and retrieves calendar slots")

    directory = get(patient, "/doctors/?available=1")
    # Other browser tests may add doctors. Select this fixture's doctor by
    # identity instead of assuming the first available card belongs to it.
    profile_link = re.search(r'href="(/doctors/(\d+)/)">Test Doctor</a>', directory.text)
    assert profile_link, "The approved Test Doctor fixture is missing"
    path = "/book/" + profile_link[2] + "/"
    booking = get(patient, path + "?date=" + day)
    slot = re.search(r'name="slot" value="(\d+)"', booking.text)[1]
    response = post(patient, path + "?date=" + day, {"slot": slot, "mode": "in_person", "reason": "Synthetic HTTP acceptance", "consent": "on"})
    assert "Synthetic HTTP acceptance" in response.text
    appointment_path = response.url.removeprefix(ORIGIN)
    print("PASS 3: discovery, booking and saved appointment confirmation")

    other = sign("other@example.test")
    duplicate = post(other, path + "?date=" + day, {"slot": slot, "mode": "in_person", "reason": "Synthetic duplicate", "consent": "on"})
    assert "no longer available" in duplicate.text
    assert other.get(ORIGIN + appointment_path, timeout=10).status_code == 404
    print("PASS 4: duplicate booking rejected and object access isolated")

    def action(session, value):
        page = get(session, appointment_path)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.text)[1]
        response = session.post(ORIGIN + appointment_path + "action/", data={"csrfmiddlewaretoken": token, "action": value}, headers={"Origin": ORIGIN}, timeout=10)
        response.raise_for_status()
        return response

    assert "Confirmed" in action(doctor, "confirmed").text
    assert "Confirmed" in get(patient, appointment_path).text
    assert "Cancelled" in action(patient, "cancelled").text
    assert f'value="{slot}"' in get(patient, path + "?date=" + day).text
    print("PASS 5: doctor confirms, patient sees status and cancellation releases slot")

    reception = sign("reception@example.test")
    assert "Synthetic Updated Patient" in get(reception, "/patients/?q=" + email).text
    assert reception.get(ORIGIN + "/admin/users/", timeout=10).status_code == 403
    pharmacy = sign("pharmacy@example.test")
    assert "Inventory" in get(pharmacy, "/inventory/").text
    assert pharmacy.get(ORIGIN + "/patients/", timeout=10).status_code == 403
    print("PASS 6: receptionist and pharmacist role boundaries")

    admin = sign("admin@example.test")
    assert "User management" in get(admin, "/admin/users/").text
    assert "Operational report" in get(admin, "/admin/operations/").text
    metadata = get(admin, "/admin/data/schema/?table=care_department")
    assert "SQL type" in metadata.text and "care_department" in metadata.text
    assert patient.get(ORIGIN + "/admin/data/schema/", timeout=10).status_code == 403
    print("PASS 7: administrator operational pages and actual schema metadata; patient denied")

    assert get(patient, "/health/").json() == {"status": "ok"}
    assert "Appointment cancelled." in get(patient, "/notifications/").text
    assert patient.post(ORIGIN + "/profile/", data={"name": "forged"}, timeout=10).status_code == 403
    print("PASS 8: health, saved notifications and actual HTTP CSRF rejection")


if __name__ == "__main__":
    main()
