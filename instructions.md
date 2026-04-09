## DCT Developer Captstone Project Instructions

Welcome to your DCT DVA Capstone Project! You will be building a web application designed to show off you developer skills!

## Notes about this capstone:

- The instructions will get you 90%+ of the way there
- However, some details are missing / omitted - this is deliberate!
- Your job is to solve each challenge along the way
- It is highly recommended to use AWS CloudShell

## Web Application Workflow:

### 1. Image Upload Interface:
- Users are greeted with a web interface hosted on AWS Fargate, accessible through a custom domain managed by Route 53.
- The main page (`index.html`) includes a button that leads to an image upload page (`upload.html`), served by a Lambda function via a Function URL.

### 2. Image Upload Process:
- On the upload page, users can select and upload an image file to an S3 bucket (`$ACCOUNT_ID-upload-bucket-$REGION`).
- Metadata for the image, including the image key and a placeholder for a description, is stored in a DynamoDB table (`ImageMetadata`).

### 3. Image Processing and AI Description Generation:
- A Lambda function, triggered by the upload, processes the image, generates a unique URL, stores additional metadata, and moves the image to a separate S3 bucket for website assets (`$ACCOUNT_ID-website-assets-$REGION`).
- For AI-generated descriptions, another Lambda function retrieves the image, sends it to Amazon Bedrock (using the anthropic claude 3-haiku model), and updates the DynamoDB table with the generated description.

### 4. Viewing Uploaded Images:
- The main application page also lists all uploaded images with their AI-generated descriptions, fetched from DynamoDB and displayed to the user.

### 5. CI/CD Pipeline:
- Application updates are managed through a CI/CD pipeline using GitHub Actions.
- Changes in the GitHub repository on the main branch triggers a GitHub actions, creating a new Docker image, updating the ECR, and deploying a new task definition in AWS Fargate.

## Key Components:
- **AWS Fargate**: Hosts Docker containers for the application, ensuring scalability.
- **Amazon S3**: Stores uploaded images and website assets.
- **AWS Lambda**: Manages backend logic for the application.
- **Amazon DynamoDB**: Stores metadata and AI-generated descriptions for images.
- **Amazon Route 53**: Manages the custom domain for the application.
- **GitHub and GitHub Actions**: Automate the build, test, and deployment process.
- **Amazon Bedrock**: Utilizes the anthropic claude 3-haiku model for AI-generated image descriptions.

This project showcases a real-world application of AWS services for building, deploying, and managing a modern web application with dynamic content and automated deployment.


## Prerequisites:

- Install the AWS CLI on your local machine and authenticate as an IAM user with Admin Permissions (or use AWS CloudShell)- we will doing most of the building using the CLI.
- A domain name in Route 53 with no current or older records.
- The CLI commands will assume you are running the commands in the folder which the code files in which are being referenced, you should know how to use simple OS commands like `ls`,`pwd`, `cd` etc to naviagte the file system and interact with the AWS command line. We have built these instructions to work on a Linux OS - you can use WSL, a Mac Command line or failing that AWS CloudShell.
- Install Docker (if you are using CloudShell it should already be installed).
- Get a GitHub account and sign in
- There will be some more advanced bash syntax and scripting within this tutorial i.e variables, outputs, parameters etc. - you won't be expected to know them, but it'll give you wider exposure to building infrastructure using the AWS CLI.
- Consider installing `tree` on your linux machine to help visualise folder structure i.e.

```bash
sudo yum install tree -y # for Cloudshell / Amazon Linux 2023)
```

**Before you build this capstone project you need to go to the Amazon Bedrock console and manage your model access, and choose the anthropic claude 3-haiku model. You need to go to the providers page within Bedrock, go to Anthropic, Claude models and click Request access. For the `Describe your use case` write the following:**

*I am building a lab exercise for my students to learn more about generative AI which consists of an AI Image Description Generator application using AWS Lambda.*

- You have to fill in the form, go back on the page and select Manage Model Access again, then select the Anthropic models and scroll down and click `Save changes`.

- Access should be granted within a few minutes. Reach out to Jack on Slack if you have problems.

## Step 1: Create the Upload Microservice

We'll start by building out the `Upload` microservice, which hosts a webpage and allows the user to upload an image to be later catalogued within the application and interacted with by the AI Description Generation workflow. 

