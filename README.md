# Study Buddy - AI-Powered Learning Assistant

## Design Decisions

### Architecture

While the original project included a local server implementation, the instructions encouraged creative liberties, so I approached this how I'd typically make a similar LLM app on my own. I got rid of the local server entirely and moved everything to CDK with serverless services.

### AI Agent Implementation

The conversational AI is powered by the Strands SDK running on AWS Lambda with Amazon Bedrock's Claude 3.5 Haiku model. I'm using an S3SessionManager to maintain conversation memory across API calls. The agent uses structured output to return both the response and metadata about which study materials are most relevant to the current discussion.

### Knowledge Base & RAG Implementation

To handle the pdf context, I actually decided to experiment with the new s3 vector buckets in preview for bedrock knowledge bases. These store embeddings directly in S3, eliminating the need for separate vector databases like OpenSearch. Much cheaper than OpenSearch Serverless and no separate database infrastructure to manage.

Since this feature is still in preview, there are no CDK constructs available yet. This is the one part of the infrastructure that I had to be set up manually in the AWS Console. I used it mostly because its so much cheaper than open search or some other vector db (yes I could have ran one locally with the server setup but I just wanted to see how this would work because I hadn't used the vector buckets yet either).

For the PDF content, I used semantic chunking to help preserve context by respecting natural topic boundaries rather than arbitrarily cutting text every N characters. The JSON materials were left unchunked since they're already small and well-structured.

Youll see I pass that Knowledge Base ID into the CDK deployment via context to connect it to everything else in the IaC:

```bash
npx cdk deploy --context knowledgeBaseId=YOUR_KB_ID
```

### MCP Tools Integration

I created a custom MCP tool that allows the agent to query the Bedrock Knowledge Base during conversations. The agent only fetches what's needed for the current question and returns source snippets in its response, which get displayed in the frontend's supplemental materials panel.

### Frontend Enhancements

I reworked the UI just a bit as well. I added react markdown to make the agents chats a little nicer, and I pretty much completely redid the context sidebar. I really wasnt grasping what the intended purpose of it was given the original implementation, so I decided to just sort of make it a "suplemental materials" section. as I said, the agent will tell us which topic is most relevant and the frontend will display it under the study guide section. Then I added a second tab that shows any source snippets from the pdf that that the agent used in its discussion for reference. These should auto update as the discussion goes on.

---

## 🏗️ Project Structure

```
study-buddy/
├── cdk/                          # AWS Infrastructure (CDK)
│   ├── bin/
│   │   └── study-buddy.ts        # CDK app entry point
│   ├── lib/
│   │   └── study-buddy-stack.ts  # Main infrastructure stack
│   ├── lambda/
│   │   ├── agent_handler.py      # Strands agent Lambda function
│   │   ├── materials.json        # Study materials (copied to Lambda)
│   │   └── requirements.txt      # Python dependencies
│   ├── data/
│   │   ├── json/
│   │   │   └── materials.json    # Source study materials
│   │   └── pdf/                  # PDF learning resources
│   └── cdk.json                  # CDK configuration
│
├── src/                          # Frontend (React + TypeScript)
│   ├── components/
│   │   ├── Chat.tsx              # Main chat interface
│   │   ├── Context.tsx           # Supplemental materials panel
│   │   └── StudyMaterials.tsx    # Study guide display
│   ├── services/
│   │   └── api.ts                # API Gateway client
│   ├── types/
│   │   └── chat.ts               # TypeScript interfaces
│   └── main.tsx                  # App entry point
│
├── public/                       # Static assets
├── scripts/                      # Utility scripts
└── package.json                  # Frontend dependencies
```

---

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React)                              │
│                       http://localhost:5173                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTP/REST
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API Gateway (REST)                              │
│                  POST /chat  |  GET /materials                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ Lambda Integration
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Lambda Function (Python 3.12)                       │
│                    Strands Agent + MCP Tools                            │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  1. Load session from S3                                     │     │
│  │  2. Query Knowledge Base (if needed via MCP tool)            │     │
│  │  3. Send prompt to Bedrock                                   │     │
│  │  4. Get structured response + sources                        │     │
│  │  5. Save session to S3                                       │     │
│  └──────────────────────────────────────────────────────────────┘     │
└──────────┬─────────────────────────────┬────────────────────────────────┘
           │                             │
           │                             │
           ▼                             ▼
