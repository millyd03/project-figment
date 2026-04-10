import themeparks
import mousetools
from typing import List, Dict, Optional, Tuple
import math
import asyncio
from database import SessionLocal, MustDoRide, SessionState

class DisneyIntelligenceEngine:
    """
    Disney Genie replacement with scoring algorithm and nudge logic.
    """

    def __init__(self):
        self.tp_api = themeparks.api()  # ThemeParks.wiki API
        self.mt = mousetools.MouseTools()  # MouseTools for additional data

    def get_ride_data(self, park_id: str) -> List[Dict]:
        """
        Fetch current ride wait times and status from ThemeParks.wiki
        """
        park = self.tp_api.get_park(park_id)
        rides = []
        for ride in park.rides:
            rides.append({
                'id': ride.id,
                'name': ride.name,
                'wait_time': ride.wait_time,
                'status': ride.status,
                'location': ride.location  # GPS coords
            })
        return rides

    def get_ride_average(self, ride_id: str) -> float:
        """
        Get 30-day rolling average wait time for a ride.
        TODO: Implement historical data fetching
        """
        # Placeholder: return current wait as average
        return 30.0  # minutes

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
        Returns 1.0 if ok, 0.0 if any member can't ride.
        """
        # TODO: Implement height and age restrictions lookup
        # For now, assume all ok
        return 1.0

    def calculate_score(self, ride: Dict, user_location: Tuple[float, float],
                       party_composition: Dict) -> float:
        """
        Calculate priority score S(a) for a ride.
        S(a) = (W_delta * 0.4) - (D_prox * 0.3) + (P_pref * 0.3)
        """
        w_delta = ride['wait_time'] - self.get_ride_average(ride['id'])
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
            if ride['status'] == 'Operating':
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

    async def start_nudge_polling(self, park_id: str, user_location: Tuple[float, float],
                                 interval: int = 300):  # 5 minutes
        """
        Background task to poll for nudges every 5 minutes.
        TODO: Implement actual background task and notifications
        """
        while True:
            nudges = self.check_nudges(park_id, user_location)
            if nudges:
                # TODO: Send web push notification
                print(f"Nudges: {nudges}")
            await asyncio.sleep(interval)