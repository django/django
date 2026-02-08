"""
Tests for Session.__bool__ implementation.
"""
from django.contrib.sessions.backends.db import SessionStore


def test_bool():
    """Quick test to verify Session.__bool__ works."""
    # Empty session should be False
    session = SessionStore()
    assert bool(session) is False
    
    # Session with data should be True
    session["key"] = "value"
    assert bool(session) is True
    
    # Session after clear should be False
    session.clear()
    assert bool(session) is False
    
    print("✅ All Session.__bool__ tests passed!")


if __name__ == "__main__":
    test_bool()
