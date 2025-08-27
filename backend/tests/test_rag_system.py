"""
Integration tests for RAGSystem functionality.
Tests end-to-end query processing and component integration.
"""

import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch, Mock
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


@dataclass
class MockConfig:
    """Mock configuration for testing"""
    ANTHROPIC_API_KEY: str = "test-api-key"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


class TestRAGSystemInitialization:
    """Test RAGSystem initialization and component setup"""
    
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    def test_rag_system_initialization(self, mock_session_mgr, mock_ai_gen, mock_vector_store, mock_doc_proc):
        """Test RAGSystem initializes all components correctly"""
        config = MockConfig()
        
        # Create RAGSystem
        rag_system = RAGSystem(config)
        
        # Verify all components were initialized
        mock_doc_proc.assert_called_once_with(config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        mock_vector_store.assert_called_once_with(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        mock_ai_gen.assert_called_once_with(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
        mock_session_mgr.assert_called_once_with(config.MAX_HISTORY)
        
        # Verify components are accessible
        assert rag_system.document_processor is not None
        assert rag_system.vector_store is not None
        assert rag_system.ai_generator is not None
        assert rag_system.session_manager is not None
        assert rag_system.tool_manager is not None
        assert rag_system.search_tool is not None
        assert rag_system.outline_tool is not None
    
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    def test_tools_registration(self, mock_session_mgr, mock_ai_gen, mock_vector_store, mock_doc_proc):
        """Test that tools are properly registered in the system"""
        config = MockConfig()
        rag_system = RAGSystem(config)
        
        # Check tool definitions
        tool_definitions = rag_system.tool_manager.get_tool_definitions()
        tool_names = [tool["name"] for tool in tool_definitions]
        
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
        assert len(tool_definitions) == 2


class TestRAGSystemQueryProcessing:
    """Test RAGSystem query processing functionality"""
    
    def create_mock_rag_system(self):
        """Create RAGSystem with mocked components"""
        config = MockConfig()
        
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm:
            
            # Setup mock vector store
            mock_vector_store = MagicMock()
            mock_vs.return_value = mock_vector_store
            
            # Setup mock AI generator
            mock_ai_generator = MagicMock()
            mock_ai.return_value = mock_ai_generator
            
            # Setup mock session manager
            mock_session_manager = MagicMock()
            mock_sm.return_value = mock_session_manager
            
            rag_system = RAGSystem(config)
            
            return rag_system, mock_vector_store, mock_ai_generator, mock_session_manager
    
    def test_successful_query_without_session(self):
        """Test successful query processing without session context"""
        rag_system, mock_vector_store, mock_ai_generator, mock_session_manager = self.create_mock_rag_system()
        
        # Mock AI generator response
        mock_ai_generator.generate_response.return_value = "Machine learning is a subset of artificial intelligence."
        
        # Mock sources from tool manager
        with patch.object(rag_system.tool_manager, 'get_last_sources') as mock_sources:
            mock_sources.return_value = [{"text": "AI Course - Lesson 1", "url": "https://example.com/lesson1"}]
            
            # Execute query
            response, sources = rag_system.query("What is machine learning?")
            
            # Verify response
            assert response == "Machine learning is a subset of artificial intelligence."
            assert len(sources) == 1
            assert sources[0]["text"] == "AI Course - Lesson 1"
            
            # Verify AI generator was called correctly
            mock_ai_generator.generate_response.assert_called_once()
            call_args = mock_ai_generator.generate_response.call_args[1]
            assert "What is machine learning?" in call_args["query"]
            assert call_args["conversation_history"] is None
            assert call_args["tools"] is not None
            assert call_args["tool_manager"] is not None
    
    def test_query_with_session_context(self):
        """Test query processing with session context"""
        rag_system, mock_vector_store, mock_ai_generator, mock_session_manager = self.create_mock_rag_system()
        
        # Mock session history
        mock_session_manager.get_conversation_history.return_value = "Previous conversation context"
        mock_ai_generator.generate_response.return_value = "Follow-up response about ML."
        
        # Mock sources
        with patch.object(rag_system.tool_manager, 'get_last_sources') as mock_sources:
            mock_sources.return_value = []
            
            # Execute query with session
            response, sources = rag_system.query("Tell me more", session_id="test-session")
            
            # Verify session history was retrieved
            mock_session_manager.get_conversation_history.assert_called_once_with("test-session")
            
            # Verify AI generator received history
            call_args = mock_ai_generator.generate_response.call_args[1]
            assert call_args["conversation_history"] == "Previous conversation context"
            
            # Verify session was updated
            mock_session_manager.add_exchange.assert_called_once_with(
                "test-session", 
                "Answer this question about course materials: Tell me more",
                "Follow-up response about ML."
            )
    
    def test_query_error_handling(self):
        """Test query error handling"""
        rag_system, mock_vector_store, mock_ai_generator, mock_session_manager = self.create_mock_rag_system()
        
        # Mock AI generator to raise exception
        mock_ai_generator.generate_response.side_effect = Exception("API Error: Invalid API key")
        
        # Query should propagate the exception
        with pytest.raises(Exception) as exc_info:
            rag_system.query("Test query")
        
        assert "API Error: Invalid API key" in str(exc_info.value)
    
    def test_sources_reset_after_query(self):
        """Test that sources are reset after each query"""
        rag_system, mock_vector_store, mock_ai_generator, mock_session_manager = self.create_mock_rag_system()
        
        mock_ai_generator.generate_response.return_value = "Test response"
        
        with patch.object(rag_system.tool_manager, 'get_last_sources') as mock_get_sources, \
             patch.object(rag_system.tool_manager, 'reset_sources') as mock_reset_sources:
            
            mock_get_sources.return_value = [{"text": "Test Source", "url": None}]
            
            # Execute query
            response, sources = rag_system.query("Test query")
            
            # Verify sources were retrieved and reset
            mock_get_sources.assert_called_once()
            mock_reset_sources.assert_called_once()


class TestRAGSystemDocumentManagement:
    """Test RAGSystem document loading and management"""
    
    def create_mock_rag_system_for_docs(self):
        """Create RAGSystem with mocked components for document testing"""
        config = MockConfig()
        
        with patch('rag_system.DocumentProcessor') as mock_dp, \
             patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            # Setup mock document processor
            mock_doc_processor = MagicMock()
            mock_dp.return_value = mock_doc_processor
            
            # Setup mock vector store
            mock_vector_store = MagicMock()
            mock_vs.return_value = mock_vector_store
            
            rag_system = RAGSystem(config)
            
            return rag_system, mock_doc_processor, mock_vector_store
    
    def test_add_course_document_success(self):
        """Test successful course document addition"""
        rag_system, mock_doc_processor, mock_vector_store = self.create_mock_rag_system_for_docs()
        
        # Mock course and chunks
        mock_lesson = Lesson(
            lesson_number=1,
            title="Introduction",
            content="Lesson content",
            lesson_link="https://example.com/lesson1"
        )
        mock_course = Course(
            title="Test Course",
            instructor="Test Instructor",
            lessons=[mock_lesson],
            course_link="https://example.com/course"
        )
        mock_chunks = [
            CourseChunk("Test Course", 1, 0, "Chunk content")
        ]
        
        mock_doc_processor.process_course_document.return_value = (mock_course, mock_chunks)
        
        # Add document
        course, chunk_count = rag_system.add_course_document("test_file.pdf")
        
        # Verify processing
        mock_doc_processor.process_course_document.assert_called_once_with("test_file.pdf")
        mock_vector_store.add_course_metadata.assert_called_once_with(mock_course)
        mock_vector_store.add_course_content.assert_called_once_with(mock_chunks)
        
        assert course.title == "Test Course"
        assert chunk_count == 1
    
    def test_add_course_document_error(self):
        """Test course document addition error handling"""
        rag_system, mock_doc_processor, mock_vector_store = self.create_mock_rag_system_for_docs()
        
        # Mock processing error
        mock_doc_processor.process_course_document.side_effect = Exception("File not found")
        
        # Add document should handle error gracefully
        course, chunk_count = rag_system.add_course_document("nonexistent.pdf")
        
        assert course is None
        assert chunk_count == 0
    
    def test_add_course_folder_with_existing_courses(self):
        """Test adding course folder with existing courses"""
        rag_system, mock_doc_processor, mock_vector_store = self.create_mock_rag_system_for_docs()
        
        # Mock existing courses
        mock_vector_store.get_existing_course_titles.return_value = ["Existing Course"]
        
        # Mock new course
        mock_lesson = Lesson(1, "New Lesson", "Content", "link")
        mock_course = Course("New Course", "Instructor", [mock_lesson], "link")
        mock_chunks = [CourseChunk("New Course", 1, 0, "Content")]
        
        mock_doc_processor.process_course_document.return_value = (mock_course, mock_chunks)
        
        with patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile:
            
            mock_exists.return_value = True
            mock_listdir.return_value = ["new_course.pdf"]
            mock_isfile.return_value = True
            
            # Add folder
            courses, chunks = rag_system.add_course_folder("test_folder")
            
            # Verify new course was added
            assert courses == 1
            assert chunks == 1
            mock_vector_store.add_course_metadata.assert_called_once()
            mock_vector_store.add_course_content.assert_called_once()
    
    def test_get_course_analytics(self):
        """Test course analytics functionality"""
        rag_system, mock_doc_processor, mock_vector_store = self.create_mock_rag_system_for_docs()
        
        # Mock analytics data
        mock_vector_store.get_course_count.return_value = 3
        mock_vector_store.get_existing_course_titles.return_value = ["Course 1", "Course 2", "Course 3"]
        
        analytics = rag_system.get_course_analytics()
        
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Course 1" in analytics["course_titles"]


class TestRAGSystemIntegration:
    """Integration tests with minimal mocking"""
    
    def test_tool_manager_integration(self):
        """Test that tool manager correctly integrates tools"""
        config = MockConfig()
        
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'):
            
            # Setup mock vector store
            mock_vector_store = MagicMock()
            mock_vs.return_value = mock_vector_store
            
            rag_system = RAGSystem(config)
            
            # Test tool execution through manager
            mock_results = SearchResults(
                documents=["Test content"],
                metadata=[{"course_title": "Test Course", "lesson_number": 1}],
                distances=[0.1]
            )
            mock_vector_store.search.return_value = mock_results
            
            # Execute search tool
            result = rag_system.tool_manager.execute_tool(
                "search_course_content",
                query="test query"
            )
            
            assert "Test Course" in result
            assert "Test content" in result
    
    def test_end_to_end_query_simulation(self):
        """Test end-to-end query simulation with mocked components"""
        config = MockConfig()
        
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_sm:
            
            # Setup detailed mocks
            mock_vector_store = MagicMock()
            mock_vs.return_value = mock_vector_store
            
            mock_ai_generator = MagicMock()
            mock_ai.return_value = mock_ai_generator
            
            mock_session_manager = MagicMock()
            mock_sm.return_value = mock_session_manager
            mock_session_manager.create_session.return_value = "test-session-123"
            
            # Mock successful tool execution flow
            mock_results = SearchResults(
                documents=["Machine learning is a method of data analysis..."],
                metadata=[{"course_title": "AI Fundamentals", "lesson_number": 2}],
                distances=[0.2]
            )
            mock_vector_store.search.return_value = mock_results
            mock_vector_store.get_lesson_link.return_value = "https://example.com/ai-lesson2"
            
            # Mock AI response
            mock_ai_generator.generate_response.return_value = "Machine learning is a powerful technique for analyzing data and making predictions."
            
            rag_system = RAGSystem(config)
            
            # Execute query
            response, sources = rag_system.query("What is machine learning?", session_id="test-session")
            
            # Verify complete flow
            assert response == "Machine learning is a powerful technique for analyzing data and making predictions."
            assert len(sources) == 1
            assert sources[0]["text"] == "AI Fundamentals - Lesson 2"
            assert sources[0]["url"] == "https://example.com/ai-lesson2"
            
            # Verify AI generator was called with correct parameters
            mock_ai_generator.generate_response.assert_called_once()
            call_args = mock_ai_generator.generate_response.call_args[1]
            assert "tools" in call_args
            assert "tool_manager" in call_args
            assert len(call_args["tools"]) == 2  # search_course_content + get_course_outline


if __name__ == "__main__":
    pytest.main([__file__, "-v"])