┌──────────────────────┐      ┌──────────────────────────────────────────┐
│   S3 Bucket          │      │   Amazon Bedrock                         │
│                      │      │                                          │
│  Session Storage     │      │  ┌────────────────────────────────────┐  │
│  (Conversation       │      │  │  Claude 3.5 Haiku                  │  │
│   History)           │      │  │  (LLM)                             │  │
│                      │      │  └────────────────────────────────────┘  │
└──────────────────────┘      │                                          │
                              │  ┌────────────────────────────────────┐  │
                              │  │  Knowledge Base                    │  │
                              │  │  (S3 Vector Buckets - Preview)     │  │
                              │  │  - PDF embeddings                  │  │
                              │  │  - Semantic chunking               │  │
                              │  └────────────────────────────────────┘  │
                              └──────────────────────────────────────────┘
```

API Gateway (REST API) with CORS configured for localhost development, proxying to a Lambda function running the Strands agent (Python 3.12, 512MB memory, 30s timeout). The deployment package includes `materials.json` for direct access.

Storage is handled through an S3 bucket for conversation history (session management) and the Bedrock Knowledge Base for vector storage of the PDFs (manually created).

Using Amazon Bedrock for Claude 3.5 Haiku model access, Strands Agents framework for conversation orchestration, and custom MCP tools for querying the knowledge base.

### API Endpoints

```
POST /chat
  Body: { message: string, sessionId: string }
  Returns: {
    response: string,
    sources: Array<{content: string, metadata: object}>,
    relevantTopic: string
  }

GET /materials
  Returns: Complete materials.json structure
```

### Data Flow

User sends message via React frontend → API Gateway routes to Lambda → Strands agent loads conversation history from S3 → queries Bedrock Knowledge Base if needed (via MCP tool) → sends prompt to Claude 3.5 Haiku → returns structured response with sources and topic metadata → saves updated conversation to S3 → frontend updates chat and supplemental materials panel.

---

## 📦 Key Dependencies

### Frontend

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **axios** - HTTP client
- **react-markdown** - Markdown rendering in chat

### Backend (CDK)

- **aws-cdk-lib** - Infrastructure as code
- **AWS Lambda** - Serverless compute
- **API Gateway** - REST API management

### Backend (Lambda)

- **strands-agents** - AI agent orchestration
- **boto3** - AWS SDK for Python
- **amazon-bedrock-mcp-server** - MCP tools for Bedrock

### Running the Application

The backend infrastructure is already deployed and ready to use. To get started:

```bash
# Install dependencies
pnpm install

# Start the frontend development server
pnpm dev
```

The frontend will start on `http://localhost:5173` and automatically connect to the deployed production backend.

## 🚢 Deploying Your Own Stack

The production backend is already live, but if you'd like to deploy your own instance:

First, create the Knowledge Base manually (S3 Vector Buckets are still in preview and it had to be done manually as I said above). Head to Amazon Bedrock > Knowledge Bases in the AWS Console, create a new Knowledge Base with S3 Vector Bucket storage, upload the PDFs from `cdk/data/`, configure semantic chunking, and note the Knowledge Base ID.

Then deploy the CDK stack:

```bash
cd cdk
pnpm install
npx cdk bootstrap  # First time only
npx cdk deploy --context knowledgeBaseId=YOUR_KB_ID
```

Finally, update `src/services/api.ts` with your new API Gateway endpoint.

---

## 🧪 Testing

You can test the API directly:

```bash
curl -X POST https://your-api-url.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is photosynthesis?", "sessionId": "test-123"}' | jq
```

## Future Work

If I had more time the first things that come to mind are:

- Locking down the API (trusting yall not to DDOS my AWS bill too much with requests) and tying session access to their rightful owners.
- More fine-tuning of the system prompt. I added a lot to take care of most cases and shape responses fairly well, but I don't love it. I think it needs more dynamic transitions between the user just asking for information and challenging their knowledge.
- Write all the tests
- Right size the lambda
- Logging and metrics around the agent. Tracking how often the actions are used, errors, average cost/token use, etc.
- More error handling in general. I was skimpy with this admittedly. Was already running a little over time due to some difficulties with the UI rework and really only got some basic stuff for if the agent fails, and making sure stuff like the study guide subject validation works.
- Continue sessions across refreshes. This would have been pretty simple for this little prototype. I probably would have just saved the session id to a cookie and reloaded on page load. Then the user could have picked up where they left off (are start a new session with some new 'new chat' button).
