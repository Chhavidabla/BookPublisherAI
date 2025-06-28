#!/usr/bin/env python3
"""
Automated Book Publication Workflow - Main Orchestrator
Coordinates the entire pipeline from scraping to final publication
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Import our modules
from scraping.scrape import WikisourceScaper
from ai_agents.writer_agent import AIWriterAgent, WritingTask
from ai_agents.reviewer_agent import AIReviewerAgent
from ai_agents.editor_agent import AIEditorAgent
from storage.chromadb_interface import ContentStorage
from storage.versioning import VersionManager
from human_review.review_interface import HumanReviewInterface


class BookPublicationWorkflow:
    """
    Main orchestrator for the automated book publication workflow
    """
    
    def __init__(self, config_file: str = "config.json"):
        """Initialize the workflow with configuration"""
        self.config = self._load_config(config_file)
        self.output_dir = Path(self.config.get('output_dir', 'output'))
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.scraper = WikisourceScaper(str(self.output_dir / 'scraped_content'))
        self.storage = ContentStorage(self.config.get('chromadb_path', 'content_db'))
        self.version_manager = VersionManager(str(self.output_dir / 'versions'))
        
        # Initialize AI agents
        api_key = self.config.get('gemini_api_key')
        if not api_key:
            raise ValueError("Gemini API key not found in configuration")
        
        self.writer_agent = AIWriterAgent(api_key)
        self.reviewer_agent = AIReviewerAgent(api_key)
        self.editor_agent = AIEditorAgent(api_key)
        
        # Initialize human review interface
        self.human_interface = HumanReviewInterface(
            storage=self.storage,
            version_manager=self.version_manager
        )
        
        # Workflow state
        self.current_project = None
        self.workflow_history = []
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            'output_dir': 'output',
            'chromadb_path': 'content_db',
            'gemini_api_key': '',
            'scraping': {
                'delay_between_requests': 2,
                'max_retries': 3
            },
            'ai_agents': {
                'writer': {
                    'default_style': 'literary',
                    'creativity_level': 0.7
                },
                'reviewer': {
                    'quality_threshold': 0.7,
                    'max_iterations': 3
                },
                'editor': {
                    'final_polish': True,
                    'style_consistency': True
                }
            },
            'human_review': {
                'require_approval': True,
                'allow_multiple_reviewers': True
            }
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
            default_config.update(user_config)
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default configuration file: {config_file}")
            print("Please update the gemini_api_key in the config file")
        
        return default_config
    
    async def create_project(self, project_name: str, source_urls: List[str]) -> str:
        """
        Create a new book publication project
        
        Args:
            project_name: Name of the project
            source_urls: List of URLs to scrape content from
            
        Returns:
            Project ID
        """
        project_id = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        project_data = {
            'project_id': project_id,
            'project_name': project_name,
            'source_urls': source_urls,
            'created_at': datetime.now().isoformat(),
            'status': 'created',
            'stages_completed': [],
            'current_stage': 'scraping'
        }
        
        # Save project metadata
        project_file = self.output_dir / f"{project_id}_project.json"
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        self.current_project = project_data
        print(f"Created project: {project_name} (ID: {project_id})")
        
        return project_id
    
    async def run_full_workflow(self, project_id: str) -> Dict:
        """
        Run the complete workflow for a project
        
        Args:
            project_id: The project to process
            
        Returns:
            Final workflow results
        """
        print(f"Starting full workflow for project: {project_id}")
        
        try:
            # Stage 1: Scraping
            print("\n=== STAGE 1: CONTENT SCRAPING ===")
            scraped_content = await self._run_scraping_stage(project_id)
            
            # Stage 2: AI Writing
            print("\n=== STAGE 2: AI CONTENT TRANSFORMATION ===")
            written_content = await self._run_writing_stage(scraped_content)
            
            # Stage 3: AI Review
            print("\n=== STAGE 3: AI CONTENT REVIEW ===")
            reviewed_content = await self._run_review_stage(written_content)
            
            # Stage 4: Human Review
            print("\n=== STAGE 4: HUMAN REVIEW ===")
            human_approved_content = await self._run_human_review_stage(reviewed_content)
            
            # Stage 5: AI Editing
            print("\n=== STAGE 5: FINAL AI EDITING ===")
            final_content = await self._run_editing_stage(human_approved_content)
            
            # Stage 6: Storage and Publication
            print("\n=== STAGE 6: STORAGE AND PUBLICATION ===")
            publication_result = await self._run_publication_stage(final_content)
            
            # Update project status
            self._update_project_status(project_id, 'completed', 'publication')
            
            print(f"\n✅ Workflow completed successfully for project: {project_id}")
            return publication_result
            
        except Exception as e:
            print(f"\n❌ Workflow failed: {str(e)}")
            self._update_project_status(project_id, 'failed', error=str(e))
            raise e
    
    async def _run_scraping_stage(self, project_id: str) -> List[Dict]:
        """Run the content scraping stage"""
        project_data = self._load_project(project_id)
        source_urls = project_data['source_urls']
        
        scraped_results = []
        for url in source_urls:
            print(f"Scraping: {url}")
            result = await self.scraper.scrape_chapter(url)
            scraped_results.append(result)
            
            # Store in version control
            if 'error' not in result:
                version_id = self.version_manager.create_version(
                    content=result['content'],
                    metadata={
                        'stage': 'scraped',
                        'source_url': url,
                        'title': result['title'],
                        'project_id': project_id
                    }
                )
                result['version_id'] = version_id
        
        self._update_project_status(project_id, 'in_progress', 'scraping')
        return scraped_results
    
    async def _run_writing_stage(self, scraped_content: List[Dict]) -> List[Dict]:
        """Run the AI writing transformation stage"""
        written_results = []
        
        for content_item in scraped_content:
            if 'error' in content_item:
                written_results.append(content_item)
                continue
            
            # Create writing task
            task = WritingTask(
                source_content=content_item['content'],
                title=content_item['title'],
                target_style=self.config['ai_agents']['writer']['default_style'],
                creativity_level=self.config['ai_agents']['writer']['creativity_level']
            )
            
            # Transform content
            result = await self.writer_agent.transform_content(task)
            
            if 'error' not in result:
                # Store transformed version
                version_id = self.version_manager.create_version(
                    content=result['transformed_content'],
                    metadata={
                        'stage': 'ai_written',
                        'original_version_id': content_item.get('version_id'),
                        'transformation_params': result['transformation_parameters'],
                        'project_id': self.current_project['project_id']
                    }
                )
                result['version_id'] = version_id
                result['original_content'] = content_item
            
            written_results.append(result)
        
        return written_results
    
    async def _run_review_stage(self, written_content: List[Dict]) -> List[Dict]:
        """Run the AI review stage"""
        reviewed_results = []
        
        for content_item in written_content:
            if 'error' in content_item:
                reviewed_results.append(content_item)
                continue
            
            # Review the transformed content
            review_result = await self.reviewer_agent.review_content(
                content=content_item['transformed_content'],
                original_content=content_item['original_content']['content'],
                title=content_item['original_title']
            )
            
            if 'error' not in review_result:
                # Store review version
                version_id = self.version_manager.create_version(
                    content=content_item['transformed_content'],
                    metadata={
                        'stage': 'ai_reviewed',
                        'written_version_id': content_item.get('version_id'),
                        'review_score': review_result['overall_score'],
                        'review_feedback': review_result['feedback'],
                        'project_id': self.current_project['project_id']
                    }
                )
                review_result['version_id'] = version_id
                review_result['content_item'] = content_item
            
            reviewed_results.append(review_result)
        
        return reviewed_results
    
    async def _run_human_review_stage(self, reviewed_content: List[Dict]) -> List[Dict]:
        """Run the human review stage"""
        if not self.config['human_review']['require_approval']:
            print("Human review disabled, skipping...")
            return reviewed_content
        
        print("Starting human review interface...")
        
        # Prepare content for human review
        review_items = []
        for item in reviewed_content:
            if 'error' not in item and 'content_item' in item:
                review_items.append({
                    'content': item['content_item']['transformed_content'],
                    'title': item['content_item']['original_title'],
                    'ai_feedback': item['feedback'],
                    'ai_score': item['overall_score'],
                    'version_id': item['version_id']
                })
        
        # Launch human review interface
        approved_items = await self.human_interface.start_review_session(review_items)
        
        # Process approved content
        human_approved = []
        for item in approved_items:
            # Create version for human-approved content
            version_id = self.version_manager.create_version(
                content=item['content'],
                metadata={
                    'stage': 'human_approved',
                    'previous_version_id': item['version_id'],
                    'human_feedback': item.get('human_feedback', ''),
                    'approval_timestamp': datetime.now().isoformat(),
                    'project_id': self.current_project['project_id']
                }
            )
            item['version_id'] = version_id
            human_approved.append(item)
        
        return human_approved
    
    async def _run_editing_stage(self, human_approved_content: List[Dict]) -> List[Dict]:
        """Run the final AI editing stage"""
        edited_results = []
        
        for content_item in human_approved_content:
            if 'error' in content_item:
                edited_results.append(content_item)
                continue
            
            # Final editing pass
            editing_result = await self.editor_agent.edit_content(
                content=content_item['content'],
                title=content_item['title'],
                final_polish=self.config['ai_agents']['editor']['final_polish']
            )
            
            if 'error' not in editing_result:
                # Store final edited version
                version_id = self.version_manager.create_version(
                    content=editing_result['edited_content'],
                    metadata={
                        'stage': 'final_edited',
                        'human_approved_version_id': content_item.get('version_id'),
                        'editing_changes': editing_result['changes_made'],
                        'project_id': self.current_project['project_id']
                    }
                )
                editing_result['version_id'] = version_id
                editing_result['content_item'] = content_item
            
            edited_results.append(editing_result)
        
        return edited_results
    
    async def _run_publication_stage(self, final_content: List[Dict]) -> Dict:
        """Run the final storage and publication stage"""
        publication_results = []
        
        for content_item in final_content:
            if 'error' in content_item:
                publication_results.append(content_item)
                continue
            
            # Store in ChromaDB for semantic search
            content_id = await self.storage.store_content(
                content=content_item['edited_content'],
                metadata={
                    'title': content_item['content_item']['title'],
                    'stage': 'published',
                    'version_id': content_item['version_id'],
                    'project_id': self.current_project['project_id'],
                    'publication_date': datetime.now().isoformat()
                }
            )
            
            content_item['content_id'] = content_id
            publication_results.append(content_item)
            
            print(f"Published: {content_item['content_item']['title']} (ID: {content_id})")
        
        # Create final publication summary
        publication_summary = {
            'project_id': self.current_project['project_id'],
            'total_chapters': len(publication_results),
            'successful_publications': len([r for r in publication_results if 'error' not in r]),
            'failed_publications': len([r for r in publication_results if 'error' in r]),
            'publication_date': datetime.now().isoformat(),
            'content_ids': [r.get('content_id') for r in publication_results if 'content_id' in r]
        }
        
        # Save publication summary
        summary_file = self.output_dir / f"{self.current_project['project_id']}_publication_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(publication_summary, f, indent=2)
        
        return publication_summary
    
    def _load_project(self, project_id: str) -> Dict:
        """Load project data"""
        project_file = self.output_dir / f"{project_id}_project.json"
        if not project_file.exists():
            raise FileNotFoundError(f"Project file not found: {project_file}")
        
        with open(project_file, 'r') as f:
            return json.load(f)
    
    def _update_project_status(self, project_id: str, status: str, stage: str = None, error: str = None):
        """Update project status"""
        project_data = self._load_project(project_id)
        project_data['status'] = status
        project_data['last_updated'] = datetime.now().isoformat()
        
        if stage:
            project_data['current_stage'] = stage
            if stage not in project_data['stages_completed']:
                project_data['stages_completed'].append(stage)
        
        if error:
            project_data['error'] = error
        
        project_file = self.output_dir / f"{project_id}_project.json"
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        self.current_project = project_data
    
    async def search_published_content(self, query: str, limit: int = 5) -> List[Dict]:
        """Search published content using semantic search"""
        return await self.storage.search_content(query, limit)
    
    def get_project_status(self, project_id: str) -> Dict:
        """Get current project status"""
        return self._load_project(project_id)
    
    def list_projects(self) -> List[Dict]:
        """List all projects"""
        projects = []
        for project_file in self.output_dir.glob("*_project.json"):
            with open(project_file, 'r') as f:
                projects.append(json.load(f))
        return projects


async def main():
    """Main entry point for the workflow"""
    parser = argparse.ArgumentParser(description='Automated Book Publication Workflow')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--project-name', required=True, help='Name of the project')
    parser.add_argument('--urls', nargs='+', required=True, help='Source URLs to scrape')
    parser.add_argument('--mode', choices=['full', 'scrape-only', 'continue'], 
                       default='full', help='Workflow mode')
    
    args = parser.parse_args()
    
    try:
        # Initialize workflow
        workflow = BookPublicationWorkflow(args.config)
        
        if args.mode == 'full':
            # Create new project and run full workflow
            project_id = await workflow.create_project(args.project_name, args.urls)
            result = await workflow.run_full_workflow(project_id)
            
            print(f"\n🎉 Publication completed!")
            print(f"Project ID: {project_id}")
            print(f"Published chapters: {result['successful_publications']}")
            print(f"Failed chapters: {result['failed_publications']}")
            
        elif args.mode == 'scrape-only':
            # Just scrape content for testing
            project_id = await workflow.create_project(args.project_name, args.urls)
            scraped_content = await workflow._run_scraping_stage(project_id)
            
            print(f"\n✅ Scraping completed!")
            print(f"Scraped {len(scraped_content)} items")
        
        else:
            print("Continue mode not implemented yet")
    
    except Exception as e:
        print(f"❌ Workflow failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())