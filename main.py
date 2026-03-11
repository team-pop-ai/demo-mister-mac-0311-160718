import os
import json
import base64
from typing import Optional
from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import anthropic
import openai

app = FastAPI()
templates = Jinja2Templates(directory=".")

# Initialize AI clients
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Load mock data
def load_mock_data():
    try:
        with open("data/fallback.json", "r") as f:
            return json.load(f)
    except:
        return {
            "customers": [],
            "guidance_examples": {
                "email_setup": "Tell them: 'I can see your email settings got corrupted. Don't worry, this is common and easy to fix. Go to Settings, then Mail, and tap on your email account.' Wait for them to do that, then continue: 'Now tap Delete Account - this won't delete your emails, just the broken settings. Then we'll add it back properly with the correct configuration.'"
            }
        }

mock_data = load_mock_data()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze-issue")
async def analyze_issue(
    customer_description: str = Form(...),
    screen_image: Optional[UploadFile] = File(None),
    customer_id: str = Form(default="CUST001")
):
    try:
        # Get customer context
        customer_info = next(
            (c for c in mock_data["customers"] if c["id"] == customer_id),
            mock_data["customers"][0] if mock_data["customers"] else {
                "name": "Sarah Johnson",
                "device": "iPhone 14",
                "previous_issues": ["Email setup fixed 2 months ago", "iCloud sync issue resolved"]
            }
        )
        
        # Prepare context for AI
        context = f"""Customer: {customer_info.get('name', 'Unknown')}
Device: {customer_info.get('device', 'iPhone')}
Previous issues: {', '.join(customer_info.get('previous_issues', []))}

Customer's problem description: "{customer_description}"
"""
        
        # Add screen analysis if image provided
        screen_analysis = ""
        if screen_image and screen_image.filename:
            # In production, this would analyze the actual screenshot
            # For demo, we'll simulate based on the description
            if "email" in customer_description.lower():
                screen_analysis = "\nScreen shows: iPhone Settings > Mail, Accounts & Passwords. No email accounts configured."
            elif "scam" in customer_description.lower():
                screen_analysis = "\nScreen shows: Suspicious email with 'Your Apple ID has been locked' message and fake Apple logo."
            elif "backup" in customer_description.lower():
                screen_analysis = "\nScreen shows: iPhone Storage full warning, backup failed error in Settings > Apple ID > iCloud."
        
        # Generate AI guidance using Claude
        system_prompt = """You are an expert Apple technician coaching junior support staff. Generate step-by-step guidance that a junior technician can read aloud to customers during support calls.

Your guidance style:
- Explain what you can see is wrong
- Give exact words for the tech to say to the customer  
- Include reassurance ("don't worry", "this is common")
- Break into small, clear steps with pauses
- Use Scott Baker's professional but friendly coaching approach

Format your response as clear numbered steps that the junior tech can follow and read verbatim."""

        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=system_prompt,
            messages=[{
                "role": "user", 
                "content": f"{context}{screen_analysis}\n\nGenerate guidance for the junior technician to help this customer."
            }]
        )
        
        guidance_text = response.content[0].text
        
        # Categorize the issue
        issue_category = "general"
        if "email" in customer_description.lower():
            issue_category = "email_setup"
        elif "scam" in customer_description.lower():
            issue_category = "scam_validation"
        elif "backup" in customer_description.lower():
            issue_category = "backup_restore"
        elif "icloud" in customer_description.lower():
            issue_category = "internal_tools"
        
        return {
            "success": True,
            "guidance": guidance_text,
            "customer_info": customer_info,
            "issue_category": issue_category,
            "screen_analysis": screen_analysis.strip(),
            "estimated_resolution_time": "5-10 minutes"
        }
        
    except Exception as e:
        # Fallback to pre-generated guidance if AI fails
        fallback_guidance = mock_data["guidance_examples"].get(
            "email_setup",
            "Tell them: 'I can see the issue. Let me walk you through this step by step. First, go to Settings on your iPhone.'"
        )
        
        return {
            "success": True,
            "guidance": fallback_guidance,
            "customer_info": mock_data["customers"][0] if mock_data["customers"] else {"name": "Customer", "device": "iPhone"},
            "issue_category": "general",
            "screen_analysis": "Demo mode - using fallback guidance",
            "estimated_resolution_time": "5-10 minutes",
            "note": "Using fallback guidance - Claude API unavailable"
        }

@app.post("/transcribe-audio")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    try:
        # In production, this would use OpenAI Whisper to transcribe the audio
        # For demo, we'll return a realistic transcription based on common issues
        
        audio_content = await audio_file.read()
        
        # Simulate Whisper transcription (in production, would actually process the audio)
        sample_transcriptions = [
            "Hi, my iPhone email stopped working and I can't receive any messages. It was working fine yesterday but now nothing is coming through.",
            "I got this email saying my Apple ID is locked and I need to verify it, but I'm not sure if it's real or a scam. Should I click the link?",
            "My iPhone backup keeps failing and says my iCloud storage is full, but I already upgraded my plan. I don't know what to do.",
            "I can't sign into my Apple ID on my new iPhone. It keeps saying my password is wrong but I know it's right."
        ]
        
        # Return a realistic transcription (would be actual Whisper output in production)
        return {
            "success": True,
            "transcription": sample_transcriptions[0],  # In production: actual Whisper result
            "confidence": 0.95,
            "duration": 8.5
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "Audio transcription failed",
            "fallback": "Customer described an iPhone email issue"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)