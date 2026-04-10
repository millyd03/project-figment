This is the blueprint for **FIGMENT**. This document is designed to be fed directly into a coding assistant (like Gemini in VS Code) to provide the architectural guardrails, logic flows, and data schemas required to build the agent from scratch.

---

# Technical Design Document: Project FIGMENT

**Project Goal:** A personal agentic hub built on Google ADK, providing "Smart Genie" park routing for Disney and "Rule-Based Curation" for Spotify.
**Primary Hardware:** Pixel 9XL Pro (via PWA).
**Primary Framework:** Google Agent Development Kit (ADK).

---

## 1. System Architecture
FIGMENT follows a "Headless" architecture to allow for flexible deployment and multi-LLM support.

* **Logic Engine:** Google ADK (Python).
* **LLM Gateway:** `LiteLLM` (Interfacing with Gemini 1.5 Pro and local Ollama/Gemma 2).
* **API Layer:** `FastAPI` (RESTful communication).
* **Frontend:** `Streamlit` or `Reflex` (PWA-enabled for Android/Pixel).
* **Database:** `SQLite` (Session state, "Must-Do" lists, and user configs).

---

## 2. The Disney Intelligence Engine ("Genie Replacement")

### A. Data Integration
* **Source A:** `ThemeParks.wiki` API (Wait times, Lightning Lane windows, Park hours).
* **Source B:** `MouseTools` (Python library) for Dining menus, Showtimes, and granular Ride Status/Refurbishments.

### B. Recommendation Scoring Algorithm ($S$)
For every attraction ($a$), calculate a priority score based on the current state:
$$S(a) = (W_{delta} \times 0.4) - (D_{prox} \times 0.3) + (P_{pref} \times 0.3)$$
* **$W_{delta}$**: Difference between current wait and 30-day rolling average.
* **$D_{prox}$**: Walking distance from user’s current GPS/Land coordinates.
* **$P_{pref}$**: Party Profile multiplier (filters out height-restricted or "motion-sensitive" rides based on the party list).

### C. The Nudge Logic
A background process polls `ThemeParks.wiki` every 5 minutes.
* **Trigger:** If a "Must-Do" ride drops $>30\%$ below its average wait OR a top-tier ride hits $<20$ mins within 500ft of the user.
* **Output:** Web Push Notification to the Pixel 9XL Pro.

---

## 3. The Spotify Rule Engine

### A. Global Constraint Logic (Standard)
1.  **Followed-Only Filter:** Cross-reference all potential tracks against the user's `Followed Artists` list.
2.  **Tiered Artist Cap (The "Star Power" Rule):**
    * $\le 50k$ followers: **1 track max**
    * $50k - 500k$: **2 tracks max**
    * $500k - 1M$: **3 tracks max**
    * $1M - 5M$: **4 tracks max**
    * $5M - 10M$: **5 tracks max**
    * $> 10M$: **No Cap**
3.  **Anti-Batching:** All selected tracks must be shuffled globally before the playlist is created to ensure no artist clusters.

### B. Feature Toggles (Optional)
* **Throwback:** Filter for `release_date < 2011-01-01`.
* **Fresh:** Sliding window filter: `release_date > (TODAY - 5 Years)`.
* **TACNO (They're All Covers, No Originals):** Short-circuit search to only pull from the user's "Covers" Playlist ID.
* **Christmas:** Short-circuit search to only pull from the "Punk Rawk Christmas" Playlist ID.
* **Clean:** Filter `explicit == False`.

---

## 4. Technical Implementation Requirements

### Multi-LLM Socket
The ADK must utilize a configuration file (`config.yaml`) to swap models:
```yaml
model_provider:
  active: "gemini-pro" # Options: gemini-pro, ollama-local
  ollama_endpoint: "http://localhost:11434"
```

### Authentication & Secrets
* Use **Google Cloud Secret Manager** or a local `.env` for:
    * Spotify Developer Client ID/Secret.
    * Google Gemini API Key.
    * Disney/MyDisneyExperience login tokens (managed via MouseTools).

### PWA Manifest (Mobile)
A `manifest.json` must be served by the FastAPI backend to enable "Add to Home Screen" on the Pixel 9XL Pro, including `standalone` display mode and theme color mapping for the Pixel's dark mode.

---

## 5. Development Roadmap (Action Items for Coding Assistant)
1.  **Phase 1:** Initialize Google ADK skeleton with LiteLLM.
2.  **Phase 2:** Build the `SpotifyRuleEngine` class with the Tiered Cap logic.
3.  **Phase 3:** Integrate `mousetools` and `themeparks.wiki` wrappers.
4.  **Phase 4:** Create the FastAPI endpoints for `get_next_action` and `create_playlist`.
5.  **Phase 5:** Build the Streamlit/PWA frontend for mobile interaction.

---

**Hand-off Note:** *When implementing the recommendation engine, prioritize the "Party Composition" filter to ensure any attractions with height requirements exceeding the daughter's profile are automatically assigned a score of 0.*