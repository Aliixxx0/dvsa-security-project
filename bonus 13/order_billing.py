import json
import urllib3
import boto3
import os
import time
import decimal
from decimal import Decimal


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
    print(json.dumps(event))

    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                if o % 1 > 0:
                    return float(o)
                else:
                    return int(o)
            return super(DecimalEncoder, self).default(o)

    try:
        orderId = event.get("orderId")
        userId = event.get("user")
        billing = event.get("billing")

        if not orderId:
            return {"status": "err", "msg": "missing orderId"}

        if not userId:
            return {"status": "err", "msg": "unauthenticated"}

        if not isinstance(billing, dict):
            return {"status": "err", "msg": "missing billing data"}

        for field in ["ccn", "exp", "cvv"]:
            if field not in billing or not str(billing[field]).strip():
                return {"status": "err", "msg": "missing billing field"}

        http = urllib3.PoolManager()

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(os.environ["ORDERS_TABLE"])

        response = table.get_item(
            Key={
                "orderId": orderId,
                "userId": userId
            },
            AttributesToGet=["orderId", "orderStatus", "itemList", "address"]
        )

        if "Item" not in response:
            return {"status": "err", "msg": "could not find order"}

        order = response["Item"]

        # Fix 1: Require shipping information before billing
        address = order.get("address")

        if not address:
            return {"status": "err", "msg": "shipping information required"}

        if isinstance(address, str):
            try:
                address_obj = json.loads(address)
            except Exception:
                address_obj = {}
        elif isinstance(address, dict):
            address_obj = address
        else:
            address_obj = {}

        required_shipping_fields = ["name", "address", "phone"]

        for field in required_shipping_fields:
            if field not in address_obj or not str(address_obj[field]).strip():
                return {"status": "err", "msg": "shipping information required"}

        # Fix 2: Validate item list before calculating total
        itemList = order.get("itemList")

        if not isinstance(itemList, dict) or len(itemList) == 0:
            return {"status": "err", "msg": "invalid or missing items"}

        data_dict = []

        for key, value in itemList.items():
            try:
                quantity = int(value)
            except Exception:
                return {"status": "err", "msg": "invalid quantity"}

            if quantity <= 0:
                return {"status": "err", "msg": "quantity must be positive"}

            data_dict.append({
                "itemId": key,
                "quantity": quantity
            })

        status = int(json.dumps(order["orderStatus"], cls=DecimalEncoder))

        if status >= 120:
            return {"status": "err", "msg": "order already made"}

        data = json.dumps(data_dict, cls=DecimalEncoder)

        # GET TOTAL FOR BILLING
        url = os.environ["GET_CART_TOTAL"]
        clen = len(data)

        req = http.request(
            "POST",
            url,
            body=data,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(clen)
            }
        )

        res = json.loads(req.data)
        cartTotal = float(res["total"])
        missings = res.get("missing", {})

        if cartTotal <= 0:
            return {"status": "err", "msg": "invalid order total"}

        # SEND BILLING DATA TO PAYMENT
        url = os.environ["PAYMENT_PROCESS_URL"]
        data = json.dumps(billing)
        clen = len(data)

        req = http.request(
            "POST",
            url,
            body=data,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(clen)
            }
        )

        res = json.loads(req.data)
        ts = int(time.time())

        if res["status"] == 110:
            return {"status": "err", "msg": "invalid payment details"}

        elif res["status"] == 120:
            key = {
                "orderId": orderId,
                "userId": userId
            }

            update_expression = (
                "SET orderStatus = :orderstatus, "
                "paymentTS = :paymentTS, "
                "totalAmount = :total, "
                "confirmationToken = :token"
            )

            TWOPLACES = Decimal(10) ** -2

            expression_attributes = {
                ":orderstatus": res["status"],
                ":paymentTS": ts,
                ":total": Decimal(cartTotal).quantize(TWOPLACES),
                ":token": res["confirmation_token"]
            }

            if missings:
                new_item_list = {}
                response = table.get_item(Key=key)
                items = response.get("Item", {}).get("itemList", {})

                for item in items:
                    new_item_list[item] = (
                        items[item] - missings[item]
                        if missings.get(item)
                        else items[item]
                    )

                expression_attributes[":il"] = new_item_list
                update_expression += ", itemList = :il"

            try:
                response = table.update_item(
                    Key=key,
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attributes
                )

                sqs = boto3.client("sqs")
                sqs.send_message(
                    QueueUrl=os.environ["SQS_URL"],
                    MessageBody=json.dumps({
                        "orderId": orderId,
                        "userId": userId
                    }),
                    DelaySeconds=10
                )

                return {
                    "status": "ok",
                    "amount": float(cartTotal),
                    "token": res["confirmation_token"],
                    "missing": missings
                }

            except Exception:
                return {"status": "err", "msg": "unknown error"}

        else:
            return {"status": "err", "msg": "could not process payment"}

    except Exception:
        return {"status": "err", "msg": "invalid request"}