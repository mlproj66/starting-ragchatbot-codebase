#!/usr/bin/env python3
"""
Quick diagnostic script to identify the 'query failed' issue.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config():
    """Test configuration"""
    print("=" * 50)
    print("TESTING CONFIGURATION")
    print("=" * 50)
    
    try:
        from config import config
        print(f"✅ Configuration loaded")
        print(f"   API Key: {'SET' if config.ANTHROPIC_API_KEY else 'NOT SET'}")
        print(f"   Model: {config.ANTHROPIC_MODEL}")
        print(f"   ChromaDB Path: {config.CHROMA_PATH}")
        return True
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False

def test_database():
    """Test database connectivity and data"""
    print("\n" + "=" * 50)
    print("TESTING DATABASE")
    print("=" * 50)
    
    try:
        from config import config
        from vector_store import VectorStore
        
        store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        print(f"✅ VectorStore initialized")
        
        course_count = store.get_course_count()
        course_titles = store.get_existing_course_titles()
        print(f"   Courses: {course_count}")
        print(f"   Titles: {course_titles}")
        
        if course_count == 0:
            print("⚠️  No courses in database - this could be the issue!")
            return False
        
        # Test search
        results = store.search("test query", limit=1)
        if results.error:
            print(f"❌ Search failed: {results.error}")
            return False
        
        print(f"✅ Database search working")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_tools():
    """Test tool system"""
    print("\n" + "=" * 50)
    print("TESTING TOOLS")
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
        
        definitions = tool_manager.get_tool_definitions()
        print(f"✅ Tools registered: {[d['name'] for d in definitions]}")
        
        # Test tool execution
        if store.get_course_count() > 0:
            result = tool_manager.execute_tool("search_course_content", query="test")
            if "No relevant content found" in result or "error" in result.lower():
                print(f"⚠️  Tool execution issue: {result}")
                return False
            else:
                print(f"✅ Tool execution working")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool test failed: {e}")
        return False

def test_ai_system():
    """Test AI system"""
    print("\n" + "=" * 50)
    print("TESTING AI SYSTEM")
    print("=" * 50)
    
    try:
        from config import config
        from ai_generator import AIGenerator
        
        if not config.ANTHROPIC_API_KEY:
            print("❌ No API key - cannot test AI system")
            return False
        
        generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
        print(f"✅ AI Generator initialized")
        print(f"   Model: {generator.model}")
        
        # Test system prompt
        prompt_length = len(AIGenerator.SYSTEM_PROMPT)
        print(f"   System prompt length: {prompt_length}")
        
        # Check if prompt mentions tools
        if "search_course_content" in AIGenerator.SYSTEM_PROMPT:
            print(f"✅ System prompt includes tool instructions")
        else:
            print(f"❌ System prompt missing tool instructions")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ AI system test failed: {e}")
        return False

def test_rag_system():
    """Test full RAG system"""
    print("\n" + "=" * 50)
    print("TESTING RAG SYSTEM")
    print("=" * 50)
    
    try:
        from config import config
        from rag_system import RAGSystem
        
        rag_system = RAGSystem(config)
        print(f"✅ RAG System initialized")
        
        # Test analytics
        analytics = rag_system.get_course_analytics()
        print(f"   Database: {analytics['total_courses']} courses")
        
        if analytics['total_courses'] == 0:
            print("⚠️  No courses loaded - this is likely the issue!")
            return False
        
        # Test tool availability
        tools = rag_system.tool_manager.get_tool_definitions()
        print(f"   Tools: {[t['name'] for t in tools]}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        return False

def simulate_query():
    """Simulate a query to identify the exact failure point"""
    print("\n" + "=" * 50)
    print("SIMULATING QUERY")
    print("=" * 50)
    
    try:
        from config import config
        from rag_system import RAGSystem
        
        rag_system = RAGSystem(config)
        
        # Try a simple query
        print("Executing query: 'What is machine learning?'")
        response, sources = rag_system.query("What is machine learning?")
        
        print(f"✅ Query executed successfully")
        print(f"   Response length: {len(response)}")
        print(f"   Sources: {len(sources)}")
        print(f"   Response preview: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

def main():
    """Run all diagnostic tests"""
    print("RAG SYSTEM QUICK DIAGNOSTIC")
    print("Identifying the 'query failed' issue...\n")
    
    tests = [
        ("Configuration", test_config),
        ("Database", test_database),
        ("Tools", test_tools),
        ("AI System", test_ai_system),
        ("RAG System", test_rag_system),
        ("Query Simulation", simulate_query)
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
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
    
    failed_tests = [name for name, passed in results.items() if not passed]
    
    if failed_tests:
        print(f"\n🔍 LIKELY ISSUE: {failed_tests[0]}")
        
        if "Database" in failed_tests:
            print("   → No courses loaded in database")
            print("   → Check if documents are in ../docs folder")
            print("   → Restart application to trigger document loading")
        
        elif "Query Simulation" in failed_tests:
            print("   → Query execution is failing")
            print("   → Check API key and connectivity")
            print("   → Check tool execution")
        
    else:
        print("\n✅ All tests passed - issue may be intermittent or environmental")
    
    return len(failed_tests) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)