- Build the DynamoDB Table:

```bash
TABLE_NAME="ImageMetadata" && \
aws dynamodb create-table \
    --table-name "${TABLE_NAME}" \
    --attribute-definitions AttributeName=ImageKey,AttributeType=S \
    --key-schema AttributeName=ImageKey,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --tags Key=Purpose,Value=ImageMetadataStorage && \
export TABLE_NAME
```
- Build the S3 Buckets

- Retrieve your AWS Account Id and save it as a variable

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
```
- Set the AWS Region and save it as a variable (adjust as needed)

```bash
REGION=$'us-east-1'
```
-  Create a bucket for website assets (these commands use your account id and region to make it globally unique)

```bash
aws s3 mb s3://"${ACCOUNT_ID}-website-assets-${REGION}" --region "${REGION}"
```

-  Create a bucket for uploaded images
```bash
aws s3 mb s3://"${ACCOUNT_ID}-upload-bucket-${REGION}" --region "${REGION}"
```

## 2.  Build the Upload Microservice Lambda Function

 ***For all of the Lambda functions going forward, you'll need to have the Lambda deployment package (ZIP file) ready for each Lambda function, containing the function code in Python. You can zip them using the CLI or using your UI. I left it in plain text so you can read the code and understand what's going on at each step***

- use `sed` to replace placeholders within the `upload.json` from the "uploadMicroservice" to make the IAM Role permissions statement

```bash
WEBSITE_ASSETS_BUCKET="${ACCOUNT_ID}-website-assets-${REGION}"
UPLOAD_BUCKET="${ACCOUNT_ID}-upload-bucket-${REGION}"
sed -i "s/{REGION}/${REGION}/g" upload.json
sed -i "s/{ACCOUNT_ID}/${ACCOUNT_ID}/g" upload.json
sed -i "s/{WEBSITE_ASSETS_BUCKET}/${WEBSITE_ASSETS_BUCKET}/g" upload.json
sed -i "s/{UPLOAD_BUCKET}/${UPLOAD_BUCKET}/g" upload.json
```
- if you check the `upload.json` the placeholders will be replaced.

- Create the role

```bash
UPLOAD_ROLE_ARN=$(aws iam create-role \
  --role-name lambda-upload-webpage-role \
  --assume-role-policy-document file://trust-policy.json \
  --query 'Role.Arn' --output text)
```
- create and attach the policy to the role

```bash
aws iam put-role-policy \
  --role-name lambda-upload-webpage-role \
  --policy-name LambdaUploadWebpagePolicy \
  --policy-document file://upload.json
```

- create the upload webpage function (you'll have to zip your code up):

```bash
UPLOAD_WEBPAGE_FUNCTION_ARN=$(aws lambda create-function \
  --function-name upload-page-function \
  --runtime python3.12 \
  --role "$UPLOAD_ROLE_ARN" \
  --handler upload.lambda_handler \
  --zip-file fileb://upload.zip \
  --environment Variables="{WEBSITE_ASSETS_BUCKET=${ACCOUNT_ID}-website-assets-${REGION},UPLOAD_BUCKET=${ACCOUNT_ID}-upload-bucket-${REGION}}" \
  --query 'FunctionArn' --output text)
```

-  Create a function URL and access the lambda frontend:

```bash
aws lambda create-function-url-config \
    --function-name upload-page-function \
    --auth-type NONE \
    --cors '{
        "AllowCredentials":false,
        "AllowHeaders":["*"],
        "AllowMethods":["GET"],
        "AllowOrigins":["*"],
        "ExposeHeaders":["ETag", "Content-Type"],
        "MaxAge":3600
    }'
```
- Edit CORS on the Upload S3 Bucket:

(add in your function url in `AllowedOrigins` **DON'T add a slash to the end of your function URL**)

```bash
aws s3api put-bucket-cors --bucket $UPLOAD_BUCKET --cors-configuration '{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["PUT"],
      "AllowedOrigins": ["https://yourfunctionrurl"],
      "ExposeHeaders": ["ETag", "Content-Type", "Content-Length"] 
    }
  ]
}'
```
- add permissions for the lambda to be invoked by the function url

```bash
aws lambda add-permission \
    --function-name upload-page-function \
    --statement-id "FunctionURLAllowPublicAccess" \
    --action "lambda:InvokeFunctionUrl" \
    --principal "*" \
    --function-url-auth-type "NONE"
