# CloudPilot — Implementation Plan
> Multi-Cloud Infrastructure Automation via Intent-Driven Deployment

---

## 🧠 What We're Building (Read This Every Session)

**CloudPilot** is a tool where a user describes what they want to deploy in plain English,
and the system figures out the infrastructure, asks a few clarifying questions, and deploys it
automatically to their chosen cloud provider.

### The Core Flow
```
User: "I want to deploy a website for 200 people"
         ↓
[Intent Parser]  →  extracts: { use_case, scale, cloud }
         ↓
[Knowledge Base] →  maps intent to a template name
         ↓
[Conversation]   →  asks only what's missing (cloud? region?)
         ↓
[Template Engine]→  fills Terraform variables
         ↓
[Cloud Adapter]  →  runs terraform apply on the right provider
         ↓
User gets: live URL + resource summary
```

### Design Rules (Never Break These)
1. **LLM is called ONCE max** — only to extract intent from ambiguous input. Everything else is deterministic.
2. **AI never writes Terraform** — templates are pre-written, AI only selects and parameterizes them.
3. **Adding a new cloud = add one folder** — provider abstraction must be strict.
4. **Conversation is a state machine** — not a chat loop. Fixed questions, fixed states.
5. **Terraform state is per-user, per-deployment** — never shared.

### Tech Stack
| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| IaC Engine | Terraform (subprocess calls) |
| Knowledge Base | YAML files |
| Intent Parsing | Rule engine + Claude API fallback |
| Job Queue | Celery + Redis |
| State Storage | S3 backend (or local for dev) |
| Frontend | Streamlit (MVP) |
| Clouds Supported | AWS, GCP, DigitalOcean |

### Folder Structure (Target)
```
cloudpilot/
├── main.py                  # FastAPI entry point
├── intent/
│   ├── parser.py            # Rule-based + LLM fallback
│   ├── rules.yaml           # Keyword → intent mappings
│   └── schema.py            # IntentObject dataclass
├── knowledge_base/
│   ├── catalog.yaml         # use_case → tier → template mapping
│   └── loader.py
├── conversation/
│   ├── state_machine.py     # States: ASK_USECASE, ASK_SCALE, ASK_CLOUD, CONFIRM, DEPLOY
│   └── questions.yaml       # Per-state prompts and options
├── templates/
│   ├── aws/
│   │   ├── static_website/  # main.tf, variables.tf, outputs.tf
│   │   ├── containerized_app/
│   │   └── database/
│   ├── gcp/
│   │   ├── static_website/
│   │   ├── containerized_app/
│   │   └── database/
│   └── digitalocean/
│       └── static_website/
├── engine/
│   ├── template_selector.py # intent → template path
│   ├── variable_injector.py # fills .tfvars from intent
│   └── terraform_runner.py  # subprocess wrapper for tf init/plan/apply
├── adapters/
│   ├── base.py              # Abstract CloudAdapter
│   ├── aws_adapter.py
│   ├── gcp_adapter.py
│   └── do_adapter.py
├── jobs/
│   ├── worker.py            # Celery worker
│   └── tasks.py             # deploy_task, destroy_task
├── ui/
│   └── app.py               # Streamlit UI
└── tests/
    ├── test_intent.py
    ├── test_selector.py
    └── test_terraform.py
```

---

## Phase 0 — Project Scaffold
**Goal:** Empty but wired project. Copilot has full context from day 1.

### Tasks
- [ ] Init git repo, create folder structure above (empty files ok)
- [ ] `pip install fastapi uvicorn pyyaml python-dotenv anthropic celery redis`
- [ ] Write `schema.py` — the `IntentObject` dataclass (most important shared type):
```python
@dataclass
class IntentObject:
    use_case: str           # "static_website" | "containerized_app" | "database"
    traffic_tier: str       # "low" | "medium" | "high"
    cloud: str              # "aws" | "gcp" | "digitalocean"
    region: str
    project_name: str
    raw_input: str          # original user message
    confidence: float       # 0.0–1.0, below 0.7 triggers LLM fallback
```
- [ ] Write `catalog.yaml` skeleton (3 use cases × 3 clouds × 3 tiers = 27 entries)
- [ ] Write `questions.yaml` (per-state question text + answer options)
- [ ] Create `.env.example` with all required env vars
- [ ] Write `README.md` with project overview and run instructions

**Copilot Prompt to use:**
> "I'm building CloudPilot, a multi-cloud infrastructure automation tool. The IntentObject dataclass in schema.py is the central data structure passed between all modules. Help me scaffold [module name] that receives an IntentObject and..."

---

