import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import google.generativeai as genai
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")


@dataclass
class WritingTask:
    """Represents a writing task with source content and requirements"""
    source_content: str
    title: str
    target_style: str = "literary"
    target_length: str = "similar"  # "shorter", "similar", "longer"
    preserve_meaning: bool = True
    creativity_level: float = 0.7  # 0.0 to 1.0
    task_id: str = None
    
    def __post_init__(self):
        if self.task_id is None:
            self.task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


class AIWriterAgent:
    """
    AI-powered writing agent that transforms and "spins" content while preserving meaning
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        """
        Initialize the AI Writer Agent
        
        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.writing_history = []
        
    def _build_writing_prompt(self, task: WritingTask) -> str:
        """Build a comprehensive prompt for content transformation"""
        
        style_instructions = {
            "literary": "elegant, sophisticated prose with rich descriptions and varied sentence structure",
            "modern": "contemporary, accessible language with clear, direct communication",
            "classical": "formal, traditional prose reminiscent of classic literature",
            "journalistic": "clear, factual reporting style with engaging narrative flow",
            "creative": "imaginative, experimental prose with unique voice and perspective"
        }
        
        length_instructions = {
            "shorter": "condense the content while maintaining all key points and narrative elements",
            "similar": "maintain approximately the same length as the original",
            "longer": "expand the content with additional detail, context, and descriptive elements"
        }
        
        creativity_guidance = {
            0.0: "Stay very close to the original structure and phrasing",
            0.3: "Make moderate changes while preserving the original tone",
            0.5: "Balance creativity with faithfulness to the source",
            0.7: "Be creative with language and structure while preserving meaning",
            1.0: "Transform creatively while maintaining the core narrative and facts"
        }
        
        # Find closest creativity level
        creativity_key = min(creativity_guidance.keys(), 
                           key=lambda x: abs(x - task.creativity_level))
        
        prompt = f"""
You are an expert literary editor and writer tasked with transforming the following content. Your goal is to create a fresh, engaging version while preserving the core meaning and narrative.

**TRANSFORMATION REQUIREMENTS:**
- Style: {style_instructions.get(task.target_style, task.target_style)}
- Length: {length_instructions.get(task.target_length, task.target_length)}
- Creativity Level: {creativity_guidance[creativity_key]}
- Preserve Meaning: {"Absolutely maintain all factual content and narrative elements" if task.preserve_meaning else "Focus on creative expression over strict accuracy"}

**GUIDELINES:**
1. Maintain the narrative flow and character development
2. Preserve all important plot points and factual information
3. Use varied sentence structures and rich vocabulary
4. Ensure the transformed content feels natural and engaging
5. Keep the same general tone and mood as the original
6. If dialogue exists, preserve character voices while improving flow
7. Enhance descriptions and settings without changing the essence

**ORIGINAL CONTENT TO TRANSFORM:**
Title: {task.title}

{task.source_content}

**INSTRUCTIONS:**
Transform this content according to the requirements above. Return only the transformed content without any meta-commentary or explanations. The output should be publication-ready prose.
"""
        return prompt
    
    async def transform_content(self, task: WritingTask) -> Dict:
        """
        Transform content based on the writing task requirements
        
        Args:
            task: WritingTask containing source content and transformation parameters
            
        Returns:
            Dictionary containing the transformed content and metadata
        """
        try:
            print(f"Starting content transformation for: {task.title}")
            
            # Build the prompt
            prompt = self._build_writing_prompt(task)
            
            # Generate transformed content
            response = await self._generate_with_retry(prompt)
            
            if not response:
                raise Exception("Failed to generate content after retries")
            
            # Extract and clean the generated content
            transformed_content = response.text.strip()
            
            # Calculate metrics
            original_words = len(task.source_content.split())
            transformed_words = len(transformed_content.split())
            
            # Prepare result
            result = {
                'task_id': task.task_id,
                'original_title': task.title,
                'transformed_content': transformed_content,
                'original_word_count': original_words,
                'transformed_word_count': transformed_words,
                'length_ratio': transformed_words / original_words if original_words > 0 else 0,
                'transformation_parameters': {
                    'style': task.target_style,
                    'target_length': task.target_length,
                    'creativity_level': task.creativity_level,
                    'preserve_meaning': task.preserve_meaning
                },
                'generated_at': datetime.now().isoformat(),
                'agent': 'AIWriterAgent',
                'model_used': self.model.model_name
            }
            
            # Add to history
            self.writing_history.append(result)
            
            print(f"Content transformation completed:")
            print(f"  Original words: {original_words}")
            print(f"  Transformed words: {transformed_words}")
            print(f"  Length ratio: {result['length_ratio']:.2f}")
            
            return result
            
        except Exception as e:
            error_result = {
                'task_id': task.task_id,
                'error': str(e),
                'generated_at': datetime.now().isoformat(),
                'agent': 'AIWriterAgent'
            }
            print(f"Error in content transformation: {e}")
            return error_result
    
    async def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Generate content with retry logic"""
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(
                    self.model.generate_content, 
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=4000,
                    )
                )
                
                if response and response.text:
                    return response
                    
            except Exception as e:
                print(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise e
        
        return None
    
    def batch_transform(self, tasks: List[WritingTask]) -> List[Dict]:
        """
        Transform multiple pieces of content
        
        Args:
            tasks: List of WritingTask objects
            
        Returns:
            List of transformation results
        """
        async def _batch_process():
            results = []
            for i, task in enumerate(tasks, 1):
                print(f"Processing task {i}/{len(tasks)}: {task.title}")
                result = await self.transform_content(task)
                results.append(result)
                
                # Add delay between requests to respect rate limits
                if i < len(tasks):
                    await asyncio.sleep(1)
            
            return results
        
        return asyncio.run(_batch_process())
    
    def get_writing_history(self) -> List[Dict]:
        """Get the history of all writing tasks"""
        return self.writing_history.copy()
    
    def save_result(self, result: Dict, output_file: str = None) -> str:
        """
        Save transformation result to file
        
        Args:
            result: Transformation result dictionary
            output_file: Optional custom output filename
            
        Returns:
            Path to saved file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"transformed_content_{result.get('task_id', timestamp)}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Result saved to: {output_file}")
        return output_file
    
    def create_writing_variations(self, source_content: str, title: str, 
                                count: int = 3) -> List[Dict]:
        """
        Create multiple variations of the same content with different parameters
        
        Args:
            source_content: Original content to transform
            title: Content title
            count: Number of variations to create
            
        Returns:
            List of transformation results
        """
        # Define different transformation parameters
        variation_configs = [
            {'style': 'literary', 'creativity_level': 0.5, 'target_length': 'similar'},
            {'style': 'modern', 'creativity_level': 0.7, 'target_length': 'shorter'},
            {'style': 'classical', 'creativity_level': 0.4, 'target_length': 'longer'},
            {'style': 'creative', 'creativity_level': 0.8, 'target_length': 'similar'},
            {'style': 'journalistic', 'creativity_level': 0.3, 'target_length': 'shorter'}
        ]
        
        # Create tasks for the requested number of variations
        tasks = []
        for i in range(min(count, len(variation_configs))):
            config = variation_configs[i]
            task = WritingTask(
                source_content=source_content,
                title=f"{title} - Variation {i+1}",
                **config
            )
            tasks.append(task)
        
        return self.batch_transform(tasks)


# Example usage and testing
async def test_writer_agent():
    """Test the AI Writer Agent"""
    
    
    writer = AIWriterAgent(API_KEY)
    
    # Sample content for testing
    sample_content = """
    The morning sun cast long shadows across the cobblestone streets as Margaret hurried 
    toward the marketplace. Her basket swung rhythmically at her side, empty save for 
    the few copper coins that jingled softly with each step. The baker's shop came into 
    view, its windows glowing warmly in the early light, and the scent of fresh bread 
    filled the air. She had promised her children breakfast, and despite their meager 
    circumstances, she was determined to keep that promise.
    """
    
    # Create a writing task
    task = WritingTask(
        source_content=sample_content,
        title="Margaret's Morning Journey",
        target_style="literary",
        creativity_level=0.6,
        target_length="longer"
    )
    
    # Transform the content
    result = await writer.transform_content(task)
    
    if 'error' not in result:
        print("Transformation successful!")
        print(f"Original: {result['original_word_count']} words")
        print(f"Transformed: {result['transformed_word_count']} words")
        print(f"Preview: {result['transformed_content'][:200]}...")
        
        # Save the result
        writer.save_result(result)
    else:
        print(f"Transformation failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_writer_agent())