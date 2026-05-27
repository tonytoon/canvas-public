import csv
import os
import time
import traceback
from pathlib import Path
from canvasapi import Canvas
from pathvalidate import sanitize_filename
from pathvalidate import sanitize_filepath
import requests
import json
import urllib.parse

# used for canvasapi. we normally run our scripts in an environment where this data is saved as environment
# variables. feel free to replace with the actual string data if you prefer.
# TODO since we have to use requests, remove all the canvasapi stuff to reduce dependenceies.

# API_URL = "https://myinstitution.instructure.com"
# API_KEY = "secret"

API_URL = os.environ["CANVAS_LMS_URL"]
API_KEY = os.environ["CANVAS_LMS_TOKEN"]

# used by requests to directly interact with the web server.
DOMAIN = "myinstitution.instructure.com"
BASE_URL = f"https://{DOMAIN}"

# directory into which to store all downloaded gradebook CSVs
# final output will be BASE_DIR/account name/subaccount name/MATH123/YYYY-MM-DDTTTT_Grades-CourseCode.csv
BASE_DIR = "gradebooks"

# term for which you need gradebooks
term_id = 3389

# the list of accounts from which you wish to retrieve gradebooks.
# it will retrieve all courses in those accounts. we did not use our
# root account because we keep our avademic courses in their own subaccounts

accounts = (16124, 16087, 16090, 16125)

# you will need to save the cookie from a session where you have logged into Canvas with an
# account that has access to the requested subaccounts/courses.
# Cookie-Editor extension for Google Chrome (export as .json) is one way to get that.
# save it as cookies.json in the same directory from which you run this script


def get_csrf_token(session):

    matches = [
        c for c in session.cookies if c.name == "_csrf_token" and DOMAIN in c.domain
    ]

    if not matches:

        matches = [c for c in session.cookies if c.name == "_csrf_token"]

    if not matches:

        raise RuntimeError("No _csrf_token cookie found")

    # Prefer shortest path / root cookie if available

    matches.sort(key=lambda c: (c.path != "/", len(c.path or "")))

    return urllib.parse.unquote(matches[0].value)


def export_gradebook(session, base_url, course_id, output_dir):
    gradebook_url = f"{base_url}/courses/{course_id}/gradebook"
    export_url = f"{base_url}/courses/{course_id}/gradebook_csv"

    page = session.get(gradebook_url)
    page.raise_for_status()

    csrf_token = get_csrf_token(session)
    if not csrf_token:
        raise RuntimeError("No _csrf_token cookie found")

    headers = {
        "X-CSRF-Token": csrf_token,
        "Referer": gradebook_url,
        "Origin": base_url,
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    r = session.post(export_url, headers=headers)
    r.raise_for_status()
    job = r.json()

    attachment_id = job["attachment_id"]
    progress_id = job["progress_id"]
    filename = job["filename"]

    while True:
        p = session.get(f"{base_url}/api/v1/progress/{progress_id}")
        p.raise_for_status()
        pdata = p.json()

        if pdata["workflow_state"] == "completed":
            break
        if pdata["workflow_state"] == "failed":
            raise RuntimeError(f"Export failed: {pdata}")

        time.sleep(1)

    user_id = pdata["user_id"]
    fm = session.get(f"{base_url}/api/v1/users/{user_id}/files/{attachment_id}")
    fm.raise_for_status()

    download_url = fm.json()["url"]

    csv_response = session.get(download_url, headers={"Referer": gradebook_url})
    csv_response.raise_for_status()

    output_path = Path(output_dir) / filename
    output_path.write_bytes(csv_response.content)

    return output_path


def main():
    canvas = Canvas(API_URL, API_KEY)
    session = requests.Session()

    with open("cookies.json", "r") as f:
        cookies = json.load(f)

    for cookie in cookies:
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )

    failures = []
    Path(BASE_DIR).mkdir(exist_ok=True)
    for account in accounts:
        campuses = canvas.get_account(account).get_subaccounts()
        for campus in campuses:
            campus_dir = f"{BASE_DIR}/{sanitize_filepath(campus.name)}"
            Path(campus_dir).mkdir(exist_ok=True)
            courses = campus.get_courses(
                with_enrollments=True, enrollment_term_id=term_id
            )
            for course in courses:
                output_dir = (
                    f"{campus_dir}/{sanitize_filename(course.course_code[0:7])}"
                )
                Path(output_dir).mkdir(exist_ok=True)
                course_id = course.id
                course_code = course.course_code
                try:
                    print(f"Exporting {course_id}...")
                    path = export_gradebook(session, BASE_URL, course_id, output_dir)
                    print(f"Downloaded: {path}")
                except Exception as e:
                    print(f"FAILED {course_code}: {e}")
                    failures.append((course_code, str(e), traceback.format_exc()))
                    continue

            with open("gradebook_export_failures.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["course", "error", "traceback"])
                writer.writerows(failures)

    print(f"Done. Failures: {len(failures)}")


if __name__ == "__main__":
    main()