## Phase 1 — Terraform Templates
**Goal:** Working, manually-tested Terraform modules for 3 use cases on AWS.

### Use Cases to Build
1. **static_website** — S3 + CloudFront (low), EC2 + ALB (medium)
2. **containerized_app** — ECS Fargate (low/medium), EKS (high)
3. **database** — RDS MySQL t3.micro (low), RDS Multi-AZ (medium)

### Per Template Structure
```
templates/aws/static_website/
├── main.tf          # resources
├── variables.tf     # all inputs as variables (no hardcoding)
├── outputs.tf       # url, resource IDs
└── meta.yaml        # human-readable description, required vars list
```

### Tasks
- [ ] Write `templates/aws/static_website/` — S3 + CloudFront
- [ ] Write `templates/aws/containerized_app/` — ECS Fargate
- [ ] Write `templates/aws/database/` — RDS MySQL
- [ ] Manually `terraform init && terraform apply` each to verify they work
- [ ] Write `meta.yaml` for each template
- [ ] Add `templates/gcp/` equivalents: GCS+CDN, Cloud Run, Cloud SQL
- [ ] Add `templates/digitalocean/static_website/` — App Platform (1 resource, dead simple)

### Rules for Writing Templates
- Every input must be a variable — no hardcoded values
- Every template must have an `outputs.tf` with at minimum: `endpoint_url`, `resource_id`
- Variable names must be identical across clouds where possible (e.g. `var.project_name`, `var.region`)

**Copilot Prompt to use:**
> "Write a Terraform module for [use case] on [cloud]. It must use only variables defined in variables.tf, no hardcoded values. Output must include endpoint_url and resource_id. Keep it minimal and production-safe."

---

## Phase 2 — Knowledge Base + Template Selector
**Goal:** Given an IntentObject, the system picks the right template path.

### `catalog.yaml` Format
```yaml
static_website:
  low:                        # < 1000 users
    aws: aws/static_website
    gcp: gcp/static_website
    digitalocean: digitalocean/static_website
  medium:                     # 1k–50k users
    aws: aws/static_website_ec2
    gcp: gcp/cloud_run
  high:                       # 50k+ users
    aws: aws/static_website_ec2_ha
    gcp: gcp/cloud_run_ha

containerized_app:
  low:
    aws: aws/containerized_app
    gcp: gcp/containerized_app
  ...
```

### Traffic Tier Thresholds
```yaml
thresholds:
  low:    max_users: 1000
  medium: max_users: 50000
  high:   max_users: 999999999
```

### Tasks
- [ ] Write full `catalog.yaml`
- [ ] Write `knowledge_base/loader.py` — loads and validates catalog on startup
- [ ] Write `engine/template_selector.py`:
  - Input: `IntentObject`
  - Output: `str` (template path) or raises `TemplateNotFoundError`
  - Logic: `catalog[use_case][traffic_tier][cloud]`
- [ ] Write `engine/variable_injector.py`:
  - Input: template path + IntentObject
  - Output: writes a `terraform.tfvars` file in a temp workspace directory
- [ ] Unit tests for both in `tests/`

**Copilot Prompt to use:**
> "In template_selector.py, write a function select_template(intent: IntentObject) -> str that loads catalog.yaml and returns the template folder path. Raise TemplateNotFoundError with a helpful message if no match. The catalog structure is [paste catalog.yaml snippet]."

---

## Phase 3 — Conversation State Machine
**Goal:** A clean multi-turn conversation that only asks what's missing.

### States
```
INIT → ASK_USECASE → ASK_SCALE → ASK_CLOUD → ASK_REGION → CONFIRM → DEPLOYING → DONE
                                                              ↑
                                                    (if intent already has it, skip)
```

### Skip Logic
If the user's initial input already contains the info for a state, skip it.

Example: "deploy a static website on AWS for 500 users"
→ skip ASK_USECASE (static_website), skip ASK_SCALE (low), skip ASK_CLOUD (aws)
→ only ask ASK_REGION → CONFIRM

### `questions.yaml` Format
```yaml
ASK_USECASE:
  prompt: "What are you deploying?"
  options:
    - label: "Static Website"
      value: "static_website"
    - label: "Containerized App (Docker)"
      value: "containerized_app"
    - label: "Database"
      value: "database"

ASK_SCALE:
  prompt: "How many users do you expect?"
  options:
    - label: "Up to 1,000"
      value: "low"
    - label: "1,000 – 50,000"
      value: "medium"
    - label: "50,000+"
      value: "high"

ASK_CLOUD:
  prompt: "Which cloud provider?"
  options:
    - label: "AWS"
      value: "aws"
    - label: "GCP"
      value: "gcp"
    - label: "DigitalOcean"
      value: "digitalocean"
```