```

- Upload the website files to the website assets bucket (make sure you're in the correct directory)

First, replace the `<script>` tag in the upload.html to reflect the addition of the function URL i.e. from this:

```html
https://ex7a6l73rg6jynrfqtcpof5tue0pisuf.lambda-url.us-east-1.on.aws/
<script src="upload.js"></script>
```
to this:
```html
<script src="https://yourfunctionrurl/upload.js"></script>
```
Also - edit the placeholder within the `upload.js` with your function URL then upload to S3:

```bash
aws s3 cp upload.html s3://${ACCOUNT_ID}-website-assets-${REGION}/ && \
aws s3 cp upload.js s3://${ACCOUNT_ID}-website-assets-${REGION}/ 
```

- Test your function by accessing the webpage via the function URL and ensuring you can upload a file and that it succesfully ends up in the upload bucket

## Step 3. Creating the `Push Website Assets` function

- Create the IAM Role

- For the "pushMicroservice" use `sed` to replace placeholders within the `pushwebsiteassets.json` permissions statement

```bash
sed -i "s/{REGION}/${REGION}/g" pushwebsiteassets.json
sed -i "s/{ACCOUNT_ID}/${ACCOUNT_ID}/g" pushwebsiteassets.json
sed -i "s/{WEBSITE_ASSETS_BUCKET}/${WEBSITE_ASSETS_BUCKET}/g" pushwebsiteassets.json
sed -i "s/{UPLOAD_BUCKET}/${UPLOAD_BUCKET}/g" pushwebsiteassets.json
sed -i "s/{DYNAMODB_TABLE_NAME}/${TABLE_NAME}/g" pushwebsiteassets.json
```
- if you check the `pushwebsiteassets.json` the placeholders will be replaced.

- Create the role

```bash
PUSH_ROLE_ARN=$(aws iam create-role \
  --role-name push-website-assets-role \
  --assume-role-policy-document file://trust-policy.json \
  --query 'Role.Arn' --output text)
```
- create and attach the policy to the role

```bash
aws iam put-role-policy \
  --role-name push-website-assets-role \
  --policy-name PushWebsiteAssetsRole \
  --policy-document file://pushwebsiteassets.json
```

- create the push website function:

```bash
PUSH_FUNCTION_ARN=$(aws lambda create-function \
  --function-name push-website-function \
  --runtime python3.12 \
  --role "$PUSH_ROLE_ARN" \
  --handler push.lambda_handler \
  --zip-file fileb://push.zip \
  --memory-size 2048 \
  --environment Variables="{WEBSITE_ASSETS_BUCKET=${ACCOUNT_ID}-website-assets-${REGION},UPLOAD_BUCKET=${ACCOUNT_ID}-upload-bucket-${REGION},DYNAMODB_TABLE=${TABLE_NAME}}" \
  --layers arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p312-Pillow:1 \
  --query 'FunctionArn' --output text)
```

- Give lambda the permissions to be invoked by the event notification

```bash
aws lambda add-permission \
    --function-name "$PUSH_FUNCTION_ARN" \
    --principal s3.amazonaws.com \
    --statement-id s3invoke \
    --action "lambda:InvokeFunction" \
    --source-arn "arn:aws:s3:::$UPLOAD_BUCKET" \
    --source-account "$ACCOUNT_ID"
