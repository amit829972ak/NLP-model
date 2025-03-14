import streamlit as st
import spacy
import dateparser
import re
import pandas as pd
from datetime import datetime, timedelta
from dateparser.search import search_dates
import json
import geonamescache
from openai import OpenAI
from word2number import w2n
import google.generativeai as genai

# Configure the Gemini API with your API key
def setup_gemini():
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]  # Store your API key in Streamlit secrets
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel('gemini-1.5-pro')  # Choose the appropriate model

# Function to generate itinerary using Gemini
def generate_itinerary_with_gemini(prompt):
    model = setup_gemini()
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating itinerary: {str(e)}"

# Load spaCy model globally
@st.cache_resource
def load_spacy_model():
    try:
        return spacy.load("en_core_web_lg")  # Load large model
    except OSError:
        st.warning("Large model not found. Falling back to `en_core_web_sm`. Install `en_core_web_lg` for better accuracy.")
        return spacy.load("en_core_web_sm")  # Fallback to small model

nlp = load_spacy_model()

# Load city database from geonamescache
gc = geonamescache.GeonamesCache()
cities_dict = {city["name"].lower(): city["name"] for city in gc.get_cities().values()}

# Define seasonal mappings
seasonal_mappings = {
  "summer": "06-01",
    "mid summer": "07-15",
    "end of summer": "08-25",
    "autumn": "09-15",
    "fall": "09-15",
    "monsoon": "09-10",
    "winter": "12-01",
    "early winter": "11-15",
    "late winter": "01-15",
    "spring": "04-01"  
}