### Tasks
- [ ] Write `conversation/state_machine.py` — `ConversationSession` class with:
  - `session_id`, `current_state`, `intent` (partial IntentObject)
  - `next_question()` → returns question + options or None if ready
  - `answer(value)` → updates intent, advances state
  - `is_ready()` → True when all required fields are filled
- [ ] Write CLI runner in `main_cli.py` to test the full flow end-to-end
- [ ] Make sure skip logic works — pre-fill intent fields from Phase 4's parser output

**Copilot Prompt to use:**
> "Write a ConversationSession class in state_machine.py. It manages a state machine with these states: [list]. It holds a partial IntentObject and fills it field by field. next_question() returns the next unanswered question from questions.yaml. answer(value) updates the intent and moves to the next state. Skip states where the intent field is already populated."

---

## Phase 4 — Intent Parser
**Goal:** Convert free-text user input to a partial IntentObject.

### Rule Engine First (No LLM)
```python
RULES = {
    "use_case": {
        "static_website": ["website", "web app", "frontend", "react", "next", "html"],
        "containerized_app": ["docker", "container", "api", "backend", "microservice"],
        "database": ["database", "db", "mysql", "postgres", "storage"],
    },
    "traffic_tier": {
        "low":    ["small", "personal", "startup", r"\b\d{1,3}\s*(users|people)\b"],
        "medium": [r"\b[1-9]\d{3,4}\s*(users|people)\b"],
        "high":   ["enterprise", "large scale", r"\b[1-9]\d{5,}\b"],
    },
    "cloud": {
        "aws":          ["aws", "amazon", "s3", "ec2", "lambda"],
        "gcp":          ["gcp", "google", "cloud run", "gke"],
        "digitalocean": ["digitalocean", "do", "droplet"],
    }
}
```

### LLM Fallback (only if confidence < 0.7)
```python
FALLBACK_PROMPT = """
Extract deployment intent from this message. Return ONLY valid JSON.
Message: "{user_input}"

Return:
{
  "use_case": "static_website|containerized_app|database|unknown",
  "traffic_tier": "low|medium|high|unknown",
  "cloud": "aws|gcp|digitalocean|unknown",
  "confidence": 0.0-1.0
}
"""
```

### Tasks
- [ ] Write `intent/parser.py` with `parse(text: str) -> IntentObject`
- [ ] Implement rule engine with regex support
- [ ] Calculate confidence score based on how many fields matched rules
- [ ] Add Claude API fallback call for low-confidence inputs
- [ ] Write `tests/test_intent.py` with 15+ test cases covering edge cases

**Copilot Prompt to use:**
> "In intent/parser.py, write a parse(text) function that uses the RULES dict to extract use_case, traffic_tier, and cloud from user input using keyword matching and regex. Return an IntentObject with a confidence score. If confidence < 0.7, call the LLM fallback in _llm_fallback(text)."

---

## Phase 5 — Terraform Runner + Cloud Adapters
**Goal:** Actually run Terraform and get back a URL.

### `terraform_runner.py`
```python
def run_deployment(template_path, tfvars, workspace_dir, cloud_credentials):
    # 1. Copy template to workspace_dir
    # 2. Write terraform.tfvars
    # 3. Write provider credentials (env vars, not files)
    # 4. Run: terraform init
    # 5. Run: terraform plan → capture output
    # 6. Run: terraform apply -auto-approve
    # 7. Run: terraform output -json → return as dict
```

### Workspace Per Deployment
```
/tmp/cloudpilot/
  {session_id}/
    main.tf
    variables.tf
    outputs.tf
    terraform.tfvars      ← generated
    .terraform/           ← after init
    terraform.tfstate     ← after apply
```

### Cloud Adapter Pattern
```python
# adapters/base.py
class CloudAdapter(ABC):
    @abstractmethod
    def get_env_vars(self, credentials: dict) -> dict:
        """Return env vars to inject for this provider's Terraform auth."""

# adapters/aws_adapter.py
class AWSAdapter(CloudAdapter):
    def get_env_vars(self, credentials):
        return {
            "AWS_ACCESS_KEY_ID": credentials["access_key"],
            "AWS_SECRET_ACCESS_KEY": credentials["secret_key"],
            "AWS_DEFAULT_REGION": credentials["region"],
        }
```

