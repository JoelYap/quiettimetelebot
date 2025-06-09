import os
import re
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
from dataclasses import dataclass
import urllib.parse

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ESV_API_KEY = os.getenv('ESV_API_KEY')

# Simple timezone mappings
TIMEZONES = {
    'EST': -5, 'EDT': -4,
    'PST': -8, 'PDT': -7,
    'GMT': 0, 'UTC': 0,
    'SGT': 8, 'GMT+7': 7, 'GMT+8': 8
}

@dataclass
class ReadingPlan:
    references: str
    start_date: str
    daily_time: str
    timezone: str
    current_day: int = 1

class BibleReferenceParser:
    """Simple Bible reference parser"""
    
    BOOKS = {
        'gen': 'Genesis', 'genesis': 'Genesis',
        'ps': 'Psalms', 'psalm': 'Psalms', 'psalms': 'Psalms',
        'rom': 'Romans', 'romans': 'Romans',
        'matt': 'Matthew', 'matthew': 'Matthew',
        'john': 'John',
        # Add more as needed
    }
    
    def parse(self, reference_text: str) -> List[Dict]:
        """Parse 'Psalms 1-15,120-134' format"""
        references = []
        
        # Simple regex for book + chapter ranges
        pattern = r'([A-Za-z]+)\s*(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)'
        matches = re.findall(pattern, reference_text, re.IGNORECASE)
        
        for book, ranges in matches:
            normalized_book = self.BOOKS.get(book.lower(), book.title())
            chapter_list = self._parse_ranges(ranges)
            
            references.append({
                'book': normalized_book,
                'chapters': chapter_list,
                'chapter_count': len(chapter_list)
            })
        
        return references
    
    def _parse_ranges(self, ranges_text: str) -> List[int]:
        """Convert '1-15,120-134' to list of chapter numbers"""
        chapters = []
        parts = ranges_text.split(',')
        
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                chapters.extend(range(start, end + 1))
            else:
                chapters.append(int(part))
        
        return chapters

class BibleAPI:
    """ESV Bible API client for retrieving Bible passages"""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ESV API key is required")
        self.api_key = api_key
        self.base_url = "https://api.esv.org/v3"
    
    async def get_passage(self, reference: str) -> Optional[Dict]:
        """Retrieve Bible passage from ESV API
        
        Args:
            reference: Bible reference (e.g., "John 3:16", "Romans 1")
            
        Returns:
            Dict with 'text', 'reference', and 'link' keys, or None if failed
        """
        if not reference or not reference.strip():
            return None
            
        headers = {
            "Authorization": f"Token {self.api_key}",
            "User-Agent": "QuietTimeTeleBot/1.0"
        }
        
        params = {
            "q": reference.strip(),
            "include-headings": "true",
            "include-verse-numbers": "true",
            "include-short-copyright": "true",
            "include-footnotes": "false",
            "include-audio-link": "false"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                url = f"{self.base_url}/passage/text/"
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        passages = data.get('passages', [])
                        
                        if not passages or not passages[0].strip():
                            return None
                            
                        return {
                            'text': passages[0].strip(),
                            'reference': reference,
                            'link': self._bible_gateway_link(reference),
                            'copyright': data.get('copyright', '')
                        }
                    elif response.status == 401:
                        print(f"ESV API: Invalid API key")
                    elif response.status == 403:
                        print(f"ESV API: Access forbidden - check API key permissions")
                    elif response.status == 429:
                        print(f"ESV API: Rate limit exceeded")
                    else:
                        print(f"ESV API: HTTP {response.status}")
                        
        except asyncio.TimeoutError:
            print(f"ESV API: Request timeout for {reference}")
        except aiohttp.ClientError as e:
            print(f"ESV API: Connection error - {e}")
        except Exception as e:
            print(f"ESV API: Unexpected error - {e}")
            
        return None
    
    def _bible_gateway_link(self, reference: str) -> str:
        """Generate Bible Gateway link for reference
        
        Args:
            reference: Bible reference
            
        Returns:
            Formatted Bible Gateway URL
        """
        encoded = urllib.parse.quote(reference)
        return f"https://www.biblegateway.com/passage/?search={encoded}&version=ESV"

class TelegramBot:
    """Simple Telegram bot client"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    async def send_message(self, chat_id: str, text: str):
        """Send message via Telegram API"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Telegram Error: {e}")
            return False

