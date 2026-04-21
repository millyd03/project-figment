from disney_engine import DisneyIntelligenceEngine
de = DisneyIntelligenceEngine()
rides = de.get_ride_data('MagicKingdomWaltDisneyWorld')
print(f'Total rides: {len(rides)}')
operating = [r for r in rides if r.get('status') == 'OPERATING']
print(f'Operating rides: {len(operating)}')
if operating:
    print(f'First operating: {operating[0]}')
if rides:
    print(f'First ride: {rides[0]}')
    statuses = list(set(r.get('status') for r in rides))
    print(f'All statuses: {statuses}')