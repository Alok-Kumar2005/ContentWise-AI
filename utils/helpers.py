import os
import tempfile
import requests
import random
import re
from typing import List, Dict, Tuple
from datetime import datetime
from models.video_processor import Quiz, QuizQuestion

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

def validate_video_url(url):
    """Validate if URL is a valid video URL"""
    valid_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    return any(domain in url.lower() for domain in valid_domains)

def format_timestamp(seconds):
    """Format seconds to MM:SS or HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"
    
class QuizUtils:
    """Utility functions for quiz operations"""
    
    @staticmethod
    def validate_quiz_data(quiz_data: Dict) -> bool:
        """Validate quiz data structure"""
        try:
            if not isinstance(quiz_data, dict):
                return False
            
            if 'questions' not in quiz_data:
                return False
            
            questions = quiz_data['questions']
            if not isinstance(questions, list) or len(questions) == 0:
                return False
            
            for question in questions:
                if not isinstance(question, QuizQuestion):
                    return False
                
                # Check question has text
                if not question.question or not question.question.strip():
                    return False
                
                # Check options
                if not question.options or len(question.options) != 4:
                    return False
                
                # Check correct answer is valid
                if not isinstance(question.correct_answer, int) or question.correct_answer not in [0, 1, 2, 3]:
                    return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def shuffle_quiz_options(quiz: Quiz, seed: int = None) -> Quiz:
        """Shuffle quiz options while maintaining correct answer tracking"""
        if seed:
            random.seed(seed)
        
        shuffled_questions = []
        
        for question in quiz.questions:
            # Create list of (option, is_correct) tuples
            options_with_correctness = [
                (option, i == question.correct_answer) 
                for i, option in enumerate(question.options)
            ]
            
            # Shuffle the options
            random.shuffle(options_with_correctness)
            
            # Extract shuffled options and find new correct answer index
            shuffled_options = []
            new_correct_answer = None
            
            for i, (option, is_correct) in enumerate(options_with_correctness):
                shuffled_options.append(option)
                if is_correct:
                    new_correct_answer = i
            
            # Create new question with shuffled options
            shuffled_question = QuizQuestion(
                question=question.question,
                options=shuffled_options,
                correct_answer=new_correct_answer,
                explanation=question.explanation
            )
            
            shuffled_questions.append(shuffled_question)
        
        return Quiz(
            title=quiz.title,
            questions=shuffled_questions,
            total_questions=len(shuffled_questions)
        )
    
    @staticmethod
    def get_grade_letter(percentage: float) -> str:
        """Convert percentage to letter grade"""
        if percentage >= 90:
            return "A+"
        elif percentage >= 85:
            return "A"
        elif percentage >= 80:
            return "A-"
        elif percentage >= 75:
            return "B+"
        elif percentage >= 70:
            return "B"
        elif percentage >= 65:
            return "B-"
        elif percentage >= 60:
            return "C+"
        elif percentage >= 55:
            return "C"
        elif percentage >= 50:
            return "C-"
        elif percentage >= 40:
            return "D"
        else:
            return "F"
    
    @staticmethod
    def get_performance_message(percentage: float) -> Tuple[str, str]:
        """Get performance message and emoji based on score"""
        if percentage >= 90:
            return "🌟 Outstanding! Perfect understanding!", "success"
        elif percentage >= 80:
            return "🎉 Excellent work! Great comprehension!", "success"
        elif percentage >= 70:
            return "👏 Good job! Solid understanding!", "info"
        elif percentage >= 60:
            return "👍 Not bad! You got the basics!", "info"
        elif percentage >= 50:
            return "📚 Keep studying! You're getting there!", "warning"
        else:
            return "📖 More review needed. Don't give up!", "error"
    
    @staticmethod
    def analyze_quiz_difficulty(quiz_results: Dict) -> Dict:
        """Analyze quiz difficulty based on results"""
        if not quiz_results or 'results' not in quiz_results:
            return {"analysis": "No data available", "difficulty": "unknown"}
        
        total_questions = len(quiz_results['results'])
        correct_answers = quiz_results['score']
        
        difficulty_score = correct_answers / total_questions if total_questions > 0 else 0
        
        if difficulty_score >= 0.8:
            difficulty = "Easy"
            analysis = "Most questions were answered correctly. Consider more challenging content."
        elif difficulty_score >= 0.6:
            difficulty = "Moderate"
            analysis = "Good balance of difficulty. Appropriate challenge level."
        elif difficulty_score >= 0.4:
            difficulty = "Challenging"
            analysis = "Questions were appropriately challenging. Good learning opportunity."
        else:
            difficulty = "Hard"
            analysis = "Questions were quite difficult. May need to review the material more thoroughly."
        
        return {
            "difficulty": difficulty,
            "analysis": analysis,
            "difficulty_score": round(difficulty_score, 2),
            "recommendation": QuizUtils._get_difficulty_recommendation(difficulty_score)
        }
    
    @staticmethod
    def _get_difficulty_recommendation(score: float) -> str:
        """Get recommendation based on difficulty score"""
        if score >= 0.8:
            return "Try more advanced topics or longer quizzes for better challenge."
        elif score >= 0.6:
            return "Great balance! Continue with similar difficulty levels."
        elif score >= 0.4:
            return "Review the video content and try the quiz again to improve."
        else:
            return "Consider watching the video again and focusing on key concepts."
    
    @staticmethod
    def export_quiz_results(quiz_results: Dict, quiz: Quiz) -> str:
        """Export quiz results as formatted text"""
        if not quiz_results or not quiz:
            return "No quiz results to export."
        
        export_text = []
        export_text.append(f"Quiz Results: {quiz.title}")
        export_text.append("=" * (len(quiz.title) + 15))
        export_text.append("")
        
        # Summary
        export_text.append(f"Score: {quiz_results['score']}/{quiz_results['total']}")
        export_text.append(f"Percentage: {quiz_results['percentage']}%")
        export_text.append(f"Grade: {QuizUtils.get_grade_letter(quiz_results['percentage'])}")
        export_text.append(f"Status: {'PASSED' if quiz_results['passed'] else 'FAILED'}")
        export_text.append("")
        
        # Detailed results
        export_text.append("Detailed Results:")
        export_text.append("-" * 20)
        
        for i, result in enumerate(quiz_results['results']):
            question_num = i + 1
            status = "✓" if result['is_correct'] else "✗"
            
            export_text.append(f"\nQuestion {question_num}: {status}")
            export_text.append(f"Q: {result['question']}")
            
            for j, option in enumerate(result['options']):
                marker = ""
                if j == result['correct_answer']:
                    marker = " [CORRECT]"
                elif j == result['user_answer']:
                    marker = " [YOUR ANSWER]" if not result['is_correct'] else " [YOUR ANSWER - CORRECT]"
                
                export_text.append(f"   {chr(65+j)}) {option}{marker}")
        
        return "\n".join(export_text)
    
    @staticmethod
    def clean_question_text(text: str) -> str:
        """Clean and format question text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Ensure question ends with question mark if it's a question
        if text and not text.endswith(('?', '.', '!', ':')):
            text += "?"
        
        return text
    
    @staticmethod
    def validate_user_answers(user_answers: Dict, total_questions: int) -> bool:
        """Validate user answers format and completeness"""
        if not isinstance(user_answers, dict):
            return False
        
        if len(user_answers) != total_questions:
            return False
        
        for i in range(total_questions):
            key = str(i)
            if key not in user_answers:
                return False
            
            answer = user_answers[key]
            if not isinstance(answer, int) or answer not in [0, 1, 2, 3]:
                return False
        
        return True