import anthropic
from typing import List, Optional, Dict, Any
from config import config

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
1. **search_course_content**: For finding specific course content and detailed educational materials
2. **get_course_outline**: For retrieving complete course outlines including title, course link, and all lessons with their numbers and titles

Tool Usage Guidelines:
- **Sequential tool calling**: You can make multiple rounds of tool calls (maximum 2 rounds) to gather comprehensive information
- **Strategic approach**: Use results from first tools to inform second round of searches when needed
- **Round 1 examples**: Get course outline to identify relevant lessons, search for basic content
- **Round 2 examples**: Search specific lesson content based on outline results, get additional details from identified courses
- Use **search_course_content** for questions about specific course content and detailed educational materials
- Use **get_course_outline** for questions about course structure, lesson lists, or when users ask for a course outline/overview
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course content questions**: Use search_course_content tool first, then answer
- **Course outline questions**: Use get_course_outline tool first, then answer  
- **Course structure/overview questions**: Use get_course_outline tool to provide complete course information including title, course link, and all lessons
- **Complex queries**: Use sequential tools strategically (e.g., get outline → search specific content)
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"

For outline responses, always include:
- Course title
- Course link (if available)
- Complete list of lessons with lesson numbers and titles

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         max_tool_rounds: int = None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum rounds of tool calls (defaults to config.MAX_TOOL_ROUNDS)
            
        Returns:
            Generated response as string
        """
        
        # Set default max_tool_rounds if not provided
        if max_tool_rounds is None:
            max_tool_rounds = config.MAX_TOOL_ROUNDS
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager, max_tool_rounds)
        
        # Return direct response
        return response.content[0].text
    
    def _execute_tools_for_response(self, response, tool_manager):
        """
        Execute all tool calls in a response and return formatted results.
        
        Args:
            response: The response containing tool use requests
            tool_manager: Manager to execute tools
            
        Returns:
            List of tool result dictionaries formatted for API
        """
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        return tool_results
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, max_tool_rounds: int = 2):
        """
        Handle sequential tool execution with up to max_tool_rounds rounds.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential rounds
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        current_round = 1
        response = initial_response
        
        # Main execution loop - handle up to max_tool_rounds of tool calls
        while current_round <= max_tool_rounds and response.stop_reason == "tool_use":
            # Add AI's tool use response to messages
            messages.append({"role": "assistant", "content": response.content})
            
            # Execute all tools in current response
            tool_results = self._execute_tools_for_response(response, tool_manager)
            
            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }
            
            # Include tools if not on final round (to allow another round)
            if current_round < max_tool_rounds:
                api_params["tools"] = base_params.get("tools", [])
                api_params["tool_choice"] = {"type": "auto"}
            
            # Get next response
            response = self.client.messages.create(**api_params)
            current_round += 1
        
        # Return final response text
        return response.content[0].text