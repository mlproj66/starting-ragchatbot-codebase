"""
Diagnostic tests for RAG system debugging.
Provides detailed analysis of system components and failure points.
"""

import pytest
import sys
import os
import tempfile
import shutil
import logging
from unittest.mock import MagicMock, patch, Mock
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure detailed logging for diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestEnvironmentDiagnostics:
    """Diagnostic tests for environment and dependencies"""
    
    def test_python_version(self):
        """Test Python version compatibility"""
        import sys
        python_version = sys.version_info
        logger.info(f"Python version: {python_version}")
        
        assert python_version.major >= 3, "Python 3.x required"
        assert python_version.minor >= 8, "Python 3.8+ recommended"
    
    def test_required_packages(self):
        """Test that all required packages are available"""
        required_packages = [
            'anthropic',
            'chromadb', 
            'sentence_transformers',
            'fastapi',
            'uvicorn',
            'python-dotenv',
            'pytest'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                logger.info(f"✓ {package} is available")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"✗ {package} is missing")
        
        if missing_packages:
            pytest.fail(f"Missing required packages: {missing_packages}")
    
    def test_anthropic_client_creation(self):
        """Test Anthropic client can be created"""
        try:
            import anthropic
            
            # Test with dummy API key
            client = anthropic.Anthropic(api_key="test-key")
            assert client is not None
            logger.info("✓ Anthropic client can be created")
            
        except Exception as e:
            logger.error(f"✗ Anthropic client creation failed: {e}")
            pytest.fail(f"Cannot create Anthropic client: {e}")
    
    def test_chromadb_creation(self):
        """Test ChromaDB client can be created"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Create temporary directory for test
            temp_dir = tempfile.mkdtemp()
            try:
                client = chromadb.PersistentClient(
                    path=temp_dir,
                    settings=Settings(anonymized_telemetry=False)
                )
                assert client is not None
                
                # Test collection creation
                collection = client.get_or_create_collection("test_collection")
                assert collection is not None
                
                logger.info("✓ ChromaDB client and collection can be created")
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"✗ ChromaDB creation failed: {e}")
            pytest.fail(f"Cannot create ChromaDB client: {e}")
    
    def test_sentence_transformers_model_loading(self):
        """Test sentence transformers model can be loaded"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Try loading the default model
            model_name = "all-MiniLM-L6-v2"
            model = SentenceTransformer(model_name)
            assert model is not None
            
            # Test encoding
            test_text = "This is a test sentence."
            embedding = model.encode([test_text])
            assert embedding is not None
            assert len(embedding) > 0
            
            logger.info(f"✓ SentenceTransformer model '{model_name}' loaded successfully")
            
        except Exception as e:
            logger.warning(f"⚠ SentenceTransformer model loading failed (may require internet): {e}")
            pytest.skip(f"Model loading failed: {e}")


class TestConfigurationDiagnostics:
    """Diagnostic tests for configuration issues"""
    
    def test_config_loading(self):
        """Test configuration loading and validation"""
        try:
            from config import config
            
            logger.info("Configuration loaded:")
            logger.info(f"  ANTHROPIC_API_KEY: {'SET' if config.ANTHROPIC_API_KEY else 'NOT SET'}")
            logger.info(f"  ANTHROPIC_MODEL: {config.ANTHROPIC_MODEL}")
            logger.info(f"  EMBEDDING_MODEL: {config.EMBEDDING_MODEL}")
            logger.info(f"  CHUNK_SIZE: {config.CHUNK_SIZE}")
            logger.info(f"  CHUNK_OVERLAP: {config.CHUNK_OVERLAP}")
            logger.info(f"  MAX_RESULTS: {config.MAX_RESULTS}")
            logger.info(f"  MAX_HISTORY: {config.MAX_HISTORY}")
            logger.info(f"  CHROMA_PATH: {config.CHROMA_PATH}")
            
            # Check for common configuration issues
            issues = []
            
            if not config.ANTHROPIC_API_KEY:
                issues.append("ANTHROPIC_API_KEY is not set")
            elif config.ANTHROPIC_API_KEY == "":
                issues.append("ANTHROPIC_API_KEY is empty")
            elif config.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
                issues.append("ANTHROPIC_API_KEY is still placeholder value")
            
            if config.CHUNK_SIZE <= 0:
                issues.append("CHUNK_SIZE must be positive")
            
            if config.MAX_RESULTS <= 0:
                issues.append("MAX_RESULTS must be positive")
            
            if issues:
                logger.error("Configuration issues found:")
                for issue in issues:
                    logger.error(f"  ✗ {issue}")
                pytest.fail(f"Configuration issues: {issues}")
            else:
                logger.info("✓ Configuration appears valid")
                
        except Exception as e:
            logger.error(f"✗ Configuration loading failed: {e}")
            pytest.fail(f"Cannot load configuration: {e}")
    
    def test_env_file_presence(self):
        """Test .env file presence and content"""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(backend_dir, '.env')
        
        if not os.path.exists(env_file):
            logger.warning("⚠ .env file not found - this may cause API key issues")
            return
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                
            logger.info("✓ .env file found")
            
            # Check for common issues
            if 'ANTHROPIC_API_KEY=' not in content:
                logger.warning("⚠ ANTHROPIC_API_KEY not found in .env file")
            elif 'ANTHROPIC_API_KEY=your_anthropic_api_key_here' in content:
                logger.warning("⚠ ANTHROPIC_API_KEY appears to be placeholder in .env file")
            else:
                logger.info("✓ ANTHROPIC_API_KEY appears to be set in .env file")
                
        except Exception as e:
            logger.error(f"✗ Error reading .env file: {e}")


