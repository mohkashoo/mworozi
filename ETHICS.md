# Mworozi — Ethics, Impact & Accessibility Brief

## What Problem Does It Solve?

Smallholder farmers in Rwanda and across East Africa lose 30-60% of their crops annually to preventable diseases, pests, and poor treatment timing. Most farmers rely on visual inspection alone and have no access to agricultural extension officers who are outnumbered 1:10,000 in rural areas.

Mworozi puts an AI crop health assistant in every farmer's pocket. Upload a photo of a diseased crop, and the system identifies the issue, recommends treatment using locally available materials, creates a staged recovery plan, and tracks progress over time — all in the farmer's own language.

---

## Ethical Considerations

### 1. Human-in-the-Loop (AI as Assistant, Not Decision-Maker)

The app never bypasses human judgment. Every AI diagnosis includes a mandatory "Extension Officer Review" step where a human must explicitly approve or reject the recommendation before a treatment plan is created. The AI advises — the farmer or officer decides.

### 2. Bias and Fairness

- The model is prompted specifically for East African crops, diseases, and locally available treatments
- Organic treatment options are provided alongside chemical ones to respect farmers with different resource levels
- All output is available in Kinyarwanda, Swahili, French, and English — no language barrier to access
- The voice feature reads treatments aloud for farmers with limited literacy

### 3. Accountability

- Every diagnosis, treatment plan, and progress update is stored in a persistent database with timestamps
- Farmers can review their full assessment history at any time
- A disclaimer clearly states that AI-generated recommendations should be verified with a local extension officer
- The app never claims to replace agricultural experts

### 4. Transparency

- Users can see whether the analysis came from Gemini AI or from the built-in demo data
- Confidence scores are displayed alongside every diagnosis
- Treatment recommendations are explicitly marked as AI-generated
- When Gemini is unavailable, the app transparently falls back to pre-loaded data — it never pretends to have more capability than it does

### 5. Privacy

- No user data is transmitted to external servers beyond the Gemini API call for image analysis
- Assessment history is stored locally in SQLite — the farmer owns their data
- Images uploaded for progress tracking are stored locally, not on any cloud

---

## Accessibility & UI/UX for All Users

The app is designed for users across the literacy and age spectrum:

### For Young or Tech-Savvy Users
- Full web interface with dark theme
- Image upload from gallery or camera
- Speed-adjustable audio playback
- Keyboard-navigable controls

### For Older or Low-Literacy Users
- **Voice playback**: Click one button to hear the treatment plan read aloud in Kinyarwanda
- **Simple flow**: Upload photo → get result → hear treatment — only three steps
- **Visual indicators**: Color-coded alerts (red for severe, amber for moderate, green for healthy)
- **No typing required**: Farmer name and location are the only text inputs; everything else is a selection or button

### For Users with Limited Internet
- The app works fully offline using demo disease samples
- Voice playback is pre-generated and cached — no streaming needed
- All assessment history is stored locally
- The interface loads fast even on 2G connections

### UI Design Principles
- High-contrast dark theme for outdoor use in bright sunlight
- Large touch targets (buttons span full width)
- Clear visual hierarchy: problem → severity → action
- Consistent layout: sidebar for input, main area for results
- Bootstrap Icons supplement text labels for universal recognition

---

## Bonus Features

### Human Approval Step
Every treatment plan requires explicit approval from an extension officer or informed farmer before creation. The AI diagnosis is presented for review alongside confidence metrics. The user can either approve and start the plan or reject and flag for expert consultation.

### Evaluation Metrics
- **AI Confidence Score**: Displayed with every diagnosis to indicate certainty level
- **Recovery Rate**: The treatment dashboard shows the percentage of check-ins marked as "improving" vs total check-ins, giving a measurable success metric
- **Treatment Outcomes**: Each progress update records the AI's verdict (improving/stable/worsening) so farmers and officers can track what works

### Personalization with Constraints
- **Resource Preference**: Farmers select between organic-only, chemical-only, or both — treatment recommendations respect this constraint
- **Seasonal Context**: The current season (planting, growing, harvest, dry) is recorded with each assessment, enabling seasonally appropriate advice
- **Location-Based**: Farmer's location is stored with every assessment for future analysis of regional disease patterns
- **Crop-Specific**: Treatment plans are tailored to the specific crop variety and disease

---

## Summary

Mworozi is not an AI that replaces farmers or extension officers. It is a tool that amplifies human capability — giving a farmer in Rulindo the same quality of crop health advice they would get from a university-trained agronomist, in their language, on their phone, at no cost.
