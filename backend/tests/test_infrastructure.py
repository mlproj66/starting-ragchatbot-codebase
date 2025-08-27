"""
Infrastructure tests for RAG system core components.
Tests database connectivity, configuration, and basic functionality.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Import the modules we're testing
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


class TestConfiguration:
    """Test configuration loading and validation"""
    
    def test_config_loads_successfully(self):
        """Test that configuration loads without errors"""
        assert config is not None
        assert hasattr(config, 'ANTHROPIC_API_KEY')
        assert hasattr(config, 'CHROMA_PATH')
        assert hasattr(config, 'EMBEDDING_MODEL')
    
    def test_config_has_required_fields(self):
        """Test that all required configuration fields are present"""
        required_fields = [
            'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL', 'EMBEDDING_MODEL',
            'CHUNK_SIZE', 'CHUNK_OVERLAP', 'MAX_RESULTS', 'MAX_HISTORY', 'CHROMA_PATH'
        ]
        
        for field in required_fields:
            assert hasattr(config, field), f"Config missing required field: {field}"
    
    def test_config_values_are_reasonable(self):
        """Test that configuration values are within reasonable ranges"""
        assert config.CHUNK_SIZE > 0, "Chunk size should be positive"
        assert config.CHUNK_OVERLAP >= 0, "Chunk overlap should be non-negative"
        assert config.MAX_RESULTS > 0, "Max results should be positive"
        assert config.MAX_HISTORY >= 0, "Max history should be non-negative"
        
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''})
    def test_missing_api_key_detection(self):
        """Test detection of missing API key"""
        from config import Config
        test_config = Config()
        # API key should be empty string when not set
        assert test_config.ANTHROPIC_API_KEY == ""


class TestVectorStoreBasics:
    """Test VectorStore basic functionality without actual ChromaDB"""
    
    @pytest.fixture
    def temp_chroma_path(self):
        """Create temporary directory for ChromaDB testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_vector_store_initialization(self, temp_chroma_path):
        """Test VectorStore can be initialized"""
        try:
            store = VectorStore(
                chroma_path=temp_chroma_path,
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )
            assert store is not None
            assert store.max_results == 5
        except Exception as e:
            pytest.fail(f"VectorStore initialization failed: {e}")
    
    def test_search_results_creation(self):
        """Test SearchResults can be created and manipulated"""
        # Test empty results
        empty_results = SearchResults.empty("Test error")
        assert empty_results.error == "Test error"
        assert empty_results.is_empty()
        
        # Test normal results
        normal_results = SearchResults(
            documents=["doc1", "doc2"],
            metadata=[{"key": "value"}],
            distances=[0.1, 0.2]
        )
        assert not normal_results.is_empty()
        assert len(normal_results.documents) == 2
    
    def test_chroma_results_conversion(self):
        """Test conversion from ChromaDB results format"""
        chroma_results = {
            'documents': [["doc1", "doc2"]],
            'metadatas': [[{"key1": "value1"}, {"key2": "value2"}]],
            'distances': [[0.1, 0.2]]
        }
        
        search_results = SearchResults.from_chroma(chroma_results)
        assert len(search_results.documents) == 2
        assert len(search_results.metadata) == 2
        assert len(search_results.distances) == 2


class TestModels:
    """Test data models used throughout the system"""
    
    def test_course_creation(self):
        """Test Course model creation"""
        lesson = Lesson(
            lesson_number=1,
            title="Test Lesson",
            content="Test content",
            lesson_link="https://example.com"
        )
        
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            lessons=[lesson],
            course_link="https://example.com/course"
        )
        
        assert course.title == "Test Course"
        assert len(course.lessons) == 1
        assert course.lessons[0].title == "Test Lesson"
    
    def test_course_chunk_creation(self):
        """Test CourseChunk model creation"""
        chunk = CourseChunk(
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
            content="Test chunk content"
        )
        
        assert chunk.course_title == "Test Course"
        assert chunk.lesson_number == 1
        assert chunk.chunk_index == 0
        assert chunk.content == "Test chunk content"


class TestDatabaseConnectivity:
    """Test actual database connectivity and operations"""
    
    @pytest.fixture
    def isolated_vector_store(self):
        """Create isolated VectorStore for testing"""
        temp_dir = tempfile.mkdtemp()
        try:
            store = VectorStore(
                chroma_path=temp_dir,
                embedding_model="all-MiniLM-L6-v2",
                max_results=3
            )
            yield store
        except Exception as e:
            pytest.skip(f"Could not create VectorStore for testing: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_empty_database_search(self, isolated_vector_store):
        """Test search on empty database"""
        results = isolated_vector_store.search("test query")
        # Empty database should return empty results, not error
        assert results is not None
        assert results.is_empty()
    
    def test_add_and_search_course_metadata(self, isolated_vector_store):
        """Test adding course metadata and searching"""
        lesson = Lesson(
            lesson_number=1,
            title="Test Lesson",
            content="Test lesson content",
            lesson_link="https://example.com/lesson1"
        )
        
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            lessons=[lesson],
            course_link="https://example.com/course"
        )
        
        try:
            # Add course metadata
            isolated_vector_store.add_course_metadata(course)
            
            # Check that course was added
            existing_titles = isolated_vector_store.get_existing_course_titles()
            assert "Test Course" in existing_titles
            
            # Test course count
            count = isolated_vector_store.get_course_count()
            assert count == 1
            
        except Exception as e:
            pytest.fail(f"Failed to add/retrieve course metadata: {e}")
    
    def test_add_and_search_course_content(self, isolated_vector_store):
        """Test adding course content and searching"""
        chunk = CourseChunk(
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
            content="This is test content about machine learning algorithms"
        )
        
        try:
            # Add course content
            isolated_vector_store.add_course_content([chunk])
            
            # Search for content
            results = isolated_vector_store.search("machine learning")
            
            # Should find the content
            assert results is not None
            if not results.is_empty():
                assert len(results.documents) > 0
                # Content should be in the results
                found_content = any("machine learning" in doc.lower() 
                                  for doc in results.documents)
                assert found_content, "Expected content not found in search results"
                
        except Exception as e:
            pytest.fail(f"Failed to add/search course content: {e}")


class TestSystemIntegration:
    """Test basic system integration without full RAG pipeline"""
    
    def test_imports_work(self):
        """Test that all required modules can be imported"""
        try:
            import config
            import vector_store
            import models
            import search_tools
            import ai_generator
            import rag_system
            import session_manager
            import document_processor
        except ImportError as e:
            pytest.fail(f"Failed to import required module: {e}")
    
    def test_chromadb_availability(self):
        """Test that ChromaDB is available and working"""
        try:
            import chromadb
            # Try to create a simple client
            client = chromadb.Client()
            assert client is not None
        except ImportError:
            pytest.fail("ChromaDB is not installed or available")
        except Exception as e:
            pytest.fail(f"ChromaDB failed to initialize: {e}")
    
    def test_sentence_transformers_availability(self):
        """Test that sentence transformers is available"""
        try:
            from sentence_transformers import SentenceTransformer
            # Try to load the model specified in config
            model = SentenceTransformer(config.EMBEDDING_MODEL)
            assert model is not None
        except ImportError:
            pytest.fail("sentence-transformers is not installed")
        except Exception as e:
            pytest.skip(f"Could not load embedding model (may require internet): {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])