class TestDatabaseDiagnostics:
    """Diagnostic tests for database issues"""
    
    def test_chroma_db_directory(self):
        """Test ChromaDB directory and permissions"""
        from config import config
        
        chroma_path = config.CHROMA_PATH
        logger.info(f"Testing ChromaDB path: {chroma_path}")
        
        # Check if directory exists
        if not os.path.exists(chroma_path):
            logger.info(f"ChromaDB directory does not exist: {chroma_path}")
            logger.info("This is normal for first run - directory will be created")
            return
        
        # Check permissions
        if not os.access(chroma_path, os.R_OK):
            pytest.fail(f"Cannot read ChromaDB directory: {chroma_path}")
        
        if not os.access(chroma_path, os.W_OK):
            pytest.fail(f"Cannot write to ChromaDB directory: {chroma_path}")
        
        # Check contents
        try:
            contents = os.listdir(chroma_path)
            logger.info(f"ChromaDB directory contents: {contents}")
            
            if 'chroma.sqlite3' in contents:
                logger.info("✓ ChromaDB SQLite file found")
            else:
                logger.warning("⚠ ChromaDB SQLite file not found - database may be empty")
                
        except Exception as e:
            logger.error(f"✗ Error reading ChromaDB directory: {e}")
    
    def test_existing_data_access(self):
        """Test access to existing data in the system"""
        try:
            from config import config
            from vector_store import VectorStore
            
            # Create vector store instance
            store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
            
            # Test basic operations
            course_count = store.get_course_count()
            course_titles = store.get_existing_course_titles()
            
            logger.info(f"Database diagnostics:")
            logger.info(f"  Course count: {course_count}")
            logger.info(f"  Course titles: {course_titles}")
            
            if course_count == 0:
                logger.warning("⚠ No courses found in database - this may be expected for fresh install")
            else:
                logger.info("✓ Database contains course data")
            
            # Test search on existing data
            if course_count > 0:
                try:
                    results = store.search("test query", limit=1)
                    if results.error:
                        logger.error(f"✗ Search failed: {results.error}")
                    else:
                        logger.info("✓ Database search working")
                except Exception as e:
                    logger.error(f"✗ Search error: {e}")
            
        except Exception as e:
            logger.error(f"✗ Database access failed: {e}")
            pytest.fail(f"Cannot access database: {e}")


class TestToolDiagnostics:
    """Diagnostic tests for tool functionality"""
    
    def test_tool_registration_and_execution(self):
        """Test tool registration and execution flow"""
        try:
            from config import config
            from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
            from vector_store import VectorStore
            
            # Create components
            store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
            tool_manager = ToolManager()
            search_tool = CourseSearchTool(store)
            outline_tool = CourseOutlineTool(store)
            
            # Register tools
            tool_manager.register_tool(search_tool)
            tool_manager.register_tool(outline_tool)
            
            # Test tool definitions
            definitions = tool_manager.get_tool_definitions()
            logger.info(f"Registered tools: {[d['name'] for d in definitions]}")
            
            assert len(definitions) == 2
            tool_names = [d["name"] for d in definitions]
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names
            
            logger.info("✓ Tools registered successfully")
            
            # Test tool execution with mock data
            with patch.object(store, 'search') as mock_search:
                from vector_store import SearchResults
                mock_search.return_value = SearchResults(
                    documents=["Test diagnostic content"],
                    metadata=[{"course_title": "Diagnostic Course", "lesson_number": 1}],
                    distances=[0.1]
                )
                
                result = tool_manager.execute_tool("search_course_content", query="test")
                assert "Diagnostic Course" in result
                logger.info("✓ Tool execution working")
            
        except Exception as e:
            logger.error(f"✗ Tool diagnostics failed: {e}")
            pytest.fail(f"Tool system failure: {e}")


