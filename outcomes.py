#!/usr/bin/env python3

import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from canvasapi import Canvas  # used for interfacing with canvas

CANVAS_DIR = os.environ["CANVAS_DIR"]
API_URL = os.environ["CANVAS_SERVER_NAME"]
API_KEY = os.environ["CANVAS_LMS_TOKEN"]

output = Path(CANVAS_DIR) / "output" / "outcomes"
output.mkdir(parents=True, exist_ok=True)
configdir = Path(CANVAS_DIR) / "etc" / "outcomes.d"

config_files = [f for f in configdir.iterdir() if f.is_file()]

configdata = []

# read config information
for config_file in config_files:
    f = open(config_file.absolute())
    configdata.append(json.load(f))
    f.close()

# account info
for config in configdata:
    account_id = config["account_id"]
    account_ids = config["account_ids"]

    # Initialize a new Canvas object
    canvas = Canvas(API_URL, API_KEY)
    account = canvas.get_account(account_id)

    # list of courses needing outcomes organizations
    outcomes_courses = config["outcomes_courses"]

    # term/acct information
    term_name = config["term_name"]
    terms = config["terms"]
    term_suffix = config["term_suffix"]
    term_id = config["org_term"]

    ########### nothing below this line should need to modified per term

    outcomes_acct_code = config["outcomes_acct_code"]
    org_suffix = f"-{config['org_suffix']}-{term_suffix}-INI"

    # part of term codes
    termcodes = config["termcodes"]

    # diffing options
    # see: https://canvas.instructure.com/doc/api/file.sis_csv.html
    diff_code = "OUTCOMES-" + term_suffix
    diff_remaster = False
    clear_sticky = True
    override_sticky = True

    # file handling
    courses_header = [
        "course_id",
        "short_name",
        "long_name",
        "account_id",
        "term_id",
        "status",
    ]
    sections_header = [
        "section_id",
        "course_id",
        "name",
        "status",
        "start_date",
        "end_date",
    ]
    enrollments_header = [
        "course_id",
        "user_id",
        "role",
        "section_id",
        "status",
        "limit_section_privileges",
    ]

    courses_file = tempfile.NamedTemporaryFile(prefix="crs_", suffix=".csv")
    sections_file = tempfile.NamedTemporaryFile(prefix="sec_", suffix=".csv")
    enrollments_file = tempfile.NamedTemporaryFile(prefix="enr_", suffix=".csv")

    # generate courses
    courses = []

    # we want source courses of: ACCT101 in P1 sub-account
    # to create a single org of: ACCT101-OUTCOMES-SW-ORGZ-202210-INI

    print("processing courses.")
    for course_code in outcomes_courses:
        courses.append(
            [
                f"{course_code}{org_suffix}",
                f"{course_code}{org_suffix}",
                f"{term_name} {course_code} Outcomes",
                outcomes_acct_code,
                term_id,
                "ACTIVE",
            ]
        )
    print(f"{len(courses)} courses found.")
    print(f"writing to {courses_file.name}.")

    # write courses.csv
    with open(courses_file.name, "w", encoding="UTF8", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(courses_header)
        csvwriter.writerows(courses)

    # generate sections
    sections = []

    # we want a source course of:       ACCT101-0AC-C1-202210-VI-81X
    # to create an outcomes section of: ACCT101-0AC-C1-202210-VI-OUTCOMES-81X
    # in the organization:              ACCT101-OUTCOMES-SW-ORGZ-202210-INI
    print("processing sections")
    for term in terms:
        this_term = canvas.get_account(account_id).get_enrollment_term(term)
        for course_code in outcomes_courses:
            for a in account_ids:
                src_courses = canvas.get_account(a).get_courses(
                    search_term=course_code, enrollment_term_id=term
                )
                for c in src_courses:
                    if "ORGZ" not in c.course_code:
                        section = c.course_code
                        for tc in termcodes:
                            section = section.replace(tc, f"OUTCOMES-{tc}")
                        sections.append(
                            [
                                section,
                                f"{course_code}{org_suffix}",
                                section,
                                "ACTIVE",
                                this_term.start_at,
                                this_term.end_at,
                            ]
                        )
    print(f"{len(sections)} sections found.")

    # write sections.csv
    with open(sections_file.name, "w", encoding="UTF8", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(sections_header)
        csvwriter.writerows(sections)

    # generate enrollments
    enrollments = []

    print("generating enrollments.")
    for term in terms:
        for course_code in outcomes_courses:
            for a in account_ids:
                src_courses = canvas.get_account(a).get_courses(
                    search_term=course_code, enrollment_term_id=term
                )
                target_org = f"{course_code}{org_suffix}"
                for c in src_courses:
                    if "ORGZ" not in c.course_code:
                        section = c.course_code
                        for tc in termcodes:
                            section = section.replace(tc, f"OUTCOMES-{tc}")

                        # add students
                        s_users = c.get_users(enrollment_type=["student"])
                        for s in s_users:
                            enrollments.append(
                                [
                                    target_org,
                                    s.sis_user_id,
                                    "student",
                                    section,
                                    "active",
                                    "TRUE",
                                ]
                            )

                        # add instructors
                        # we use the Outcomes Instructor role in the outcomes org
                        # for custom permissions
                        t_users = c.get_users(enrollment_type=["teacher"])
                        for t in t_users:
                            enrollments.append(
                                [
                                    target_org,
                                    t.sis_user_id,
                                    "Outcomes Instructor",
                                    section,
                                    "active",
                                    "TRUE",
                                ]
                            )

    print(f"{len(enrollments)} found.")

    # write enrollments.csv
    with open(enrollments_file.name, "w", encoding="UTF8", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(enrollments_header)
        csvwriter.writerows(enrollments)

    # create final output file names
    now = datetime.now()
    time_string = now.strftime("%Y%m%d%H%M%S")
    output_zip_name = f"{term_suffix}_outcomes_enrollments_{time_string}.zip"
    output_zip_file = Path(output / output_zip_name)

    # create zip file to upload
    zipObj = ZipFile(output_zip_file, "w")
    zipObj.write(courses_file.name, Path(courses_file.name).name)
    zipObj.write(sections_file.name, Path(sections_file.name).name)
    zipObj.write(enrollments_file.name, Path(enrollments_file.name).name)
    zipObj.close()

    # upload sis feed
    # check https://canvas.instructure.com/doc/api/file.sis_csv.html
    # since we use diffing, we have to use the api
    account.create_sis_import(
        str(output_zip_file.resolve()),
        diffing_data_set_identifier=diff_code,
        diffing_drop_status="inactive",
        diffing_remaster_data_set=diff_remaster,
        override_sis_stickiness=override_sticky,
        clear_sis_stickiness=clear_sticky,
    )