class ReadingPlanManager:
    """Manage reading plans with simple file storage"""
    
    PLAN_FILE = "reading_plan.json"
    
    def load_plan(self) -> Optional[ReadingPlan]:
        """Load reading plan from file"""
        try:
            if os.path.exists(self.PLAN_FILE):
                with open(self.PLAN_FILE, 'r') as f:
                    data = json.load(f)
                    return ReadingPlan(**data)
        except Exception as e:
            print(f"Error loading plan: {e}")
        return None
    
    def save_plan(self, plan: ReadingPlan):
        """Save reading plan to file"""
        try:
            with open(self.PLAN_FILE, 'w') as f:
                json.dump(plan.__dict__, f, indent=2)
        except Exception as e:
            print(f"Error saving plan: {e}")
    
    def calculate_duration(self, references: List[Dict]) -> int:
        """Calculate total days needed"""
        total_chapters = sum(ref['chapter_count'] for ref in references)
        return total_chapters  # One chapter per day
    
    def get_today_reference(self, plan: ReadingPlan, references: List[Dict]) -> Optional[str]:
        """Get today's reading reference"""
        total_chapters = 0
        
        for ref in references:
            for chapter in ref['chapters']:
                total_chapters += 1
                if total_chapters == plan.current_day:
                    return f"{ref['book']} {chapter}"
        
        return None
    
    def is_time_to_send(self, plan: ReadingPlan) -> bool:
        """Check if it's time to send today's verse"""
        # Simple timezone calculation
        tz_offset = TIMEZONES.get(plan.timezone, 0)
        current_utc = datetime.now(datetime.timezone.utc)
        local_time = current_utc + timedelta(hours=tz_offset)
        
        # Parse daily time (e.g., "08:00")
        hour, minute = map(int, plan.daily_time.split(':'))
        target_time = time(hour, minute)
        
        # Check if we're within 1 hour of target time
        current_time = local_time.time()
        target_datetime = datetime.combine(local_time.date(), target_time)
        current_datetime = datetime.combine(local_time.date(), current_time)
        
        diff = abs((current_datetime - target_datetime).total_seconds())
        return diff <= 3600  # Within 1 hour

def format_passage_message(passage_data: Dict, current_day: int) -> str:
    """Format message with Bible passage text"""
    text = passage_data['text']
    
    # Truncate if too long for Telegram
    if len(text) > 3000:
        text = text[:3000] + "..."
    
    message = f"""📖 <b>Today's Bible Reading - Day {current_day}</b>

<b>{passage_data['reference']}</b>

{text}

<a href="{passage_data['link']}">Read on Bible Gateway</a>

<b>Follow up Questions:</b>
- What do you learn about God/Jesus?
- What do you learn about yourselves?

React to this message once read. 📖"""
    
    return message

def format_fallback_message(reference: str, current_day: int, bible_api: BibleAPI) -> str:
    """Format fallback message when API fails"""
    return f"""📖 <b>Today's Bible Reading - Day {current_day}</b>

<b>{reference}</b>

<a href="{bible_api._bible_gateway_link(reference)}">Read on Bible Gateway</a>

<b>Follow up Questions:</b>
- What do you learn about God/Jesus?
- What do you learn about yourselves?

React to this message once read. 📖"""

async def main():
    """Main bot logic for sending daily Bible readings"""
    # Validate required environment variables
    if not ESV_API_KEY:
        print("Error: ESV_API_KEY environment variable is required")
        return
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN environment variable is required") 
        return
    if not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_CHAT_ID environment variable is required")
        return
    
    # Initialize components
    parser = BibleReferenceParser()
    
    try:
        bible_api = BibleAPI(ESV_API_KEY)
        telegram = TelegramBot(TELEGRAM_TOKEN)
        plan_manager = ReadingPlanManager()
    except ValueError as e:
        print(f"Initialization error: {e}")
        return
    
    # For demo purposes, create a sample plan if none exists
    plan = plan_manager.load_plan()
    if not plan:
        # Sample plan - you would set this up via conversation later
        plan = ReadingPlan(
            references="Psalms 1-15,120-134",
            start_date=datetime.now().strftime('%Y-%m-%d'),
            daily_time="08:00",
            timezone="SGT",
            current_day=1
        )
        plan_manager.save_plan(plan)
        print("Created sample reading plan")
    
    # Parse references
    references = parser.parse(plan.references)
    if not references:
        print("No valid references found")
        return
    
    # Check if it's time to send (for GitHub Actions, we'll send regardless)
    today_ref = plan_manager.get_today_reference(plan, references)
    if not today_ref:
        print("Reading plan completed!")
        return
    
    print(f"Today's reading: {today_ref}")
    
    # Get passage from API
    passage_data = await bible_api.get_passage(today_ref)
    
    if not passage_data:
        # Fallback message when API fails
        print(f"Failed to retrieve passage for {today_ref}, using fallback")
        message = format_fallback_message(today_ref, plan.current_day, bible_api)
    else:
        # Format message with passage text
        message = format_passage_message(passage_data, plan.current_day)
        print(f"Retrieved passage for {today_ref} ({len(passage_data['text'])} chars)")
    
    # Send message
    success = await telegram.send_message(TELEGRAM_CHAT_ID, message)
    
    if success:
        # Update plan for next day
        plan.current_day += 1
        plan_manager.save_plan(plan)
        print(f"Sent day {plan.current_day - 1} successfully")
    else:
        print("Failed to send message")

if __name__ == "__main__":
    asyncio.run(main())