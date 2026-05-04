# Lesson 10: Unhandled Exceptions

## Part 1) Goal and Vulnerability Summary

This lesson demonstrates an Unhandled Exceptions vulnerability in the DVSA application. When invalid or malformed input is sent to the backend API, the system crashes and returns detailed error information to the client.

The affected component is the AWS Lambda function responsible for handling order updates (`DVSA-ORDER-UPDATE`). The impact is that sensitive internal details such as file paths, source code structure, and line numbers are exposed to the user.

---

## Part 2) Why This Works / Root Cause

The vulnerability exists because the backend code does not properly validate input before using it. Specifically, it directly accesses fields like `event["items"]` without checking whether they exist.

When a required field is missing, a Python exception (`KeyError`) is raised, and the system does not handle it properly. As a result, the full stack trace is returned to the client instead of a safe error message.

---

```json
{
  "action": "update",
  "order-id": "f3817a9b-d005-4981-9b11-3263592f7db3"
}

Part 5) Evidence and Proof

The system returns the following response:

{
  "errorMessage": "'items'",
  "errorType": "KeyError",
  "stackTrace": [
    "File \"/var/task/update_order.py\", line 18, in lambda_handler\n itemList = event[\"items\"]\n"
  ]
}

Part 6) Fix Strategy / Probable Mitigation

The fix is to implement proper input validation and exception handling in the backend code.

The application should:

validate required fields before accessing them
ensure correct data types
handle exceptions using try/catch blocks
return generic error messages instead of stack traces
Part 7) Code / Config Changes
Before (vulnerable code):
orderId = event["orderId"]
itemList = event["items"]
userId = event["user"]
After (fixed code):
try:
    orderId = event.get("orderId")
    itemList = event.get("items")
    userId = event.get("user")

    if not orderId:
        return {"status": "err", "msg": "missing orderId"}

    if not userId:
        return {"status": "err", "msg": "unauthenticated"}

    if not isinstance(itemList, dict) or len(itemList) == 0:
        return {"status": "err", "msg": "invalid or missing items"}

except Exception:
    return {"status": "err", "msg": "invalid request"}
Part 8) Verification After Fix
Send the same malformed request again:
{
  "action": "update",
  "order-id": "f3817a9b-d005-4981-9b11-3263592f7db3"
}
Expected result:
{
  "status": "err",
  "msg": "invalid or missing items"
}
Verify:
No stack trace is returned.
No internal file paths or code details are exposed.