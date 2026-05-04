import json
import boto3
import os
from botocore.exceptions import ClientError

# status list
# 100: open
# 105: billing in progress / locked
# 110: payment-failed
# 120: paid
# 200: processing
# 210: shipped
# 300: delivered
# 500: cancelled
# 600: rejected

def lambda_handler(event, context):
    orderId = event["orderId"]
    itemList = event["items"]
    userId = event["user"]

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])

    try:
        response = table.update_item(
            Key={
                "orderId": orderId,
                "userId": userId
            },
            UpdateExpression="SET itemList = :itemList",
            ConditionExpression="orderStatus = :open",
            ExpressionAttributeValues={
                ":itemList": itemList,
                ":open": 100
            },
            ReturnValues="UPDATED_NEW"
        )

        return {
            "status": "ok",
            "msg": "cart updated"
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "status": "err",
                "msg": "order is locked, paid, or not editable"
            }

        return {
            "status": "err",
            "msg": "could not update cart"
        }