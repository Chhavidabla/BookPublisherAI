# BookPublisherAI
# Automated Book Publication Workflow

A sophisticated AI-powered system that automates the entire book publication process from web content scraping to final publication with human-in-the-loop quality control.

## 🚀 Features

- **Web Scraping**: Automated content extraction from Wikisource with screenshot capture
- **AI Content Transformation**: Intelligent "spinning" of content while preserving meaning
- **Multi-Agent AI Pipeline**: Writer, Reviewer, and Editor agents working in sequence
- **Human Review Interface**: Interactive review system with approval workflows
- **Version Control**: Complete versioning of all content iterations
- **Semantic Search**: ChromaDB-powered intelligent content retrieval
- **Reinforcement Learning**: Adaptive search algorithm for optimal content retrieval

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Scraping  │───▶│  AI Writer      │───▶│  AI Reviewer    │
│   (Playwright)  │    │  (Gemini)       │    │  (Gemini)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Final Storage │◀───│  AI Editor      │◀───│  Human Review   │
│   (ChromaDB)    │    │  (Gemini)       │    │  (Interface)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
book-publisher-ai/
├── scraping/
│   └── scrape.py              # Web scraping with Playwright
├── ai_agents/
│   ├── writer_agent.py        # Content transformation agent
│   ├── reviewer_agent.py      # Quality review agent
│   └── editor_agent.py        # Final editing agent
├── human_review/
│   └── review_interface.py    # Human review UI
├── storage/
│   ├── chromadb_interface.py  # Vector database interface
│   └── versioning.py          # Content version management
├── utils/
│   └── screenshot.py          # Screenshot utilities
├── main.py                    # Main workflow orchestrator
├── requirements.txt           # Python dependencies
├── config.json               # Configuration file
└── README.md                 # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.9 or higher
- Node.js (for Playwright browser automation)
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/book-publisher-ai.git
   cd book-publisher-ai
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configure the system**
   ```bash
   cp config.json.template config.json
   # Edit config.json and add your Gemini API key
   ```

5. **Initialize database**
   ```bash
   python -c "from storage.chromadb_interface import ContentStorage; ContentStorage('content_db')"
   ```

## 🔧 Configuration

Edit `config.json` to customize the workflow:

```json
{
  "gemini_api_key": "your_api_key_here",
  "ai_agents": {
    "writer": {
      "creativity_level": 0.7,
      "target_style": "literary"
    }
  }
}
```

Key configuration options:

- **gemini_api_key**: Your Google AI API key
- **creativity_level**: AI creativity (0.0-1.0)
- **target_style**: Writing style (literary, modern, classical, etc.)
- **human_review.require_approval**: Enable/disable human review

## 🚀 Usage

### Basic Usage

Transform content from a single Wikisource chapter:

```bash
python main.py \
  --project-name "The Gates of Morning" \
  --urls "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1"
```

### Advanced Usage

Multiple chapters with custom configuration:

```bash
python main.py \
  --project-name "Complete Novel" \
  --urls \
    "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1" \
    "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_2" \
  --config custom_config.json
```

### Scraping Only

For testing or content analysis:

```bash
python main.py \
  --project-name "Test Scrape" \
  --urls "https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1" \
  --mode scrape-only
```

## 🔄 Workflow Stages

### 1. Content Scraping
- Extracts text content from Wikisource pages
- Captures full-page screenshots for reference
- Cleans and structures the content
- Stores raw content with metadata

### 2. AI Writing Transformation
- Applies intelligent "spinning" to the content
- Preserves original meaning and narrative flow
- Adapts writing style according to configuration
- Maintains character development and plot points

### 3. AI Quality Review
- Evaluates transformed content quality
- Checks for narrative consistency
- Provides detailed feedback and scoring
- Suggests improvements if needed

### 4. Human Review (Optional)
- Interactive web interface for human reviewers
- Side-by-side comparison of original and transformed content
- Approval/rejection workflow with comments
- Support for multiple reviewer roles

### 5. Final AI Editing
- Grammar and style refinement
- Final polish and consistency checks
- Publication-ready formatting
- Quality assurance

### 6. Storage and Publication
- Stores final content in ChromaDB vector database
- Creates semantic embeddings for search
- Maintains complete version history
- Enables intelligent content retrieval

## 🔍 Content Search

Search published content using semantic similarity:

```python
from main import BookPublicationWorkflow

workflow = BookPublicationWorkflow()
results = await workflow.search_published_content("morning adventure", limit=5)
```

## 📊 Monitoring and Analytics

### Project Status

Check project progress:

```python
status = workflow.get_project_status("project_id")
print(f"Current stage: {status['current_stage']}")
print(f"Completed stages: {status['stages_completed']}")
```

### Content Metrics

Track content transformation metrics:
- Original vs. transformed word count
- Quality scores from AI review
- Human approval ratings
- Processing time per stage

## 🛡️ Quality Assurance

### AI Quality Control
- Multi-stage AI review process
- Configurable quality thresholds
- Automatic iteration for low-quality content
- Consistency checking across chapters

### Human Oversight
- Mandatory human approval for publication
- Interactive review interface
- Comment and feedback system
- Version comparison tools

### Content Integrity
- Meaning preservation validation
- Plagiarism detection capabilities
- Original source attribution
- Complete audit trail

## 🔧 Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black .
flake8 .
```

### Adding New AI Agents

1. Create agent class in `ai_agents/`
2. Implement required methods:
   - `process_content()`
   - `get_agent_info()`
3. Register agent in main workflow
4. Add configuration options

### Custom Storage Backends

Implement the storage interface:

```python
class CustomStorage:
    async def store_content(self, content, metadata):
        # Implementation
        pass
    
    async def search_content(self, query, limit):
        # Implementation
        pass
```

## 📈 Performance Optimization

### Parallel Processing
- Concurrent AI agent processing
- Batch content transformation
- Async/await throughout the pipeline

### Caching
- API response caching
- Intermediate result storage
- Smart cache invalidation

### Resource Management
- Memory usage monitoring
- API rate limit handling
- Graceful error recovery
