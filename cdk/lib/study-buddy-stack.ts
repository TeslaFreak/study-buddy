import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import * as path from 'path';

export interface StudyBuddyStackProps extends cdk.StackProps {}

export class StudyBuddyStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: StudyBuddyStackProps) {
    super(scope, id, props);

    // S3 bucket for session storage
    const sessionBucket = new s3.Bucket(this, 'SessionStorageBucket', {
      bucketName: this.node.tryGetContext('sessionBucketName') || undefined,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      lifecycleRules: [
        {
          expiration: Duration.days(30),
        },
      ],
    });

    // IAM role for Lambda
    const lambdaRole = new iam.Role(this, 'ChatLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Execution role for Study Buddy chat handler',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // S3 access for sessions
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:GetBucketLocation',
      ],
      resources: [
        sessionBucket.bucketArn,
        `${sessionBucket.bucketArn}/*`,
      ],
    }));

    // Bedrock permissions for Knowledge Base retrieval and model invocation
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
        'bedrock:Retrieve',
      ],
      resources: ['*'],
    }));

    // Lambda function with Strands Agent handler
    const chatHandler = new lambda.Function(this, 'ChatHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'agent_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -r . /asset-output'
          ],
        },
      }),
      role: lambdaRole,
      timeout: Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        SESSION_BUCKET: sessionBucket.bucketName,
        KNOWLEDGE_BASE_ID: scope.node.tryGetContext('knowledgeBaseId') || '',
      },
    });

    // Grant Lambda access to buckets
    sessionBucket.grantReadWrite(chatHandler);

    // API Gateway REST API
    const api = new apigw.LambdaRestApi(this, 'StudyBuddyApi', {
      handler: chatHandler,
      proxy: false,
      restApiName: 'StudyBuddyService',
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: apigw.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });

    // Chat endpoint
    const chat = api.root.addResource('chat');
    chat.addMethod('POST');

    // Materials endpoint - returns full materials.json
    const materials = api.root.addResource('materials');
    materials.addMethod('GET');

    // Health check endpoint
    const health = api.root.addResource('health');
    health.addMethod('GET', new apigw.MockIntegration({
      integrationResponses: [{ statusCode: '200' }],
      passthroughBehavior: apigw.PassthroughBehavior.NEVER,
      requestTemplates: { 'application/json': '{ "statusCode": 200 }' }
    }), { methodResponses: [{ statusCode: '200' }] });

    // Stack outputs
    new cdk.CfnOutput(this, 'SessionBucketName', { 
      value: sessionBucket.bucketName, 
      description: 'S3 bucket for conversation sessions' 
    });
    
    new cdk.CfnOutput(this, 'ApiUrl', { 
      value: api.url, 
      description: 'API Gateway endpoint' 
    });
    
    new cdk.CfnOutput(this, 'ChatLambdaName', { 
      value: chatHandler.functionName, 
      description: 'Lambda function name' 
    });
  }
}

export default StudyBuddyStack;
