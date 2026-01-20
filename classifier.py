"""
AI-powered classification module using Claude API.
Classifies QR code destinations with confidence scoring.
"""
import os
from anthropic import Anthropic
from config import Config
import base64


class QRClassifier:
    """
    Classifies QR code destinations using Claude AI.
    Returns classification and confidence score.
    """

    # Classification categories
    CATEGORIES = {
        'promotional': 'Marketing, advertisements, product promotions',
        'informational': 'Educational content, documentation, information',
        'business': 'Business websites, company pages, contact info',
        'personal': 'Personal websites, social media profiles',
        'transactional': 'Payment links, shopping, e-commerce',
        'social': 'Social media links, sharing, engagement',
        'event': 'Event tickets, registrations, invitations',
        'scam': 'Suspicious phishing attempts, fake sites',
        'malicious': 'Known malware, dangerous sites',
        'shortened_url': 'URL shortener requiring investigation',
        'other': 'Does not fit other categories'
    }

    def __init__(self):
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def classify(self, url, page_title=None, page_preview=None, screenshot_path=None, warnings=None):
        """
        Classify a QR code destination.
        Returns (category, confidence, is_malicious, reasoning)
        """

        # Build context for Claude
        context = self._build_context(url, page_title, page_preview, warnings)

        # Prepare messages
        messages = [
            {
                "role": "user",
                "content": self._build_prompt(context, screenshot_path)
            }
        ]

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Use efficient model
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more consistent classifications
                messages=messages
            )

            # Parse response
            result = self._parse_classification(response.content[0].text)
            return result

        except Exception as e:
            print(f"Classification error: {e}")
            return {
                'category': 'error',
                'confidence': 0.0,
                'is_malicious': False,
                'reasoning': f"Classification failed: {str(e)}"
            }

    def _build_context(self, url, title, preview, warnings):
        """Build context string for classification"""
        context = f"URL: {url}\n"

        if title:
            context += f"Page Title: {title}\n"

        if preview:
            context += f"Page Preview: {preview[:300]}...\n"

        if warnings:
            context += f"Safety Warnings: {', '.join(warnings)}\n"

        return context

    def _build_prompt(self, context, screenshot_path=None):
        """Build classification prompt for Claude"""

        # If we have a screenshot, include it
        content = []

        if screenshot_path and os.path.exists(screenshot_path):
            # Read and encode screenshot
            with open(screenshot_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')

            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data
                }
            })

        # Add text prompt
        categories_str = '\n'.join([f"- {k}: {v}" for k, v in self.CATEGORIES.items()])

        prompt = f"""You are analyzing a QR code destination for a security research project.

Context:
{context}

Available Categories:
{categories_str}

Please classify this destination into ONE of the categories above.

Respond in this exact format:
CATEGORY: <category_name>
CONFIDENCE: <0.0-1.0>
MALICIOUS: <yes/no>
REASONING: <brief explanation>

Consider:
1. URL structure and domain reputation
2. Page content and purpose
3. Any security warnings present
4. Visual appearance (if screenshot provided)
5. Likelihood of legitimate vs malicious intent

Be conservative - flag anything suspicious for manual review (confidence < 0.7)."""

        content.append({
            "type": "text",
            "text": prompt
        })

        return content

    def _parse_classification(self, response_text):
        """Parse Claude's response into structured format"""
        try:
            lines = response_text.strip().split('\n')
            result = {
                'category': 'other',
                'confidence': 0.5,
                'is_malicious': False,
                'reasoning': response_text
            }

            for line in lines:
                line = line.strip()
                if line.startswith('CATEGORY:'):
                    result['category'] = line.split(':', 1)[1].strip().lower()
                elif line.startswith('CONFIDENCE:'):
                    conf_str = line.split(':', 1)[1].strip()
                    result['confidence'] = float(conf_str)
                elif line.startswith('MALICIOUS:'):
                    mal_str = line.split(':', 1)[1].strip().lower()
                    result['is_malicious'] = mal_str in ['yes', 'true']
                elif line.startswith('REASONING:'):
                    result['reasoning'] = line.split(':', 1)[1].strip()

            # Validation
            if result['category'] not in self.CATEGORIES:
                result['category'] = 'other'

            if not 0.0 <= result['confidence'] <= 1.0:
                result['confidence'] = 0.5

            return result

        except Exception as e:
            print(f"Parse error: {e}")
            return {
                'category': 'error',
                'confidence': 0.0,
                'is_malicious': False,
                'reasoning': f"Failed to parse: {response_text[:200]}"
            }

    def should_skip_classification(self, qr_code, is_duplicate):
        """
        Determine if we should skip classification to save costs.
        Skip if: duplicate AND already classified AND high confidence
        """
        if not is_duplicate:
            return False

        if not qr_code.classification:
            return False

        if qr_code.confidence_score and qr_code.confidence_score >= 0.8:
            # Already classified with high confidence
            return True

        return False


if __name__ == '__main__':
    # Test the classifier
    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"Classifying: {test_url}\n")

        try:
            classifier = QRClassifier()
            result = classifier.classify(
                url=test_url,
                page_title="Test Page",
                warnings=['Suspicious TLD'] if '.tk' in test_url else None
            )

            print("=== Classification Result ===")
            print(f"Category: {result['category']}")
            print(f"Confidence: {result['confidence']:.2%}")
            print(f"Malicious: {result['is_malicious']}")
            print(f"Reasoning: {result['reasoning']}")

            if result['confidence'] < 0.7:
                print("\n⚠️ Flagged for manual review (low confidence)")

        except ValueError as e:
            print(f"Error: {e}")
            print("Make sure ANTHROPIC_API_KEY is set in .env")
    else:
        print("Usage: python classifier.py <url>")
