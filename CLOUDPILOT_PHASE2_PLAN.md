# CloudPilot — Phase 2: Bring Your Own Site
> Small business owners upload their website files and deploy to AWS via plain-English prompts.

---

## Context (Read Every Session)

**What CloudPilot does:** User describes what they want → conversational intent extraction → 
Terraform template selected → infrastructure deployed automatically.

**What Phase 1 built:**
- Multi-turn chat conversation (backend/session.py)
- Intent parser with GPT-4o-mini fallback (backend/intent.py)
- Terraform runner streaming live output (backend/runner.py)
- AWS S3 + CloudFront static website template (templates/aws/static_website/)
- FastAPI backend + SSE streaming (backend/main.py)
- Chat UI with terminal log panel (frontend/index.html)

**What Phase 2 adds:**
- File upload (zip or individual files) after conversation completes
- Validate uploaded files (index.html must exist)
- Show file summary before deploy
- Deploy USER'S files instead of starter template
- New conversation state: ASK_UPLOAD

**Design Rules (Never Break):**
1. LLM called once max — only for intent fallback
2. AI never writes Terraform — templates are pre-written
3. Upload folder path is /tmp/cloudpilot/{session_id}/site/
4. Runner always deploys whatever is in the site/ folder — no hardcoding
5. index.html is required — validate before allowing deploy

---

## Folder Structure Changes

```
cloudpilot/
├── backend/
│   ├── main.py          ← ADD upload endpoint, update deploy flow
│   ├── session.py       ← ADD ASK_UPLOAD state
│   ├── runner.py        ← UPDATE to use uploaded files from site/ folder
│   └── uploader.py      ← NEW — handles zip extraction + validation
├── templates/
│   └── aws/
│       └── static_website/
│           └── main.tf  ← UPDATE to upload all files in site/ folder
└── frontend/
    └── index.html       ← ADD drag-and-drop upload zone + file summary
```

---

## Block 1 — Update Terraform Template

**Goal:** Template uploads ALL files in site/ folder, not just index.html.

**Copilot Prompt:**
```
Update templates/aws/static_website/main.tf.

Current issue: it only uploads site/index.html using a single aws_s3_object resource.

Fix: Use the fileset() function to upload ALL files in the site/ directory recursively.
Replace the single aws_s3_object with:

resource "aws_s3_object" "site_files" {
  for_each = fileset("${path.module}/site", "**/*")
  
  bucket       = aws_s3_bucket.site.id
  key          = each.value
  source       = "${path.module}/site/${each.value}"
  content_type = lookup(local.mime_types, split(".", each.value)[length(split(".", each.value)) - 1], "application/octet-stream")
  etag         = filemd5("${path.module}/site/${each.value}")
}

Add a locals block with mime_types map covering:
html, css, js, json, png, jpg, jpeg, gif, svg, ico, woff, woff2, ttf, pdf

Keep all other resources unchanged (S3 bucket, CloudFront, OAC).
Keep outputs: cloudfront_url, bucket_name.
```

---

## Block 2 — uploader.py (New File)

**Goal:** Accept uploaded files, extract if zip, validate, return file summary.

**Copilot Prompt:**
```
Create backend/uploader.py.

It handles file uploads for a deployment session.

UPLOAD_BASE = "/tmp/cloudpilot"

Functions:

1. get_site_dir(session_id: str) -> Path
   Returns Path(UPLOAD_BASE) / session_id / "site"
   Creates the directory if it doesn't exist

2. async save_upload(session_id: str, file: UploadFile) -> dict
   - Get site_dir from get_site_dir()
   - If file.filename ends with .zip:
       Save to /tmp/cloudpilot/{session_id}/upload.zip
       Extract all contents into site_dir using zipfile module
       Skip __MACOSX and .DS_Store files
       If zip has a single top-level folder, flatten it 
       (so site/subfolder/index.html becomes site/index.html)
   - If not zip: save directly into site_dir with original filename
   - Call validate_site(site_dir)
   - Return result of validate_site()

3. validate_site(site_dir: Path) -> dict
   - Check if index.html exists in site_dir (not in subdirectory)
   - List all files recursively
   - Categorize: html_files, css_files, js_files, image_files, other_files
   - Return:
     {
       valid: bool,
       error: str | None,       # "index.html not found" if invalid
       files: list[str],        # all file paths relative to site_dir
       summary: {
         html: int,
         css: int, 
         js: int,
         images: int,
         other: int,
         total_size_kb: float
       }
     }

4. get_site_dir_for_runner(session_id: str) -> str
   Returns string path of site_dir for use in terraform runner
   Raises FileNotFoundError if site_dir doesn't exist or has no index.html
```

---

## Block 3 — Update session.py

**Goal:** Add ASK_UPLOAD state and upload_provided flag.

