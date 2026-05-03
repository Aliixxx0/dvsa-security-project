const { LambdaClient, InvokeCommand } = require("@aws-sdk/client-lambda");
const { CognitoIdentityProviderClient, AdminGetUserCommand } = require("@aws-sdk/client-cognito-identity-provider");
const jose = require("node-jose");

function response(statusCode, body) {
    return {
        statusCode: statusCode,
        headers: {
            "Access-Control-Allow-Origin": "*"
        },
        body: JSON.stringify(body)
    };
}

exports.handler = (event, context, callback) => {
    let req = {};
    let headers = {};

    try {
        req = typeof event.body === "string" ? JSON.parse(event.body) : event.body;
        headers = event.headers || {};
    } catch (e) {
        callback(null, response(400, {
            status: "err",
            msg: "invalid request body"
        }));
        return;
    }

    const auth_header = headers.Authorization || headers.authorization;

    if (!auth_header) {
        callback(null, response(401, {
            status: "err",
            msg: "missing authorization"
        }));
        return;
    }

    const token_sections = auth_header.split(".");

    if (token_sections.length < 2) {
        callback(null, response(401, {
            status: "err",
            msg: "invalid token"
        }));
        return;
    }

    let token = {};

    try {
        const auth_data = jose.util.base64url.decode(token_sections[1]);
        token = JSON.parse(auth_data);
    } catch (e) {
        callback(null, response(401, {
            status: "err",
            msg: "invalid token"
        }));
        return;
    }

    const user = token.username;

    if (!user) {
        callback(null, response(401, {
            status: "err",
            msg: "missing user"
        }));
        return;
    }

    let isAdmin = false;

    const params = {
        UserPoolId: process.env.userpoolid,
        Username: user
    };

    const cognitoidentityserviceprovider = new CognitoIdentityProviderClient();
    const command = new AdminGetUserCommand(params);

    cognitoidentityserviceprovider.send(command)
        .then((userData) => {
            const len = Object.keys(userData.UserAttributes).length;

            for (let i = 0; i < len; i++) {
                if (userData.UserAttributes[i].Name === "custom:is_admin") {
                    isAdmin = userData.UserAttributes[i].Value;
                    break;
                }
            }

            const action = req.action;
            let payload = {};
            let functionName = "";

            switch (action) {
                case "new":
                    payload = {
                        user: user,
                        cartId: req["cart-id"],
                        items: req["items"]
                    };
                    functionName = "DVSA-ORDER-NEW";
                    break;

                case "update":
                    payload = {
                        user: user,
                        orderId: req["order-id"],
                        items: req["items"]
                    };
                    functionName = "DVSA-ORDER-UPDATE";
                    break;

                case "cancel":
                    payload = {
                        user: user,
                        orderId: req["order-id"]
                    };
                    functionName = "DVSA-ORDER-CANCEL";
                    break;

                case "get":
                    payload = {
                        user: user,
                        orderId: req["order-id"],
                        isAdmin: isAdmin
                    };
                    functionName = "DVSA-ORDER-GET";
                    break;

                case "orders":
                    payload = {
                        user: user
                    };
                    functionName = "DVSA-ORDER-ORDERS";
                    break;

                case "account":
                    payload = {
                        user: user
                    };
                    functionName = "DVSA-USER-ACCOUNT";
                    break;

                case "profile":
                    payload = {
                        user: user,
                        profile: req["data"]
                    };
                    functionName = "DVSA-USER-PROFILE";
                    break;

                case "shipping":
                    payload = {
                        user: user,
                        orderId: req["order-id"],
                        shipping: req["data"]
                    };
                    functionName = "DVSA-ORDER-SHIPPING";
                    break;

                case "billing":
                    payload = {
                        user: user,
                        orderId: req["order-id"],
                        billing: req["data"]
                    };
                    functionName = "DVSA-ORDER-BILLING";
                    break;

                case "complete":
                    if (isAdmin === "true") {
                        payload = {
                            orderId: req["order-id"]
                        };
                        functionName = "DVSA-ORDER-COMPLETE";
                        break;
                    }

                    callback(null, response(403, {
                        status: "err",
                        msg: "Unauthorized"
                    }));
                    return;

                case "inbox":
                    payload = {
                        action: "inbox",
                        user: user
                    };
                    functionName = "DVSA-USER-INBOX";
                    break;

                case "message":
                    payload = {
                        action: "get",
                        user: user,
                        msgId: req["msg-id"],
                        type: req["type"]
                    };
                    functionName = "DVSA-USER-INBOX";
                    break;

                case "delete":
                    payload = {
                        action: "delete",
                        user: user,
                        msgId: req["msg-id"]
                    };
                    functionName = "DVSA-USER-INBOX";
                    break;

                case "upload":
                    payload = {
                        user: user,
                        file: req["attachment"]
                    };
                    functionName = "DVSA-FEEDBACK-UPLOADS";
                    break;

                case "feedback":
                    callback(null, response(200, {
                        status: "ok",
                        message: `Thank you ${req["data"]["name"]}.`
                    }));
                    return;

                case "admin-orders":
                    if (isAdmin === "true") {
                        payload = {
                            user: user,
                            data: req["data"]
                        };
                        functionName = "DVSA-ADMIN-GET-ORDERS";
                        break;
                    }

                    callback(null, response(403, {
                        status: "err",
                        message: "Unauthorized"
                    }));
                    return;

                default:
                    callback(null, response(400, {
                        status: "err",
                        msg: "invalid action"
                    }));
                    return;
            }

            const lambda_client = new LambdaClient();

            const invokeParams = {
                FunctionName: functionName,
                InvocationType: "RequestResponse",
                Payload: JSON.stringify(payload)
            };

            const invokeCommand = new InvokeCommand(invokeParams);

            lambda_client.send(invokeCommand)
                .then((lambda_response) => {
                    const data = JSON.parse(Buffer.from(lambda_response.Payload).toString());
                    callback(null, response(200, data));
                })
                .catch((e) => {
                    console.log(e);
                    callback(null, response(500, {
                        status: "err",
                        msg: "backend error"
                    }));
                });
        })
        .catch((e) => {
            console.log(e);
            callback(null, response(401, {
                status: "err",
                msg: "authorization failed"
            }));
        });
};