import json
import urllib3
import boto3
import os
import time
import decimal
from decimal import Decimal
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    orderId = event["orderId"]
    userId = event["user"]
    
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    
    # 🔒 LOCK ORDER (Atomic update to prevent double-charging)
    try:
        table.update_item(
            Key={
                "orderId": orderId,
                "userId": userId
            },
            UpdateExpression="SET orderStatus = :locked",
            ConditionExpression="orderStatus = :open",
            ExpressionAttributeValues={
                ":locked": 105, # Status: billing in progress
                ":open": 100    # Status: open
            }
        )
    except ClientError as e:
        # If the condition (orderStatus = 100) fails, it means it's already locked or paid
        return {"status": "err", "msg": "Order is already being processed or locked"}

    http = urllib3.PoolManager()



    print(json.dumps(event))
    
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o) if o % 1 > 0 else int(o)
            return super(DecimalEncoder, self).default(o)

    # Proceed to get the items since the lock was successful
    response = table.get_item(
        Key={
            "orderId": orderId,
            "userId": userId
        },
        AttributesToGet=['orderId', 'orderStatus', 'itemList']
    )

    if 'Item' not in response:
        return {"status": "err", "msg": "could not find order"}

    status = int(json.dumps(response["Item"]['orderStatus'], cls=DecimalEncoder))
    
    if status == 105:
        data_dict = []
        for key, value in response["Item"]['itemList'].items():
            data_dict.append({"itemId": key, "quantity": int(value)})
        data = json.dumps(data_dict, cls=DecimalEncoder)
        
        # GET TOTAL FOR BILLING
        url = os.environ["GET_CART_TOTAL"]
        clen = len(data)
        req = http.request("POST", url, body=data, headers={'Content-Type': 'application/json', 'Content-Length': clen})
        res = json.loads(req.data)
        cartTotal = float(res['total'])
        missings = res.get("missing", {})
            
        # SEND BILLING DATA TO PAYMENT
        url = os.environ["PAYMENT_PROCESS_URL"]
        data = json.dumps(event["billing"])
        clen = len(data)
        req = http.request("POST", url, body=data, headers={'Content-Type': 'application/json', 'Content-Length': clen})
        res = json.loads(req.data)
        ts = int(time.time())
        
        if res['status'] == 110:
            # Note: You might want to unlock the order (set back to 100) here if payment fails
            return {"status": "err", "msg": "invalid payment details"}

        elif res['status'] == 120:
            key = {"orderId": orderId, "userId": userId}
            update_expression = 'SET orderStatus = :orderstatus, paymentTS = :paymentTS, totalAmount = :total, confirmationToken = :token'
            TWOPLACES = Decimal(10) ** -2
            expression_attributes = {
                ':orderstatus': res['status'],
                ':paymentTS': ts,
                ':total': Decimal(cartTotal).quantize(TWOPLACES),
                ':token': res['confirmation_token']
            }
            
            if missings:
                new_item_list = {}
                # We already have the item from the previous get_item, but your logic refetches
                items = response.get("Item", {}).get("itemList", {})
                for item in items:
                    new_item_list[item] = items[item] - missings[item] if missings.get(item) else items[item]
                expression_attributes[":il"] = new_item_list
                update_expression += ', itemList = :il'

            try:
                table.update_item(
                    Key=key,
                    UpdateExpression=update_expression,
                    ConditionExpression="orderStatus = :locked",
                    ExpressionAttributeValues={
                        **expression_attributes,
                        ":locked": 105
                    }
                )

                # SEND MESSAGE TO SQS
                sqs = boto3.client('sqs')
                sqs.send_message(
                    QueueUrl=os.environ["SQS_URL"],
                    MessageBody=json.dumps({"orderId": orderId, "userId": userId}),
                    DelaySeconds=10
                )
                return {"status": "ok", "amount": float(cartTotal), "token": res['confirmation_token'], "missing": missings}
            except Exception:
                  return {"status": "err", "msg": "unknown error"}
            
        else:
            return {"status": "err", "msg": "could not process payment"}
    else:
        return {"status": "err", "msg": "order already made"}