class TestAIDiagnostics:
    """Diagnostic tests for AI functionality"""
    
    def test_ai_generator_initialization(self):
        """Test AI generator initialization with current config"""
        try:
            from config import config
            from ai_generator import AIGenerator
            
            if not config.ANTHROPIC_API_KEY:
                logger.warning("⚠ ANTHROPIC_API_KEY not set - skipping AI diagnostics")
                pytest.skip("API key not set")
            
            generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
            assert generator is not None
            
            logger.info(f"AI Generator initialized:")
            logger.info(f"  Model: {generator.model}")
            logger.info(f"  Temperature: {generator.base_params['temperature']}")
            logger.info(f"  Max tokens: {generator.base_params['max_tokens']}")
            
            logger.info("✓ AI Generator initialization successful")
            
        except Exception as e:
            logger.error(f"✗ AI Generator initialization failed: {e}")
            pytest.fail(f"AI initialization failure: {e}")
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_ai_api_call_structure(self, mock_anthropic):
        """Test AI API call structure without actual API call"""
        from config import config
        from ai_generator import AIGenerator
        
        # Mock client and response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Test diagnostic response"
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
        
        # Test simple response
        response = generator.generate_response("Diagnostic test query")
        
        assert response == "Test diagnostic response"
        
        # Verify API call structure
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        
        logger.info("API call structure:")
        logger.info(f"  Model: {call_args['model']}")
        logger.info(f"  Temperature: {call_args['temperature']}")
        logger.info(f"  Max tokens: {call_args['max_tokens']}")
        logger.info(f"  Messages: {len(call_args['messages'])}")
        logger.info(f"  System prompt length: {len(call_args['system'])}")
        
        assert call_args["model"] == config.ANTHROPIC_MODEL
        assert "tools" not in call_args  # No tools in simple call
        
        logger.info("✓ AI API call structure correct")


class TestFullSystemDiagnostics:
    """End-to-end diagnostic tests"""
    
    def test_full_system_component_chain(self):
        """Test that all system components can work together"""
        try:
            from config import config
            from rag_system import RAGSystem
            
            logger.info("Testing full system component chain...")
            
            # Check API key
            if not config.ANTHROPIC_API_KEY:
                logger.error("✗ Cannot test full system - ANTHROPIC_API_KEY not set")
                pytest.skip("API key required for full system test")
            
            # Initialize RAG system
            rag_system = RAGSystem(config)
            
            logger.info("✓ RAG system initialized")
            
            # Check tool availability
            tool_definitions = rag_system.tool_manager.get_tool_definitions()
            logger.info(f"Available tools: {[t['name'] for t in tool_definitions]}")
            assert len(tool_definitions) == 2
            
            # Check database
            analytics = rag_system.get_course_analytics()
            logger.info(f"Database status: {analytics['total_courses']} courses")
            
            logger.info("✓ Full system component chain working")
            
        except Exception as e:
            logger.error(f"✗ Full system test failed: {e}")
            pytest.fail(f"System integration failure: {e}")
    
    def test_simulate_common_failure_scenarios(self):
        """Test common failure scenarios to identify issues"""
        logger.info("Testing common failure scenarios...")
        
        # Scenario 1: Missing API key
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}):
            try:
                from config import Config
                test_config = Config()
                if not test_config.ANTHROPIC_API_KEY:
                    logger.info("✓ Missing API key detected correctly")
            except Exception as e:
                logger.error(f"✗ API key detection failed: {e}")
        
        # Scenario 2: Invalid ChromaDB path
        try:
            from vector_store import VectorStore
            invalid_path = "/invalid/path/that/does/not/exist"
            try:
                store = VectorStore(invalid_path, "all-MiniLM-L6-v2", 5)
                logger.warning("⚠ Invalid path did not raise error - may need validation")
            except Exception:
                logger.info("✓ Invalid ChromaDB path properly rejected")
        except Exception as e:
            logger.error(f"✗ Path validation test failed: {e}")
        
        logger.info("Common failure scenario tests completed")


def run_diagnostics():
    """Run all diagnostic tests and generate a report"""
    logger.info("=" * 50)
    logger.info("RAG SYSTEM DIAGNOSTIC REPORT")
    logger.info("=" * 50)
    
    # Run tests and collect results
    test_results = {}
    
    try:
        pytest.main([__file__, "-v", "--tb=short"])
    except SystemExit:
        pass  # pytest calls sys.exit
    
    logger.info("=" * 50)
    logger.info("DIAGNOSTIC REPORT COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_diagnostics()