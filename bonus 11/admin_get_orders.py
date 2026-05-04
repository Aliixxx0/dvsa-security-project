import boto3
import json
import decimal
import os
import time
from boto3.dynamodb.conditions import Attr


def lambda_handler(event, context):
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                if o % 1 > 0:
                    return float(o)
                return int(o)
            return super(DecimalEncoder, self).default(o)

    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(os.environ["ORDERS_TABLE"])

        ts = int(time.time())

        date_to = event.get("to", ts)
        date_from = event.get("from", 0)

        try:
            date_to = int(date_to)
            date_from = int(date_from)
        except Exception:
            return {"status": "err", "msg": "invalid date range"}

        filter_expr = Attr("paymentTS").between(date_from, date_to)

        if "orderId" in event:
            filter_expr = filter_expr & Attr("orderId").eq(event["orderId"])

        if "userId" in event:
            filter_expr = filter_expr & Attr("userId").eq(event["userId"])

        if "status" in event:
            try:
                status = int(event["status"])
            except Exception:
                return {"status": "err", "msg": "invalid status"}

            filter_expr = filter_expr & Attr("orderStatus").eq(status)

        orders = []

        response = table.scan(FilterExpression=filter_expr)

        for item in response.get("Items", []):
            orders.append(item)

        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )

            for item in response.get("Items", []):
                orders.append(item)

        result = {
            "status": "ok",
            "orders": orders
        }

        return json.loads(json.dumps(result, cls=DecimalEncoder))

    except Exception:
        return {
            "status": "err",
            "msg": "invalid request"
        }