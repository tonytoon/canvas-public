## Bulk Gradebook CSV Export

This script uses (abuses) Canvas's built-in CSV export functionality to bulk-export gradebooks from courses. This will be the same CSV that instructors would get if they initiated the export themeselves.

This script has been barely tested and offers no support and relieves itself of all liability. It worked the one time I needed it to.

This functionality is not exposed via the API so we act as a headless browser and initiate the exports that way. This is *not* an optimal way to download gradebook data, and a tool using CD2 or a custom API call that properly formats the existing grade data would be a superior approach - however this was put together on an extremely short time-frame during a time we were concerned about losing access to Canvas (see - the canvas breach of 2026).

You'll need to save the cookies from a logged in session that has access to the required subaccounts/courses. I used Cookie-Editor for Chrome to do this but there are probably others. Save the .json export as cookies.json in the same directory from which you run this script.

# TODO
So much cleanup and refactoring or preferably - write a tool that uses the normal API and creates a match for the CSV export.
