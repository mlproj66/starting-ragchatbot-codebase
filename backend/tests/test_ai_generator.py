"""
Unit tests for AIGenerator functionality.
Tests AI tool calling, system prompt compliance, and error handling.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, Mock
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool


class TestAIGeneratorInitialization:
    """Test AIGenerator initialization and configuration"""
    
    def test_initialization_success(self):
        """Test AIGenerator initializes successfully"""
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        
        assert generator is not None
        assert generator.model == "claude-sonnet-4-20250514"
        assert generator.base_params["model"] == "claude-sonnet-4-20250514"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800
    
    def test_system_prompt_contains_tool_instructions(self):
        """Test that system prompt includes tool usage instructions"""
        prompt = AIGenerator.SYSTEM_PROMPT
        
        # Check for tool-related instructions
        assert "search_course_content" in prompt
        assert "get_course_outline" in prompt
        assert "tool" in prompt.lower()
        assert "course" in prompt.lower()
        
        # Check for response guidelines
        assert "brief" in prompt.lower() or "concise" in prompt.lower()
        assert "educational" in prompt.lower()


class TestAIGeneratorResponseGeneration:
    """Test AIGenerator response generation without tool calls"""
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_simple_response_without_tools(self, mock_anthropic):
        """Test generating response without tool calls"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock response without tool use
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "This is a test response"
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response("What is machine learning?")
        
        assert response == "This is a test response"
        
        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-sonnet-4-20250514"
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "What is machine learning?"
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_response_with_conversation_history(self, mock_anthropic):
        """Test generating response with conversation history"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Response with history"
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        history = "Previous conversation context"
        response = generator.generate_response("Follow up question", conversation_history=history)
        
        assert response == "Response with history"
        
        # Verify history was included in system message
        call_args = mock_client.messages.create.call_args[1]
        assert "Previous conversation context" in call_args["system"]
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_response_with_tools_but_no_tool_use(self, mock_anthropic):
        """Test response when tools are available but not used"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "General knowledge response"
        mock_client.messages.create.return_value = mock_response
        
        # Mock tool definitions
        mock_tools = [{
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {"type": "object"}
        }]
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response("What is 2+2?", tools=mock_tools)
        
        assert response == "General knowledge response"
        
        # Verify tools were passed to API
        call_args = mock_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tools"] == mock_tools
        assert call_args["tool_choice"] == {"type": "auto"}


