# interface/human_loop.py - Human-in-the-Loop Interface

import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os

@dataclass
class ReviewRequest:
    """Structure for human review requests"""
    request_id: str
    content: str
    original_content: str
    ai_feedback: Dict
    review_type: str  # 'writer', 'reviewer', 'editor'
    priority: int  # 1-5, 5 being highest
    created_at: str
    status: str  # 'pending', 'in_progress', 'completed', 'rejected'

@dataclass
class HumanFeedback:
    """Structure for human feedback"""
    request_id: str
    reviewer_id: str
    action: str  # 'approve', 'revise', 'reject'
    feedback: str
    suggested_changes: str
    rating: int  # 1-10
    timestamp: str

class HumanLoopInterface:
    """Interface for managing human-in-the-loop interactions"""
    
    def __init__(self, data_dir: str = "./human_loop_data"):
        """Initialize the human loop interface"""
        self.data_dir = data_dir
        self.pending_reviews = []
        self.completed_reviews = []
        self.feedback_callbacks = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load existing review requests and feedback"""
        try:
            pending_file = os.path.join(self.data_dir, "pending_reviews.json")
            completed_file = os.path.join(self.data_dir, "completed_reviews.json")
            
            if os.path.exists(pending_file):
                with open(pending_file, 'r') as f:
                    data = json.load(f)
                    self.pending_reviews = [ReviewRequest(**item) for item in data]
            
            if os.path.exists(completed_file):
                with open(completed_file, 'r') as f:
                    data = json.load(f)
                    self.completed_reviews = [HumanFeedback(**item) for item in data]
                    
        except Exception as e:
            print(f"Error loading existing data: {e}")
    
    def _save_data(self):
        """Save current state to files"""
        try:
            pending_file = os.path.join(self.data_dir, "pending_reviews.json")
            completed_file = os.path.join(self.data_dir, "completed_reviews.json")
            
            with open(pending_file, 'w') as f:
                json.dump([asdict(req) for req in self.pending_reviews], f, indent=2)
            
            with open(completed_file, 'w') as f:
                json.dump([asdict(feedback) for feedback in self.completed_reviews], f, indent=2)
                
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def submit_for_review(self, content: str, original_content: str, 
                         ai_feedback: Dict, review_type: str = 'reviewer',
                         priority: int = 3) -> str:
        """
        Submit content for human review
        
        Args:
            content: Content to be reviewed
            original_content: Original source content
            ai_feedback: AI-generated feedback
            review_type: Type of review needed
            priority: Priority level (1-5)
        
        Returns:
            Request ID for tracking
        """
        request_id = f"{review_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.pending_reviews)}"
        
        review_request = ReviewRequest(
            request_id=request_id,
            content=content,
            original_content=original_content,
            ai_feedback=ai_feedback,
            review_type=review_type,
            priority=priority,
            created_at=datetime.now().isoformat(),
            status='pending'
        )
        
        self.pending_reviews.append(review_request)
        self._save_data()
        
        print(f"✅ Content submitted for {review_type} review - ID: {request_id}")
        return request_id
    
    def get_pending_reviews(self, review_type: Optional[str] = None,
                          priority_min: int = 1) -> List[ReviewRequest]:
        """Get pending reviews, optionally filtered by type and priority"""
        filtered_reviews = []
        
        for review in self.pending_reviews:
            if review.status != 'pending':
                continue
            
            if review_type and review.review_type != review_type:
                continue
            
            if review.priority < priority_min:
                continue
            
            filtered_reviews.append(review)
        
        # Sort by priority (highest first) and creation time
        filtered_reviews.sort(key=lambda x: (-x.priority, x.created_at))
        return filtered_reviews
    
    def display_review_interface(self, request_id: str) -> bool:
        """Display interactive review interface for a specific request"""
        request = self._find_request_by_id(request_id)
        if not request:
            print(f"❌ Review request {request_id} not found")
            return False
        
        print("\n" + "="*80)
        print(f"📋 HUMAN REVIEW INTERFACE - {request.review_type.upper()}")
        print("="*80)
        print(f"Request ID: {request.request_id}")
        print(f"Priority: {request.priority}/5")
        print(f"Created: {request.created_at}")
        print("\n" + "-"*40 + " CONTENT TO REVIEW " + "-"*40)
        print(request.content)
        
        if request.original_content:
            print("\n" + "-"*40 + " ORIGINAL CONTENT " + "-"*40)
            print(request.original_content[:500] + "..." if len(request.original_content) > 500 else request.original_content)
        
        if request.ai_feedback:
            print("\n" + "-"*40 + " AI FEEDBACK " + "-"*40)
            if isinstance(request.ai_feedback, dict):
                for key, value in request.ai_feedback.items():
                    print(f"{key.title()}: {value}")
            else:
                print(request.ai_feedback)
        
        print("\n" + "="*80)
        return True
    
    def collect_human_feedback(self, request_id: str, reviewer_id: str) -> Optional[HumanFeedback]:
        """Collect human feedback interactively"""
        request = self._find_request_by_id(request_id)
        if not request:
            return None
        
        if not self.display_review_interface(request_id):
            return None
        
        print("\n📝 Please provide your feedback:")
        
        # Collect action
        while True:
            action = input("\n🔍 Action (approve/revise/reject): ").strip().lower()
            if action in ['approve', 'revise', 'reject']:
                break
            print("❌ Please enter 'approve', 'revise', or 'reject'")
        
        # Collect feedback
        feedback = input("\n💭 General feedback: ").strip()
        
        # Collect suggested changes
        suggested_changes = input("\n✏️ Suggested changes (if any): ").strip()
        
        # Collect rating
        while True:
            try:
                rating = int(input("\n⭐ Quality rating (1-10): ").strip())
                if 1 <= rating <= 10:
                    break
                print("❌ Rating must be between 1 and 10")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # Create feedback object
        human_feedback = HumanFeedback(
            request_id=request_id,
            reviewer_id=reviewer_id,
            action=action,
            feedback=feedback,
            suggested_changes=suggested_changes,
            rating=rating,
            timestamp=datetime.now().isoformat()
        )
        
        # Update request status
        request.status = 'completed'
        
        # Move to completed reviews
        self.completed_reviews.append(human_feedback)
        
        # Save data
        self._save_data()
        
        print(f"\n✅ Feedback submitted successfully!")
        print(f"Action: {action}")
        print(f"Rating: {rating}/10")
        
        # Trigger callback if registered
        if request_id in self.feedback_callbacks:
            try:
                self.feedback_callbacks[request_id](human_feedback)
            except Exception as e:
                print(f"❌ Callback error: {e}")
        
        return human_feedback
    
    def _find_request_by_id(self, request_id: str) -> Optional[ReviewRequest]:
        """Find review request by ID"""
        for request in self.pending_reviews:
            if request.request_id == request_id:
                return request
        return None
    
    def register_feedback_callback(self, request_id: str, callback: Callable):
        """Register callback function for when feedback is received"""
        self.feedback_callbacks[request_id] = callback
    
    def get_review_summary(self, request_id: str) -> Optional[Dict]:
        """Get summary of review for a specific request"""
        feedback = None
        for fb in self.completed_reviews:
            if fb.request_id == request_id:
                feedback = fb
                break
        
        if not feedback:
            return None
        
        return {
            "request_id": request_id,
            "reviewer_id": feedback.reviewer_id,
            "action": feedback.action,
            "rating": feedback.rating,
            "feedback": feedback.feedback,
            "suggested_changes": feedback.suggested_changes,
            "timestamp": feedback.timestamp
        }
    
    def generate_review_report(self) -> Dict:
        """Generate comprehensive review report"""
        total_reviews = len(self.completed_reviews)
        if total_reviews == 0:
            return {"message": "No completed reviews found"}
        
        # Calculate statistics
        avg_rating = sum(fb.rating for fb in self.completed_reviews) / total_reviews
        
        action_counts = {"approve": 0, "revise": 0, "reject": 0}
        for fb in self.completed_reviews:
            action_counts[fb.action] = action_counts.get(fb.action, 0) + 1
        
        type_counts = {}
        for req in self.pending_reviews + [r for r in self.pending_reviews if r.status == 'completed']:
            type_counts[req.review_type] = type_counts.get(req.review_type, 0) + 1
        
        return {
            "total_completed_reviews": total_reviews,
            "average_rating": round(avg_rating, 2),
            "action_breakdown": action_counts,
            "review_type_breakdown": type_counts,
            "approval_rate": round((action_counts["approve"] / total_reviews) * 100, 1),
            "pending_reviews": len([r for r in self.pending_reviews if r.status == 'pending'])
        }
    
    def batch_review_interface(self, review_type: Optional[str] = None):
        """Interactive interface for batch reviewing"""
        pending = self.get_pending_reviews(review_type)
        
        if not pending:
            print("📭 No pending reviews found!")
            return
        
        print(f"\n📋 Found {len(pending)} pending reviews")
        
        for i, request in enumerate(pending):
            print(f"\n--- Review {i+1}/{len(pending)} ---")
            print(f"ID: {request.request_id}")
            print(f"Type: {request.review_type}")
            print(f"Priority: {request.priority}/5")
            
            choice = input("\n🔍 Actions: (r)eview, (s)kip, (q)uit: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 's':
                continue
            elif choice == 'r':
                reviewer_id = input("👤 Enter your reviewer ID: ").strip()
                if reviewer_id:
                    self.collect_human_feedback(request.request_id, reviewer_id)
                else:
                    print("❌ Invalid reviewer ID")
    
    async def wait_for_feedback(self, request_id: str, timeout: int = 3600) -> Optional[HumanFeedback]:
        """Wait for human feedback with timeout"""
        start_time = datetime.now()
        
        while True:
            # Check if feedback has been provided
            for feedback in self.completed_reviews:
                if feedback.request_id == request_id:
                    return feedback
            
            # Check timeout
            elapsed = (datetime.now() - start_time).seconds
            if elapsed > timeout:
                print(f"⏰ Timeout waiting for feedback on {request_id}")
                return None
            
            # Wait before checking again
            await asyncio.sleep(10)

# CLI Interface for standalone usage
def main():
    """Main CLI interface for human reviewers"""
    interface = HumanLoopInterface()
    
    print("🔄 Human-in-the-Loop Review Interface")
    print("=====================================")
    
    while True:
        print("\n📋 Available actions:")
        print("1. View pending reviews")
        print("2. Review specific content")
        print("3. Batch review")
        print("4. View review statistics")
        print("5. Exit")
        
        choice = input("\n🔍 Choose an action (1-5): ").strip()
        
        if choice == '1':
            pending = interface.get_pending_reviews()
            if pending:
                print(f"\n📋 {len(pending)} pending reviews:")
                for req in pending:
                    print(f"  - {req.request_id} ({req.review_type}) Priority: {req.priority}/5")
            else:
                print("📭 No pending reviews")
        
        elif choice == '2':
            request_id = input("🆔 Enter request ID: ").strip()
            if request_id:
                reviewer_id = input("👤 Enter your reviewer ID: ").strip()
                if reviewer_id:
                    interface.collect_human_feedback(request_id, reviewer_id)
        
        elif choice == '3':
            review_type = input("📝 Review type (writer/reviewer/editor) or press Enter for all: ").strip()
            interface.batch_review_interface(review_type if review_type else None)
        
        elif choice == '4':
            report = interface.generate_review_report()
            print("\n📊 Review Statistics:")
            for key, value in report.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        elif choice == '5':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()