def extract_details(text):
    doc = nlp(text)
    text_lower = text.lower()
    details = {
        "Starting Location": None,
        "Destination": None,
        "Start Date": None,
        "End Date": None,
        "Trip Duration": None,
        "Trip Type": None,
        "Number of Travelers": None,
        "Budget Range": None,
        "Transportation Preferences": None,
        "Accommodation Preferences": None,
        "Special Requirements": None
    }
    # Extract locations
    locations = [ent.text for ent in doc.ents if ent.label_ in {"GPE", "LOC"}]    
    common_destinations = {"goa","Goa","French countryside","goa","Maldives", "Bali", "Paris", "New York", "Los Angeles", "San Francisco", "Tokyo", "London", "Dubai", "Rome", "Bangkok"}
    # Backup regex-based location extraction
    regex_matches = re.findall(r'\b(?:from|to|visit|traveling to|heading to|going to|in|at|of|to the|toward the)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)', text)
    # Check for cities in text using geonamescache
    extracted_cities = []
    words = text.split()
    for i in range(len(words)):
        for j in range(i + 1, min(i + 4, len(words))):  # Check up to 3-word phrases
            phrase = " ".join(words[i:j+1])
            if phrase.lower() in cities_dict or phrase in common_destinations:
                extracted_cities.append(cities_dict[phrase.lower()])

    # Combine all sources and remove duplicates while preserving order
    seen = set()
    all_locations = [loc for loc in locations + regex_matches + extracted_cities if not (loc in seen or seen.add(loc))]

    # Determine starting location and destination using dependency parsing
    start_location, destination = None, None
    for token in doc:
        if token.text.lower() == "from":
            location = " ".join(w.text for w in token.subtree if w.ent_type_ in {"GPE", "LOC"})
            if location:
                start_location = location
        elif token.text.lower() in {"to", "toward"}:
            location = " ".join(w.text for w in token.subtree if w.ent_type_ in {"GPE", "LOC"})
            if location:
                destination = location

    # If dependency parsing fails, use list extraction
    if not start_location and not destination:
        if len(all_locations) > 1:
            start_location, destination = all_locations[:2]
        elif len(all_locations) == 1:
            destination = all_locations[0]

    # Construct final details dictionary
    details = {}
    if start_location:
        details["Starting Location"] = start_location
    if destination:
        details["Destination"] = destination

    # Extract duration
    duration_match = re.search(r'(?P<value>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*[-]?\s*(?P<unit>day|days|night|nights|week|weeks|month|months)', text, re.IGNORECASE)
    duration_days = None

    if duration_match:
        unit = duration_match.group("unit").lower()
        value = duration_match.group("value").lower()

        # Convert word-based numbers to digits
        try:
            value = int(value) if value.isdigit() else w2n.word_to_num(value)
        except ValueError:
            value = 1  # Default to 1 if conversion fails
        if "week" in unit:
            duration_days = value * 7   
        elif "month" in unit:
            duration_days = value * 30
        else:
            duration_days = value
        details["Trip Duration"] = f"{duration_days} days"
    else:
        # Handle cases where the duration is mentioned without a number
        if "week" in text:
            duration_days = 7
        elif "month" in text:
            duration_days = 30
        elif "day" in text or "night" in text:
            duration_days = 1
        
        if duration_days:
            details["Trip Duration"] = f"{duration_days} days"        
    
    # Extract dates
    text_lower = text.lower()
    
    # NEW PATTERN: Handle date ranges with format "5-12th june"
    text_lower = text.lower()
    
    # Create patterns for different date formats
    
    # Pattern 1: Handle date ranges with format "from 3-13th april 2025"
    date_range_ordinal_pattern = r'from\s+(\d{1,2})(?:st|nd|rd|th)?-(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?'
    ordinal_match = re.search(date_range_ordinal_pattern, text, re.IGNORECASE)
    
    # Pattern 2: Handle formats like "from 22th june 2025 to 29th june 2025"
    date_to_date_pattern = r'from\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?\s+to\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?'
    to_date_match = re.search(date_to_date_pattern, text, re.IGNORECASE)
    
    # Pattern 3: Handle formats like "from 02-04-2025 to 29-04-2025"
    numeric_date_pattern = r'from\s+(\d{1,2})-(\d{1,2})-(\d{4})\s+to\s+(\d{1,2})-(\d{1,2})-(\d{4})'
    numeric_match = re.search(numeric_date_pattern, text, re.IGNORECASE)
    
    # Pattern 4: Handle formats like "from 12th march for two week"
    date_for_duration_pattern = r'from\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?\s+for\s+(\d+|a|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)'
    date_for_duration_match = re.search(date_for_duration_pattern, text, re.IGNORECASE)
    
    # Pattern 5: Handle formats like "for a week from 13th april"
    duration_from_date_pattern = r'for\s+(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)\s+from\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?'
    duration_from_date_match = re.search(duration_from_date_pattern, text, re.IGNORECASE)
    
    # Pattern 6: Handle formats like "for two weeks on 3rd april"
    duration_on_date_pattern = r'for\s+(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?'
    duration_on_date_match = re.search(duration_on_date_pattern, text, re.IGNORECASE)
    
    # Pattern 7: Handle formats like "on 13th march for a week"
    on_date_for_duration_pattern = r'on\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?\s+for\s+(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)'
    on_date_for_duration_match = re.search(on_date_for_duration_pattern, text, re.IGNORECASE)
    
    # Pattern 8: Handle formats like "for 2 weeks on 20/05/2025" or "for two weeks on 02-08-2025"
    duration_on_numeric_date_pattern = r'for\s+(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)\s+on\s+(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})'
    duration_on_numeric_date_match = re.search(duration_on_numeric_date_pattern, text, re.IGNORECASE)
    
    # Pattern 9: Handle formats like "on 05/06/2025 for two weeks" or "on 06-07-2025 for 2 weeks"
    on_numeric_date_for_duration_pattern = r'on\s+(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\s+for\s+(\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)'
    on_numeric_date_for_duration_match = re.search(on_numeric_date_for_duration_pattern, text, re.IGNORECASE)
    
    # Function to convert text numbers to integers
    def convert_text_to_number(text_num):
        if text_num.lower() in ['a', 'an']:
            return 1
        try:
            return int(text_num)
        except ValueError:
            # Convert word numbers to digits
            word_to_num = {
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
            }
            return word_to_num.get(text_num.lower(), 1)
    
    # Function to convert unit to days
    def convert_unit_to_days(num, unit):
        if 'week' in unit:
            return num * 7
        elif 'month' in unit:
            return num * 30
        else:  # days
            return num
    
    # Process the matched patterns
    if ordinal_match:
        # Handle format "from 3-13th april 2025"
        start_day = ordinal_match.group(1)
        end_day = ordinal_match.group(2)
        month = ordinal_match.group(3)
        year = ordinal_match.group(4) or datetime.today().year
        
        start_date_text = f"{start_day} {month} {year}"
        end_date_text = f"{end_day} {month} {year}"
        
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        end_date = dateparser.parse(end_date_text, settings={'PREFER_DATES_FROM': 'future'})
        
        if start_date and end_date:
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{(end_date - start_date).days + 1} days"  # +1 to include both days
    
    elif to_date_match:
        # Handle format "from 22th june 2025 to 29th june 2025"
        start_day = to_date_match.group(1)
        start_month = to_date_match.group(2)
        start_year = to_date_match.group(3) or datetime.today().year
        
        end_day = to_date_match.group(4)
        end_month = to_date_match.group(5) or start_month
        end_year = to_date_match.group(6) or start_year
        
        start_date_text = f"{start_day} {start_month} {start_year}"
        end_date_text = f"{end_day} {end_month} {end_year}"
        
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        end_date = dateparser.parse(end_date_text, settings={'PREFER_DATES_FROM': 'future'})
        
        if start_date and end_date:
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{(end_date - start_date).days + 1} days"
    
    elif numeric_match:
        # Handle format "from 02-04-2025 to 29-04-2025"
        start_day = numeric_match.group(1)
        start_month = numeric_match.group(2)
        start_year = numeric_match.group(3)
        
        end_day = numeric_match.group(4)
        end_month = numeric_match.group(5)
        end_year = numeric_match.group(6)
        
        start_date = datetime(int(start_year), int(start_month), int(start_day))
        end_date = datetime(int(end_year), int(end_month), int(end_day))
        
        details["Start Date"] = start_date.strftime('%Y-%m-%d')
        details["End Date"] = end_date.strftime('%Y-%m-%d')
        details["Trip Duration"] = f"{(end_date - start_date).days + 1} days"
    
    elif date_for_duration_match:
        # Handle format "from 12th march for two week"
        day = date_for_duration_match.group(1)
        month = date_for_duration_match.group(2)
        year = date_for_duration_match.group(3) or datetime.today().year
        duration_num = convert_text_to_number(date_for_duration_match.group(4))
        duration_unit = date_for_duration_match.group(5)
        
        start_date_text = f"{day} {month} {year}"
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        
        if start_date:
            duration_days = convert_unit_to_days(duration_num, duration_unit)
            end_date = start_date + timedelta(days=duration_days - 1)  # -1 to make duration inclusive of start day
            
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{duration_days} days"
    
    elif duration_from_date_match:
        # Handle format "for a week from 13th april"
        duration_num = convert_text_to_number(duration_from_date_match.group(1))
        duration_unit = duration_from_date_match.group(2)
        day = duration_from_date_match.group(3)
        month = duration_from_date_match.group(4)
        year = duration_from_date_match.group(5) or datetime.today().year
        
        start_date_text = f"{day} {month} {year}"
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        
        if start_date:
            duration_days = convert_unit_to_days(duration_num, duration_unit)
            end_date = start_date + timedelta(days=duration_days - 1)
            
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{duration_days} days"
    
    elif duration_on_date_match:
        # Handle format "for two weeks on 3rd april"
        duration_num = convert_text_to_number(duration_on_date_match.group(1))
        duration_unit = duration_on_date_match.group(2)
        day = duration_on_date_match.group(3)
        month = duration_on_date_match.group(4)
        year = duration_on_date_match.group(5) or datetime.today().year
        
        start_date_text = f"{day} {month} {year}"
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        
        if start_date:
            duration_days = convert_unit_to_days(duration_num, duration_unit)
            end_date = start_date + timedelta(days=duration_days - 1)
            
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{duration_days} days"
    
    elif on_date_for_duration_match:
        # Handle format "on 13th march for a week"
        day = on_date_for_duration_match.group(1)
        month = on_date_for_duration_match.group(2)
        year = on_date_for_duration_match.group(3) or datetime.today().year
        duration_num = convert_text_to_number(on_date_for_duration_match.group(4))
        duration_unit = on_date_for_duration_match.group(5)
        
        start_date_text = f"{day} {month} {year}"
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        
        if start_date:
            duration_days = convert_unit_to_days(duration_num, duration_unit)
            end_date = start_date + timedelta(days=duration_days - 1)
            
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{duration_days} days"
    
    elif duration_on_numeric_date_match:
        # Handle format "for 2 weeks on 20/05/2025" or "for two weeks on 02-08-2025"
        duration_num = convert_text_to_number(duration_on_numeric_date_match.group(1))
        duration_unit = duration_on_numeric_date_match.group(2)
        day = duration_on_numeric_date_match.group(3)
        month = duration_on_numeric_date_match.group(4)
        year = duration_on_numeric_date_match.group(5)
        
        try:
            start_date = datetime(int(year), int(month), int(day))
            duration_days = convert_unit_to_days(duration_num, duration_unit)
            end_date = start_date + timedelta(days=duration_days - 1)
            
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{duration_days} days"
        except ValueError:
            # Handle potential date validation errors
            pass
    
    elif on_numeric_date_for_duration_match:
        # Handle format "on 05/06/2025 for two weeks" or "on 06-07-2025 for 2 weeks"
        day = on_numeric_date_for_duration_match.group(1)
        month = on_numeric_date_for_duration_match.group(2)
        year = on_numeric_date_for_duration_match.group(3)
        duration_num = convert_text_to_number(on_numeric_date_for_duration_match.group(4))
        duration_unit = on_numeric_date_for_duration_match.group(5)
        
        try:
            start_date = datetime(int(year), int(month), int(day))
            duration_days = convert_unit_to_days(duration_num, duration_unit)
            end_date = start_date + timedelta(days=duration_days - 1)
            
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{duration_days} days"
        except ValueError:
            # Handle potential date validation errors
            pass
    
    # If none of the specific patterns matched, fall back to existing date extraction logic
    if not details.get("Start Date"):
        # Enhanced regex for extracting date ranges in multiple formats
        date_range_match = re.search(
            r'(?P<start_day>\d{1,2})(?:st|nd|rd|th)?\s*(?P<start_month>[A-Za-z]+)?,?\s*(?P<start_year>\d{4})?\s*(?:-|from|on|to|through)\s*'
            r'(?P<end_day>\d{1,2})(?:st|nd|rd|th)?\s*(?P<end_month>[A-Za-z]+)?,?\s*(?P<end_year>\d{4})?',
            text, re.IGNORECASE
)
        
    if seasonal_mappings:
        for season, start_month_day in seasonal_mappings.items():
            pattern = r'\b' + re.escape(season) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                today = datetime.today().year
                start_date = f"{today}-{start_month_day}"
                details["Start Date"] = start_date
                if "duration_days" in locals():
                    details["End Date"] = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=duration_days)).strftime('%Y-%m-%d')
                break  
    
    # Extract number of travelers
    travelers_match = re.search(r'(?P<adults>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:people|persons|adult|person|adults|man|men|woman|women|lady|ladies|climber|traveler)',text, re.IGNORECASE)
    children_match = re.search(r'(?P<children>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:child|children)', text, re.IGNORECASE)
    infants_match = re.search(r'(?P<infants>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:infant|infants)', text, re.IGNORECASE)

    solo_match = re.search(r'\b(?:solo|alone|I|me)\b', text, re.IGNORECASE)
    duo_match = re.search(r'\b(?:duo|honeymoon|couple|pair|my partner and I|my wife and I|my husband and I)\b', text, re.IGNORECASE)
    trio_match = re.search(r'\btrio\b', text, re.IGNORECASE)
    group_match = re.search(r'family of (\d+)|group of (\d+)', text, re.IGNORECASE)
     
    # Count occurrences of adult-related words
    adult_words_match = len(re.findall(r'\b(?:man|men|woman|women|lady|ladies)\b', text, re.IGNORECASE))
    number_words = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9","ten": "10"}

    # Convert written numbers for adults
    num_adults_text = travelers_match.group("adults") if travelers_match else "0"
    num_adults_text = number_words.get(num_adults_text.lower(), num_adults_text)
    num_adults = int(num_adults_text)

    # Convert written numbers for children
    num_children_text = children_match.group("children") if children_match else "0"
    num_children_text = number_words.get(num_children_text.lower(), num_children_text)
    num_children = int(num_children_text)

    # Convert written numbers for infants
    num_infants_text = infants_match.group("infants") if infants_match else "0"
    num_infants_text = number_words.get(num_infants_text.lower(), num_infants_text)
    num_infants = int(num_infants_text)

    travelers = {
    "Adults": num_adults,
    "Children": num_children,
    "Infants": num_infants
    }
    
    if solo_match:
        travelers["Adults"] = 1
    elif duo_match:
        travelers["Adults"] = 2
    elif trio_match:
        travelers["Adults"] = 3
    elif group_match:
        total_people = int(group_match.group(1) or group_match.group(2))
        if total_people > 2:
            travelers["Adults"] = max(2, total_people - travelers["Children"] - travelers["Infants"])
    
    details["Number of Travelers"] = travelers
    
    # Extract transportation preferences
    transport_modes = {
        "flight": ["flight", "fly", "airplane", "airlines","airline" ,"aeroplane"],
        "train": ["train", "railway"],
        "bus": ["bus", "coach"],
        "car": ["car", "auto", "automobile", "vehicle", "road trip", "drive"],
        "boat": ["boat", "ship", "cruise", "ferry"],
        "bike": ["bike", "bicycle", "cycling"],
        "subway": ["subway", "metro", "underground"],
        "tram": ["tram", "streetcar", "trolley"]
    }
    
    transport_matches = []
    for mode, keywords in transport_modes.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                transport_matches.append(mode)
                break
    
    details["Transportation Preferences"] = transport_matches if transport_matches else "Any"

    # Extract budget details
    # Budget classification keywords
    budget_keywords = {
    "friendly budget": "Mid-range Budget",
    "mid-range budget": "Mid-range",
    "luxury": "Luxury",
    "cheap": "Low Budget",
    "expensive": "Luxury",
    "premium": "Luxury",
    "high-range": "Luxury"
    }

    budget_matches = []
    # Check for budget keywords in text
    for key, val in budget_keywords.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.IGNORECASE):
            budget_matches.append(val)

    # Currency name to symbol mapping (handling singular & plural)
    currency_symbols = {
    "USD": "$", "dollar": "$", "dollars": "$",
    "EUR": "€", "euro": "€", "euros": "€",
    "JPY": "¥", "yen": "¥",
    "INR": "₹", "rupee": "₹", "rupees": "₹",
    "GBP": "£", "pound": "£", "pounds": "£",
    "CNY": "¥", "yuan": "¥", "RMB": "¥"
    }

    # First pattern: Budget with context words
    budget_context_match = re.search(
    r'\b(?:budget|cost|expense|spending cap|max limit|is|cost limit|amount|price)\s*(?:of\s*)?(?P<currency>\$|€|¥|₹|£)?\s*(?P<amount>[\d,]+)\s*(?P<currency_name>USD|dollars?|yen|JPY|euro|EUR|euros|rupees?|INR|pounds?|GBP|CNY|yuan|RMB)?\b',
    text, re.IGNORECASE
    )

    # Second pattern: Direct currency amount without context words
    direct_currency_match = re.search(
    r'\b(?P<currency>\$|€|¥|₹|£)\s*(?P<amount>[\d,]+)\b|\b(?P<amount2>[\d,]+)\s*(?P<currency_name>USD|dollars?|yen|JPY|euro|EUR|euros|rupees?|INR|pounds?|GBP|CNY|yuan|RMB)\b',
    text, re.IGNORECASE
    )

    # Process budget amount and currency
    if budget_context_match:
        currency_symbol = budget_context_match.group("currency") or ""
        amount = budget_context_match.group("amount").replace(",", "")  # Normalize number format
        currency_name = budget_context_match.group("currency_name") or ""
        detected_symbol = currency_symbol or currency_symbols.get(currency_name.lower(), "")
        
        if not currency_symbol and not currency_name:
            budget_value = f"{amount} (Specify currency)"
        else:
            budget_value = f"{detected_symbol}{amount}" + (f" ({currency_name})" if currency_name and not currency_symbol else "")
    
    # Use detected symbol or mapped currency name
    elif direct_currency_match:
        currency_symbol = direct_currency_match.group("currency") or ""
        amount = direct_currency_match.group("amount") or direct_currency_match.group("amount2")
        currency_name = direct_currency_match.group("currency_name") or ""
        detected_symbol = currency_symbol or currency_symbols.get(currency_name.lower(), "")
    # Use detected symbol or mapped currency name
        if not currency_symbol and not currency_name:
            budget_value = f"{amount} (Specify Currency)"
        else:
            budget_value = f"{detected_symbol}{amount}" + (f" ({currency_name})" if currency_name and not currency_symbol else "")

    else:
       budget_value = budget_matches[0] if budget_matches else "Unknown"

    # Assign to details dictionary
    details["Budget Range"] = budget_value
    
    # Extract trip type
    trip_type = {
    "Adventure Travel": ["surfing","cycling","Scuba diving","hiking","trekking","camping", "skiing","ski", "backpacking", "extreme sports"],
    "Ecotourism": ["wildlife watching", "nature walks", "eco-lodging"],
    "Cultural Tourism": ["museum visits", "historical site tours", "local festivals"],
    "Historical Tourism": ["castle tours", "archaeological site visits", "war memorial tours"],
    "Luxury Travel": ["private island stays", "first-class flights", "fine dining experiences"],
    "Wildlife Tourism": ["safari tours", "whale watching", "birdwatching"],
    "Sustainable Tourism": ["eco-resorts", "community-based tourism", "carbon-neutral travel"],
    "Volunteer Tourism": ["teaching abroad", "wildlife conservation", "disaster relief work"],
    "Medical Tourism": ["cosmetic surgery", "dental care", "alternative medicine retreats"],
    "Educational Tourism": ["study abroad programs", "language immersion", "historical research"],
    "Business Travel": ["corporate meetings", "networking events", "industry trade shows"],
    "Solo Travel": ["self-guided tours", "meditation retreats", "budget backpacking"],
    "Group Travel": ["guided tours", "cruise trips", "family reunions"],
    "Backpacking": ["hostel stays", "hitchhiking", "long-term travel"],
    "Food Tourism": ["food tasting tours", "cooking classes", "street food exploration"],
    "Religious Tourism": ["pilgrimages", "monastery visits", "religious festivals"],
    "Digital Nomadism": ["co-working spaces", "long-term stays", "remote work-friendly cafes"],
    "Family Travel": ["Family trip","theme parks","honeymoon", "kid-friendly resorts", "multi-generational travel","Family vacation"]
    }
    
    trip_type_matches = []
    for trip, keywords in trip_type.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
               trip_type_matches.append(trip)
               break
    
    details["Trip Type"] = trip_type_matches if trip_type_matches else "Leisure"
       
    # Extract accommodation preferences
    accommodation_types = {
    "Boutique hotels": ["hotel", "boutique hotel", "small hotel", "intimate hotel"],
    "Resorts": ["resort", "holiday resort", "self-contained resort", "luxury resort"],
    "Hostels": ["hostel","hostels", "dormitory", "shared accommodation"],
    "Bed and breakfasts": ["bed and breakfast", "B&B", "guesthouse"],
    "Motels": ["motel", "motor lodge", "roadside motel"],
    "Guesthouses": ["guesthouse", "private guesthouse", "pension"],
    "Vacation rentals": ["vacation rental", "holiday rental", "short-term rental", "airbnb"],
    "Camping": ["camping", "campground", "tent", "camp"]
    }
    
    accommodation_matches = []
    for accomm_type, keywords in accommodation_types.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                accommodation_matches.append(accomm_type)
                break
    
    details["Accommodation Preferences"] = accommodation_matches if accommodation_matches else "Not specified"
    
    # Extract special preferences    
    special_requirements = ["wheelchair access", "vegetarian meals", "vegan", "gluten-free"]
    found_requirements = [req for req in special_requirements if req in text.lower()]
    details["Special Requirements"] = ", ".join(found_requirements) if found_requirements else "Not specified"
    
    return details

