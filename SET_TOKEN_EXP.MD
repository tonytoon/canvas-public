# Canvas Token Expiration Tool

## Overview

`set_token_exp.py` adds or enforces expiration dates on **user-generated Canvas API tokens** belonging to administrative users.

The script:

- Finds admin users in a Canvas account or subaccount
- Optionally traverses subaccounts recursively
- Adds expiration dates to tokens that do not already expire
- Optionally shortens token lifetimes that exceed a configured maximum
- Supports excluding specific Canvas users

## Requirements

Python dependencies:

```bash
pip install canvasapi requests
```

If you are using more than one script from this repository you can also install dependencies for all of them using pip.

```bash
pip install -r requirements.txt
```

Required environment variables:

```bash
export CANVAS_LMS_URL="https://myinstitution.instructure.com"
export CANVAS_LMS_TOKEN="secret"
```

---

## Usage

```bash
python set_token_exp.py -a ACCOUNT_ID -d DAYS [options]
```

Required arguments:

| Argument | Description |
|----------|-------------|
| `-a`, `--account` | Canvas account/subaccount ID containing admins |
| `-d`, `--days` | Expiration age to assign to tokens without expirations |

Optional arguments:

| Argument | Description |
|----------|-------------|
| `-r`, `--recursive` | Include all subaccounts recursively |
| `-m`, `--max [DAYS]` | Cap existing token lifetimes. Defaults to `--days` when specified without a value |
| `-x`, `--exclude` | Exclude user IDs directly or via file |

---

## Examples

Set missing expirations to 365 days:

```bash
python set_token_exp.py -a 417 -d 365
```

Also include subaccounts:

```bash
python set_token_exp.py -a 417 -d 365 -r
```

Cap existing tokens at 365 days:

```bash
python set_token_exp.py -a 417 -d 365 -m
```

Set missing expirations to 365 days but allow existing tokens up to 730 days:

```bash
python set_token_exp.py -a 417 -d 365 -m 730
```

Exclude users listed in a file:

```bash
python set_token_exp.py -a 417 -d 365 -x exclude.txt
```

`exclude.txt` format:

```text
12345
67890
```

---

## Token Processing Logic

For each admin user:

1. Retrieve user-generated tokens
2. Ignore non-user-generated tokens
3. If `expires_at` is missing → assign expiration using `--days`
4. If expiration exceeds configured maximum → reduce expiration
5. Skip excluded users

---

## Notes

- Requires a Canvas API token with sufficient administrative permissions
- Uses direct Canvas REST calls for token operations not exposed by `canvasapi`
- Operates only on `User-Generated` tokens