class TestAIGeneratorSequentialToolCalling:
    """Test AIGenerator sequential tool calling functionality"""
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_two_round_sequential_tool_execution(self, mock_anthropic):
        """Test complete two-round sequential tool execution flow"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock Round 1: get_course_outline call
        mock_round1_response = MagicMock()
        mock_round1_response.stop_reason = "tool_use"
        mock_tool_block1 = MagicMock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "get_course_outline"
        mock_tool_block1.input = {"course_name": "AI Course"}
        mock_tool_block1.id = "tool_call_1"
        mock_round1_response.content = [mock_tool_block1]
        
        # Mock Round 2: search_course_content based on outline results
        mock_round2_response = MagicMock()
        mock_round2_response.stop_reason = "tool_use"
        mock_tool_block2 = MagicMock()
        mock_tool_block2.type = "tool_use" 
        mock_tool_block2.name = "search_course_content"
        mock_tool_block2.input = {"query": "neural networks", "course_name": "AI Course"}
        mock_tool_block2.id = "tool_call_2"
        mock_round2_response.content = [mock_tool_block2]
        
        # Mock Final response after second round
        mock_final_response = MagicMock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "Based on the course outline and content search, neural networks are covered in lesson 3..."
        
        # Configure mock to return responses in sequence
        mock_client.messages.create.side_effect = [
            mock_round1_response,    # Initial API call
            mock_round2_response,    # Round 1 with tools 
            mock_final_response      # Round 2 without tools (final)
        ]
        
        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course: AI Fundamentals\nLesson 1: Introduction\nLesson 2: History\nLesson 3: Neural Networks",
            "Neural networks are computational models inspired by biological neural networks..."
        ]
        
        # Mock tools
        mock_tools = [
            {"name": "get_course_outline", "description": "Get course outline", "input_schema": {"type": "object"}},
            {"name": "search_course_content", "description": "Search content", "input_schema": {"type": "object"}}
        ]
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "Find content about neural networks in the AI Course",
            tools=mock_tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert response == "Based on the course outline and content search, neural networks are covered in lesson 3..."
        
        # Verify both tools were executed in order
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="AI Course")
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="neural networks", course_name="AI Course")
        
        # Verify API calls made
        assert mock_client.messages.create.call_count == 3
        
        # Verify first call had tools
        first_call_args = mock_client.messages.create.call_args_list[0][1]
        assert "tools" in first_call_args
        
        # Verify second call (round 1) had tools  
        second_call_args = mock_client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_args
        
        # Verify third call (round 2/final) had no tools
        third_call_args = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_args
        
        # Verify message accumulation - final call should have full conversation
        final_messages = third_call_args["messages"]
        assert len(final_messages) >= 5  # User query + assistant + user results + assistant + user results
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_single_round_backwards_compatibility(self, mock_anthropic):
        """Test that single round tool calling still works as before"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock single tool use response
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "machine learning"}
        mock_tool_block.id = "tool_call_1"
        mock_initial_response.content = [mock_tool_block]
        
        # Mock final response
        mock_final_response = MagicMock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "Machine learning is a method of data analysis..."
        
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        
        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Machine learning content from course materials"
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "What is machine learning?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=1  # Explicit single round
        )
        
        assert response == "Machine learning is a method of data analysis..."
        
        # Verify only 2 API calls made (initial + final, no second round)
        assert mock_client.messages.create.call_count == 2
        
        # Verify tool was executed once
        mock_tool_manager.execute_tool.assert_called_once_with("search_course_content", query="machine learning")
    
    @patch('ai_generator.anthropic.Anthropic') 
    def test_early_termination_after_first_round(self, mock_anthropic):
        """Test Claude stops after first round when satisfied with results"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock initial response with tool use
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "basic concepts"}
        mock_tool_block.id = "tool_call_1"
        mock_initial_response.content = [mock_tool_block]
        
        # Mock Round 1 response - Claude chooses to provide final answer
        mock_round1_response = MagicMock()
        mock_round1_response.stop_reason = "end_turn"  # No more tool use
        mock_round1_response.content = [MagicMock()]
        mock_round1_response.content[0].text = "The basic concepts include classification, regression, and clustering."
        
        mock_client.messages.create.side_effect = [mock_initial_response, mock_round1_response]
        
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Basic ML concepts: supervised learning, unsupervised learning..."
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "What are the basic machine learning concepts?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=2  # Allow 2 but Claude chooses to stop after 1
        )
        
        assert response == "The basic concepts include classification, regression, and clustering."
        
        # Verify only 2 API calls (initial + round 1, no round 2 needed)  
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once()
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_max_rounds_enforcement(self, mock_anthropic):
        """Test system prevents more than max_rounds tool calls"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock all responses to want tool use (to test enforcement)
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        mock_tool_block1 = MagicMock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "get_course_outline"
        mock_tool_block1.input = {"course_name": "Course A"}
        mock_tool_block1.id = "tool_1"
        mock_initial_response.content = [mock_tool_block1]
        
        mock_round1_response = MagicMock()
        mock_round1_response.stop_reason = "tool_use" 
        mock_tool_block2 = MagicMock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "search_course_content"
        mock_tool_block2.input = {"query": "advanced topics"}
        mock_tool_block2.id = "tool_2"  
        mock_round1_response.content = [mock_tool_block2]
        
        # Final response forced without tools (since max rounds reached)
        mock_final_response = MagicMock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "Based on available information..."
        
        mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_round1_response, 
            mock_final_response
        ]
        
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = ["Outline results", "Content results"]
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "Find advanced topics in Course A",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert response == "Based on available information..."
        
        # Verify exactly 3 API calls (initial + 2 rounds) 
        assert mock_client.messages.create.call_count == 3
        
        # Verify exactly 2 tool executions
        assert mock_tool_manager.execute_tool.call_count == 2
        
        # Verify final call has no tools (enforcement)
        final_call_args = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in final_call_args
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_default_max_tool_rounds_from_config(self, mock_anthropic):
        """Test that default max_tool_rounds comes from config"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock simple response without tool use 
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Simple response"
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        
        # Call without max_tool_rounds parameter
        response = generator.generate_response("Simple question")
        
        assert response == "Simple response"
        # Should complete successfully using config default
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_error_handling_during_sequential_rounds(self, mock_anthropic):
        """Test graceful error handling when tools fail during sequential rounds"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock initial response with tool use
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_call_1"
        mock_initial_response.content = [mock_tool_block]
        
        # Mock final response that handles the error
        mock_final_response = MagicMock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "I apologize, there was an issue accessing the course content."
        
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        
        # Mock tool manager that returns error message
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Error: Tool execution failed - Database connection error"
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "Search for test content",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        assert response == "I apologize, there was an issue accessing the course content."
        
        # Verify tool error was passed to Claude
        final_call_args = mock_client.messages.create.call_args_list[1][1]
        tool_result = final_call_args["messages"][2]["content"][0]
        assert "Error: Tool execution failed - Database connection error" in tool_result["content"]


