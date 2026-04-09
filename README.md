# AI Image Processing Platform on AWS  
### ECS • Lambda • S3 • DynamoDB • ALB • Route 53

## Overview

This project demonstrates a **production-style cloud-native application** built on AWS that processes and serves images using a hybrid architecture combining:

- **Containers (ECS Fargate)**
- **Serverless (AWS Lambda)**
- **Storage (S3 + DynamoDB)**
- **Networking (VPC + ALB + Route 53)**

The platform allows users to upload images, process them, store metadata, and retrieve results through a scalable and secure infrastructure.

## Architecture

User → Route53 → CloudFront → ALB → ECS (Frontend)
↓
Lambda Microservices
↓
S3 + DynamoDB

### Flow:


## Tech Stack

- **Compute:** AWS ECS Fargate, AWS Lambda  
- **Networking:** VPC, ALB, Route 53  
- **Storage:** Amazon S3, DynamoDB  
- **Containerization:** Docker, ECR  
- **Security:** IAM, Security Groups, WAF  
- **Monitoring:** CloudWatch  
- **CI/CD:** GitHub + GitHub Actions (OIDC ready)

## Features

- Upload images via web interface  
- Process images using Lambda (Pillow)  
- Store images in S3  
- Store metadata in DynamoDB  
- Fetch and display processed images  
- Scalable ECS-based frontend  
- Secure architecture with private subnets  
- Custom domain via Route 53  

## Infrastructure Design

- Multi-AZ **VPC architecture**
- **Public subnets** → ALB  
- **Private subnets** → ECS tasks  
- NAT Gateway for outbound access  
- Lambda microservices for async processing  
- Fully decoupled architecture  

## Security

- ECS tasks run in **private subnets**
- ALB is the only public entry point  
- Security groups restrict traffic (ALB → ECS only)  
- IAM roles per service (least privilege)  
- No hardcoded credentials  
- WAF ready for protection  

## Deployment (AWS CLI)

```bash
cd aws-cli-deployment

./01-network.sh
./02-security.sh
./03-alb.sh
./04-ecr.sh
./05-ecs.sh
./06-route53.sh

### Challenges & Solutions
## ECS Image Architecture Issue

Error:

image Manifest does not contain descriptor matching platform 'linux/amd64'

Fix:

docker buildx build --platform linux/amd64 --push ...

## Route 53 DNS Not Resolving

Problem:
Hosted zone mismatch

Fix:

Updated domain registrar nameservers to match Route 53 hosted zone

## ECS Service Not Stabilizing

Fix:

Verified ALB target group health checks

Ensured container port mapping matched ALB listener

#### Production Improvements

HTTPS with ACM

Auto Scaling (ECS Service)

Secrets Manager integration

CloudFront CDN

WAF protection

CI/CD pipeline

### What I Learned

Deep understanding of AWS networking (VPC, subnets, NAT)

ECS + ALB integration in production environments

Debugging real-world cloud issues (DNS, containers, IAM)

Infrastructure design for scalability and security

Difference between serverless and container workloads
