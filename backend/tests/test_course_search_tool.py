"""
Unit tests for CourseSearchTool functionality.
Tests the execute method and integration with VectorStore.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolDefinition:
    """Test CourseSearchTool tool definition and interface"""
    
    def test_tool_definition_structure(self, mock_vector_store):
        """Test that tool definition has correct structure"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()
        
        # Check required fields
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition
        
        # Check tool name
        assert definition["name"] == "search_course_content"
        
        # Check input schema structure
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        
        # Check required fields
        assert "query" in schema["required"]
        
        # Check optional fields exist
        properties = schema["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties
        
        # Check field types
        assert properties["query"]["type"] == "string"
        assert properties["course_name"]["type"] == "string"
        assert properties["lesson_number"]["type"] == "integer"
    
    def test_tool_implements_interface(self, mock_vector_store):
        """Test that CourseSearchTool implements the Tool interface correctly"""
        tool = CourseSearchTool(mock_vector_store)
        
        # Should have required methods
        assert hasattr(tool, 'get_tool_definition')
        assert hasattr(tool, 'execute')
        assert callable(tool.get_tool_definition)
        assert callable(tool.execute)


class TestCourseSearchToolExecution:
    """Test CourseSearchTool execute method with various scenarios"""
    
    def test_successful_search_with_results(self, mock_vector_store):
        """Test successful search that returns results"""
        # Setup mock to return successful results
        mock_results = SearchResults(
            documents=["This is content about machine learning algorithms"],
            metadata=[{"course_title": "AI Course", "lesson_number": 1}],
            distances=[0.3]
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("machine learning")
        
        # Check that search was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="machine learning",
            course_name=None,
            lesson_number=None
        )
        
        # Check result formatting
        assert result is not None
        assert isinstance(result, str)
        assert "AI Course" in result
        assert "Lesson 1" in result
        assert "machine learning algorithms" in result
        
        # Check that sources were tracked
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "AI Course - Lesson 1"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson1"
    
    def test_search_with_course_filter(self, mock_vector_store):
        """Test search with course name filter"""
        mock_results = SearchResults(
            documents=["Course specific content"],
            metadata=[{"course_title": "Specific Course", "lesson_number": 2}],
            distances=[0.2]
        )
        mock_vector_store.search.return_value = mock_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query", course_name="Specific Course")
        
        # Check that search was called with course filter
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="Specific Course",
            lesson_number=None
        )
        
        assert "Specific Course" in result
    
    def test_search_with_lesson_filter(self, mock_vector_store):
        """Test search with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson specific content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 3}],
            distances=[0.1]
        )
        mock_vector_store.search.return_value = mock_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query", lesson_number=3)
        
        # Check that search was called with lesson filter
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name=None,
            lesson_number=3
        )
        
        assert "Lesson 3" in result
    
    def test_search_with_both_filters(self, mock_vector_store):
        """Test search with both course and lesson filters"""
        mock_results = SearchResults(
            documents=["Filtered content"],
            metadata=[{"course_title": "Filter Course", "lesson_number": 5}],
            distances=[0.4]
        )
        mock_vector_store.search.return_value = mock_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query", course_name="Filter Course", lesson_number=5)
        
        # Check that search was called with both filters
        mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="Filter Course",
            lesson_number=5
        )
        
        assert "Filter Course" in result
        assert "Lesson 5" in result
    
    def test_empty_search_results(self, mock_vector_store):
        """Test handling of empty search results"""
        # Setup mock to return empty results
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("nonexistent content")
        
        # Should return appropriate message
        assert "No relevant content found" in result
        
        # Sources should be empty
        assert len(tool.last_sources) == 0
    
    def test_empty_results_with_filters(self, mock_vector_store):
        """Test empty results message includes filter information"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test", course_name="Nonexistent Course", lesson_number=99)
        
        # Should mention the filters in the message
        assert "No relevant content found" in result
        assert "Nonexistent Course" in result
        assert "lesson 99" in result
    
    def test_search_error_handling(self, mock_vector_store):
        """Test handling of search errors"""
        # Setup mock to return error results
        error_results = SearchResults.empty("Database connection failed")
        mock_vector_store.search.return_value = error_results
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test query")
        
        # Should return the error message
        assert result == "Database connection failed"
        
        # Sources should be empty on error
        assert len(tool.last_sources) == 0
    
    def test_multiple_results_formatting(self, mock_vector_store):
        """Test formatting of multiple search results"""
        mock_results = SearchResults(
            documents=[
                "First document content about Python",
                "Second document content about JavaScript"
            ],
            metadata=[
                {"course_title": "Programming Course", "lesson_number": 1},
                {"course_title": "Web Development", "lesson_number": 2}
            ],
            distances=[0.2, 0.3]
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/prog1",
            "https://example.com/web2"
        ]
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("programming")
        
        # Check that both results are included
        assert "Programming Course" in result
        assert "Web Development" in result
        assert "Python" in result
        assert "JavaScript" in result
        assert "Lesson 1" in result
        assert "Lesson 2" in result
        
        # Check sources tracking for multiple results
        assert len(tool.last_sources) == 2
    
    def test_missing_metadata_handling(self, mock_vector_store):
        """Test handling of results with missing metadata"""
        mock_results = SearchResults(
            documents=["Content with incomplete metadata"],
            metadata=[{"course_title": "Test Course"}],  # Missing lesson_number
            distances=[0.1]
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_course_link.return_value = "https://example.com/course"
        
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute("test")
        
        # Should handle missing lesson number gracefully
        assert "Test Course" in result
        assert result is not None
        
        # Should still track sources
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course"


class TestToolManager:
    """Test ToolManager functionality with CourseSearchTool"""
    
    def test_tool_registration(self, mock_vector_store):
        """Test registering CourseSearchTool with ToolManager"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        
        manager.register_tool(tool)
        
        # Check tool is registered
        definitions = manager.get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
    
    def test_tool_execution_through_manager(self, mock_vector_store):
        """Test executing CourseSearchTool through ToolManager"""
        mock_results = SearchResults(
            documents=["Manager test content"],
            metadata=[{"course_title": "Manager Course", "lesson_number": 1}],
            distances=[0.1]
        )
        mock_vector_store.search.return_value = mock_results
        
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        
        result = manager.execute_tool("search_course_content", query="test")
        
        assert "Manager Course" in result
        assert "Manager test content" in result
    
    def test_sources_retrieval_through_manager(self, mock_vector_store):
        """Test retrieving sources through ToolManager"""
        mock_results = SearchResults(
            documents=["Source test content"],
            metadata=[{"course_title": "Source Course", "lesson_number": 1}],
            distances=[0.1]
        )
        mock_vector_store.search.return_value = mock_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/source1"
        
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)
        
        # Execute search to populate sources
        manager.execute_tool("search_course_content", query="test")
        
        # Get sources through manager
        sources = manager.get_last_sources()
        assert len(sources) == 1
        assert sources[0]["text"] == "Source Course - Lesson 1"
        assert sources[0]["url"] == "https://example.com/source1"
        
        # Test sources reset
        manager.reset_sources()
        sources_after_reset = manager.get_last_sources()
        assert len(sources_after_reset) == 0
    
    def test_nonexistent_tool_execution(self, mock_vector_store):
        """Test executing non-existent tool through ToolManager"""
        manager = ToolManager()
        
        result = manager.execute_tool("nonexistent_tool", query="test")
        assert "Tool 'nonexistent_tool' not found" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])