```

- Add S3 Event notifications to the uploadbucket

```bash
aws s3api put-bucket-notification-configuration --bucket "$UPLOAD_BUCKET" --notification-configuration "{
    \"LambdaFunctionConfigurations\": [
        {
            \"LambdaFunctionArn\": \"$PUSH_FUNCTION_ARN\",
            \"Events\": [\"s3:ObjectCreated:Put\"],
            \"Filter\": {
                \"Key\": {
                    \"FilterRules\": [
                        {
                            \"Name\": \"prefix\",
                            \"Value\": \"uploads/\"
                        }
                    ]
                }
            }
        }
    ]
}"
```

If you test the functionality now by uploading images via the orignal upload function (access the same webpage via the function url), you should see the images/uploads folder in the website assets bucket populated with the image from the upload folder, as well as the metadata placeholder populated within dynamoDB.

## Step 4: Create the Lambda Function for Fetching Image Data Microservice

This microservice will list images in the S3 bucket and query DynamoDB for metadata, returning a JSON with image URLs and descriptions to the front end to make them visible to the website users. 

- Create the IAM Role

- use `sed` to replace placeholders within the fetch.json permissions statement (copy all the commmands one at a time)

```bash
sed -i "s/{REGION}/${us-east-1}/g" fetch.json
sed -i "s/{ACCOUNT_ID}/${793323450567}/g" fetch.json
sed -i "s/{WEBSITE_ASSETS_BUCKET}/${793323450567-website-assets-us-east-1}/g" fetch.json
sed -i "s/{UPLOAD_BUCKET}/${793323450567-upload-bucket-us-east-1}/g" fetch.json
sed -i "s/{DYNAMODB_TABLE_NAME}/${ImageMetadata}/g" fetch.json
```
- if you check the fetch.json the placeholders will be replaced.

- create the role

```bash
FETCH_ROLE_ARN=$(aws iam create-role \
  --role-name fetch-images-role \
  --assume-role-policy-document file://trust-policy.json \
  --query 'Role.Arn' --output text)
```
- create and attach the policy to the role

```bash
aws iam put-role-policy \
  --role-name fetch-images-role \
  --policy-name FetchImagePolicy \
  --policy-document file://fetch.json
```
- create the upload function

```bash
FETCH_IMAGE_FUNCTION_ARN=$(aws lambda create-function \
  --function-name fetch-image-function \
  --runtime python3.12 \
  --role "$FETCH_ROLE_ARN" \
  --handler fetch.lambda_handler \
  --zip-file fileb://fetch.zip \
  --environment Variables="{WEBSITE_ASSETS_BUCKET=${ACCOUNT_ID}-website-assets-${REGION},DYNAMODB_TABLE=${TABLE_NAME}}" \
  --query 'FunctionArn' --output text)
```
Create a function URL:

```bash
aws lambda create-function-url-config \
    --function-name fetch-image-function \
    --auth-type NONE \
    --cors '{
        "AllowCredentials":false,
        "AllowHeaders":["*"],
        "AllowMethods":["GET"],
        "AllowOrigins":["*"],  
        "ExposeHeaders":["*"],
        "MaxAge":3600
    }'
```
- add permissions for the lambda to be invoked by the function url

```bash
aws lambda add-permission \
    --function-name fetch-image-function \
    --statement-id "FunctionURLAllowPublicAccess" \
    --action "lambda:InvokeFunctionUrl" \
    --principal "*" \
    --function-url-auth-type "NONE"
```
- update the placeholer in the 'index.js' file within the website files locally to add your function URL

Use the VS Code live server web extension to access your index.html and test the functionality (you should add it in cloudshell also, we are simply testing locally)

When you refresh the page it should be updated with the images you uploaded to S3.

## Step 4. Create the AI generation workflow

This lambda function is triggered when a user clicks 'Generate AI description' and grabs the image from S3 and runs a prompt to Amazon Bedrock to describe it. This respsonse is then passed to DynamoDB to be retrieved when the page is next refreshed. 

- Create the ai function:

- Use `sed` to replace placeholders within the `ai.json` permissions statement (copy all the commmands one at a time)

```bash
sed -i '' 's/{REGION}/us-east-1/g' ai.json
sed -i '' 's/{ACCOUNT_ID}/793323450567/g' ai.json
sed -i '' 's|{WEBSITE_ASSETS_BUCKET}|793323450567-website-assets-us-east-1|g' ai.json
sed -i '' 's/{TABLE_NAME}/ImageMetadata/g' ai.json
```
- If you check the ai.json the placeholders will be replaced.

- Create the role

```bash
AI_ROLE_ARN=$(aws iam create-role \
  --role-name ai-role \
  --assume-role-policy-document file://trust-policy.json \
  --query 'Role.Arn' --output text)
```
- Create and attach the policy to the role

```bash
aws iam put-role-policy \
  --role-name ai-role \
  --policy-name AIPolicy \
  --policy-document file://ai.json
