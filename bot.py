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
    
    def get_current_day(self) -> int:
        """Calculate current day based on date difference from start date"""
        start = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        days_diff = (today - start).days
        return max(1, days_diff + 1)  # Day 1 is the start date

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
    """Simple Bible API client - supports both free and ESV APIs"""
    
    def __init__(self, api_key: str = None, use_free_api: bool = False):
        self.api_key = api_key
        self.use_free_api = use_free_api
        
        if use_free_api:
            self.base_url = "https://bible-api.com"
            self.version = "kjv"  # Free API uses KJV
        else:
            self.base_url = "https://api.esv.org/v3"
            self.version = "ESV"
    
    async def get_passage(self, reference: str) -> Optional[Dict]:
        """Get passage from API"""
        if self.use_free_api:
            return await self._get_free_passage(reference)
        else:
            return await self._get_esv_passage(reference)
    
    async def _get_free_passage(self, reference: str) -> Optional[Dict]:
        """Get passage from free Bible API (KJV)"""
        try:
            # Format reference for bible-api.com (e.g., "psalms 1:1")
            formatted_ref = reference.lower().replace(' ', '%20')
            url = f"{self.base_url}/{formatted_ref}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'text': data.get('text', ''),
                            'reference': data.get('reference', reference),
                            'link': self._bible_gateway_link(reference, 'KJV'),
                            'version': 'KJV'
                        }
            return None
        except Exception as e:
            print(f"Free API Error: {e}")
            return None
    
    async def _get_esv_passage(self, reference: str) -> Optional[Dict]:
        """Get passage from ESV API"""
        headers = {"Authorization": f"Token {self.api_key}"}
        params = {
            "q": reference,
            "include-headings": "true",
            "include-verse-numbers": "true", 
            "include-short-copyright": "true"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/passage/text/"
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'text': data.get('passages', [''])[0],
                            'reference': reference,
                            'link': self._bible_gateway_link(reference, 'ESV'),
                            'version': 'ESV'
                        }
            return None
        except Exception as e:
            print(f"ESV API Error: {e}")
            return None
    
    def _bible_gateway_link(self, reference: str, version: str = "ESV") -> str:
        """Generate Bible Gateway link"""
        encoded = urllib.parse.quote(reference)
        return f"https://www.biblegateway.com/passage/?search={encoded}&version={version}"

class TelegramBot:
    """Simple Telegram bot client"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    async def send_message(self, chat_id: str, text: str):
        """Send message via Telegram API"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": str(chat_id),
            "text": str(text),
            "parse_mode": "HTML",
            "disable_web_page_preview": "false"  # String instead of boolean
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Telegram API Error {response.status}: {error_text}")
                    return response.status == 200
        except Exception as e:
            print(f"Telegram Error: {e}")
            return False

class ReadingPlanManager:
    """Manage reading plans with date-based calculation (no file storage needed)"""
    
    PLAN_FILE = "reading_plan.json"
    
    def load_plan(self) -> Optional[ReadingPlan]:
        """Load reading plan configuration from file"""
        try:
            if os.path.exists(self.PLAN_FILE):
                with open(self.PLAN_FILE, 'r') as f:
                    data = json.load(f)
                    # Remove current_day if it exists (legacy)
                    data.pop('current_day', None)
                    return ReadingPlan(**data)
        except Exception as e:
            print(f"Error loading plan: {e}")
        return None
    
    def save_plan(self, plan: ReadingPlan):
        """Save reading plan configuration to file (no need to save current_day)"""
        try:
            with open(self.PLAN_FILE, 'w') as f:
                json.dump({
                    'references': plan.references,
                    'start_date': plan.start_date,
                    'daily_time': plan.daily_time,
                    'timezone': plan.timezone
                }, f, indent=2)
            print(f"Saved reading plan configuration")
        except Exception as e:
            print(f"Error saving plan: {e}")
    
    def calculate_duration(self, references: List[Dict]) -> int:
        """Calculate total days needed"""
        total_chapters = sum(ref['chapter_count'] for ref in references)
        return total_chapters  # One chapter per day
    
    def get_today_reference(self, plan: ReadingPlan, references: List[Dict]) -> Optional[str]:
        """Get today's reading reference based on current date"""
        current_day = plan.get_current_day()
        total_chapters = 0
        
        for ref in references:
            for chapter in ref['chapters']:
                total_chapters += 1
                if total_chapters == current_day:
                    return f"{ref['book']} {chapter}"
        
        return None
    
    def is_plan_complete(self, plan: ReadingPlan, references: List[Dict]) -> bool:
        """Check if reading plan is completed"""
        current_day = plan.get_current_day()
        total_chapters = sum(ref['chapter_count'] for ref in references)
        return current_day > total_chapters
    
    def get_plan_progress(self, plan: ReadingPlan, references: List[Dict]) -> Dict:
        """Get reading plan progress information"""
        current_day = plan.get_current_day()
        total_chapters = sum(ref['chapter_count'] for ref in references)
        progress_percent = min(100, (current_day - 1) / total_chapters * 100) if total_chapters > 0 else 0
        
        return {
            'current_day': current_day,
            'total_days': total_chapters,
            'progress_percent': progress_percent,
            'is_complete': current_day > total_chapters
        }
    
    def is_time_to_send(self, plan: ReadingPlan) -> bool:
        """Check if it's time to send today's verse"""
        # Simple timezone calculation
        tz_offset = TIMEZONES.get(plan.timezone, 0)
        current_utc = datetime.utcnow()
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