### Tasks
- [ ] Write `engine/terraform_runner.py` with init/plan/apply/output/destroy functions
- [ ] Write all 3 adapters (AWS, GCP, DO)
- [ ] Add `ADAPTER_REGISTRY` dict: `{ "aws": AWSAdapter, "gcp": GCPAdapter, ... }`
- [ ] Handle subprocess errors — capture stderr, surface clean error messages
- [ ] Write `tests/test_terraform.py` — mock subprocess calls, test error handling

**Copilot Prompt to use:**
> "Write terraform_runner.py. It receives a workspace directory path and runs terraform init, plan, apply as subprocesses. Capture stdout/stderr. On failure, raise TerraformError with the stderr output. On success, run terraform output -json and return the parsed dict."

---

## Phase 6 — Async Job Queue
**Goal:** Deploy runs in background, user polls for status.

### Why Needed
Terraform deploys take 2–10 minutes. Can't block an HTTP request.

### Job Flow
```
POST /deploy → creates job_id → returns immediately
GET  /status/{job_id} → returns { status, logs, output_url }
```

### Tasks
- [ ] Set up Redis locally (`docker run -d -p 6379:6379 redis`)
- [ ] Write `jobs/tasks.py` — `deploy_task` and `destroy_task` as Celery tasks
- [ ] Write `jobs/worker.py` — Celery app config
- [ ] Add `/deploy` POST endpoint to FastAPI
- [ ] Add `/status/{job_id}` GET endpoint
- [ ] Store job logs in Redis with TTL of 24h

**Copilot Prompt to use:**
> "Write a Celery task deploy_task(session_id, intent_dict, credentials_dict) in tasks.py. It calls terraform_runner with the right parameters, updates job status in Redis at each step (PENDING → RUNNING → SUCCESS/FAILED), and stores the final output URL. Use the ADAPTER_REGISTRY to get the right cloud adapter."

---

## Phase 7 — FastAPI Backend (Wire Everything)
**Goal:** Full REST API connecting all modules.

### Endpoints
```
POST /session/start          → { session_id, first_question }
POST /session/{id}/answer    → { next_question | null, ready: bool }
POST /session/{id}/deploy    → { job_id }
GET  /job/{job_id}/status    → { status, logs[], output_url }
POST /session/{id}/destroy   → { job_id }
GET  /health                 → { status: "ok" }
```

### Tasks
- [ ] Wire all endpoints in `main.py`
- [ ] Add session storage (Redis or in-memory dict for MVP)
- [ ] Add credential input to `/session/start` payload
- [ ] Add request validation with Pydantic models
- [ ] Add basic error handling middleware

---

## Phase 8 — Streamlit UI
**Goal:** Simple web interface for the conversation flow.

### Screens
1. **Home** — text input: "Describe what you want to deploy"
2. **Conversation** — one question at a time with button options
3. **Confirm** — show terraform plan summary before deploying
4. **Deploying** — progress bar + live log stream
5. **Done** — show endpoint URL + resource summary + destroy button

### Tasks
- [ ] Build `ui/app.py` using `st.session_state` for conversation state
- [ ] Poll `/job/{job_id}/status` every 3 seconds during deploy
- [ ] Show logs in a `st.code` block that updates live
- [ ] Add "Deploy Another" and "Destroy" buttons on done screen

---

## Adding a New Cloud Provider (Reference)
This is the whole point of the extensible architecture. Steps:

1. Add templates folder: `templates/{provider}/`
2. Write `adapters/{provider}_adapter.py` extending `CloudAdapter`
3. Register in `ADAPTER_REGISTRY`
4. Add entries to `catalog.yaml`
5. Add option to `questions.yaml` under `ASK_CLOUD`

That's it. No other files change.

---

## Dev Environment Setup
```bash
# Clone and setup
git clone <repo>
cd cloudpilot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Infrastructure
docker run -d -p 6379:6379 redis   # Redis for Celery

# Env vars
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, AWS_ACCESS_KEY_ID, etc.

# Run
uvicorn main:app --reload           # API
celery -A jobs.worker worker        # Background jobs
streamlit run ui/app.py             # UI
```

---

## Copilot Usage Tips

- **Always paste the IntentObject schema** when working on any module — it's the shared contract
- **Start prompts with:** "In [filename], given an IntentObject that looks like [example]..."
- **For Terraform:** Tell Copilot the provider, use case, and that all inputs must be variables
- **For tests:** Tell Copilot the exact function signature and give 2–3 example inputs/outputs
- **When stuck:** Paste the relevant YAML file (catalog, questions, rules) directly into the prompt

---

*Project: CloudPilot | Stack: Python + FastAPI + Terraform + Celery | Clouds: AWS, GCP, DigitalOcean*
