# Bonus Vulnerability: admin_update_orders.py — JWT Trust Bypass and Privilege Confusion

## Part 1) Goal and Vulnerability Summary

This bonus finding demonstrates multiple security weaknesses in the `admin_update_orders.py` backend function. The function performs administrative order operations, but it trusts attacker-controlled data too much and does not verify authentication properly before using identity information.

The main affected component is the administrative Lambda function `admin_update_orders.py`, which interacts directly with the orders table in DynamoDB.

The security impact is severe because an attacker may be able to:
- impersonate another user by forging JWT payload claims,
- create or update orders under arbitrary user IDs,
- and exploit inconsistent key usage in database operations to bypass intended ownership checks.

---

## Part 2) Why This Works / Root Cause

This vulnerability exists because of two main security mistakes:

1. **JWT payload trust without signature verification**
   - The function base64-decodes the JWT payload and directly trusts the `username` value.
   - It does not verify the token signature, issuer, or claims before using the identity.

2. **Privilege confusion and inconsistent authorization logic**
   - In `addItem`, the function stores `userId` from `obj['userId']` instead of binding it to the authenticated caller.
   - Different database operations use different key logic:
     - `deleteItem()` uses only `orderId`
     - `getItem()` uses only `orderId`
     - `updateItem()` uses both `orderId` and `userId`

This inconsistency creates a risk that authorization and ownership checks are applied incorrectly.

---

## Part 3) Environment and Setup

- AWS Lambda administrative function reviewed: `admin_update_orders.py`
- Backend storage: DynamoDB orders table
- Analysis method:
  - source-code review
  - comparison of database key usage
  - inspection of JWT handling logic

Files used:
- `admin_update_orders.py`

---

## Part 4) Reproduction Steps

### Step 1 — Review JWT handling logic

Open `admin_update_orders.py` and locate the section that processes the `Authorization` header.

Observe that the function:
- splits the JWT into sections,
- base64-decodes the payload,
- parses the JSON,
- reads `token["username"]`,
- and uses it as the authenticated user identity.

No cryptographic signature verification is performed.

### Step 2 — Review object creation logic

Locate the `addItem(user, obj, ts)` function.

Observe that the order is stored with:

```python
'userId': obj['userId']

instead of using the authenticated user value.

This means the object owner can be chosen from request-controlled data.

Step 3 — Review inconsistent database key usage

Inspect the helper functions:

deleteItem(orderId, user)
getItem(orderId, user)
updateItem(orderId, user, obj, ts)

Observe:

deleteItem() deletes using only:
{"orderId": orderId}
getItem() fetches using only:
{"orderId": orderId}
updateItem() updates using:
{"orderId": orderId, "userId": user}

This inconsistency means authorization is not enforced uniformly.

Step 4 — Security conclusion

Based on the code logic, an attacker who can supply or forge token payload claims may impersonate another user, and an attacker who reaches this function can potentially create or operate on records with incorrect ownership semantics.

Part 5) Evidence and Proof

The following source-code findings confirm the vulnerability:

JWT handling

The code decodes and trusts the JWT payload directly:

token_sections = auth_header.split('.')
auth_data = base64.b64decode(token_sections[1])
token = json.loads(auth_data)
user = token["username"]

This shows that the backend trusts user identity from an unverified token payload.

Arbitrary user ownership in addItem

The code writes:

'userId': obj['userId']

instead of using the verified authenticated user.

Inconsistent key usage

The code uses different key formats across operations:

delete/get: only orderId
update: orderId + userId

This proves that authorization and ownership enforcement are inconsistent.

Part 6) Fix Strategy / Probable Mitigation

The function should be fixed in two major ways:

Verify JWT properly
Validate the signature using trusted Cognito keys or equivalent identity infrastructure.
Validate issuer, expiration, and expected claims before trusting user identity.
Enforce consistent ownership rules
Always derive the acting user from a verified identity source.
Never accept userId from request-controlled object data for ownership decisions.
Use a consistent DynamoDB key model across add/get/update/delete operations.

This ensures authentication integrity and consistent authorization enforcement.

Part 7) Code / Config Changes
Vulnerable pattern 1 — unverified JWT trust
token_sections = auth_header.split('.')
auth_data = base64.b64decode(token_sections[1])
token = json.loads(auth_data)
user = token["username"]
Fixed idea

Replace payload-only trust with verified JWT validation using trusted signing keys and claim checks.

Vulnerable pattern 2 — userId taken from attacker-controlled object
'userId': obj['userId']
Fixed idea

Bind ownership to the verified authenticated user:

'userId': user
Vulnerable pattern 3 — inconsistent database keys

Before:

delete/get use only orderId
update uses orderId and userId

Fixed idea:

use the same composite key format consistently for all operations
require both orderId and verified userId for access-sensitive operations
Part 8) Verification After Fix

After applying the fix:

A forged or modified JWT should be rejected.
Order ownership should always be tied to the verified authenticated user.
Add/get/update/delete operations should all enforce the same key and ownership model.
Administrative actions should no longer allow arbitrary cross-user data manipulation.

Expected security result:

token forgery no longer works,
request-controlled userId cannot override ownership,
and inconsistent authorization behavior is removed.
Part 9) Structured Operation and Security Analysis
Table A
Vulnerability	Intended Rule(s)	Artifacts Used	Normal Behavior	Exploit Behavior
JWT Trust Bypass + Privilege Confusion in admin_update_orders.py	Only verified identities may control order ownership and admin actions	Source code, JWT parsing logic, DynamoDB key usage	Backend should trust only verified user identity and apply consistent ownership checks	Backend trusts unverified token payload and inconsistent keys, enabling privilege confusion
Table B
Vulnerability	Why This Is a Deviation	Class	Fix Applied	Post-Fix Verification
JWT Trust Bypass + Privilege Confusion in admin_update_orders.py	The backend accepts unverified identity claims and mixes ownership enforcement rules across operations	Intentional misuse / security-relevant abuse	Verify JWT, bind ownership to verified user, standardize DynamoDB key usage	Forged tokens fail, ownership is consistent, and unauthorized cross-user