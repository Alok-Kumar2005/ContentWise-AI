from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import Config
from models.video_processor import Quiz, QuizQuestion
from core.templates import Template
import logging
import json
import re

class QuizGeneratorService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.3 
        )
    
    def generate_quiz(self, transcript, title="", num_questions=5):
        """Generate quiz from video transcript"""
        prompt = PromptTemplate(
            input_variables=["transcript", "title", "num_questions"],
            template=self._get_quiz_template()
        )
        
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                transcript=transcript[:8000], 
                title=title,
                num_questions=num_questions
            )
            
            quiz_data = self._parse_quiz_response(response)
            
            return Quiz(
                title=f"Quiz: {title}" if title else "Video Quiz",
                questions=quiz_data["questions"],
                total_questions=len(quiz_data["questions"])
            )
            
        except Exception as e:
            logging.error(f"Error generating quiz: {e}")
            return self._create_fallback_quiz(title)
    
    def _get_quiz_template(self):
        """Quiz generation template"""
        return Template.quiz_template
    
    def _parse_quiz_response(self, response):
        """Parse LLM response into structured quiz data"""
        questions = []
        
        try:
            question_blocks = re.split(r'QUESTION \d+:', response)[1:] 
            
            for i, block in enumerate(question_blocks):
                if i >= 5:  
                    break
                    
                lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
                
                if len(lines) < 6: 
                    continue
                
                question_text = lines[0]
                options = []
                correct_answer = None
                
                for line in lines[1:5]:
                    if line.startswith(('A)', 'B)', 'C)', 'D)')):
                        options.append(line[2:].strip())
                
                for line in lines:
                    if line.startswith('CORRECT:'):
                        correct_letter = line.split(':')[1].strip().upper()
                        if correct_letter in ['A', 'B', 'C', 'D']:
                            correct_answer = ord(correct_letter) - ord('A')
                
                if len(options) == 4 and correct_answer is not None:
                    questions.append(QuizQuestion(
                        question=question_text,
                        options=options,
                        correct_answer=correct_answer,
                        explanation="" 
                    ))
            
            if not questions:
                questions = self._create_fallback_questions()
                
        except Exception as e:
            logging.error(f"Error parsing quiz response: {e}")
            questions = self._create_fallback_questions()
        
        return {"questions": questions}
    
    def _create_fallback_quiz(self, title=""):
        """Create a fallback quiz if generation fails"""
        return Quiz(
            title=f"Quiz: {title}" if title else "Video Quiz",
            questions=self._create_fallback_questions(),
            total_questions=3
        )
    
    def _create_fallback_questions(self):
        """Create fallback questions when parsing fails"""
        return [
            QuizQuestion(
                question="What was the main topic of this video?",
                options=[
                    "Educational content",
                    "Entertainment",
                    "News update",
                    "Product review"
                ],
                correct_answer=0,
                explanation="Based on the video analysis"
            ),
            QuizQuestion(
                question="What type of content was primarily discussed?",
                options=[
                    "Technical information",
                    "Personal stories",
                    "Historical facts",
                    "General knowledge"
                ],
                correct_answer=0,
                explanation="Inferred from video content"
            ),
            QuizQuestion(
                question="What was the overall tone of the video?",
                options=[
                    "Informative",
                    "Casual",
                    "Formal",
                    "Entertaining"
                ],
                correct_answer=0,
                explanation="Based on content analysis"
            )
        ]
    
    def calculate_score(self, user_answers, quiz):
        """Calculate quiz score"""
        if not user_answers or not quiz.questions:
            return {
                "score": 0,
                "total": len(quiz.questions),
                "percentage": 0,
                "passed": False,
                "results": []
            }
        
        correct_count = 0
        results = []
        
        for i, question in enumerate(quiz.questions):
            user_answer = user_answers.get(str(i))
            is_correct = user_answer == question.correct_answer
            
            if is_correct:
                correct_count += 1
            
            results.append({
                "question_index": i,
                "question": question.question,
                "user_answer": user_answer,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
                "options": question.options
            })
        
        total_questions = len(quiz.questions)
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "score": correct_count,
            "total": total_questions,
            "percentage": round(percentage, 1),
            "passed": percentage >= 60,  # 60% passing grade
            "results": results
        }