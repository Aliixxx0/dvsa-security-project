import json
import boto3
import os

# status list
# -----------
# 100: open
# 110: payment-failed
# 120: paid
# 200: processing
# 210: shipped
# 300: delivered
# 500: cancelled
# 600: rejected

def lambda_handler(event, context):
  orderId = event.get("orderId")
  itemList = event.get("items")
  userId = event.get("user")

  if not orderId:
    return {"status": "err", "msg": "missing orderId"}

  if not userId:
    return {"status": "err", "msg": "unauthenticated"}

  if not isinstance(itemList, dict) or len(itemList) == 0:
    return {"status": "err", "msg": "invalid or missing items"}

  for itemId, qty in itemList.items():
    try:
      qty = int(qty)
    except Exception:
      return {"status": "err", "msg": "invalid quantity"}

    if qty <= 0:
      return {"status": "err", "msg": "quantity must be positive"}

  dynamodb = boto3.resource("dynamodb")
  table = dynamodb.Table(os.environ["ORDERS_TABLE"])

  response = table.get_item(
    Key={
      "orderId": orderId,
      "userId": userId
    },
    AttributesToGet=["orderStatus"]
  )

  if "Item" not in response:
    return {"status": "err", "msg": "could not find order"}

  if response["Item"]["orderStatus"] > 110:
    return {"status": "err", "msg": "order already paid"}

  response = table.update_item(
    Key={
      "orderId": orderId,
      "userId": userId
    },
    UpdateExpression="SET itemList = :itemList",
    ExpressionAttributeValues={
      ":itemList": itemList
    }
  )

  if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
    return {"status": "ok", "msg": "cart updated"}

  return {"status": "err", "msg": "could not update cart"}