**Copilot Prompt:**
```
Update backend/session.py.

Add to ConversationSession:
- upload_choice: str | None   ("upload" or "starter")
- upload_validated: bool = False
- upload_summary: dict | None = None

Add new state ASK_UPLOAD that appears AFTER all intent fields are filled 
(after ASK_PROJECT_NAME), BEFORE the session is marked done=True.

ASK_UPLOAD question:
  reply: "Do you have website files ready to upload?"
  options: [
    { label: "Upload my files", value: "upload" },
    { label: "Use a starter template", value: "starter" }
  ]

Update process_message() and to_deploy_params():
- If upload_choice == "upload" and upload_validated == False:
    done = False, waiting_for_upload = True
    (frontend shows upload zone, not chat input)
- If upload_choice == "upload" and upload_validated == True:
    done = True (proceed to confirm card)
- If upload_choice == "starter":
    done = True (use existing starter template behavior)

Add method confirm_upload(summary: dict):
  Sets upload_validated = True, upload_summary = summary

Add to_deploy_params(): include upload_choice in returned dict
```

---

## Block 4 — Update runner.py

**Goal:** Use uploaded site/ folder instead of hardcoded index.html.

**Copilot Prompt:**
```
Update backend/runner.py.

In run_deploy(), after copying template folder to workspace:

Current behavior: creates site/index.html with hardcoded HTML content

New behavior:
- Check deploy_params for upload_choice
- If upload_choice == "upload":
    Use uploader.get_site_dir_for_runner(session_id) to get uploaded files path
    Copy entire uploaded site/ directory into workspace/site/
    Yield log line: f"📁 Using uploaded files ({file_count} files found)"
- If upload_choice == "starter" or None:
    Keep existing behavior — create site/index.html with branded CloudPilot HTML

Everything else in runner.py stays the same.
Import uploader at top: from uploader import get_site_dir_for_runner
```

---

## Block 5 — Update main.py

**Goal:** Add upload endpoint, wire upload flow into session.

**Copilot Prompt:**
```
Update backend/main.py.

Add new endpoint:

POST /session/{session_id}/upload
  - Accepts multipart/form-data with field "file" (UploadFile)
  - Calls uploader.save_upload(session_id, file)
  - If result.valid == False:
      Return 400 with { error: result.error }
  - If valid:
      Look up session from sessions dict
      Call session.confirm_upload(result.summary)
      Return {
        valid: True,
        files: result.files,
        summary: result.summary,
        session_ready: True
      }

Also update POST /session/chat response:
When session returns waiting_for_upload=True, include it in response:
  { ..., waiting_for_upload: True }
So frontend knows to show upload zone instead of chat input.
```

---

## Block 6 — Update frontend/index.html

**Goal:** Add upload zone, file summary, wire into chat flow.

**Copilot Prompt:**
```
Update frontend/index.html.

Add these UI elements (hidden by default, shown when needed):

1. UPLOAD ZONE — shown when API returns waiting_for_upload=true
   Replace chat input bar with:
   
   Dark dashed border box, full width:
   "📁 Drop your website files here
    or click to browse
    ─────────────────────────
    Supports .zip or individual files
    ⚠️  Must include index.html"
   
   Clicking opens file picker (accept .zip,.html,.css,.js,.png,.jpg,.svg,.ico,.gif)
   Drag and drop also works
   Show spinner while uploading: "Uploading and validating..."

2. FILE SUMMARY — shown after successful upload
   Appears as a bot message bubble in chat:
   "✅ Got your files! Here's what I found:
    
    📄 HTML files: 2
    🎨 CSS files: 1  
    ⚡ JS files: 3
    🖼️  Images: 5
    📦 Total size: 284 KB
    
    index.html ✓ found"
   
   Below summary: show confirm card (same as existing intent summary card)
   with Deploy button

3. ERROR STATE — if upload returns error:
   Show red bot message bubble: "❌ {error message}"
   Show upload zone again so they can retry

JS logic:
- After receiving waiting_for_upload=true from /session/chat:
    Hide chat input bar
    Show upload zone
- On file drop or select:
    POST to /session/{session_id}/upload as FormData
    On success: hide upload zone, show file summary as bot message, show confirm card
    On error: show error bubble, re-show upload zone
- Deploy button behavior: same as existing (GET /session/{id}/deploy as EventSource)
```

---

## Block 7 — End to End Test Checklist

Run through these manually before calling it done:

```
[ ] Upload a zip with index.html in root → deploys correctly
[ ] Upload a zip with index.html inside a subfolder → flattened, deploys correctly  
[ ] Upload a zip with NO index.html → shows error, upload zone reappears
[ ] Upload individual .html file directly → deploys correctly
[ ] Upload a zip with CSS + JS + images → all files appear in live site
[ ] Choose "starter template" → deploys branded CloudPilot page (old behavior)
[ ] Mid-convo say "actually GCP" → cloud switches, region resets, asked again
[ ] Full flow: type prompt → conversation → upload zone → deploy → live URL
```

---

## Demo Script (With Upload)

```
1. Open CloudPilot UI
2. Type: "I want to host my business website for around 200 customers"
3. Bot detects: static_website, low tier — asks cloud → pick AWS
4. Bot asks region → pick us-east-1
5. Bot asks name → type "my-business"
6. Bot asks: "Do you have files to upload?"
7. Click "Upload my files" → upload zone appears
8. Drop a zip of a real HTML website
9. Bot shows file summary
10. Click Deploy → live log stream
11. CloudFront URL appears → click it → their actual website is live
```

That's the moment. Professor sees their real website live on AWS.

---

*Project: CloudPilot | Phase 2: Bring Your Own Site | Stack: FastAPI + Terraform + S3/CloudFront*
