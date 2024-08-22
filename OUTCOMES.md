## Outcomes
In order to better gather student outcomes on a large scale, we developed a basic in-house solution where all students taking a given course throughout our institution would also be enrolled into an "Outcomes" organization, where they would take any exams from which we wanted to easily grab aggregate data. (Much of this was deployed before solutions within Canvas could meet our exact use case and we've not had time to investigate what kind of work it would take to switch to using built-in tools...)

This script does the following:
1. It reads the required configuration from any and all JSON files located in $CANVAS_DIR/etc/outcomes.d
2. We use a single JSON per term, and can add/remove them as needed.
3. It identifies all sections of the courses we've defined in our configuration as needing a matching outcomes organization.
4. It builds an sis feed file that creates the outcomes shells needed, creates a section within each shell that maps back to an actual course section, and copies enrollments over. Users in each section are unable to see users from the other sections.
5. Students remain students, while teachers are given the "outcomes instructor" role within the shell. This role does not have the ability to modify quizzes. This is to prevent an instructor inadvertently modifying an institution-wide exam.
6. The resulting feed files are then zipped up and uploaded to our Canvas instance. I use Canvas's built-in diffing functionality so that Canvas can dynamically create/remove courses, sections, and enrollments on its own.
7. We run this script as a scheduled job three times a day, to ensure that any enrollment changes are reflected in a timely manner.
8. Individuals responsible for loading and maintaining the exams administered through these shells are added with the teacher role manually after the first time this script is run.
8. As a result, the number of support cases involving students needing access to the institution-wide outcomes exam have dropped substantially from dozens to practically zero.

You may find this script a useful example of:
1. Searching for courses in given subaccounts and/or terms.
2. Building and sending SIS feeds to Canvas.
3. Use of the diffing functionality offered by Canvas.