async def main():
    """Main bot logic"""
    # Initialize components
    parser = BibleReferenceParser()
    plan_manager = ReadingPlanManager()
    telegram = TelegramBot(TELEGRAM_TOKEN)
    
    # Choose API type based on whether ESV_API_KEY is provided
    use_free_api = not ESV_API_KEY or ESV_API_KEY == "your_esv_api_key_here" or ESV_API_KEY.strip() == ""
    bible_api = BibleAPI(ESV_API_KEY if not use_free_api else None, use_free_api=use_free_api)
    
    if use_free_api:
        print("Using free Bible API (KJV translation)")
    else:
        print("Using ESV API")
    
    # Load or create reading plan
    plan = plan_manager.load_plan()
    if not plan:
        # Create initial plan if none exists
        print("Creating new reading plan...")
        plan = ReadingPlan(
            references="Psalms 1-15,120-134",
            start_date=datetime.now().strftime('%Y-%m-%d'),
            daily_time="08:00",
            timezone="SGT"
        )
        plan_manager.save_plan(plan)
    
    # Get progress information
    progress = plan_manager.get_plan_progress(plan, [])  # Will calculate based on references
    print(f"📅 Reading plan started: {plan.start_date}")
    print(f"📖 Current day: {progress['current_day']}")
    
    # Parse references
    references = parser.parse(plan.references)
    if not references:
        print("❌ No valid references found")
        return
    
    # Update progress with actual references
    progress = plan_manager.get_plan_progress(plan, references)
    
    # Check if reading plan is completed
    if progress['is_complete']:
        print("🎉 Reading plan completed! All chapters have been read.")
        return
    
    # Get today's reference
    today_ref = plan_manager.get_today_reference(plan, references)
    if not today_ref:
        print("❌ No reading found for today")
        return
    
    print(f"📖 Today's reading: {today_ref} (Day {progress['current_day']}/{progress['total_days']})")
    
    # Get passage from API
    passage_data = await bible_api.get_passage(today_ref)
    if not passage_data:
        # Fallback message
        version = "KJV" if use_free_api else "ESV"
        link = bible_api._bible_gateway_link(today_ref, version)
        message = f"""📖 <b>Today's Bible Reading - Day {progress['current_day']}</b>

<b>{today_ref}</b>

<a href="{link}">Read on Bible Gateway</a>

<b>Follow up Questions:</b>
• What do you learn about God?
• What do you learn about yourself?

React to this message once read. 📖"""
    else:
        # Format with passage text
        text = passage_data['text']
        if len(text) > 3000:  # Telegram limit
            text = text[:3000] + "..."
        
        copyright_text = "(ESV)" if passage_data['version'] == 'ESV' else "(KJV)"
        
        message = f"""📖 <b>Today's Bible Reading - Day {progress['current_day']}</b>

<b>{today_ref}</b>

{text}

<a href="{passage_data['link']}">Read on Bible Gateway</a>

<b>Follow up Questions:</b>
• What do you learn about God/Jesus?
• What do you learn about yourselves?

React to this message once read. 📖

<i>{copyright_text}</i>"""
    
    # Send message
    success = await telegram.send_message(TELEGRAM_CHAT_ID, message)
    
    if success:
        print(f"✅ Successfully sent day {progress['current_day']}")
        print(f"📊 Progress: {progress['current_day']}/{progress['total_days']} chapters ({progress['progress_percent']:.1f}%)")
        
        if progress['current_day'] >= progress['total_days']:
            print("🎉 This was the final chapter of your reading plan!")
    else:
        print("❌ Failed to send message")

if __name__ == "__main__":
    asyncio.run(main())