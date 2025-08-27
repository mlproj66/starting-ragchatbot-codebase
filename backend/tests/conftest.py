import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    from dataclasses import dataclass
    
    @dataclass
    class MockConfig:
        ANTHROPIC_API_KEY: str = "test-api-key"
        ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
        EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
        CHUNK_SIZE: int = 800
        CHUNK_OVERLAP: int = 100
        MAX_RESULTS: int = 5
        MAX_HISTORY: int = 2
        CHROMA_PATH: str = "./test_chroma_db"
    
    return MockConfig()

@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing"""
    from unittest.mock import MagicMock
    from vector_store import SearchResults
    
    mock_store = MagicMock()
    
    # Mock successful search results
    mock_store.search.return_value = SearchResults(
        documents=["Test course content about machine learning"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.5]
    )
    
    mock_store._resolve_course_name.return_value = "Test Course"
    mock_store.get_all_courses_metadata.return_value = [{
        "title": "Test Course",
        "instructor": "Test Instructor",
        "course_link": "https://example.com/course",
        "lessons": [
            {"lesson_number": 1, "lesson_title": "Introduction", "lesson_link": "https://example.com/lesson1"}
        ]
    }]
    
    return mock_store

@pytest.fixture
def sample_course_data():
    """Sample course data for testing"""
    return {
        "title": "Test Course",
        "instructor": "Test Instructor", 
        "course_link": "https://example.com/course",
        "lessons": [
            {
                "lesson_number": 1,
                "lesson_title": "Introduction to Testing",
                "lesson_link": "https://example.com/lesson1"
            },
            {
                "lesson_number": 2,
                "lesson_title": "Advanced Testing Concepts",
                "lesson_link": "https://example.com/lesson2"
            }
        ]
    }