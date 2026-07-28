# AgriScope AI — Smart Farming Assistant

A 3-crop (Cassava, Maize, Yam) farming platform with Smart Scouting, Climate-Driven Growing Calendar, and Market Connect. Built for Rwandan smallholder farmers.

Track 01: Agriculture & BioSystems — Frontiers GenAI Hackathon 2026.

---

## Three Pillars

### Pillar 1 — Smart Scouting
- Weekly scouting plan (when, where, what to look for)
- 5 spots x 4 plants = 20 sample points, edges prioritized
- Top 3 threats per growth stage + climate
- Photo check-in with Gemini Vision diagnosis
- Human verification flag for low-confidence results
- Neighbor early warning alerts (mock data for demo)
- Every recommendation cites FAO, IITA, or CGIAR

### Pillar 2 — Climate Growing Calendar
- Land prep, planting, weeding, fertilizer, harvest windows
- Based on Open-Meteo weather + historical patterns
- Budget-constrained advice (stays within farmer's RWF budget)
- Real-time adaptation: "delay planting 5 days — rains coming late"
- Personalized to plot location + crop + planting date

### Pillar 3 — Market Connect
- Harvest estimate based on plot size + crop
- Farmgate vs market price trends (sell now vs hold)
- 5 seeded buyers per crop with contact details
- WhatsApp-ready buyer outreach messages in farmer's language
- Quality standards + negotiation tips

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Streamlit + Inter font + Bootstrap Icons |
| AI | Gemini 3.6-flash (vision + text) |
| Weather | Open-Meteo API (free, no key) |
| Database | SQLite |
| Translation | Built-in EN/RW/SW/FR system |
| Vision | Gemini crop disease detection from scout photos |

---

## Quick Start

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
streamlit run app.py
```
