# Lesson 5: Broken Access Control

## Part 1) Goal and Vulnerability Summary

This lesson demonstrates a Broken Access Control vulnerability in the DVSA application. A normal authenticated user can invoke a sensitive backend operation (`complete`) through the public API and change the order status to "paid" without completing the normal billing workflow.

The affected component is the AWS Lambda function `DVSA-ORDER-MANAGER`, which routes API actions to backend services. The impact is that users can bypass the payment process and manipulate order state.

---

## Part 2) Why This Works / Root Cause

The vulnerability exists due to missing authorization checks on sensitive actions. The backend trusts the `action` parameter from the client request and does not verify whether the user is allowed to perform that action.

Specifically, the `complete` action directly invokes the `DVSA-ORDER-COMPLETE` function without validating user role or order state.

---

## Part 3) Environment and Setup

- DVSA deployed on AWS (us-east-1)
- API Gateway endpoint:
  `https://snw2nobdde.execute-api.us-east-1.amazonaws.com/dvsa/order`
- Tool used: Postman
- Authorization: JWT token captured from browser DevTools
- Target Lambda function: `DVSA-ORDER-MANAGER`

---

## Part 4) Reproduction Steps

1. Log in to DVSA as a normal user.
2. Create a new order and proceed to shipping stage.
3. Do NOT complete billing through the normal flow.
4. Capture the API request and JWT token using DevTools.
5. Send the following request using Postman:

```json
{
  "action": "complete",
  "order-id": "f3817a9b-d005-4981-9b11-3263592f7db3"
}

Part 5) Evidence and Proof
The API accepted the request and returned a success message.
The order status was updated to "paid" on the website.
No billing/payment step was completed.

This proves that a user can manipulate order status through the API.

Part 6) Fix Strategy / Probable Mitigation

The fix is to enforce strict authorization checks on sensitive actions.

The backend should verify:

whether the user is allowed to perform the action
whether the order is in the correct state
whether the action originates from a trusted internal workflow

The complete action should not be accessible from public API calls.

Part 7) Code / Config Changes
Before (vulnerable code):
case "complete":
    payload = { "orderId": req["order-id"] };
    functionName = "DVSA-ORDER-COMPLETE";
    break;
After (fixed code):
case "complete":
    if (isAdmin == "true") {
        payload = { "orderId": req["order-id"] };
        functionName = "DVSA-ORDER-COMPLETE";
        break;
    } else {
        const response = {
            statusCode: 403,
            headers: {
                "Access-Control-Allow-Origin": "*"
            },
            body: JSON.stringify({
                "status": "err",
                "msg": "Unauthorized"
            })
        };
        callback(null, response);
        return;
    }
Part 8) Verification After Fix
Send the same request again:
{
  "action": "complete",
  "order-id": "f3817a9b-d005-4981-9b11-3263592f7db3"
}
Expected result:
{
  "status": "err",
  "msg": "Unauthorized"
}
Verify:
The order status does NOT change.
Normal users can no longer bypass the billing process.