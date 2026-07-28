**MWOROZI  AI Crop Health Assistant**  
**Mworozi** ("farmer" in Kinyarwanda) is an AI-powered crop health platform that helps farmers detect diseases, receive structured treatment plans, and track crop recovery through visual progress monitoring. Designed for low-resource agricultural settings in East Africa.  
Built for the Frontiers GenAI Hackathon 2026 — Track 01: Agriculture & BioSystems.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSdYxZ4/mJjEsxE8W8GbCFuCLTOzVXsAAPzFuVZ3dXw9AQDgtesBxPEF3bv7x0IAAAAASUVORK5CYII=)  
**Architecture**  
Farmer uploads crop photo → Gemini Vision analyzes for disease  
     → Returns: disease ID, severity, treatment, prevention  
     → Optional: create treatment plan with staged tasks  
     → Each stage: upload follow-up photo → AI compares progress  
     → Dashboard tracks recovery across all active plans  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCUpfDq4wwIAABiywEZJWQZeZ2ao9AAD+4liruzq/ngAA8Nr1ABweBgdur/QFAAAAAElFTkSuQmCC)  
**Features**  
- **Crop Disease Detection** - Upload a photo; Gemini Vision identifies diseases, pests, or nutrient deficiencies  
- **Demo Samples** - Pre-loaded disease cases (Maize Blight, Cassava Mosaic Virus, Tomato Late Blight) for offline demonstration  
- **Multi-Language Support** - Results in English, Kinyarwanda, Swahili, or French  
- **Voice Playback** - Browser-native Speech Synthesis reads treatment instructions aloud in the farmer's language. No internet required.  
- **Smart Treatment Plan** - Auto-generates a staged recovery timeline (Day 1 to Day 14) with disease-specific tasks  
- **Progress Check-Ins** - Farmer uploads a follow-up photo at each stage  
- **AI Progress Tracking** - Gemini compares before/after images and classifies: improving, stable, or worsening  
- **Treatment Dashboard** - Overview of all active plans with recovery metrics  
- **Assessment Ledger** - Persistent SQLite database of all diagnoses, visible on every page load  
- **Fallback Mode** - If Gemini API quota is exceeded or network is unavailable, the app continues with pre-loaded demo data  
- **Mobile-Compatible** - Streamlit renders on phones and tablets  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhwgJmkPYLLpnRgQU2QtIq6DIze3UGAMBf3Gu1VcfHEQAA3rseaHkEMn1wK7sAAAAASUVORK5CYII=)  
**Technology Stack**  
| | | |  
|-|-|-|  
| **Component** | **Technology** | **Role** |   
| Frontend | Streamlit | Web application framework |   
| AI Vision | Google Gemini (gemini-flash-latest) | Disease detection from crop photos |   
| AI Comparison | Google Gemini | Before/after image analysis for progress tracking |   
| Voice | Web Speech API | Text-to-speech in farmer's language (offline-capable) |   
| Database | SQLite | Assessments, treatment plans, progress records |   
| Image Generation | Pillow | Synthetic diseased leaf images for demo |   
| Data | Pandas | Query and display assessment history |   
| Icons | Bootstrap Icons | UI icon set |   
| Configuration | python-dotenv | Environment variable loading |   
| Styling | Custom CSS | Dark theme (#090a0f / #10b981 / #ef4444) |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFjsymJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrsexNkF4H1/HJoAAAAASUVORK5CYII=)  
**Project Structure**  
.  
 ├── app.py                 # Application entry point  
 ├── requirements.txt       # Python dependencies  
 ├── .env                   # API credentials (not committed)  
 ├── .env.example           # Configuration template  
 ├── .gitignore  
 ├── .streamlit/  
 │   └── config.toml        # Streamlit theme configuration  
 ├── progress/              # Treatment plan check-in photos  
 └── README.md  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAM0lEQVR4nO3OMQ0AIAwAwZKQ6kBqjSAOJywYYCIkd9OP36pqRMQMAAB+sfqJfLoBAMCN3NYoAzBA+QG0AAAAAElFTkSuQmCC)  
**Setup**  
pip install -r requirements.txt  
 export GEMINI_API_KEY="your-key-here"  
 export GEMINI_MODEL="gemini-flash-latest"  
 streamlit run app.py  
   
The application functions without an API key using built-in demo data. API access enables live image analysis.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhwgJWEPcbJpnRgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseaIkEMIPgIvAAAAAASUVORK5CYII=)  
**Demo Samples**  
| | | |  
|-|-|-|  
| **Crop** | **Disease** | **Severity** |   
| Maize | Northern Corn Leaf Blight | Moderate |   
| Cassava | Cassava Mosaic Virus | Severe |   
| Tomato | Late Blight | Severe |   
   
Each generates a synthetic leaf image with disease symptoms for demonstration.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**Treatment Plan Stages**  
| | |  
|-|-|  
| **Stage** | **Task** |   
| Day 1 | Remove affected material, apply initial treatment |   
| Day 3 | Re-apply treatment, monitor for new symptoms |   
| Day 7 | Apply secondary (organic) option, continue monitoring |   
| Day 14 | Final assessment: recovery confirmed or requires re-treatment |   
   
Each stage accepts a follow-up photograph. AI analysis compares it to the initial image and reports: improving, stable, or worsening.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCkLfFDZwwIgHRiywEZJWQZeZ2ao9AAD+4lyruzq+ngAA8Nr1AOH0BedHjjlfAAAAAElFTkSuQmCC)  
**Limitations**  
- Treatment recommendations are AI-generated and should be verified with a local agricultural extension officer  
- Diagnostic accuracy depends on image quality  
- Voice synthesis quality depends on browser and operating system language support  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OMQ0AIAwAwZIgBKn1gjJsdGLBABMhuZt+/JaZIyJmAADwi9VP1NMNAABu1AaU4gUeBSGW2wAAAABJRU5ErkJggg==)  
*Frontiers GenAI Hackathon 2026 — ALX Kigali, Rwanda*  
