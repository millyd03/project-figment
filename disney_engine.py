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
            'MagicKingdomWaltDisneyWorld': '75ea578a-adc8-4116-a54d-dccb60765ef9',
            'EpcotWaltDisneyWorld': '47f90d2c-e191-4239-a466-5892ef59a88b',
        }

    def get_ride_data(self, park_id: str) -> List[Dict]:
        """
        Fetch current ride wait times and status from ThemeParks.wiki API
        """
        if park_id not in self.park_ids:
            return []
        
        entity_id = self.park_ids[park_id]
        url = f"{self.api_base}/entity/{entity_id}/live"
        
        try:
            response = requests.get(url)
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
            print(f"Error fetching ride data: {e}")
            return []

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