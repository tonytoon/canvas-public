# Canvas user-generated token expiration management tool
# 2026 Tony Toon <rtoon@ivytech.edu>

import os
import sys
import argparse
from canvasapi import Canvas
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

GLOBALS = {}


def checkEnv():
    required_env = [
        "CANVAS_LMS_URL",
        "CANVAS_LMS_TOKEN",
    ]

    missing = [var for var in required_env if var not in os.environ]

    if missing:
        missing_text = "\n".join(f"  {var}" for var in missing)

        print(
            f"""Missing required environment variables:
        {missing_text}

        Example:
        export CANVAS_LMS_URL="https://canvas.example.edu"
        export CANVAS_LMS_TOKEN="your-token"
        """,
            file=sys.stderr,
        )
        return False

    GLOBALS["api_url"] = os.environ["CANVAS_LMS_URL"]
    GLOBALS["api_key"] = os.environ["CANVAS_LMS_TOKEN"]
    GLOBALS["session"] = requests.Session()
    GLOBALS["session"].headers.update(
        {
            "Authorization": f"Bearer {GLOBALS["api_key"]}",
            "User-Agent": "Canvas Token Tool/1.0",
        }
    )
    return True


def initArgs():
    parser = argparse.ArgumentParser(
        description="Add expiration dates to user-generated Canvas authentication tokens belonging to admin users.",
        epilog="""
    Requires environment variables:
      CANVAS_LMS_URL     Canvas instance URL
      CANVAS_LMS_TOKEN   Canvas API token

    Example:
      export CANVAS_LMS_URL="https://canvas.example.edu"
      export CANVAS_LMS_TOKEN="your-token"

   Examples:
      %(prog)s -a 417 -d 365
          Set authentication tokens without an expiration date for all admin users in account 417 to expire in 365 days.

      %(prog)s -a 417 -d 365 -m
          As prior, but also reduce existing token expiration dates to 365 days.

      %(prog)s -a 417 -d 365 -m 730
          Set missing expirations to 365 days and cap existing expirations at 730 days

      %(prog)s -a 417 -d 365 -r -x exclude.txt
          Set authentication tokens without an expiration date for all admin users in account 417 to expire in 365 days.
          Also include admin users in all subaccounts (recursively).
          Exclude admins listed in exclude.txt (plaintext, one canvas id per line).
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-a",
        "--account",
        type=int,
        required=True,
        help="Canvas id of (sub)account containing admin users.",
    )

    parser.add_argument(
        "-r",
        "--recursive",
        help="Also recursively process all subaccounts.",
        action="store_true",
    )

    parser.add_argument(
        "-d",
        "--days",
        type=int,
        required=True,
        help="Number of days (from today) to set as expiration date.",
    )

    parser.add_argument(
        "-m",
        "--max",
        nargs="?",
        type=int,
        const=None,
        default=None,
        help="Maximum token lifetime in days. Tokens exceeding this value will have their expiration reduced. Only applied when -m/--max is specified. Defaults to the value passed to -d/--days. Must be greater than -d/--days.",
    )

    parser.add_argument(
        "-x",
        "--exclude",
        nargs="+",
        help="Canvas ids of users to exclude (e.g. -x 1234 1235 or -x exclude.txt).",
    )

    args = parser.parse_args()

    if args.max is None:
        args.max = args.days

    if args.max < args.days:
        parser.error("--max must be greater than or equal to --days")

    return args


def buildExclude(args):
    exclude = args.exclude
    if exclude is not None:
        if len(exclude) == 1 and Path(exclude[0]).is_file():
            with open(exclude[0]) as f:
                exclude = [line.strip() for line in f if line.strip()]

    exclude = set(int(x) for x in exclude) if exclude is not None else set()
    return exclude


def getAdmins(account, recursive=False):
    admin_users = set()

    print(f"Processing {account}", end=" ... ")

    for admin in account.get_admins():
        admin_users.add(admin.user["id"])

    print(f"{len(admin_users)} admins found.")

    if recursive:
        for subaccount in account.get_subaccounts():
            admin_users.update(getAdmins(subaccount))

    return admin_users


def getUserTokens(canvas, user_id):
    session = GLOBALS["session"]
    user = canvas.get_user(user_id)
    url = f"{GLOBALS["api_url"]}/api/v1/users/{user.id}/user_generated_tokens"
    r = session.get(url)
    try:
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        print(e)
        return []


def setTokenExpiration(canvas, token, days):
    session = GLOBALS["session"]
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    url = f"{GLOBALS["api_url"]}/api/v1/users/{token['user_id']}/tokens/{token['id']}"
    print(
        f"Setting expiration for token {token['id']} ({token['purpose']}) ({token['visible_token']}) belonging to {canvas.get_user(token['user_id'])} to {expires}."
    )

    r = session.put(
        url,
        data={"token[expires_at]": expires},
    )

    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        print(e)


def tokenExpireTooLong(token, max_expiry):
    return (
        datetime.strptime(token["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        > max_expiry
    )


def main():
    if not checkEnv():
        sys.exit(1)

    canvas = Canvas(GLOBALS["api_url"], GLOBALS["api_key"])
    args = initArgs()
    exclude = buildExclude(args)

    max_expiry = datetime.now(timezone.utc) + timedelta(days=args.days)

    account = canvas.get_account(args.account)
    admin_users = getAdmins(account, args.recursive)
    for user in admin_users:
        if exclude is not None and user in exclude:
            print(f"Skipping user {canvas.get_user(user)} - specified as exclude.")
        else:
            for token in getUserTokens(canvas, user):
                if token["app_name"] == "User-Generated":
                    if token["expires_at"] is None:
                        setTokenExpiration(canvas, token, args.days)
                    elif tokenExpireTooLong(token, max_expiry):
                        setTokenExpiration(canvas, token, args.max)


if __name__ == "__main__":
    main()
