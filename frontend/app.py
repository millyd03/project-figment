import streamlit as st
import requests
import json
import time
from config import settings
from urllib.parse import urlparse

# Configure page for mobile-first design
st.set_page_config(
    page_title="FIGMENT",
    page_icon="🎢",
    layout="centered",  # Mobile-first: single column
    initial_sidebar_state="collapsed"
)

# Inject PWA manifest and service worker registration
st.markdown(
    """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#1F1F1F">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/service-worker.js').then(reg => {
                console.log('Service Worker registered');
            }).catch(err => {
                console.log('Service Worker registration failed:', err);
            });
        }
        
        // Request notification permissions
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    </script>
    """,
    unsafe_allow_html=True
)

# Custom CSS for mobile optimization
st.markdown("""
    <style>
        /* Mobile-first design */
        .stApp {
            max-width: 600px;
            margin: 0 auto;
        }
        
        /* Dark mode for Pixel */
        html {
            background-color: #121212;
            color: #fff;
        }
        
        /* Large touch targets */
        button {
            min-height: 48px !important;
            font-size: 16px !important;
        }
        
        /* Better spacing on mobile */
        [data-testid="stForm"] {
            padding: 1rem 0.5rem;
        }
        
        /* Tab styling */
        [data-testid="stTabs"] button {
            font-size: 14px !important;
        }
    </style>
    """,
    unsafe_allow_html=True)

# API base URL derived from backend redirect URI in config
parsed = urlparse(settings.spotify_redirect_uri)
API_BASE = f"{parsed.scheme}://{parsed.netloc}"

# App title
st.markdown("# 🎢🎵 FIGMENT")
st.markdown("*Smart Disney Genie + Spotify Curator*")

# Initialize session state for refreshes
if "last_disney_refresh" not in st.session_state:
    st.session_state.last_disney_refresh = 0
if "auto_refresh_disney" not in st.session_state:
    st.session_state.auto_refresh_disney = False

# Create tabs for mobile navigation
tab_spotify, tab_disney = st.tabs(["🎵 Playlist", "🎢 Genie"])

