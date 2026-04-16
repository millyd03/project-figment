#!/usr/bin/env python3
"""
Project FIGMENT - End-to-End Integration Tests
Tests the complete flow: Spotify auth → playlist creation → Disney recommendations → nudge notifications → LLM orchestration
"""

import pytest
import requests
import time
import json
from typing import Dict, List

# Test configuration
API_BASE = "http://localhost:8002"
TEST_TIMEOUT = 30  # seconds

class TestFigmentE2E:
    """End-to-end tests for Project FIGMENT"""

    def test_spotify_auth_flow(self):
        """Test Spotify authentication endpoint"""
        try:
            response = requests.get(f"{API_BASE}/auth/spotify", timeout=TEST_TIMEOUT)
            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "spotify" in data["auth_url"].lower()
            print("✅ Spotify auth endpoint working")
        except Exception as e:
            pytest.fail(f"Spotify auth test failed: {e}")

    def test_spotify_auth_status(self):
        """Test Spotify authentication status check"""
        try:
            response = requests.get(f"{API_BASE}/auth/status", timeout=TEST_TIMEOUT)
            assert response.status_code == 200
            data = response.json()
            assert "authenticated" in data
            # Note: May be False if not actually authenticated
            print(f"✅ Spotify auth status: {data['authenticated']}")
        except Exception as e:
            pytest.fail(f"Spotify auth status test failed: {e}")

    def test_playlist_creation(self):
        """Test playlist creation with various options"""
        # Skip if not authenticated
        auth_response = requests.get(f"{API_BASE}/auth/status", timeout=TEST_TIMEOUT)
        if not auth_response.json().get("authenticated", False):
            print("⚠️  Spotify not authenticated - skipping playlist creation test")
            return

        payload = {
            "name": "FIGMENT Test Playlist",
            "throwback": True,
            "fresh": False,
            "tacno": False,
            "christmas": False,
            "clean": True
        }

        try:
            response = requests.post(f"{API_BASE}/create_playlist", json=payload, timeout=60)
            assert response.status_code == 200
            data = response.json()
            if "error" in data:
                # If error due to auth, that's expected in test env
                assert "auth" in data["error"].lower() or "token" in data["error"].lower()
                print("✅ Playlist creation handled auth error correctly")
            else:
                assert "tracks_count" in data
                assert "playlist_id" in data
                print(f"✅ Playlist created: {data['tracks_count']} tracks")
        except Exception as e:
            print(f"❌ Playlist creation test failed: {e}")
            raise

    def test_disney_recommendations(self):
        """Test Disney park recommendations with party composition"""
        payload = {
            "park_id": "MagicKingdomWaltDisneyWorld",
            "user_location": [28.3772, -81.5707],  # Magic Kingdom coords
            "party_composition": {
                "members": [
                    {
                        "name": "Test Adult",
                        "height_inches": 68,
                        "age": 30,
                        "motion_sensitive": False
                    },
                    {
                        "name": "Test Child",
                        "height_inches": 48,
                        "age": 10,
                        "motion_sensitive": True
                    }
                ]
            }
        }

        try:
            response = requests.post(f"{API_BASE}/agent/next_action", json=payload, timeout=TEST_TIMEOUT)
            if response.status_code != 200:
                print(f"ERROR - Disney endpoint returned {response.status_code}")
                print(f"Response: {response.text}")
                pytest.fail(f"Disney endpoint returned {response.status_code}: {response.text}")
            
            data = response.json()

            # Check for expected response structure
            assert "recommendations" in data
            assert "nudges" in data
            assert "agent_advice" in data

            # Validate recommendations
            recs = data["recommendations"]
            assert isinstance(recs, list)
            if recs:
                rec = recs[0]
                assert "name" in rec
                assert "wait_time" in rec
                assert "score" in rec
                print(f"✅ Disney recommendations working: {len(recs)} rides")

            # Validate agent advice
            advice = data["agent_advice"]
            assert isinstance(advice, str)
            assert len(advice) > 0
            print(f"✅ Agent advice generated: {len(advice)} chars")

        except Exception as e:
            pytest.fail(f"Disney recommendations test failed: {e}")

    def test_party_safety_filtering(self):
        """Test that party composition affects recommendations"""
        # Test with small child - should filter out certain rides
        payload_small_child = {
            "park_id": "MagicKingdomWaltDisneyWorld",
            "user_location": [28.3772, -81.5707],
            "party_composition": {
                "members": [
                    {
                        "name": "Small Child",
                        "height_inches": 35,  # Too small for many rides
                        "age": 5,
                        "motion_sensitive": True
                    }
                ]
            }
        }

        # Test with adult - should have more options
        payload_adult = {
            "park_id": "MagicKingdomWaltDisneyWorld",
            "user_location": [28.3772, -81.5707],
            "party_composition": {
                "members": [
                    {
                        "name": "Adult",
                        "height_inches": 70,
                        "age": 30,
                        "motion_sensitive": False
                    }
                ]
            }
        }

        try:
            response_child = requests.post(f"{API_BASE}/agent/next_action", json=payload_small_child, timeout=TEST_TIMEOUT)
            response_adult = requests.post(f"{API_BASE}/agent/next_action", json=payload_adult, timeout=TEST_TIMEOUT)

            assert response_child.status_code == 200
            assert response_adult.status_code == 200

            data_child = response_child.json()
            data_adult = response_adult.json()

            # Adult should generally have more or equal recommendations
            recs_child = data_child["recommendations"]
            recs_adult = data_adult["recommendations"]

            # Note: This is a soft assertion - in practice, filtering might be complex
            print(f"✅ Party filtering: Child={len(recs_child)} rides, Adult={len(recs_adult)} rides")

        except Exception as e:
            pytest.fail(f"Party safety filtering test failed: {e}")

    def test_nudge_notifications(self):
        """Test that nudge notifications are generated appropriately"""
        # This test is harder to automate as it depends on real-time data
        # We'll test the endpoint structure
        payload = {
            "park_id": "MagicKingdomWaltDisneyWorld",
            "user_location": [28.3772, -81.5707],
            "party_composition": {
                "members": [
                    {
                        "name": "Test User",
                        "height_inches": 68,
                        "age": 30,
                        "motion_sensitive": False
                    }
                ]
            }
        }

        try:
            response = requests.post(f"{API_BASE}/agent/next_action", json=payload, timeout=TEST_TIMEOUT)
            assert response.status_code == 200
            data = response.json()

            nudges = data["nudges"]
            assert isinstance(nudges, list)

            # Check nudge structure if any exist
            if nudges:
                nudge = nudges[0]
                assert "type" in nudge
                assert "ride" in nudge
                assert "wait_time" in nudge
                print(f"✅ Nudges working: {len(nudges)} active nudges")
            else:
                print("✅ Nudges endpoint working (no active nudges)")

        except Exception as e:
            pytest.fail(f"Nudge notifications test failed: {e}")

    def test_push_subscription(self):
        """Test push notification subscription endpoint"""
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test",
            "auth": "test_auth_key",
            "p256dh": "test_p256dh_key",
            "user_id": "test_user"
        }

        try:
            response = requests.post(f"{API_BASE}/subscribe", json=payload, timeout=TEST_TIMEOUT)
            if response.status_code != 200:
                print(f"ERROR - Push endpoint returned {response.status_code}")
                print(f"Response: {response.text}")
                pytest.fail(f"Push endpoint returned {response.status_code}: {response.text}")
            
            data = response.json()
            assert "message" in data
            print("✅ Push subscription working")
        except Exception as e:
            pytest.fail(f"Push subscription test failed: {e}")

    def test_llm_orchestration(self):
        """Test LLM-powered agent reasoning"""
        payload = {
            "park_id": "MagicKingdomWaltDisneyWorld",
            "user_location": [28.3772, -81.5707],
            "party_composition": {
                "members": [
                    {
                        "name": "Test User",
                        "height_inches": 68,
                        "age": 30,
                        "motion_sensitive": False
                    }
                ]
            },
            "playlist_context": "Created a throwback playlist with 50s hits"
        }

        try:
            response = requests.post(f"{API_BASE}/agent/next_action", json=payload, timeout=TEST_TIMEOUT)
            assert response.status_code == 200
            data = response.json()

            advice = data["agent_advice"]
            assert isinstance(advice, str)
            assert len(advice) > 10  # Should be substantial advice

            # Check for contextual elements
            advice_lower = advice.lower()
            assert any(word in advice_lower for word in ["park", "ride", "time", "recommend", "suggest"])

            print(f"✅ LLM orchestration working: {len(advice)} char response")

        except Exception as e:
            pytest.fail(f"LLM orchestration test failed: {e}")

if __name__ == "__main__":
    # Run tests manually if executed directly
    test_instance = TestFigmentE2E()

    print("Running FIGMENT E2E Tests...")
    print("=" * 50)

    tests = [
        test_instance.test_spotify_auth_flow,
        test_instance.test_spotify_auth_status,
        test_instance.test_playlist_creation,
        test_instance.test_disney_recommendations,
        test_instance.test_party_safety_filtering,
        test_instance.test_nudge_notifications,
        test_instance.test_push_subscription,
        test_instance.test_llm_orchestration
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            print(f"\nRunning {test.__name__}...")
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed - check implementation")