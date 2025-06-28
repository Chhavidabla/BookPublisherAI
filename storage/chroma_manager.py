# storage/chroma_manager.py - ChromaDB Integration for Content Versioning

import chromadb
from chromadb.config import Settings
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

class ChromaContentManager:
    """Manages content versioning and retrieval using ChromaDB"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB client and collections"""
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collections for different content types
        self.content_collection = self._get_or_create_collection("book_content")
        self.versions_collection = self._get_or_create_collection("content_versions")
        self.metadata_collection = self._get_or_create_collection("content_metadata")
    
    def _get_or_create_collection(self, name: str):
        """Get existing collection or create new one"""
        try:
            return self.client.get_collection(name=name)
        except ValueError:
            return self.client.create_collection(name=name)
    
    def store_content(self, content: str, chapter_id: str, version: int = 1, 
                     metadata: Dict = None) -> str:
        """
        Store content with versioning support
        
        Args:
            content: The content to store
            chapter_id: Unique identifier for the chapter
            version: Version number
            metadata: Additional metadata
        
        Returns:
            Unique document ID
        """
        doc_id = f"{chapter_id}_v{version}_{uuid.uuid4().hex[:8]}"
        content_hash = self._generate_content_hash(content)
        
        # Prepare metadata
        store_metadata = {
            "chapter_id": chapter_id,
            "version": version,
            "content_hash": content_hash,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(content.split()),
            "char_count": len(content)
        }
        
        if metadata:
            store_metadata.update(metadata)
        
        # Store in content collection
        self.content_collection.add(
            documents=[content],
            metadatas=[store_metadata],
            ids=[doc_id]
        )
        
        # Update version tracking
        self._update_version_tracking(chapter_id, version, doc_id, content_hash)
        
        return doc_id
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _update_version_tracking(self, chapter_id: str, version: int, 
                               doc_id: str, content_hash: str):
        """Update version tracking information"""
        version_id = f"version_{chapter_id}_{version}"
        
        version_data = {
            "chapter_id": chapter_id,
            "version": version,
            "doc_id": doc_id,
            "content_hash": content_hash,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            self.versions_collection.add(
                documents=[json.dumps(version_data)],
                metadatas=[{"type": "version_info", "chapter_id": chapter_id}],
                ids=[version_id]
            )
        except Exception as e:
            print(f"Version tracking update failed: {e}")
    
    def retrieve_content(self, chapter_id: str, version: Optional[int] = None) -> Dict:
        """
        Retrieve content by chapter ID and optional version
        
        Args:
            chapter_id: Chapter identifier
            version: Specific version (latest if None)
        
        Returns:
            Dictionary with content and metadata
        """
        try:
            if version:
                # Get specific version
                results = self.content_collection.get(
                    where={"chapter_id": chapter_id, "version": version},
                    include=["documents", "metadatas"]
                )
            else:
                # Get latest version
                results = self.content_collection.get(
                    where={"chapter_id": chapter_id},
                    include=["documents", "metadatas"]
                )
                
                if results['documents']:
                    # Sort by version to get latest
                    sorted_results = sorted(
                        zip(results['documents'], results['metadatas']),
                        key=lambda x: x[1].get('version', 0),
                        reverse=True
                    )
                    results['documents'] = [sorted_results[0][0]]
                    results['metadatas'] = [sorted_results[0][1]]
            
            if results['documents']:
                return {
                    "content": results['documents'][0],
                    "metadata": results['metadatas'][0],
                    "found": True
                }
            else:
                return {"found": False, "error": "Content not found"}
                
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def search_similar_content(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search for similar content using semantic similarity
        
        Args:
            query: Search query
            n_results: Number of results to return
        
        Returns:
            List of similar content with similarity scores
        """
        try:
            results = self.content_collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            similar_content = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                similar_content.append({
                    "content": doc,
                    "metadata": metadata,
                    "similarity_score": 1 - distance,  # Convert distance to similarity
                    "rank": i + 1
                })
            
            return similar_content
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_chapter_versions(self, chapter_id: str) -> List[Dict]:
        """Get all versions of a specific chapter"""
        try:
            results = self.content_collection.get(
                where={"chapter_id": chapter_id},
                include=["documents", "metadatas"]
            )
            
            versions = []
            for doc, metadata in zip(results['documents'], results['metadatas']):
                versions.append({
                    "version": metadata.get('version'),
                    "timestamp": metadata.get('timestamp'),
                    "word_count": metadata.get('word_count'),
                    "content_preview": doc[:200] + "..." if len(doc) > 200 else doc
                })
            
            # Sort by version number
            versions.sort(key=lambda x: x.get('version', 0))
            return versions
            
        except Exception as e:
            print(f"Error retrieving versions: {e}")
            return []
    
    def delete_content(self, chapter_id: str, version: Optional[int] = None) -> bool:
        """Delete content by chapter ID and optional version"""
        try:
            if version:
                # Delete specific version
                where_clause = {"chapter_id": chapter_id, "version": version}
            else:
                # Delete all versions of chapter
                where_clause = {"chapter_id": chapter_id}
            
            # Get IDs to delete
            results = self.content_collection.get(
                where=where_clause,
                include=["metadatas"]
            )
            
            if results['ids']:
                self.content_collection.delete(ids=results['ids'])
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Delete error: {e}")
            return False
    
    def get_content_stats(self) -> Dict:
        """Get statistics about stored content"""
        try:
            all_content = self.content_collection.get(include=["metadatas"])
            
            if not all_content['metadatas']:
                return {"total_documents": 0}
            
            chapters = set()
            versions = 0
            total_words = 0
            
            for metadata in all_content['metadatas']:
                chapters.add(metadata.get('chapter_id'))
                versions += 1
                total_words += metadata.get('word_count', 0)
            
            return {
                "total_documents": len(all_content['metadatas']),
                "unique_chapters": len(chapters),
                "total_versions": versions,
                "total_words": total_words,
                "average_words_per_doc": total_words / len(all_content['metadatas']) if all_content['metadatas'] else 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def backup_collection(self, output_file: str):
        """Backup collection data to JSON file"""
        try:
            all_data = self.content_collection.get(
                include=["documents", "metadatas", "ids"]
            )
            
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "documents": all_data['documents'],
                    "metadatas": all_data['metadatas'],
                    "ids": all_data['ids']
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Backup error: {e}")
            return False

# Example usage and testing
if __name__ == "__main__":
    # Initialize manager
    manager = ChromaContentManager()
    
    # Store sample content
    sample_content = """
    Elena stepped through the ancient gates, her heart pounding with anticipation. 
    The courtyard beyond was vast and mysterious, filled with echoes of forgotten times. 
    Stone gargoyles perched on weathered columns watched her progress with silent judgment.
    """
    
    # Store content
    doc_id = manager.store_content(
        content=sample_content,
        chapter_id="chapter_1",
        version=1,
        metadata={"author": "AI Writer", "genre": "fantasy"}
    )
    
    print(f"Stored content with ID: {doc_id}")
    
    # Retrieve content
    retrieved = manager.retrieve_content("chapter_1")
    if retrieved['found']:
        print(f"Retrieved: {retrieved['content'][:100]}...")
    
    # Search similar content
    similar = manager.search_similar_content("ancient gates mystery")
    print(f"Found {len(similar)} similar documents")
    
    # Get stats
    stats = manager.get_content_stats()
    print(f"Content stats: {stats}")