# ============== SPOTIFY TAB ==============
with tab_spotify:
    st.subheader("Spotify Playlist Creator")
    
    # Authentication status
    profiles = []
    active_profile = None
    auth_error = None
    try:
        auth_response = requests.get(f"{API_BASE}/auth/status")
        if auth_response.status_code == 200:
            status = auth_response.json()
            is_authenticated = status.get("authenticated", False)
            profiles = status.get("profiles", []) or []
            active_profile = status.get("active_profile")
        else:
            is_authenticated = False
            auth_error = f"Auth service error: {auth_response.status_code}"
    except Exception as e:
        is_authenticated = False
        profiles = []
        active_profile = None
        auth_error = f"Connection error: {str(e)}"
    
    # Auto-authenticate if no valid profile exists
    if not is_authenticated and not profiles and not auth_error:
        st.info("🔄 Connecting to Spotify...")
        try:
            response = requests.get(f"{API_BASE}/auth/spotify")
            if response.status_code == 200:
                auth_url = response.json().get('auth_url')
                if auth_url:
                    # Automatically redirect to auth URL via JS
                    st.markdown(f"<script>window.location.href = '{auth_url}';</script>", unsafe_allow_html=True)
                    st.stop()
            else:
                auth_error = f"Failed to get auth URL: {response.status_code}"
        except Exception as e:
            auth_error = f"Auto-auth failed: {str(e)}"
    
    # Show authentication status or error
    if auth_error:
        st.error(f"❌ Authentication failed: {auth_error}")
        if st.button("🔄 Retry Connection", use_container_width=True):
            st.rerun()
    elif is_authenticated:
        active_label = active_profile.get("profile_name") if active_profile else None
        if not active_label and active_profile:
            active_label = active_profile.get("display_name") or active_profile.get("profile_key")
        st.success(f"✅ Connected to Spotify{f' as {active_label}' if active_label else ''}")
    elif profiles:
        st.warning("❌ Not authenticated with the current profile.")
        if active_profile and active_profile.get("id"):
            if st.button("🔄 Reconnect Profile", use_container_width=True):
                try:
                    response = requests.get(f"{API_BASE}/auth/spotify", params={"profile_id": active_profile.get("id")})
                    if response.status_code == 200:
                        auth_url = response.json().get('auth_url')
                        if auth_url:
                            st.markdown(f"<script>window.location.href = '{auth_url}';</script>", unsafe_allow_html=True)
                            st.stop()
                    else:
                        st.error("Failed to get auth URL")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Profile management (only show if authenticated or profiles exist)
    if is_authenticated or profiles:
        profile_labels = []
        profile_map = {}
        if profiles:
            for profile in profiles:
                label = profile.get("profile_name") or profile.get("display_name") or profile.get("profile_key") or f"Profile {profile.get('id')}"
                if profile.get("is_active"):
                    label = f"{label} (active)"
                profile_labels.append(label)
                profile_map[label] = profile
            profile_labels.append("➕ Add New Profile")

        selected_profile = None
        if profile_labels:
            current_index = next((i for i, p in enumerate(profiles) if p.get("is_active")), 0)
            selected_label = st.selectbox("Spotify Profile", profile_labels, index=current_index if current_index < len(profile_labels) else 0)
            if selected_label != "➕ Add New Profile":
                selected_profile = profile_map[selected_label]
                if selected_profile and not selected_profile.get("is_active"):
                    if st.button("Switch to selected profile", use_container_width=True):
                        try:
                            response = requests.post(f"{API_BASE}/auth/profile/select", json={"profile_id": selected_profile.get("id")})
                            if response.status_code == 200:
                                st.success("Profile switched. Refresh the page to continue.")
                            else:
                                st.error("Unable to switch profile.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            else:
                st.markdown("### Add New Spotify Profile")
                new_profile_name = st.text_input("Profile label", "", placeholder="e.g. Family, Work, Guest")
                if st.button("Add New Profile", use_container_width=True):
                    st.info("Redirecting to Spotify to add a new profile...")
                    try:
                        params = {}
                        if new_profile_name.strip():
                            params["profile_name"] = new_profile_name.strip()
                        response = requests.get(f"{API_BASE}/auth/spotify", params=params)
                        if response.status_code == 200:
                            auth_url = response.json().get('auth_url')
                            if auth_url:
                                st.markdown(f"<script>window.location.href = '{auth_url}';</script>", unsafe_allow_html=True)
                                st.stop()
                        else:
                            st.error("Failed to get auth URL")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    


    st.divider()
    
    if is_authenticated:
        st.markdown("### Create Playlist")
        with st.form("playlist_form"):
            playlist_name = st.text_input("📝 Playlist Name", "My FIGMENT Playlist")
            
            # Feature toggles in columns for better mobile space
            col1, col2 = st.columns(2)
            with col1:
                throwback = st.checkbox("Throwback (pre-2011)")
                tacno = st.checkbox("TACNO (Covers)")
            with col2:
                fresh = st.checkbox("Fresh (5 years)")
                christmas = st.checkbox("🎄 Christmas")
            
            clean = st.checkbox("Clean (explicit off)")
            
            submitted = st.form_submit_button("✨ Create Playlist", use_container_width=True)
            
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
                    with st.spinner("Creating playlist..."):
                        response = requests.post(f"{API_BASE}/create_playlist", json=payload)
                        if response.status_code == 200:
                            data = response.json()
                            if "error" not in data:
                                st.success(f"✅ Created! {data['tracks_count']} tracks")
                                st.info(f"Playlist ID: {data['playlist_id']}")
                            else:
                                st.error(f"Error: {data['error']}")
                        else:
                            st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
    else:
        st.info("Connect Spotify first to create playlists.")

# ============== DISNEY TAB ==============
with tab_disney:
    st.subheader("Disney Park Recommendations")
    
    with st.form("disney_form"):
        st.markdown("### 🗺️ Park & Location")
        park_labels = {
            "Disneyland": "Disneyland",
            "DisneysCaliforniaAdventure": "Disney's California Adventure",
            "MagicKingdomWaltDisneyWorld": "Magic Kingdom",
            "EpcotWaltDisneyWorld": "EPCOT",
            "DisneysHollywoodStudios": "Disney's Hollywood Studios",
            "DisneysAnimalKingdom": "Disney's Animal Kingdom",
        }
        park_id = st.selectbox(
            "Select Park",
            list(park_labels.keys()),
            format_func=lambda park: park_labels.get(park, park),
            help="Which Disney park are you at?"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=28.3772, format="%.4f")
        with col2:
            lon = st.number_input("Longitude", value=-81.5707, format="%.4f")
        
        st.markdown("### 👥 Party Composition")
        party_size = st.slider("How many in your party?", 1, 10, 1)
        
        # Detailed party composition for safety filtering
        party_members = []
        if party_size > 0:
            for i in range(party_size):
                with st.expander(f"Person {i+1}", expanded=(i==0)):
                    name = st.text_input(f"Name", f"Guest {i+1}", key=f"name_{i}")
                    height = st.slider(f"Height (inches)", 30, 84, 60, key=f"height_{i}")
                    age = st.slider(f"Age", 1, 80, 30, key=f"age_{i}")
                    motion_sensitive = st.checkbox("Motion sensitive?", key=f"motion_{i}")
                    
                    party_members.append({
                        "name": name,
                        "height_inches": height,
                        "age": age,
                        "motion_sensitive": motion_sensitive
                    })
        
        submitted_disney = st.form_submit_button("🎢 Get Recommendations", use_container_width=True)
        
        if submitted_disney:
            payload = {
                "park_id": park_id,
                "user_location": [lat, lon],
                "party_composition": {"members": party_members}
            }
            try:
                with st.spinner("Finding best rides..."):
                    response = requests.post(f"{API_BASE}/agent/next_action", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Display agent advice first
                        agent_advice = data.get("agent_advice", "")
                        if agent_advice:
                            st.markdown("### 🧠 Agent Insight")
                            st.info(agent_advice)
                            st.divider()
                        
                        # Display recommendations
                        st.markdown("### 🎯 Top Recommendations")
                        recs = data.get("recommendations", [])
                        if recs:
                            for i, rec in enumerate(recs[:5], 1):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"**{i}. {rec['name']}**")
                                    st.caption(f"Wait: {rec['wait_time']} min | Score: {rec['score']:.1f}")
                                with col2:
                                    if rec['score'] > 10:
                                        st.markdown("🔥")
                                    elif rec['score'] > 5:
                                        st.markdown("⭐")
                        else:
                            st.info("No recommendations available")
                        
                        # Display nudges
                        nudges = data.get("nudges", [])
                        if nudges:
                            st.markdown("### 🚨 Active Nudges")
                            for nudge in nudges:
                                if nudge['type'] == 'must_do_drop':
                                    st.warning(f"Must-Do Alert! {nudge['ride']} - {nudge['wait_time']}min (↓{nudge.get('drop_percent', 0):.0f}%)")
                                else:
                                    st.info(f"Short Wait! {nudge['ride']} - {nudge['wait_time']}min")
                    else:
                        st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Failed: {str(e)}")
    
    # Auto-refresh toggle for live updates
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh (30s)", use_container_width=True):
            st.session_state.last_disney_refresh = time.time()
            st.rerun()
    with col2:
        st.session_state.auto_refresh_disney = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh_disney)
    
    # Auto-refresh every 30 seconds if enabled
    if st.session_state.auto_refresh_disney:
        time.sleep(30)
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; font-size: 12px; color: #888;">
    🚀 Powered by FastAPI, Streamlit & Google ADK<br>
    Made with ❤️ for Pixel 9XL Pro
    </div>
    """,
    unsafe_allow_html=True
)