# Prompt Generation Agent
def generate_prompt(details):
    #destination_place
    destination = details.get("Destination", "").strip()    
    if not destination:
        return "Error❗Error❗Error❗ Please specify a Destination place."
    
    #start_dates
    start_date_str = details.get("Start Date", "").strip()
    if not start_date_str:
           return "Error❗Error❗Error❗ Please specify a Start Date."
        
    valid_formats = ["%Y-%m-%d", "%d-%m-%Y"]
    
    start_date = None
    for fmt in valid_formats:
        try:
               start_date = datetime.strptime(start_date_str, fmt).date()
               break  # Exit loop if parsing succeeds
        except ValueError:
            continue  # Try next format
    
    if start_date is None:  # If no valid format matched
        return "Error❗Error❗Error❗ Invalid Start Date. Please enter a valid date."

    today = datetime.today().date()
    if start_date < today:
        return "Error❗Error❗Error❗ Start Date should not be in the past."
    
            
    # Trip Duration (including negative ones)
    prompt = f"Generate a detailed itinerary for a {details.get('Trip Type', 'general')} trip to {details.get('Destination', 'an unknown destination')} for {details['Number of Travelers'].get('Adults', '1')} adult"
    trip_duration = details.get("Trip Duration", "").strip()
    match = re.search(r"-?\d+", trip_duration)  
    if match:
        duration_value = int(match.group())
        if duration_value <= 0:
            return "Error❗Error❗Error❗ Enter the correct dates."
        
    #Budget_range   
    budget_range = details.get("Budget Range", "").strip()
    match = re.search(r"\d+", budget_range)
    if not match:
        return "Error❗Error❗Error❗ Please specify your budget as a range (e.g., 1000-2000)." 
    #number_of_travelers
    number_of_travelers = details.get("Number of Travelers", "")
    adults = number_of_travelers.get("Adults", 0)
    children = number_of_travelers.get("Children", 0) 
    if adults == 0 and children == 0:
        return "Error❗Error❗Error❗ At least one adult or a child should be there for the trip."
    
    # Pluralize 'adults' correctly
    if details['Number of Travelers'].get('Adults', '1') != "1":
        prompt += "s"
    
    # Add children & infants if applicable
    if details['Number of Travelers'].get('Children', "0") != "0":
        prompt += f" and {details['Number of Travelers']['Children']} children"
    
    if details['Number of Travelers'].get('Infants', "0") != "0":
        prompt += f" and {details['Number of Travelers']['Infants']} infants"
    
    # Starting location and start date (only if both exist)
    if "Starting Location" in details and "Start Date" in details:
        prompt += f", starting from {details['Starting Location']} and departing on {details['Start Date']}"
    elif "Starting Location" in details:
        prompt += f", starting from {details['Starting Location']}"
    elif "Start Date" in details:
        prompt += f", departing on {details['Start Date']}"
    
    # End date
    if details.get("End Date"):
        prompt += f". The trip ends on {details['End Date']}."
    
    # Budget and general recommendations
    prompt += f" Please consider a {details.get('Budget Range', 'moderate')} budget and provide accommodation, dining, and activity recommendations."
    
    # Transportation preferences
    if details.get("Transportation Preferences") and details["Transportation Preferences"] != "Any":
        prompt += f" Suggested transportation methods include: {', '.join(details['Transportation Preferences'])}."
    
    # Accommodation preferences
    if details.get("Accommodation Preferences") and details["Accommodation Preferences"] != "Any":
        prompt += f" Preferred accommodation: {details['Accommodation Preferences']}."
    
    # Special requirements
    if details.get("Special Requirements") and details["Special Requirements"] not in ["None", "", None]:
        prompt += f" Special requirements: {details['Special Requirements']}."
    
    return prompt

