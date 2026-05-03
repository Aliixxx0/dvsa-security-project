# Lesson 9: Vulnerable Dependencies

## Part 1) Goal and Vulnerability Summary

This lesson demonstrates a vulnerable dependency in the DVSA application. The backend uses the `node-serialize` library, which allows unsafe deserialization of attacker-controlled input.

The affected component is the `DVSA-ORDER-MANAGER` Lambda function. The impact is that an attacker can inject JavaScript code into the request, which may be executed during deserialization.

---

## Part 2) Why This Works / Root Cause

The vulnerability exists because the application uses:

```javascript
serialize.unserialize(event.body)