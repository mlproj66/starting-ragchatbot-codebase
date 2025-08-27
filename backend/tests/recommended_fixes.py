"""
Recommended fixes for the RAG system based on test findings.
The core system is working, but these improvements will prevent edge case failures.
"""

# Fix 1: Enhanced error handling in app.py
APP_PY_ENHANCED_ERROR_HANDLING = '''
@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    import traceback
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        
        # Log the query for debugging
        logger.info(f"Processing query: {request.query[:100]}...")
        
        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)
        
        # Validate response
        if not answer or answer.strip() == "":
            logger.warning("Empty response generated")
            answer = "I apologize, but I wasn't able to generate a response for your query. Please try rephrasing your question."
        
        # Log successful completion
        logger.info(f"Query completed successfully. Response length: {len(answer)}, Sources: {len(sources)}")
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        # Enhanced error logging
        error_msg = str(e)
        logger.error(f"Query failed: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Provide more specific error messages
        if "api" in error_msg.lower():
            detail = "AI service temporarily unavailable. Please try again."
        elif "database" in error_msg.lower() or "chroma" in error_msg.lower():
            detail = "Course database temporarily unavailable. Please try again."
        elif "tool" in error_msg.lower():
            detail = "Search functionality temporarily unavailable. Please try again."
        else:
            detail = f"Query processing error: {error_msg}"
        
        raise HTTPException(status_code=500, detail=detail)
'''

# Fix 2: CourseOutlineTool source tracking
COURSE_OUTLINE_TOOL_SOURCE_TRACKING = '''
class CourseOutlineTool(Tool):
    """Tool for getting course outlines with complete lesson information"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Add source tracking like CourseSearchTool
    
    def execute(self, course_name: str) -> str:
        """Execute the course outline tool with given course name."""
        
        # First resolve the course name
        course_title = self.store._resolve_course_name(course_name)
        if not course_title:
            self.last_sources = []  # Clear sources on error
            return f"No course found matching '{course_name}'"
        
        # Get all courses metadata to find our specific course
        all_courses = self.store.get_all_courses_metadata()
        course_metadata = None
        
        for course in all_courses:
            if course.get('title') == course_title:
                course_metadata = course
                break
        
        if not course_metadata:
            self.last_sources = []  # Clear sources on error
            return f"Course metadata not found for '{course_title}'"
        
        # Track source for the outline
        course_link = course_metadata.get('course_link')
        self.last_sources = [{
            "text": course_metadata.get('title', 'Unknown Course'),
            "url": course_link if course_link else None
        }]
        
        # Format the course outline
        return self._format_outline(course_metadata)
'''

# Fix 3: Enhanced AI system prompt with better error handling instructions
ENHANCED_SYSTEM_PROMPT = '''
SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
1. **search_course_content**: For finding specific course content and detailed educational materials
2. **get_course_outline**: For retrieving complete course outlines including title, course link, and all lessons with their numbers and titles

Tool Usage Guidelines:
- Use **search_course_content** for questions about specific course content or detailed educational materials
- Use **get_course_outline** for questions about course structure, lesson lists, or when users ask for a course outline/overview
- **One tool call per query maximum**
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives
- ALWAYS attempt to use tools for course-related questions, even if you have general knowledge about the topic

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course content questions**: Use search_course_content tool first, then answer
- **Course outline questions**: Use get_course_outline tool first, then answer
- **Course structure/overview questions**: Use get_course_outline tool to provide complete course information including title, course link, and all lessons
- **Error handling**: If tools fail or return no results, acknowledge this and provide what help you can with general knowledge
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
5. **Helpful** - Always provide some useful information, even if tools fail

Provide only the direct answer to what was asked.
"""
'''

# Fix 4: Frontend error handling improvement
FRONTEND_ERROR_HANDLING = '''
// Enhanced error handling in frontend JavaScript
async function submitQuery() {
    const queryText = document.getElementById('query').value.trim();
    if (!queryText) return;
    
    // Show loading state
    showLoadingState();
    
    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: queryText,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            // Parse error details
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Validate response data
        if (!data.answer || data.answer.trim() === '') {
            throw new Error('Empty response received from server');
        }
        
        displayResponse(data);
        
    } catch (error) {
        console.error('Query failed:', error);
        
        // Show user-friendly error message
        let errorMessage = 'Query failed. ';
        
        if (error.message.includes('temporarily unavailable')) {
            errorMessage += error.message + ' Please try again in a moment.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
            errorMessage += 'Network connection issue. Please check your connection and try again.';
        } else {
            errorMessage += 'Please try rephrasing your question or try again later.';
        }
        
        displayError(errorMessage);
    } finally {
        hideLoadingState();
    }
}

function displayError(message) {
    const responseDiv = document.getElementById('response');
    responseDiv.innerHTML = `
        <div class="error-message">
            <h3>⚠️ ${message}</h3>
            <p>If the problem persists, please try:</p>
            <ul>
                <li>Refreshing the page</li>
                <li>Asking a more specific question</li>
                <li>Checking your internet connection</li>
            </ul>
        </div>
    `;
}
'''

print("Recommended fixes prepared:")
print("1. Enhanced error handling in app.py")
print("2. CourseOutlineTool source tracking") 
print("3. Enhanced AI system prompt")
print("4. Frontend error handling improvement")