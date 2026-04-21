import requests
import mousetools
from typing import List, Dict, Optional, Tuple
import math
import asyncio
from database import SessionLocal, MustDoRide, SessionState, PartyMember

# Disney ride height restrictions (in inches) and motion sensitivity
# Data sourced from Disney official specifications
RIDE_RESTRICTIONS = {
    # Magic Kingdom
    "Big Thunder Mountain": {"height_min": 40, "motion_sensitive": True},
    "Space Mountain": {"height_min": 44, "motion_sensitive": True},
    "Splash Mountain": {"height_min": 40, "motion_sensitive": True},
    "Tomorrowland Speedway": {"height_min": 32, "motion_sensitive": False},
    "Dumbo the Flying Elephant": {"height_min": 0, "motion_sensitive": False},
    "It's a Small World": {"height_min": 0, "motion_sensitive": False},
    "Pirates of the Caribbean": {"height_min": 0, "motion_sensitive": False},
    "Haunted Mansion": {"height_min": 0, "motion_sensitive": False},
    "Jungle Cruise": {"height_min": 0, "motion_sensitive": False},
    "Cinderella Castle": {"height_min": 0, "motion_sensitive": False},
    "Carousel of Progress": {"height_min": 0, "motion_sensitive": False},
    "Hall of Presidents": {"height_min": 0, "motion_sensitive": False},
    "Liberty Belle Riverboat": {"height_min": 0, "motion_sensitive": False},
    "Matterhorn Bobsleds": {"height_min": 42, "motion_sensitive": True},
    "Millennium Falcon: Smugglers Run": {"height_min": 42, "motion_sensitive": True},
    "Rise of the Resistance": {"height_min": 40, "motion_sensitive": True},
    "Avatar Flight of Passage": {"height_min": 44, "motion_sensitive": True},
    "Test Track": {"height_min": 40, "motion_sensitive": True},
    "Guardians of the Galaxy": {"height_min": 42, "motion_sensitive": True},
    "Flying Carpet": {"height_min": 36, "motion_sensitive": True},
    "Aladdin Magic Carpets": {"height_min": 36, "motion_sensitive": False},
    # Epcot
    "Soarin' Around the World": {"height_min": 40, "motion_sensitive": True},
    "Mission Space": {"height_min": 44, "motion_sensitive": True},
    "Living with the Land": {"height_min": 0, "motion_sensitive": False},
    "Impressions de France": {"height_min": 0, "motion_sensitive": False},
    "Frozen Ever After": {"height_min": 0, "motion_sensitive": False},
    "Maelstrom": {"height_min": 0, "motion_sensitive": False},
    "Remy's Ratatouille Adventure": {"height_min": 0, "motion_sensitive": False},
    "Spaceship Earth": {"height_min": 0, "motion_sensitive": False},
    "Gran Fiesta Tour Starring The Three Caballeros": {"height_min": 0, "motion_sensitive": False},
    "Journey into Imagination": {"height_min": 0, "motion_sensitive": False},
    "Turtle Talk with Crush": {"height_min": 0, "motion_sensitive": False},
    # Disneyland
    "Space Mountain": {"height_min": 44, "motion_sensitive": True},
    "Matterhorn Bobsleds": {"height_min": 42, "motion_sensitive": True},
    "Pirates of the Caribbean": {"height_min": 0, "motion_sensitive": False},
    "Haunted Mansion": {"height_min": 0, "motion_sensitive": False},
    "It's a Small World": {"height_min": 0, "motion_sensitive": False},
    "Big Thunder Mountain Railroad": {"height_min": 40, "motion_sensitive": True},
    "Splash Mountain": {"height_min": 40, "motion_sensitive": True},
    "Indiana Jones Adventure": {"height_min": 46, "motion_sensitive": True},
    "Star Tours": {"height_min": 40, "motion_sensitive": True},
    "Radiator Springs Racers": {"height_min": 40, "motion_sensitive": True},
    "Finding Nemo Submarine Voyage": {"height_min": 0, "motion_sensitive": False},
    "Jungle Cruise": {"height_min": 0, "motion_sensitive": False},
    "Dumbo the Flying Elephant": {"height_min": 0, "motion_sensitive": False},
    "Autopia": {"height_min": 32, "motion_sensitive": False},
    "Buzz Lightyear Astro Blasters": {"height_min": 0, "motion_sensitive": False},
    # Disney's California Adventure
    "Radiator Springs Racers": {"height_min": 40, "motion_sensitive": True},
    "Guardians of the Galaxy - Mission: BREAKOUT!": {"height_min": 42, "motion_sensitive": True},
    "Incredicoaster": {"height_min": 48, "motion_sensitive": True},
    "Soarin' Around the World": {"height_min": 40, "motion_sensitive": True},
    "Grizzly River Run": {"height_min": 42, "motion_sensitive": True},
    "Toy Story Midway Mania": {"height_min": 0, "motion_sensitive": False},
    "Monsters, Inc. Mike & Sulley to the Rescue!": {"height_min": 0, "motion_sensitive": False},
    "California Screamin'": {"height_min": 48, "motion_sensitive": True},
    "Goofy's Sky School": {"height_min": 42, "motion_sensitive": True},
    "Jessie's Critter Carousel": {"height_min": 0, "motion_sensitive": False},
    "Mater's Junkyard Jamboree": {"height_min": 0, "motion_sensitive": False},
    "Luigi's Rollickin' Roadsters": {"height_min": 32, "motion_sensitive": False},
    "Redwood Creek Challenge Trail": {"height_min": 0, "motion_sensitive": False},
    "The Little Mermaid - Ariel's Undersea Adventure": {"height_min": 0, "motion_sensitive": False},
    # Disney's Hollywood Studios
    "Star Wars: Rise of the Resistance": {"height_min": 40, "motion_sensitive": True},
    "Millennium Falcon: Smugglers Run": {"height_min": 42, "motion_sensitive": True},
    "The Twilight Zone Tower of Terror": {"height_min": 40, "motion_sensitive": True},
    "Rock 'n' Roller Coaster": {"height_min": 48, "motion_sensitive": True},
    "Slinky Dog Dash": {"height_min": 38, "motion_sensitive": True},
    "Toy Story Midway Mania": {"height_min": 0, "motion_sensitive": False},
    "Star Tours": {"height_min": 40, "motion_sensitive": True},
    "Muppet*Vision 3D": {"height_min": 0, "motion_sensitive": False},
    "Beauty and the Beast - Live on Stage": {"height_min": 0, "motion_sensitive": False},
    "Voyage of the Little Mermaid": {"height_min": 0, "motion_sensitive": False},
    "Indiana Jones Epic Stunt Spectacular": {"height_min": 0, "motion_sensitive": False},
    "For the First Time in Forever: A Frozen Sing-Along Celebration": {"height_min": 0, "motion_sensitive": False},
    "Jedi Training: Trials of the Temple": {"height_min": 0, "motion_sensitive": False},
    # Disney's Animal Kingdom
    "Avatar Flight of Passage": {"height_min": 44, "motion_sensitive": True},
    "Na'vi River Journey": {"height_min": 0, "motion_sensitive": False},
    "Expedition Everest": {"height_min": 44, "motion_sensitive": True},
    "Kilimanjaro Safaris": {"height_min": 0, "motion_sensitive": False},
    "Festival of the Lion King": {"height_min": 0, "motion_sensitive": False},
    "Finding Nemo - The Musical": {"height_min": 0, "motion_sensitive": False},
    "DINOSAUR": {"height_min": 40, "motion_sensitive": True},
    "Kali River Rapids": {"height_min": 38, "motion_sensitive": True},
    "Primeval Whirl": {"height_min": 48, "motion_sensitive": True},
    "TriceraTop Spin": {"height_min": 0, "motion_sensitive": False},
    "The Boneyard": {"height_min": 0, "motion_sensitive": False},
    "Maharajah Jungle Trek": {"height_min": 0, "motion_sensitive": False},
    "Wildlife Express Train": {"height_min": 0, "motion_sensitive": False},
    "Flights of Wonder": {"height_min": 0, "motion_sensitive": False},
}