st.title("Travel Plan Extractor")
user_input = st.text_area("Enter your travel details:")
if st.button("Plan my Trip", type='primary'):
    if user_input:
        details = extract_details(user_input)  # Extract details once
        # Create a pandas DataFrame for table presentation
        details_df = pd.DataFrame(details.items(), columns=["Detail", "Value"])
        details_df.index = details_df.index + 1
        st.subheader("Extracted Travel Details")
        st.table(details_df)

        # Generate and display the itinerary prompt
        prompt = generate_prompt(details)
        st.subheader("Itinerary Request Prompt")
        st.write(prompt)

        # Display JSON output
        error_messages = ["Error❗Error❗Error❗", "Failed to generate", "Invalid input"]  # Add more error patterns if needed
        if not any(error in prompt for error in error_messages):
            with st.spinner("Generating detailed itinerary with Google Gemini..."):
                itinerary = generate_itinerary_with_gemini(prompt)  
            st.subheader("Your Personalized Itinerary (Powered by Google Gemini)")
            st.markdown(itinerary)
            details_json = json.dumps(details, indent=4)  
            st.subheader("Extracted Travel Details (JSON)")
            st.json(details_json)  # Display JSON output
        else:
            st.warning("An error occurred in itinerary generation. JSON details will not be generated.")
    else:
        st.warning("Please enter some text to extract details.")
     # Footer
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Be specific about dates, locations, and number of travelers
    - Include budget information if available
    - Mention transportation and accommodation preferences
    - Add any special requirements or considerations
    """)
