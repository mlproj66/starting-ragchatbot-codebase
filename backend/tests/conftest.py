import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import List, Dict, Any
import tempfile
import shutil

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

@pytest.fixture
def mock_rag_system():
    """Mock RAG system for API testing"""
    mock_system = MagicMock()
    
    # Mock query method
    mock_system.query.return_value = (
        "This is a test answer about machine learning concepts.", 
        ["Test Course - Lesson 1", "Test Course - Lesson 2"]
    )
    
    # Mock get_course_analytics method
    mock_system.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course", "Advanced Test Course"]
    }
    
    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.create_session.return_value = "test-session-123"
    mock_system.session_manager = mock_session_manager
    
    return mock_system

@pytest.fixture
def test_app(mock_rag_system):
    """Create test FastAPI app with mocked dependencies"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict, Any
    import os
    
    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")
    
    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Define models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    # Define test endpoints (same as production but with mocked dependencies)
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

@pytest.fixture 
def test_client(test_app):
    """Create test client for FastAPI app"""
    return TestClient(test_app)

@pytest.fixture
def temp_frontend_dir():
    """Create temporary frontend directory for static file testing"""
    temp_dir = tempfile.mkdtemp()
    
    # Create basic frontend files
    index_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test RAG System</title></head>
    <body>
        <h1>Test RAG System</h1>
        <div id="app"></div>
    </body>
    </html>
    """
    
    with open(os.path.join(temp_dir, "index.html"), "w") as f:
        f.write(index_html)
    
    with open(os.path.join(temp_dir, "style.css"), "w") as f:
        f.write("body { font-family: Arial, sans-serif; }")
        
    with open(os.path.join(temp_dir, "script.js"), "w") as f:
        f.write("console.log('Test RAG System loaded');")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def full_test_app_with_static(mock_rag_system, temp_frontend_dir):
    """Create test FastAPI app with static file serving"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict, Any
    
    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test with Static", root_path="")
    
    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Define models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    # Define endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    # Mount static files
    app.mount("/", StaticFiles(directory=temp_frontend_dir, html=True), name="static")
    
    return app

@pytest.fixture
def full_test_client(full_test_app_with_static):
    """Create test client with static file serving"""
    return TestClient(full_test_app_with_static)

@pytest.fixture
def sample_api_responses():
    """Sample API responses for testing"""
    return {
        "query_response": {
            "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn automatically.",
            "sources": [
                "Introduction to ML - Lesson 1", 
                "ML Fundamentals - Lesson 2"
            ],
            "session_id": "test-session-456"
        },
        "courses_response": {
            "total_courses": 3,
            "course_titles": [
                "Introduction to Machine Learning",
                "Advanced Python Programming", 
                "Data Science Fundamentals"
            ]
        }
    }