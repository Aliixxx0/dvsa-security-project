All steps are in the attached word report

And here are the configuraiton changes made:

1- To the S3 Privileges:
{
"Statement": [
{
"Effect": "Allow",
"Action": [
"s3:GetObject",
"s3:PutObject"
],
"Resource": "arn:aws:s3:::dvsa-receipts-bucket-454231081197-us-east-1/\*"
}
]
}

2- To DynamoDB:
{
"Statement": [
{
"Effect": "Allow",
"Action": [
"dynamodb:GetItem"
],
"Resource": "arn:aws:dynamodb:us-east-1:454231081197:table/DVSA-ORDERS-DB"
}
]
}

3- After Removing AmazonSESFullAccess and creating SendEmail Policy, here is its content:
{
"Version": "2012-10-17",
"Statement": [
{
"Effect": "Allow",
"Action": [
"ses:SendEmail"
],
"Resource": "\*"
}
]
}
