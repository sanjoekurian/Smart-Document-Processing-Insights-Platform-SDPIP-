from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import json
import re
from typing import List

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        load_dotenv()
        
        # Configure default headers for OpenRouter
        default_headers = {
            "HTTP-Referer": "https://github.com/OpenRouterTeam/openrouter-python",
            "X-Title": "Document Chat System"
        }
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_headers=default_headers  # Set headers at client initialization
        )

    def _clean_text(self, text: str) -> str:
        """Clean text by removing markdown formatting and normalizing structure."""
        # Remove markdown headings and separators
        text = re.sub(r'#{1,6}\s+', '', text)
        text = re.sub(r'-{3,}', '', text)
        
        # Remove markdown-style bold/italic
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Convert bullet points to proper format
        text = re.sub(r'^\s*[*-]\s+', '• ', text, flags=re.MULTILINE)
        
        # Convert numbered lists to proper format
        text = re.sub(r'^\s*(\d+)\.\s+', r'\n\1. ', text, flags=re.MULTILINE)
        
        # Fix spacing around colons in headings
        text = re.sub(r'(\w+):\s*(\w)', r'\1: \2', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix spacing after periods and colons
        text = re.sub(r'\.(?=\w)', '. ', text)
        text = re.sub(r':(?=\w)', ': ', text)
        
        # Add proper line breaks for sections
        text = re.sub(r'(?<=\.) (?=[A-Z][a-z]+ [A-Z])', '\n\n', text)
        
        # Ensure proper spacing around bullet points
        text = re.sub(r'•\s*', '• ', text)
        
        # Add proper line breaks before bullet points
        text = re.sub(r' •', '\n•', text)
        
        # Normalize newlines and remove excessive spacing
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def _chunk_text(self, text: str, max_chunk_size: int = 12000) -> List[str]:
        """Split text into chunks that fit within token limits."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            # Approximate token count (rough estimate: 4 chars = 1 token)
            word_size = len(word) // 4 + 1
            if current_size + word_size > max_chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    async def generate_summary(self, text: str, max_tokens: int = 500) -> str:
        """
        Generate a summary of the provided text using OpenAI's API.
        Handles large documents by chunking and combining summaries.
        
        Args:
            text (str): The text to summarize
            max_tokens (int): Maximum number of tokens in the summary
            
        Returns:
            str: The generated summary
        """
        try:
            logger.info("Sending summary generation request to OpenAI")
            
            # Split text into chunks if it's too large
            chunks = self._chunk_text(text)
            chunk_summaries = []
            
            # Generate summary for each chunk
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1} of {len(chunks)}")
                completion = self.client.chat.completions.create(
                    model="openai/gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a helpful assistant that creates well-structured document summaries.
                            Follow these formatting rules:
                            1. Use clear section headings with proper capitalization
                            2. Use proper paragraph breaks between sections
                            3. Use bullet points (•) for lists instead of asterisks
                            4. Format numbered lists with proper indentation
                            5. Keep text clean without any markdown or special characters
                            6. Use consistent spacing throughout the document"""
                        },
                        {
                            "role": "user",
                            "content": f"""Create a concise summary of this text section.
                            Focus on key points and main ideas.
                            
                            Text to summarize:\n\n{chunk}"""
                        }
                    ],
                    max_tokens=max(200, max_tokens // len(chunks)),
                    temperature=0.7
                )
                
                if not completion or not hasattr(completion, 'choices') or not completion.choices:
                    logger.error(f"Invalid completion format: {completion}")
                    raise ValueError("Invalid completion format from OpenAI")
                
                chunk_summary = completion.choices[0].message.content
                if chunk_summary:
                    chunk_summaries.append(chunk_summary)
            
            # If we have multiple chunks, combine their summaries
            if len(chunk_summaries) > 1:
                combined_summary = "\n\n".join(chunk_summaries)
                
                # Generate a final, consolidated summary
                completion = self.client.chat.completions.create(
                    model="openai/gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that consolidates multiple section summaries into a coherent, well-structured final summary."
                        },
                        {
                            "role": "user",
                            "content": f"""Combine these section summaries into a single coherent summary.
                            Maintain a clear structure and avoid redundancy.
                            
                            Section summaries:\n\n{combined_summary}"""
                        }
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                
                final_summary = completion.choices[0].message.content
            else:
                final_summary = chunk_summaries[0] if chunk_summaries else ""
            
            if not final_summary:
                logger.error("Empty summary content")
                raise ValueError("Empty summary content")
                
            logger.info("Successfully generated summary")
            return self._clean_text(final_summary)
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise Exception(f"Failed to generate summary: {str(e)}")

    async def analyze_sentiment(self, text: str) -> dict:
        """
        Analyze the sentiment and key themes of the provided text.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            dict: Dictionary containing sentiment analysis and key themes
        """
        try:
            logger.info("Sending sentiment analysis request to OpenAI")
            completion = self.client.chat.completions.create(
                model="openai/gpt-3.5-turbo",  # Changed to a more reliable model
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing text sentiment and identifying key themes. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze the sentiment and identify key themes in this text. 
                        Return a JSON object with exactly this format:
                        {{
                            "sentiment": "positive|negative|neutral",
                            "themes": ["theme1", "theme2", ...]
                        }}
                        
                        Text to analyze:\n{text}"""
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            if not completion or not hasattr(completion, 'choices') or not completion.choices:
                logger.error(f"Invalid completion format: {completion}")
                raise ValueError("Invalid completion format from OpenAI")
            
            response_text = completion.choices[0].message.content
            if not response_text:
                logger.error("Empty response text")
                raise ValueError("Empty response text")
            
            logger.info("Attempting to parse sentiment response")
            
            # Try to parse the response
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON using regex
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    logger.warning("Failed to parse JSON response, returning default")
                    return {
                        "sentiment": "neutral",
                        "themes": ["Unable to extract themes"]
                    }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            raise Exception(f"Failed to analyze sentiment: {str(e)}")

    def generate_chat_response(self, question: str, document_context: dict) -> str:
        try:
            # Extract the relevant text content from document context
            document_text = document_context.get('text', '')  # Try to get 'text' first
            if not document_text:  # If 'text' is not found, try 'content'
                document_text = document_context.get('content', '')
            
            if not document_text:
                raise ValueError("No document content found in context")

            # Include summary and metadata if available
            summary = document_context.get('summary', '')
            metadata = document_context.get('metadata', {})
            
            # Construct the prompt with document context and user question
            prompt = f"""
            Document Content: {document_text}

            Additional Context:
            Summary: {summary}
            Metadata: {str(metadata)}
            
            Question: {question}
            
            Please provide a detailed and accurate answer based on the document content above.
            If the answer cannot be derived from the content, please indicate that.
            Keep your response focused and relevant to the question.
            """
            
            logger.info("Sending chat completion request to OpenAI")
            
            # Call OpenAI API using OpenRouter
            response = self.client.chat.completions.create(
                model="openai/gpt-3.5-turbo",  # Changed to a more reliable model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant that answers questions about documents. Provide accurate, concise answers based on the document context provided. If the answer cannot be found in the document, clearly state that."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            logger.info("Received response from OpenAI")
            
            if not response:
                logger.error("No response received from OpenAI")
                raise ValueError("No response received from OpenAI")
                
            if not hasattr(response, 'choices') or not response.choices:
                logger.error(f"Invalid response format: {response}")
                raise ValueError("Invalid response format from OpenAI")
                
            message = response.choices[0].message
            if not message:
                logger.error("No message in OpenAI response")
                raise ValueError("No message in OpenAI response")
                
            content = message.content
            if not content:
                logger.error("No content in OpenAI message")
                raise ValueError("No content in OpenAI message")
            
            logger.info("Successfully extracted response content")
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error in generate_chat_response: {str(e)}")
            logger.error(f"Document context keys: {list(document_context.keys()) if document_context else 'None'}")
            raise Exception(f"Error generating chat response: {str(e)}")

# Initialize the OpenAI service
openai_service = OpenAIService() 