class DisneyIntelligenceEngine:
    """
    Disney Genie replacement with scoring algorithm and nudge logic.
    """

    def __init__(self):
        # ThemeParks.wiki API base
        self.api_base = "https://api.themeparks.wiki/v1"
        # Park IDs mapping - will be populated dynamically
        self.park_ids = {}
        self._load_park_ids()
        self.mt = None  # mousetools.MouseTools()  # For additional data - TODO: fix import

    def _load_park_ids(self):
        """Load park IDs from the API"""
        # For now, use hardcoded IDs
        self.park_ids = {
            'Disneyland': '7340550b-c14d-4def-80bb-acdb51d49a66',
            'DisneysCaliforniaAdventure': '832fcd76-4176-48a5-9c11-6b0c9b7607b1',
            'MagicKingdomWaltDisneyWorld': '75ea578a-adc8-4116-a54d-dccb60765ef9',
            'EpcotWaltDisneyWorld': '47f90d2c-e191-4239-a466-5892ef59a88b',
            'DisneysHollywoodStudios': '288747d1-8b4f-4a64-867e-ea7c9b27bad8',
            'DisneysAnimalKingdom': '1c84a229-8862-4648-8754-37433054b11b',
        }

    def get_ride_data(self, park_id: str) -> List[Dict]:
        """
        Fetch current ride wait times and status from ThemeParks.wiki API
        Falls back to mock data if API is unavailable
        """
        if park_id not in self.park_ids:
            return []
        
        entity_id = self.park_ids[park_id]
        url = f"{self.api_base}/entity/{entity_id}/live"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rides = []
            for item in data.get('liveData', []):
                if item.get('entityType') == 'ATTRACTION':
                    rides.append({
                        'id': item['id'],
                        'name': item['name'],
                        'wait_time': item.get('queue', {}).get('STANDBY', {}).get('waitTime', 0),
                        'status': item.get('status', 'Unknown'),
                        'location': (item.get('location', {}).get('latitude', 0), 
                                   item.get('location', {}).get('longitude', 0))
                    })
            return rides
        except Exception as e:
            print(f"API unavailable ({e}), using mock data for {park_id}")
            return self._get_mock_ride_data(park_id)

    def _get_mock_ride_data(self, park_id: str) -> List[Dict]:
        """
        Return mock ride data when API is unavailable.
        Uses realistic wait times and locations for demo purposes.
        """
        mock_data = {
            'MagicKingdomWaltDisneyWorld': [
                {'id': 'mk001', 'name': 'Space Mountain', 'wait_time': 45, 'status': 'OPERATING', 'location': (28.4187, -81.5812)},
                {'id': 'mk002', 'name': 'Big Thunder Mountain', 'wait_time': 30, 'status': 'OPERATING', 'location': (28.4202, -81.5854)},
                {'id': 'mk003', 'name': 'Splash Mountain', 'wait_time': 60, 'status': 'OPERATING', 'location': (28.4198, -81.5870)},
                {'id': 'mk004', 'name': 'Pirates of the Caribbean', 'wait_time': 25, 'status': 'OPERATING', 'location': (28.4180, -81.5839)},
                {'id': 'mk005', 'name': 'Haunted Mansion', 'wait_time': 35, 'status': 'OPERATING', 'location': (28.4205, -81.5824)},
            ],
            'EpcotWaltDisneyWorld': [
                {'id': 'ep001', 'name': 'Soarin\' Around the World', 'wait_time': 40, 'status': 'OPERATING', 'location': (28.3724, -81.5490)},
                {'id': 'ep002', 'name': 'Test Track', 'wait_time': 55, 'status': 'OPERATING', 'location': (28.3728, -81.5478)},
                {'id': 'ep003', 'name': 'Frozen Ever After', 'wait_time': 30, 'status': 'OPERATING', 'location': (28.3710, -81.5495)},
                {'id': 'ep004', 'name': 'Mission Space', 'wait_time': 45, 'status': 'OPERATING', 'location': (28.3732, -81.5470)},
                {'id': 'ep005', 'name': 'Spaceship Earth', 'wait_time': 20, 'status': 'OPERATING', 'location': (28.3752, -81.5490)},
            ],
            'Disneyland': [
                {'id': 'dl001', 'name': 'Space Mountain', 'wait_time': 50, 'status': 'OPERATING', 'location': (33.8121, -117.9190)},
                {'id': 'dl002', 'name': 'Matterhorn Bobsleds', 'wait_time': 40, 'status': 'OPERATING', 'location': (33.8132, -117.9185)},
                {'id': 'dl003', 'name': 'Pirates of the Caribbean', 'wait_time': 25, 'status': 'OPERATING', 'location': (33.8115, -117.9200)},
                {'id': 'dl004', 'name': 'Haunted Mansion', 'wait_time': 30, 'status': 'OPERATING', 'location': (33.8118, -117.9220)},
                {'id': 'dl005', 'name': 'Big Thunder Mountain Railroad', 'wait_time': 35, 'status': 'OPERATING', 'location': (33.8128, -117.9175)},
            ],
            'DisneysCaliforniaAdventure': [
                {'id': 'dca001', 'name': 'Radiator Springs Racers', 'wait_time': 70, 'status': 'OPERATING', 'location': (33.8045, -117.9215)},
                {'id': 'dca002', 'name': 'Incredicoaster', 'wait_time': 60, 'status': 'OPERATING', 'location': (33.8050, -117.9200)},
                {'id': 'dca003', 'name': 'Soarin\' Around the World', 'wait_time': 45, 'status': 'OPERATING', 'location': (33.8060, -117.9190)},
                {'id': 'dca004', 'name': 'Toy Story Midway Mania', 'wait_time': 40, 'status': 'OPERATING', 'location': (33.8040, -117.9220)},
                {'id': 'dca005', 'name': 'Guardians of the Galaxy - Mission: BREAKOUT!', 'wait_time': 50, 'status': 'OPERATING', 'location': (33.8055, -117.9185)},
            ],
            'DisneysHollywoodStudios': [
                {'id': 'hs001', 'name': 'Star Wars: Rise of the Resistance', 'wait_time': 90, 'status': 'OPERATING', 'location': (28.3530, -81.5610)},
                {'id': 'hs002', 'name': 'Millennium Falcon: Smugglers Run', 'wait_time': 65, 'status': 'OPERATING', 'location': (28.3525, -81.5605)},
                {'id': 'hs003', 'name': 'The Twilight Zone Tower of Terror', 'wait_time': 55, 'status': 'OPERATING', 'location': (28.3598, -81.5585)},
                {'id': 'hs004', 'name': 'Rock \'n\' Roller Coaster', 'wait_time': 50, 'status': 'OPERATING', 'location': (28.3600, -81.5580)},
                {'id': 'hs005', 'name': 'Slinky Dog Dash', 'wait_time': 45, 'status': 'OPERATING', 'location': (28.3570, -81.5600)},
            ],
            'DisneysAnimalKingdom': [
                {'id': 'ak001', 'name': 'Avatar Flight of Passage', 'wait_time': 80, 'status': 'OPERATING', 'location': (28.3575, -81.5910)},
                {'id': 'ak002', 'name': 'Expedition Everest', 'wait_time': 55, 'status': 'OPERATING', 'location': (28.3580, -81.5905)},
                {'id': 'ak003', 'name': 'Kilimanjaro Safaris', 'wait_time': 35, 'status': 'OPERATING', 'location': (28.3590, -81.5920)},
                {'id': 'ak004', 'name': 'DINOSAUR', 'wait_time': 40, 'status': 'OPERATING', 'location': (28.3570, -81.5915)},
                {'id': 'ak005', 'name': 'Na\'vi River Journey', 'wait_time': 30, 'status': 'OPERATING', 'location': (28.3578, -81.5908)},
            ],
        }
        
        return mock_data.get(park_id, [])

    def get_ride_average(self, ride_id: str) -> float:
        """
        Get 30-day rolling average wait time for a ride.
        Pulls from WaitTimeHistory table, or returns sensible default if no data.
        """
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            # Query last 30 days of wait times for this ride
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            from database import WaitTimeHistory
            history = db.query(WaitTimeHistory).filter(
                WaitTimeHistory.ride_id == ride_id,
                WaitTimeHistory.recorded_at >= thirty_days_ago
            ).all()
            
            if not history or len(history) == 0:
                # No historical data; return conservative default
                # This handles the first 30 days of operation
                return 25.0  # Default average of 25 minutes
            
            # Calculate average of wait times, excluding CLOSED status and None values
            valid_waits = [h.wait_time for h in history if h.status == "OPERATING" and h.wait_time is not None]
            if not valid_waits:
                return 25.0
            
            avg = sum(valid_waits) / len(valid_waits)
            return avg
        finally:
            db.close()

    def calculate_distance(self, loc1: Tuple[float, float], loc2: Tuple[float, float]) -> float:
        """
        Calculate walking distance between two GPS coordinates in feet.
        """
        # Haversine or simple Euclidean for park scale
        lat1, lon1 = loc1
        lat2, lon2 = loc2
        # Simplified calculation
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        distance = math.sqrt(dlat**2 + dlon**2) * 364000  # Rough feet conversion
        return distance

    def get_party_filter(self, ride_name: str, party_composition: Dict) -> float:
        """
        Check if ride meets party composition requirements.
        Returns 1.0 if all party members can ride, 0.0 if any member is restricted.
        
        party_composition: Dict with list of party members, e.g.:
        {
            "members": [
                {"name": "Parent", "height_inches": 70, "age": 45, "motion_sensitive": False},
                {"name": "Child", "height_inches": 38, "age": 6, "motion_sensitive": True}
            ]
        }
        """
        # Find matching ride in restrictions (case-insensitive, partial match)
        ride_restrictions = None
        for restricted_ride, restrictions in RIDE_RESTRICTIONS.items():
            if restricted_ride.lower() in ride_name.lower() or ride_name.lower() in restricted_ride.lower():
                ride_restrictions = restrictions
                break
        
        # If no restrictions found, assume ride is accessible to all
        if ride_restrictions is None:
            return 1.0
        
        # Get party members from the provided dictionary
        members = party_composition.get("members", [])
        if not members:
            return 1.0
        
        # Check each party member against ride restrictions
        for member in members:
            height = member.get("height_inches", 0)
            is_motion_sensitive = member.get("motion_sensitive", False)
            
            # Height restriction check
            height_min = ride_restrictions.get("height_min", 0)
            if height < height_min:
                return 0.0  # Member too short for ride
            
            # Motion sensitivity check
            if is_motion_sensitive and ride_restrictions.get("motion_sensitive", False):
                return 0.0  # Member can't ride due to motion sensitivity
        
        # All party members can safely ride
        return 1.0

    def calculate_score(self, ride: Dict, user_location: Tuple[float, float],
                       party_composition: Dict) -> float:
        """
        Calculate priority score S(a) for a ride.
        S(a) = (W_delta * 0.4) - (D_prox * 0.3) + (P_pref * 0.3)
        """
        # Handle None wait_time
        current_wait = ride.get('wait_time') or 0
        avg_wait = self.get_ride_average(ride['id'])
        w_delta = current_wait - avg_wait
        d_prox = self.calculate_distance(user_location, ride['location']) / 1000  # Normalize
        p_pref = self.get_party_filter(ride['name'], party_composition)

        score = (w_delta * 0.4) - (d_prox * 0.3) + (p_pref * 0.3)
        return max(0, score)  # Non-negative

    def get_recommendations(self, park_id: str, user_location: Tuple[float, float],
                           party_composition: Dict, top_n: int = 5) -> List[Dict]:
        """
        Get top ride recommendations based on scoring.
        """
        rides = self.get_ride_data(park_id)
        scored_rides = []
        for ride in rides:
            if ride['status'] == 'OPERATING':
                score = self.calculate_score(ride, user_location, party_composition)
                scored_rides.append({**ride, 'score': score})

        # Sort by score descending
        scored_rides.sort(key=lambda x: x['score'], reverse=True)
        return scored_rides[:top_n]

    def check_nudges(self, park_id: str, user_location: Tuple[float, float]) -> List[Dict]:
        """
        Check for nudge triggers: Must-Do rides with >30% drop or top rides <20min within 500ft.
        """
        db = SessionLocal()
        must_do_rides = db.query(MustDoRide).all()
        db.close()

        rides = self.get_ride_data(park_id)
        nudges = []

        for ride in rides:
            if ride['status'] == 'Operating':
                distance = self.calculate_distance(user_location, ride['location'])
                if distance <= 500:  # Within 500ft
                    if ride['wait_time'] < 20:
                        nudges.append({
                            'type': 'low_wait',
                            'ride': ride['name'],
                            'wait_time': ride['wait_time']
                        })
                    # Check Must-Do drop
                    for must_do in must_do_rides:
                        if must_do.ride_name.lower() in ride['name'].lower():
                            avg = self.get_ride_average(ride['id'])
                            if ride['wait_time'] < avg * 0.7:  # >30% drop
                                nudges.append({
                                    'type': 'must_do_drop',
                                    'ride': ride['name'],
                                    'wait_time': ride['wait_time'],
                                    'drop_percent': (avg - ride['wait_time']) / avg * 100
                                })

        return nudges

    def store_wait_times(self, park_id: str) -> None:
        """
        Fetch current ride wait times and store them in WaitTimeHistory.
        This should be called periodically (every 5 minutes) by a background scheduler.
        """
        from database import WaitTimeHistory
        
        db = SessionLocal()
        try:
            rides = self.get_ride_data(park_id)
            
            for ride in rides:
                # Create a history entry for each ride
                history_entry = WaitTimeHistory(
                    ride_id=ride['id'],
                    ride_name=ride['name'],
                    park_id=park_id,
                    wait_time=ride['wait_time'],
                    status=ride['status']
                )
                db.add(history_entry)
            
            db.commit()
            print(f"Stored {len(rides)} wait time records for park {park_id}")
        except Exception as e:
            print(f"Error storing wait times: {e}")
            db.rollback()
        finally:
            db.close()

    async def start_nudge_polling(self, park_id: str, user_location: Tuple[float, float],
                                 interval: int = 300):  # 5 minutes
        """
        Background task to poll for nudges every 5 minutes.
        TODO: Implement actual background task and notifications
        """
        import asyncio
        
        while True:
            nudges = self.check_nudges(park_id, user_location)
            if nudges:
                # TODO: Send web push notification
                print(f"Nudges: {nudges}")
            await asyncio.sleep(interval)