```
- Create the AI function

```bash
AI_FUNCTION_ARN=$(aws lambda create-function \
  --function-name ai-function \
  --runtime python3.12 \
  --role "$AI_ROLE_ARN" \
  --timeout=300 \
  --handler ai.lambda_handler \
  --zip-file fileb://ai.zip \
  --environment Variables="{WEBSITE_ASSETS_BUCKET=${ACCOUNT_ID}-website-assets-${REGION},DYNAMODB_TABLE=${TABLE_NAME}}" \
  --query 'FunctionArn' --output text)
```

- Create a function URL:

```bash
aws lambda create-function-url-config \
    --function-name ai-function \
    --auth-type NONE \
    --cors '{
        "AllowCredentials":false,
        "AllowHeaders":["*"],
        "AllowMethods":["POST"],
        "AllowOrigins":["*"],  
        "ExposeHeaders":["*"],
        "MaxAge":3600
    }'
```

- Add permissions for the lambda to be invoked by the function url

```bash
aws lambda add-permission \
    --function-name ai-function \
    --statement-id "FunctionURLAllowPublicAccess" \
    --action "lambda:InvokeFunctionUrl" \
    --principal "*" \
    --function-url-auth-type "NONE"
```

- Add the function url in the placeholder on line 59 in your index.js and try to generate a description - it should work! To generate the description click on an image from the AI Image Gallery and then click the "Generate AI Description" button.

## Step 5. Build the web application using Docker and AWS Fargate

The next step is to build out the web application - which will works as follows:

- We'll have Docker containers hosted on ECS Fargate, using a Task Definition, and a Container image hosted in ECR

- This application will be routed behind an Application Load Balancer with an SSL certificate.The main application (index.html) will be hosted on the root of the load balancer and the upload microservice will be hosted on a separate function URL

- This will be hosted within a custom VPC with public and private subnets 

- The Application Load Balancer will be behind a custom domain name (you should already have this)

- Create your dockerfile:
  
- build your Docker image - there is a Dockerfile ready to use in the pipeline directory, but you need to copy the website files to this directory 

```bash
sudo docker build -t my-ai-app .
```

# Create the custom VPC, route tables, subnets etc.

- Create a custom VPC

```bash
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
```

- create two public subnets

```bash
PUBLIC_SUBNET_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
echo "Public Subnet 1: $PUBLIC_SUBNET_1"
PUBLIC_SUBNET_2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
echo "Public Subnet 2: $PUBLIC_SUBNET_2"
```

- create two private subnets

```bash
PRIVATE_SUBNET_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 --availability-zone us-east-1a --query 'Subnet.SubnetId' --output text)
echo "Private Subnet 1: $PRIVATE_SUBNET_1"
PRIVATE_SUBNET_2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.4.0/24 --availability-zone us-east-1b --query 'Subnet.SubnetId' --output text)
echo "Private Subnet 2: $PRIVATE_SUBNET_2"
```

- create an Internet Gateway and attach it to the VPC

```bash
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
echo "Internet Gateway ID: $IGW_ID"
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
```
- create a route table for the public subnets, add a route to the internet gateway, and associate it with the public subnets

```bash
ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
echo "Route Table ID: $ROUTE_TABLE_ID"
aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table  --route-table-id $ROUTE_TABLE_ID --subnet-id $PUBLIC_SUBNET_1
aws ec2 associate-route-table  --route-table-id $ROUTE_TABLE_ID --subnet-id $PUBLIC_SUBNET_2
```

- create an Elastic IP for the NAT Gateway

```bash
EIP_ALLOC_ID=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
echo "Elastic IP Allocation ID: $EIP_ALLOC_ID"
```

- create a NAT gateway

```bash
NAT_GW_ID=$(aws ec2 create-nat-gateway --subnet-id $PUBLIC_SUBNET_1 --allocation-id $EIP_ALLOC_ID --query 'NatGateway.NatGatewayId' --output text)
echo "NAT Gateway ID: $NAT_GW_ID"
```

- create a new route table for the private subnets

```bash
PRIVATE_ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
echo "Private Route Table ID: $PRIVATE_ROUTE_TABLE_ID"
```

- add a route to the NAT Gateway in the private route table

```bash
aws ec2 create-route --route-table-id $PRIVATE_ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_GW_ID
```

- associate the private route table with the private subnets

```bash
aws ec2 associate-route-table --route-table-id $PRIVATE_ROUTE_TABLE_ID --subnet-id $PRIVATE_SUBNET_1
aws ec2 associate-route-table --route-table-id $PRIVATE_ROUTE_TABLE_ID --subnet-id $PRIVATE_SUBNET_2
```

- create the ECR Repository ready for the Docker Image

```bash
REPO_NAME="my-ai-app"
ECR_REPO_URI=$(aws ecr create-repository --repository-name $REPO_NAME --query 'repository.repositoryUri' --output text)
echo "ECR Repository URI: $ECR_REPO_URI"
```
- tag and Push Your Docker Image to ECR

```bash
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
sudo docker tag my-ai-app:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/my-ai-app:latest
sudo docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/my-ai-app:latest
```

- create an ALB security group

```bash
ALB_SG=$(aws ec2 create-security-group --group-name my-alb-sg --description "Security group for ALB" --vpc-id $VPC_ID --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $ALB_SG --protocol tcp --port 443 --cidr 0.0.0.0/0
```

- create the ECS Security Group

```bash
ECS_TASKS_SG=$(aws ec2 create-security-group --group-name ecs-tasks-sg --description "Security group for ECS tasks" --vpc-id $VPC_ID --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $ECS_TASKS_SG --protocol tcp --port 80 --source-group $ALB_SG
```

- create the task defintition

use the sed command to edit the task-def.json file:
 
```bash
sed -i "s/ACCOUNT_ID/${ACCOUNT_ID}/g" task-def.json
```

- create a role with to be assumed by ECS

```bash
ECS_ROLE_ARN=$(aws iam create-role --role-name YourEcsTaskExecutionRole --assume-role-policy-document file://ecs-trust-policy.json --query 'Role.Arn' --output text)
sed -i "s/ECS_ROLE_NAME/${ECS_ROLE_NAME}/g" task-def.json
aws iam attach-role-policy --role-name YourEcsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```
- register the task definition with ECS:

```bash
aws ecs register-task-definition --cli-input-json file://task-def.json
```

- add the load balancer and autoscaling


- create the ALB:

```bash
ALB_ARN=$(aws elbv2 create-load-balancer --name my-web-app-alb --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 --security-groups $ALB_SG --scheme internet-facing --type application --query 'LoadBalancers[0].LoadBalancerArn' --output text)
```
- create a Target Group

```bash
TARGET_GROUP_ARN=$(aws elbv2 create-target-group --name my-web-app-tg --protocol HTTP --port 80 --vpc-id $VPC_ID --target-type ip --query 'TargetGroups[0].TargetGroupArn' --output text)
```
- create an SSL certificate for your custom domain name and the ALB domain name - simply replace with your full qualified domain name

```bash
CERT_ARN=$(aws acm request-certificate \
    --domain-name example.com \
    --validation-method DNS \
    --key-algorithm EC_prime256v1 \
    --query CertificateArn --output text)
``` 
- After requesting the certificate, you need to validate your domain. ACM provides you with a CNAME record to add to your DNS configuration if you chose DNS validation. Once ACM can verify the CNAME record, your certificate's status will change to "Issued." You'll have to do this in the console.
- Create an HTTPS Listener in the ALB console and add your certificate

- create the ECS Cluster

```bash
CLUSTER_NAME="my-ecs-cluster"
CLUSTER_ARN=$(aws ecs create-cluster --cluster-name $CLUSTER_NAME --query 'cluster.clusterArn' --output text)
echo "Cluster ARN: $CLUSTER_ARN"
```

- create your ECS service

```bash
aws ecs create-service --cluster $CLUSTER_NAME --service-name my-ai-app-service --task-definition my-ai-app --desired-count 2 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2],securityGroups=[$ECS_TASKS_SG],assignPublicIp=DISABLED}" --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=web,containerPort=80"
```

- configure Auto Scaling

```bash
aws application-autoscaling register-scalable-target --service-namespace ecs --resource-id service/$CLUSTER_NAME/my-ai-app-service --scalable-dimension ecs:service:DesiredCount --min-capacity 1 --max-capacity 4
```
- add the custom domain name

In the console add your domain name as an alias A record to the load balancer (on www. and on the naked domain) and watch it work!

Before we build the rest of the application using CICD, we need to edit the `upload.html`, as this is out of scope of the future CICD pipeline. We can do this by simply editing the `upload.html` and so that when we click `Upload images`on the webpage, it will route to the `upload.html` which is hosted on the 'upload function url'.

First edit the upload.html locally (line 16) to reflect your domain name:

```html
<a href="https://www.YOURDOMANNAME.com" class="btn btn-secondary">Back to Gallery</a>
```

Then upload the html file back into the website assets bucket. 

```bash
aws s3 cp upload.html s3://${ACCOUNT_ID}-website-assets-${REGION}
```
You will need to clear cache and hard reload for this to work properly (go to developer tools and right click the refresh button and click Clear cache and hard reload in Chrome)

Now if you access the upload.html via the function URL and try to return to the homepage, it should work. 

## Step 6. Create the CICD pipeline

If you remember, we haven't yet updated the HTML tags in the index.html to properly reflect the fact that the upload.html is hosted on the function URL. Therefore we need to now update the website files to reflect these changes.

Here's how it is now in the homepage index.html file on the live Docker container:

```html
<a href="upload.html" class="btn btn-primary mt-3 mb-3">Upload New Image</a>
```

We now need to update the `<a> tag` on the index.html that it routes back and forth to the homepage hosted behind the domain name, like this:

```html
<a href="https://UPLOADIMAGEFUNCTIONURL" class="btn btn-primary mt-3 mb-3">Upload New Image</a>
```

As the application is already succesfully created and hosted on ECS Fargate, it's not a good idea to edit this by logging on to production Web Servers and editing application code. Instead, we are going to build a CICD pipeline to edit the code safely and securely, editing the application by creating a new Fargate Task Definition, and updating the application by using the new Task Defintion. 

### Create the GitHub repository

## Step 1: Generate SSH Key on AWS CloudShell

1. Open **AWS CloudShell** and run the following command to generate an SSH key pair:

```bash
    ssh-keygen -t rsa -b 4096 -C "your_email@example.com" # use your github email
```
- You will be prompted to specify a file to save the key. Press **Enter** to accept the default location (`/home/cloudshell-user/.ssh/id_rsa`).
- You may also be prompted to set a passphrase for added security, but you can leave this blank for simplicity.

2. Once the SSH key is generated, display the public key with:

```bash
    cat ~/.ssh/id_rsa.pub
```

3. Copy the output (your SSH public key). It will look something like this:
```bash
  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQD3lD9f... your_email@example.com
  ```

## Step 2: Add SSH Key to GitHub
1. Log into your [GitHub account](https://github.com).
2. Go to **Settings** (click your profile icon in the top-right and select "Settings").
3. In the left sidebar, click **SSH and GPG keys**.
4. Click the **New SSH key** button in the top-right.
5. Give the key a title (e.g., "AWS CloudShell SSH Key") and paste your SSH public key into the "Key" field.
6. Click **Add SSH key**.

## Step 3: Test SSH Connection
To verify that your SSH key is correctly set up, run the following command in AWS CloudShell:

```bash
ssh -T git@github.com
```

You should see a message like:

```bash
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

Now that your SSH key is set up, you can clone your GitHub repository using SSH. Run the following command:

```bash
git clone git@github.com:your-username/MyAIWebApp.git
```


- change into the cloned repo and copy only your webfiles into it and commit to the repo

```bash
git add index.html index.js Dockerfile # adds your web files to staging
git commit -m "Your commit message"  # Commits your changes
```
p.s - you may need to run some commands after you commit, you may see the following error:

*** Please tell me who you are.

Run

  git config --global user.email "you@example.com"
  git config --global user.name "Your Name"

Simply follow the instructions and try to commit again - this should work fine!

```bash
git push --set-upstream origin main # pushes them to the repository
```

### Step 4: Create AWS IAM Role for GitHub Actions

To allow GitHub Actions to interact with AWS, we need to create an IAM role that GitHub Actions can assume with the necessary permissions.

# 1. Create the Trust Policy for GitHub Actions

# 2: Create AWS IAM Role for GitHub Actions

To allow GitHub Actions to interact with AWS, we will create an IAM role. First, we need to create trust and permissions policies.

## 3. Create the Trust Policy for GitHub Actions

We will use `sed` commands to dynamically replace placeholders with the appropriate values.

```bash
# Use sed to replace placeholders with actual values
sed -i "s/{ACCOUNT_ID}/${ACCOUNT_ID}/g" trust-policy-githubactions.json
sed -i "s/{REGION}/${REGION}/g" trust-policy-githubactions.json
sed -i "s/your-username/MyGitHubUsername/g" trust-policy-githubactions.json #add your username instead of MyGitHubUsername
```

Run the following commands to create the IAM user and attach the necessary policy:

```bash
aws iam create-user --user-name GitHubActionsUser
aws iam attach-user-policy --user-name GitHubActionsUser --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

You will then need to create access keys for this user, so as to use them later to authenticate to GitHub.

```bash
aws iam create-access-key --user-name GitHubActionsUser
```

We will now create the GitHub Actions workflow file. Let’s use sed commands to replace placeholders dynamically in the workflow configuration.

# Define variables - run the following commands:
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
REGION=$'us-east-1' 
TASK_DEFINITION_NAME="my-ai-app"
ECR_IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/my-ai-app:latest"
CLUSTER_NAME="my-ecs-cluster"
SERVICE_NAME="my-ai-app-service"

# Now, let's use sed to replace the placeholders in your deploy.yaml file

# Replace the AWS Account ID placeholder in deploy.yaml
sed -i "s/{ACCOUNT_ID}/${ACCOUNT_ID}/g" deploy.yaml

# Replace the AWS Region placeholder
sed -i "s/{REGION}/${REGION}/g" deploy.yaml

# Replace the Task Definition placeholder with your actual Task Definition Name
sed -i "s/my-ai-app-task-def/${TASK_DEFINITION_NAME}/g" deploy.yaml

# Replace the ECR Image URI placeholder
sed -i "s#\${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.\${{ secrets.AWS_REGION }}.amazonaws.com/my-ai-app:latest#${ECR_IMAGE_URI}#g" deploy.yaml

# Replace the ECS Cluster name placeholder
sed -i "s/my-ecs-cluster/${CLUSTER_NAME}/g" deploy.yaml

# Replace the ECS Service name placeholder
sed -i "s/my-ai-app-service/${SERVICE_NAME}/g" deploy.yaml
```

# Ensure that the OpenID Connect (OIDC) provider for GitHub Actions is added to your AWS account. 


1. Go to the AWS IAM console and navigate to Identity Providers.

Create a new OIDC provider with the following details:
Provider URL: https://token.actions.githubusercontent.com
Audience: sts.amazonaws.com


2. Add Secrets to GitHub Repository
Next, ensure that the necessary secrets are configured in your GitHub repository. This allows the workflow to access the required AWS account and region information.

Go to your GitHub repository settings and navigate to Secrets > Actions.

Click New repository secret and add the following secrets:

AWS_ACCESS_KEY_ID: Your AWS Access Key ID.
AWS_SECRET_ACCESS_KEY: Your AWS Secret Access Key.
AWS_REGION: The AWS region you are working in (e.g., us-east-1).

## Final Steps to Create and Test the GitHub Actions Workflow:

1. Create the GitHub Actions Workflow File:
Create a .github/workflows directory in your GitHub repository 

```bash
mkdir -p .github/workflows
```
make sure you move the deploy file to the correct location, in the .github/workflows folder

2. Push your changes to the main branch of your repository: (you can update your <a> tag` on the index.html that it routes back and forth to the homepage hosted behind the domain name as discussed before if you like and this commit will make the changes to your web app, if not feel free to do this separately in a different commit)

```html
<a href="https://UPLOADIMAGEFUNCTIONURL" class="btn btn-primary mt-3 mb-3">Upload New Image</a>
```
Then commmit this to the main branch to start the GitHub actions workflow!

```bash
git add . # run this from the root of the repo
git commit -m "Add GitHub Actions deploy workflow"
git push origin main
```

Go to the "Actions" tab of your GitHub repository to see the workflow running! It should succesfully build a new container image and push it to your repo, which will automatically deploy and new code changes directly on the website! 