class TestAIGeneratorToolExecution:
    """Test AIGenerator tool execution functionality"""
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_flow(self, mock_anthropic):
        """Test complete tool execution flow"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock initial response with tool use
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "machine learning"}
        mock_tool_block.id = "tool_call_123"
        mock_initial_response.content = [mock_tool_block]
        
        # Mock final response after tool execution
        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "Based on the search results, machine learning is..."
        
        # Configure mock client to return responses in sequence
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        
        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search results about machine learning"
        
        # Mock tools
        mock_tools = [{
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {"type": "object"}
        }]
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "Tell me about machine learning",
            tools=mock_tools,
            tool_manager=mock_tool_manager
        )
        
        assert response == "Based on the search results, machine learning is..."
        
        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="machine learning"
        )
        
        # Verify API was called twice (initial + final)
        assert mock_client.messages.create.call_count == 2
        
        # Verify final call included tool results
        final_call_args = mock_client.messages.create.call_args_list[1][1]
        messages = final_call_args["messages"]
        
        # Should have: user message, assistant tool use, user tool result
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        
        # Check tool result structure
        tool_result = messages[2]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tool_call_123"
        assert tool_result["content"] == "Search results about machine learning"
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_multiple_tool_calls(self, mock_anthropic):
        """Test handling multiple tool calls in one response"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock initial response with multiple tool uses
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        
        mock_tool_block1 = MagicMock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "search_course_content"
        mock_tool_block1.input = {"query": "machine learning"}
        mock_tool_block1.id = "tool_call_1"
        
        mock_tool_block2 = MagicMock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "get_course_outline"
        mock_tool_block2.input = {"course_name": "AI Course"}
        mock_tool_block2.id = "tool_call_2"
        
        mock_initial_response.content = [mock_tool_block1, mock_tool_block2]
        
        # Mock final response
        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "Combined response from multiple tools"
        
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        
        # Mock tool manager
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = [
            "Search result 1",
            "Outline result 2"
        ]
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "Tell me about AI courses",
            tools=[],
            tool_manager=mock_tool_manager
        )
        
        assert response == "Combined response from multiple tools"
        
        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="machine learning")
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="AI Course")
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_api_error_handling(self, mock_anthropic):
        """Test handling of Anthropic API errors"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock API error
        mock_client.messages.create.side_effect = Exception("API Error: Invalid API key")
        
        generator = AIGenerator("invalid-api-key", "claude-sonnet-4-20250514")
        
        with pytest.raises(Exception) as exc_info:
            generator.generate_response("Test query")
        
        assert "API Error: Invalid API key" in str(exc_info.value)
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_error_handling(self, mock_anthropic):
        """Test handling of tool execution errors"""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        # Mock initial response with tool use
        mock_initial_response = MagicMock()
        mock_initial_response.stop_reason = "tool_use"
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_call_123"
        mock_initial_response.content = [mock_tool_block]
        
        # Mock final response
        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock()]
        mock_final_response.content[0].text = "Error response"
        
        mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
        
        # Mock tool manager with error
        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Tool execution failed: Database error"
        
        generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
        response = generator.generate_response(
            "Test query",
            tools=[],
            tool_manager=mock_tool_manager
        )
        
        assert response == "Error response"
        
        # Verify tool error was passed to final API call
        final_call_args = mock_client.messages.create.call_args_list[1][1]
        tool_result = final_call_args["messages"][2]["content"][0]
        assert "Tool execution failed: Database error" in tool_result["content"]


class TestAIGeneratorWithRealToolManager:
    """Integration tests with real ToolManager and mocked CourseSearchTool"""
    
    def test_integration_with_tool_manager(self, mock_vector_store):
        """Test AIGenerator integration with real ToolManager"""
        # Create real tool manager and tool
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        tool_manager.register_tool(search_tool)
        
        # Mock vector store to return test results
        from vector_store import SearchResults
        mock_results = SearchResults(
            documents=["Test content about machine learning"],
            metadata=[{"course_title": "AI Course", "lesson_number": 1}],
            distances=[0.1]
        )
        mock_vector_store.search.return_value = mock_results
        
        # Mock Anthropic API
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            
            # Mock tool use response
            mock_initial_response = MagicMock()
            mock_initial_response.stop_reason = "tool_use"
            mock_tool_block = MagicMock()
            mock_tool_block.type = "tool_use"
            mock_tool_block.name = "search_course_content"
            mock_tool_block.input = {"query": "machine learning"}
            mock_tool_block.id = "tool_123"
            mock_initial_response.content = [mock_tool_block]
            
            # Mock final response
            mock_final_response = MagicMock()
            mock_final_response.content = [MagicMock()]
            mock_final_response.content[0].text = "Machine learning is a subset of AI..."
            
            mock_client.messages.create.side_effect = [mock_initial_response, mock_final_response]
            
            generator = AIGenerator("test-api-key", "claude-sonnet-4-20250514")
            response = generator.generate_response(
                "What is machine learning?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager
            )
            
            assert response == "Machine learning is a subset of AI..."
            
            # Verify the search was actually performed
            mock_vector_store.search.assert_called_once_with(
                query="machine learning",
                course_name=None,
                lesson_number=None
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])