# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Starting the Application
```bash
# Quick start - runs everything needed
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Environment Setup
```bash
# Install dependencies
uv sync

# Environment variables required in .env:
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Port Information
- Application runs on port 8000
- Web interface: http://localhost:8000  
- API docs: http://localhost:8000/docs

## Dev Tools Memory

- Use uv to run python files

## Frontend Quality Tools

### Code Quality Commands
```bash
# Install frontend dependencies (run once)
npm install

# Check all code quality (formatting + linting)
npm run quality-check

# Auto-fix all quality issues
npm run quality-fix

# Format code with Prettier
npm run format

# Check formatting without changes (CI-friendly)
npm run format:check

# Lint JavaScript and CSS
npm run lint

# Auto-fix linting issues
npm run lint:fix
```

### Development Workflow
1. Make frontend changes to files in `frontend/`
2. Run `npm run quality-fix` to auto-format and fix issues
3. Run `npm run quality-check` to verify quality standards
4. Commit changes

### Quality Tools Configured
- **Prettier**: Auto-formatting for HTML, CSS, JavaScript
- **ESLint**: JavaScript linting and error detection
- **Stylelint**: CSS linting and consistency checking

## Architecture Overview

This is a **tool-based RAG system** where Claude can intelligently search course materials using function calling rather than simple context injection.

### Core Flow
1. **Document Processing**: Course files → text chunks → embeddings via sentence-transformers
2. **Vector Storage**: ChromaDB stores embeddings in two collections (catalog + content)  
3. **Intelligent Search**: Claude uses CourseSearchTool to query vector database
4. **Response Generation**: Claude synthesizes answers from retrieved chunks
5. **Session Management**: Conversation history maintained per session

### Key Components

**RAGSystem** (`rag_system.py`) - Central orchestrator that coordinates all components

**VectorStore** (`vector_store.py`) - ChromaDB interface with dual collections:
- `course_catalog`: Course metadata for name resolution
- `course_content`: Actual text chunks for content search  

**AIGenerator** (`ai_generator.py`) - Claude API integration with tool execution handling

**ToolManager** (`search_tools.py`) - Function calling system that provides CourseSearchTool to Claude

**SessionManager** (`session_manager.py`) - Maintains conversation context with configurable history limits

### Configuration (`config.py`)
Critical settings that affect system behavior:
- `CHUNK_SIZE: 800` - Text chunk size for embeddings
- `CHUNK_OVERLAP: 100` - Overlap between chunks  
- `MAX_RESULTS: 5` - Search result limit
- `MAX_HISTORY: 2` - Conversation memory depth
- `ANTHROPIC_MODEL: "claude-sonnet-4-20250514"`

### Data Flow
- Documents loaded from `/docs` folder at startup
- Frontend sends queries to `/api/query` endpoint  
- RAG system processes with optional session context
- Claude can search vector store multiple times per query
- Sources tracked and returned to frontend

### Tool-Based Architecture
Unlike simple RAG systems that inject context, this uses Claude's function calling to:
- Search course catalog by name similarity
- Filter by course name and/or lesson number  
- Perform multiple searches per query if needed
- Maintain source attribution throughout

## File Structure Notes
- `backend/` - All Python backend code
- `frontend/` - Static HTML/CSS/JS served by FastAPI
- `docs/` - Course transcripts processed at startup  
- `chroma_db/` - Persistent vector database storage