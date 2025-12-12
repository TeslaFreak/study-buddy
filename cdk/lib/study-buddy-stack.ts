import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
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

    // ========================================
    // Build Checker Lambda (GitHub MCP Agent)
    // ========================================

    // SQS Queue for repository analysis requests
    const buildCheckQueue = new sqs.Queue(this, 'BuildCheckQueue', {
      queueName: 'build-check-queue',
      visibilityTimeout: Duration.seconds(360), // 6 minutes (Lambda timeout + buffer)
      retentionPeriod: Duration.days(14),
      deadLetterQueue: {
        queue: new sqs.Queue(this, 'BuildCheckDLQ', {
          queueName: 'build-check-dlq',
          retentionPeriod: Duration.days(14),
        }),
        maxReceiveCount: 3, // Retry 3 times before moving to DLQ
      },
    });

    // DynamoDB table for storing analysis results
    const resultsTable = new dynamodb.Table(this, 'BuildCheckResults', {
      tableName: 'build-check-results',
      partitionKey: { name: 'repository', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'ttl',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
    });

    // Add GSI for querying by hasBuildProcess (stored as string "true"/"false")
    resultsTable.addGlobalSecondaryIndex({
      indexName: 'BuildProcessIndex',
      partitionKey: { name: 'hasBuildProcess', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // IAM role for Build Checker Lambda
    const buildCheckerRole = new iam.Role(this, 'BuildCheckerLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Execution role for Build Process Security Checker',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Bedrock permissions for the agent
    buildCheckerRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream',
      ],
      resources: ['*'],
    }));

    // DynamoDB permissions
    buildCheckerRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'dynamodb:PutItem',
        'dynamodb:GetItem',
        'dynamodb:Query',
      ],
      resources: [
        resultsTable.tableArn,
        `${resultsTable.tableArn}/index/*`,
      ],
    }));

    // Build Checker Lambda with GitHub MCP integration
    const buildCheckerHandler = new lambda.Function(this, 'BuildCheckerHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'build_checker_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda'), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            [
              // Install Python dependencies
              'pip install -r requirements.txt -t /asset-output',
              // Install Node.js and npm (needed for GitHub MCP server)
              'curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -',
              'yum install -y nodejs',
              // Copy Lambda code
              'cp -r . /asset-output',
            ].join(' && ')
          ],
        },
      }),
      role: buildCheckerRole,
      timeout: Duration.seconds(300), // 5 minutes for GitHub API calls and analysis
      memorySize: 1024, // More memory for MCP server operations
      architecture: lambda.Architecture.ARM_64,
      reservedConcurrentExecutions: 5, // Limit concurrent executions to respect GitHub API rate limits
      environment: {
        GITHUB_TOKEN: scope.node.tryGetContext('githubToken') || '',
        RESULTS_TABLE: resultsTable.tableName,
      },
    });

    // Add SQS event source with batch size of 1 for sequential processing
    buildCheckerHandler.addEventSource(new lambdaEventSources.SqsEventSource(buildCheckQueue, {
      batchSize: 1, // Process one repository at a time to stay within rate limits
      reportBatchItemFailures: true, // Enable partial batch responses
    }));

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

    new cdk.CfnOutput(this, 'BuildCheckerLambdaName', { 
      value: buildCheckerHandler.functionName, 
      description: 'Build Checker Lambda function name' 
    });

    new cdk.CfnOutput(this, 'BuildCheckQueueUrl', { 
      value: buildCheckQueue.queueUrl, 
      description: 'SQS Queue URL for build check requests' 
    });

    new cdk.CfnOutput(this, 'BuildCheckQueueName', { 
      value: buildCheckQueue.queueName, 
      description: 'SQS Queue name for build check requests' 
    });

    new cdk.CfnOutput(this, 'ResultsTableName', { 
      value: resultsTable.tableName, 
      description: 'DynamoDB table for build check results' 
    });
  }
}

export default StudyBuddyStack;
