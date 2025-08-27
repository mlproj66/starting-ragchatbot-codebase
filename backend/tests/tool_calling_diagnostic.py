#!/usr/bin/env python3
"""
Specific diagnostic for tool calling behavior.
Tests whether AI is actually calling the search tools.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_direct_tool_execution():
    """Test direct tool execution"""
    print("=" * 50)
    print("TESTING DIRECT TOOL EXECUTION")
    print("=" * 50)
    
    try:
        from config import config
        from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
        from vector_store import VectorStore
        
        store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        tool_manager = ToolManager()
        search_tool = CourseSearchTool(store)
        outline_tool = CourseOutlineTool(store)
        
        tool_manager.register_tool(search_tool)
        tool_manager.register_tool(outline_tool)
        
        # Test search tool with specific course content
        print("Testing search tool with course-specific query...")
        result1 = tool_manager.execute_tool("search_course_content", query="MCP server")
        print(f"Search result length: {len(result1)}")
        print(f"Search result preview: {result1[:200]}...")
        
        # Test with general query
        print("\nTesting search tool with general query...")
        result2 = tool_manager.execute_tool("search_course_content", query="machine learning")
        print(f"Search result length: {len(result2)}")
        print(f"Search result preview: {result2[:200]}...")
        
        # Test outline tool
        print("\nTesting outline tool...")
        result3 = tool_manager.execute_tool("get_course_outline", course_name="MCP")
        print(f"Outline result length: {len(result3)}")
        print(f"Outline result preview: {result3[:200]}...")
        
        # Check sources
        sources = tool_manager.get_last_sources()
        print(f"\nSources found: {len(sources)}")
        for i, source in enumerate(sources):
            print(f"  Source {i+1}: {source}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct tool execution failed: {e}")
        return False

def test_ai_tool_calling_with_specific_queries():
    """Test AI tool calling with course-specific queries"""
    print("\n" + "=" * 50)  
    print("TESTING AI TOOL CALLING WITH COURSE-SPECIFIC QUERIES")
    print("=" * 50)
    
    try:
        from config import config
        from rag_system import RAGSystem
        
        rag_system = RAGSystem(config)
        
        # Test queries that should definitely trigger tool use
        test_queries = [
            "What is MCP and how does it work?",
            "Tell me about the MCP course outline",
            "What lessons are in the Computer Use course?", 
            "How do I build an MCP server?",
            "What is covered in the Chroma course?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nTest Query {i}: '{query}'")
            try:
                response, sources = rag_system.query(query)
                
                print(f"Response length: {len(response)}")
                print(f"Sources found: {len(sources)}")
                
                if len(sources) > 0:
                    print("✅ Tool was called - sources returned")
                    for j, source in enumerate(sources):
                        print(f"  Source {j+1}: {source}")
                else:
                    print("⚠️  No sources - tool may not have been called")
                
                print(f"Response preview: {response[:150]}...")
                
            except Exception as e:
                print(f"❌ Query failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ AI tool calling test failed: {e}")
        return False

def test_ai_response_analysis():
    """Analyze AI responses to see if they use tool data"""
    print("\n" + "=" * 50)
    print("TESTING AI RESPONSE ANALYSIS")
    print("=" * 50)
    
    try:
        from config import config
        from rag_system import RAGSystem
        
        rag_system = RAGSystem(config)
        
        # Test with a very specific question that requires course content
        specific_query = "What are the specific lessons in the MCP course?"
        
        print(f"Analyzing response to: '{specific_query}'")
        response, sources = rag_system.query(specific_query)
        
        print(f"Response: {response}")
        print(f"Sources: {sources}")
        
        # Check if response contains course-specific information
        course_indicators = [
            "lesson",
            "MCP:",
            "Build Rich-Context",
            "Anthropic",
            "server",
            "client"
        ]
        
        found_indicators = [indicator for indicator in course_indicators 
                          if indicator.lower() in response.lower()]
        
        print(f"\nCourse-specific indicators found: {found_indicators}")
        
        if len(sources) > 0:
            print("✅ Tools were used (sources present)")
        elif len(found_indicators) > 2:
            print("✅ Response contains course-specific content (likely from tools)")  
        else:
            print("⚠️  Response seems generic - tools may not be working")
        
        return True
        
    except Exception as e:
        print(f"❌ Response analysis failed: {e}")
        return False

def test_with_debug_logging():
    """Test with debug logging to see tool execution"""
    print("\n" + "=" * 50)
    print("TESTING WITH DEBUG LOGGING")
    print("=" * 50)
    
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    try:
        from config import config
        from rag_system import RAGSystem
        
        # Test the AI generator tool calling directly
        rag_system = RAGSystem(config)
        
        # Create a simple tool manager mock to track calls
        original_execute_tool = rag_system.tool_manager.execute_tool
        
        call_log = []
        def logging_execute_tool(tool_name, **kwargs):
            call_log.append({"tool": tool_name, "args": kwargs})
            print(f"🔧 Tool called: {tool_name} with args: {kwargs}")
            return original_execute_tool(tool_name, **kwargs)
        
        rag_system.tool_manager.execute_tool = logging_execute_tool
        
        # Test query
        query = "Tell me about MCP servers"
        print(f"Testing query: '{query}'")
        
        response, sources = rag_system.query(query)
        
        print(f"\nTool calls made: {len(call_log)}")
        for call in call_log:
            print(f"  {call}")
        
        print(f"Response length: {len(response)}")
        print(f"Sources: {len(sources)}")
        
        if len(call_log) > 0:
            print("✅ AI is calling tools")
        else:
            print("❌ AI is NOT calling tools - this is the issue!")
        
        return len(call_log) > 0
        
    except Exception as e:
        print(f"❌ Debug logging test failed: {e}")
        return False

def main():
    """Run tool calling diagnostics"""
    print("TOOL CALLING DIAGNOSTIC")
    print("Testing whether AI actually calls the search tools...\n")
    
    tests = [
        ("Direct Tool Execution", test_direct_tool_execution),
        ("AI Tool Calling", test_ai_tool_calling_with_specific_queries),
        ("AI Response Analysis", test_ai_response_analysis), 
        ("Debug Logging", test_with_debug_logging)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("TOOL CALLING DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
    
    # Analysis
    if not results.get("Debug Logging", False):
        print(f"\n🎯 ROOT CAUSE IDENTIFIED: AI is not calling tools!")
        print("   This explains the 'query failed' - the AI tries to answer from")
        print("   general knowledge but fails when it needs specific course content.")
        print("\n🔧 LIKELY FIXES:")
        print("   1. Check system prompt - ensure it instructs AI to use tools")
        print("   2. Verify tool definitions are correct")
        print("   3. Test Anthropic API tool calling functionality")
        print("   4. Check if model supports tool calling")
    else:
        print(f"\n✅ Tools are being called correctly")
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)