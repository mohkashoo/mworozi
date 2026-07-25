import os
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

TREE_HEALTH_PROMPT = """You are a senior Rwandan forestry expert and plant pathologist. 
Analyze this tree photo and provide:

1. **Species**: Best guess of tree species
2. **Health Score**: 0-100 (100 = perfectly healthy)
3. **Disease/Pest**: Name any visible disease, pest, or deficiency
4. **Symptoms**: What you observe (leaf color, bark condition, root exposure, canopy density)
5. **Severity**: Mild / Moderate / Severe / Critical
6. **Treatment**: 2-3 actionable steps the farmer should take
7. **Risk to Nearby Trees**: How contagious/spreading this is

Be concise. Use simple language a rural farmer would understand."""

FOREST_AUDIO_PROMPT = """You are a Rwandan forest acoustics expert. 
Analyze this audio recording from a forest and provide:

1. **Biodiversity Index**: 0-100 (100 = rich ecosystem)
2. **Bird Species Detected**: How many distinct bird calls you hear
3. **Insect Activity**: Normal / High / Low / None
4. **Threats Detected**: Can you hear chainsaws, vehicles, gunshots, or other human activity?
5. **Alert Needed**: YES or NO — is there a immediate threat (chainsaw = YES)
6. **Forest Health Assessment**: Based on sounds alone, is this a healthy forest?
7. **Recommendation**: What action to take

Be honest — if you hear a chainsaw, say it clearly. This is used by park rangers."""

REFORESTATION_PROMPT = """You are a Rwandan agroforestry specialist working with the Rwanda Forestry Authority.
Based on the following land description, create a personalized reforestation plan:

Land details:
{description}

Provide:
1. **Recommended Species**: 3-5 native tree species suitable for this land
2. **Planting Layout**: How to arrange them (agroforestry zones, spacing)
3. **5-Year Growth Forecast**: Expected height, canopy coverage by year
4. **Carbon Sequestration**: Estimated CO2 capture over 5 years (kg)
5. **Monthly Care Calendar**: What to do each month for the first year
6. **Local Benefits**: How this helps soil, water, and local biodiversity

Keep it practical and actionable for a smallholder farmer."""


def _get_client():
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


MOCK_TREE_ANALYSIS = """**Species**: Likely *Grevillea robusta* (Silver Oak)

**Health Score**: 34/100

**Disease/Pest**: Possible root rot (*Armillaria* spp.) with secondary fungal leaf spot

**Symptoms**: 
- Yellowing and browning of lower leaves
- Sparse canopy (approx 40% defoliation)
- Dark lesions visible on lower trunk bark
- Soil waterlogging around base

**Severity**: Severe

**Treatment**:
1. Improve drainage around the root zone immediately
2. Remove and destroy affected leaves to prevent spore spread
3. Apply copper-based fungicide to trunk lesions

**Risk to Nearby Trees**: High — root rot can spread through soil contact. Isolate area."""

MOCK_AUDIO_ANALYSIS = """**Biodiversity Index**: 72/100

**Bird Species Detected**: At least 4 distinct calls detected

**Insect Activity**: High — healthy insect population present

**Threats Detected**: No chainsaw or vehicle noise detected. Light wind rustling only.

**Alert Needed**: NO

**Forest Health Assessment**: Healthy forest ecosystem. Bird diversity indicates good habitat quality.

**Recommendation**: Continue monitoring. Consider periodic audio surveys to track biodiversity changes."""

MOCK_REFORESTATION = """**Recommended Species**:
1. *Prunus africana* (African cherry) — timber + medicine
2. *Grevillea robusta* — fast-growing shade tree
3. *Markhamia lutea* — nitrogen-fixing, bee forage
4. *Persea americana* (avocado) — food + income
5. *Calliandra calothyrsus* — living fence + fodder

**5-Year Growth Forecast**:
- Year 1: 1-2m height, 10% canopy
- Year 3: 4-6m height, 30% canopy
- Year 5: 8-12m height, 60% canopy, first timber harvest possible for Grevillea

**Carbon Sequestration**: ~400kg CO2 per tree over 5 years (2,000kg total for 5 trees)

**Monthly Care Calendar**: 
- Month 1-3: Water weekly, apply mulch
- Month 4-6: Weed monthly, check for pests
- Month 7-12: Reduce watering, stake if needed"""


def analyze_tree_image(image_bytes):
    client = _get_client()
    if client is None:
        return MOCK_TREE_ANALYSIS
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[TREE_HEALTH_PROMPT, image_bytes],
        )
        return response.text
    except Exception:
        return MOCK_TREE_ANALYSIS


def analyze_forest_audio(audio_bytes):
    client = _get_client()
    if client is None:
        return MOCK_AUDIO_ANALYSIS
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[FOREST_AUDIO_PROMPT, audio_bytes],
        )
        return response.text
    except Exception:
        return MOCK_AUDIO_ANALYSIS


def generate_reforestation_plan(description):
    client = _get_client()
    if client is None:
        return MOCK_REFORESTATION
    try:
        prompt = REFORESTATION_PROMPT.format(description=description)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception:
        return MOCK_REFORESTATION
