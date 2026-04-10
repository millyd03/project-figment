import streamlit as st
import requests
import json

st.set_page_config(
    page_title="Project FIGMENT",
    page_icon="🎢",
    layout="wide"
)

st.title("🎢 Project FIGMENT - Smart Genie & Playlist Curator")

# API base URL
API_BASE = "http://localhost:8002"

# Spotify Auth
st.header("🔐 Spotify Authentication")
auth_response = requests.get(f"{API_BASE}/auth/status")
is_authenticated = auth_response.json().get("authenticated", False)

if is_authenticated:
    st.success("✅ Connected to Spotify")
    if st.button("Disconnect"):
        # TODO: Implement disconnect
        st.rerun()
else:
    st.warning("❌ Not connected to Spotify")
    if st.button("Authenticate with Spotify"):
        try:
            response = requests.get(f"{API_BASE}/auth/spotify")
            if response.status_code == 200:
                auth_url = response.json()["auth_url"]
                st.markdown(f"[Click here to authenticate]({auth_url})")
                st.info("After authenticating, return here to create playlists.")
            else:
                st.error("Failed to get auth URL")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Spotify Playlist Creator
st.header("🎵 Spotify Playlist Creator")
if is_authenticated:
    with st.form("playlist_form"):
        playlist_name = st.text_input("Playlist Name", "My FIGMENT Playlist")
        throwback = st.checkbox("Throwback (pre-2011)")
        fresh = st.checkbox("Fresh (last 5 years)")
        tacno = st.checkbox("TACNO (Covers only)")
        christmas = st.checkbox("Christmas")
        clean = st.checkbox("Clean (no explicit)")

        submitted = st.form_submit_button("Create Playlist")
        if submitted:
            payload = {
                "name": playlist_name,
                "throwback": throwback,
                "fresh": fresh,
                "tacno": tacno,
                "christmas": christmas,
                "clean": clean
            }
            try:
                response = requests.post(f"{API_BASE}/create_playlist", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if "error" in data:
                        st.error(f"Error: {data['error']}")
                    else:
                        st.success(f"Playlist created! ID: {data['playlist_id']} with {data['tracks_count']} tracks")
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Failed to create playlist: {str(e)}")
else:
    st.info("Please authenticate with Spotify first to create playlists.")

# Disney Genie
st.header("🎢 Disney Genie - Next Action")
with st.form("disney_form"):
    park_id = st.selectbox("Park", ["MagicKingdomWaltDisneyWorld", "EpcotWaltDisneyWorld"])  # TODO: Add more parks
    lat = st.number_input("Latitude", value=28.3772, format="%.4f")
    lon = st.number_input("Longitude", value=-81.5707, format="%.4f")
    party_size = st.slider("Party Size", 1, 10, 1)
    # TODO: Add party composition details

    submitted_disney = st.form_submit_button("Get Recommendations")
    if submitted_disney:
        payload = {
            "park_id": park_id,
            "user_location": [lat, lon],
            "party_composition": {"size": party_size}  # TODO: Expand
        }
        try:
            response = requests.post(f"{API_BASE}/get_next_action", json=payload)
            if response.status_code == 200:
                data = response.json()
                st.subheader("Recommendations")
                for rec in data.get("recommendations", []):
                    st.write(f"**{rec['name']}** - Score: {rec['score']:.2f}, Wait: {rec['wait_time']} min")

                if data.get("nudges"):
                    st.subheader("🚨 Nudges")
                    for nudge in data["nudges"]:
                        st.warning(f"{nudge['type']}: {nudge['ride']} - {nudge.get('wait_time', 'N/A')} min")
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Failed to get recommendations: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*Powered by Google ADK & LiteLLM*")