import streamlit as st
import spacy
import dateparser
import re
import pandas as pd
from dateparser import parse
from datetime import datetime, timedelta
from dateparser.search import search_dates
import geonamescache
from word2number import w2n
import json
import google.generativeai as genai

# Configure the Streamlit page
st.set_page_config(
    page_title="Travel Planner Pro Z",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
        /* Main container */
        .main {
            padding: 2rem;
        }
        
        /* Headers */
        h1 {
            color: #1E88E5;
            font-size: 3rem !important;
            text-align: center;
            margin-bottom: 2rem !important;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        
        h2 {
            color: #2196F3;
            margin-top: 2rem !important;
        }
        
        h3 {
            color: #42A5F5;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background-color: #F8F9FA;
            padding: 0.5rem;
            border-radius: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 0 20px;
            background-color: #FFFFFF;
            border-radius: 5px;
            color: #1E88E5;
            font-weight: 600;
        }
        
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background-color: #1E88E5;
            color: white;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            background-color: #F8F9FA;
            border-radius: 10px;
            padding: 0.5rem;
        }
        
        /* Button styling */
        .stButton>button {
            width: 100%;
            height: 50px;
            background-color: #1E88E5;
            color: white;
            font-weight: 600;
            border-radius: 10px;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            background-color: #1976D2;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Text area styling */
        .stTextArea textarea {
            border-radius: 10px;
            border: 2px solid #E3F2FD;
            padding: 1rem;
        }
        
        .stTextArea textarea:focus {
            border-color: #1E88E5;
            box-shadow: 0 0 0 2px rgba(30,136,229,0.2);
        }
        
        /* Card-like containers */
        .css-1r6slb0 {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        
        /* Download buttons */
        .stDownloadButton>button {
            width: 100%;
            background-color: #4CAF50;
            color: white;
            padding: 0.5rem;
            border-radius: 5px;
            border: none;
            margin-top: 1rem;
        }
        
        /* Tips section */
        .tip-box {
            background-color: #E3F2FD;
            padding: 1rem;
            border-radius: 10px;
            margin-top: 2rem;
        }
        
        /* Icons and emojis */
        .icon-text {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* Table styling */
        .dataframe {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .dataframe th {
            background-color: #1E88E5;
            color: white;
            padding: 1rem !important;
        }
        
        .dataframe td {
            padding: 0.75rem !important;
        }
        
        /* Progress spinner */
        .stSpinner {
            text-align: center;
            color: #1E88E5;
        }
    </style>
""", unsafe_allow_html=True)

def setup_gemini():
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]  # Store your API key in Streamlit secrets
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel('gemini-1.5-pro')  # Choose the appropriate model

# Load spaCy model globally
@st.cache_resource
def load_spacy_model():
    return spacy.load("en_core_web_trf")

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
    date_for_duration_pattern = r'from\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?\s+for\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|days|week|weeks|month|months)'
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
    r'\b(?:budget|cost|expense|spending cap|is|max limit|cost limit|amount|price)\s*(?:of\s*)?(?P<currency>\$|€|¥|₹|£)?\s*(?P<amount>[\d,]+)\s*(?P<currency_name>USD|dollars?|yen|JPY|euro|EUR|euros|rupees?|INR|pounds?|GBP|CNY|yuan|RMB)?\b',
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

# Function to generate itinerary using Gemini
def generate_itinerary_with_gemini(prompt):
    model = setup_gemini()
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating itinerary: {str(e)}"

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
    
    # Add top attractions
    prompt += f" Include a section on the top 5-7 must-visit attractions in {destination} with brief descriptions and why they're worth visiting."
    
    # Add travel tips
    prompt += f" Provide a section with practical travel tips specific to {destination}, including local customs, transportation advice, safety information, and any seasonal considerations."
    
    # Add weather forecast
    if "Start Date" in details and details.get("Trip Duration"):
        prompt += f" Include a general weather forecast for {destination} during the trip duration (from {details['Start Date']}"
        if details.get("End Date"):
            prompt += f" to {details['End Date']}"
        prompt += "), including expected temperatures, precipitation, and appropriate clothing recommendations."
    # NEW: Add request for affordable dining options near hotels and attractions
    prompt += f" For each day, suggest 2-3 affordable dining options that are within walking distance or a short trip from the recommended accommodations and attractions for that day. Include the price range, cuisine type, and any specialties or popular dishes."
    # Daily itinerary request
    prompt += f"\n1. Daily Itinerary: Provide a detailed day-by-day plan for the entire {duration_value} day trip, including:"
    prompt += "\n   - Activities and attractions for each day with approximate time allocations"
    prompt += "\n   - Recommended accommodations for each night"
    prompt += "\n   - Suggested meals and dining options (breakfast, lunch, dinner) with price estimates in local currency and USD"
    prompt += "\n   - Transportation options between locations with costs"
    
# Top attractions request
    prompt += f"\n2. Top Attractions: List 9 must-visit attractions in {destination} with:"
    prompt += "\n   - Brief descriptions of each attraction"
    prompt += "\n   - Why they're worth visiting"
    prompt += "\n   - Entrance fees and costs"
    prompt += "\n   - Transportation options to reach them from city center with costs"

# Accommodation options - REVISED
    prompt += "\n3. Accommodation Options: Provide 7 detailed accommodation recommendations with:"
    prompt += "\n   - Specific price range per night in local currency and USD"
    prompt += "\n   - Precise neighborhood and location description"
    prompt += "\n   - Complete list of amenities and unique benefits"
    prompt += "\n   - Full address and proximity to main attractions"
    prompt += "\n   - Do NOT refer to the daily itinerary - include all details here"

# Dining recommendations - REVISED
    prompt += "\n4. Dining Recommendations:"
    prompt += "\n   - Include at least 10 restaurant options organized by neighborhood/area"
    prompt += "\n   - Specify price range per meal in local currency and USD for each restaurant"
    prompt += "\n   - Detail signature dishes and cuisine specialties for each recommendation"
    prompt += "\n   - Provide exact restaurant locations and address"
    prompt += "\n   - Do NOT refer to the daily itinerary - include all details here"

# Transportation information
    prompt += "\n5. Transportation Information:"
    prompt += "\n   - Options for getting around (public transport, taxis, rentals)"
    prompt += "\n   - Costs for each transportation method"
    prompt += "\n   - Tips for navigating local transportation"

# Travel tips
    prompt += f"\n6. Travel Tips for {destination}:"
    prompt += "\n   - Local customs and etiquette"
    prompt += "\n   - Safety information"
    prompt += "\n   - Local language and culture"
    prompt += "\n   - Currency and payment advice"
    prompt += "\n   - Seasonal considerations"

# Weather forecast
    prompt += f"\n7. Weather Forecast:"
    prompt += f"\n   - Expected temperatures and conditions in {destination} during the trip dates"
    prompt += "\n   - Clothing recommendations based on the weather"

# 8. Budget Breakdown
    prompt += "\n\n8. Budget Breakdown:"
    prompt += "\n   - Estimated total cost for the entire trip"
    prompt += "\n   - Breakdown by category (accommodation, food, transportation, activities)"
    prompt += "\n   - Money-saving tips specific to the destination"

# 9. Emergency Information
    prompt += "\n\n9. Emergency Information:"
    prompt += "\n   - Local emergency numbers"
    prompt += "\n   - Nearest hospitals or medical facilities"
    prompt += "\n   - Embassy or consulate information if international"
    return prompt


# New function to extract structured JSON from itinerary
def extract_itinerary_json(itinerary_text):
    try:
        # First try to find a JSON block that might be included in the response
        import re
        import json
        import traceback
        
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        json_match = re.search(json_pattern, itinerary_text)
        
        if json_match:
            json_str = json_match.group(1)
            try:
                return json.loads(json_str)
            except:
                pass  # If parsing fails, continue to the more complex extraction
        
        # If no JSON block or parsing failed, use more advanced parsing
        parsed_data = {
            "trip_overview": {},
            "days": [],
            "attractions": [],
            "accommodations": [],
            "dining": [],
            "transportation": [],
            "travel_tips": [],
            "weather": {}
        }
        
        # Extract trip overview
        destination_match = re.search(r'(?:itinerary for|trip to)\s+([^\n,\.]+)', itinerary_text, re.IGNORECASE)
        if destination_match:
            parsed_data["trip_overview"]["destination"] = destination_match.group(1).strip()
        
        duration_match = re.search(r'(\d+)(?:-|\s+to\s+)day', itinerary_text, re.IGNORECASE)
        if duration_match:
            parsed_data["trip_overview"]["duration_days"] = int(duration_match.group(1))
        
        # Try to extract trip type and budget
        trip_type_match = re.search(r'(?:type of trip|trip type):\s*([^\n\.]+)', itinerary_text, re.IGNORECASE)
        if trip_type_match:
            parsed_data["trip_overview"]["trip_type"] = trip_type_match.group(1).strip()
            
        budget_match = re.search(r'(?:budget|cost|price)(?:\s+range)?:\s*([^\n\.]+)', itinerary_text, re.IGNORECASE)
        if budget_match:
            parsed_data["trip_overview"]["budget_range"] = budget_match.group(1).strip()
        
        # Extract days (looking for day patterns like "Day 1", "Day 2: Title")
        day_pattern = r'Day\s+(\d+)(?:[\s\-:]+([^\n]+))?'
        day_matches = list(re.finditer(day_pattern, itinerary_text))
        
        for i, match in enumerate(day_matches):
            day_num = int(match.group(1))
            day_title = match.group(2).strip() if match.group(2) else ""
            
            # Get the content of this day (until next day or end)
            start_pos = match.end()
            end_pos = day_matches[i+1].start() if i < len(day_matches) - 1 else len(itinerary_text)
            day_content = itinerary_text[start_pos:end_pos].strip()
            
            # Initialize day data structure
            day_data = {
                "day_number": day_num,
                "title": day_title,
                "morning": "",
                "afternoon": "",
                "evening": "",
                "meals": {
                    "breakfast": "",
                    "lunch": "",
                    "dinner": ""
                },
                "accommodation": "",
                "activities": []
            }
            
            # Extract date if present
            date_match = re.search(r'(?:Date|On):\s*(\d{1,2}(?:st|nd|rd|th)?\s+\w+(?:\s+\d{4})?|\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2}(?:st|nd|rd|th)?,\s*\d{4})', day_content, re.IGNORECASE)
            if date_match:
                day_data["date"] = date_match.group(1).strip()
            
            # Extract time-based activities with more detailed pattern matching
            # Morning section
            morning_match = re.search(r'(?:Morning|AM)(?:[\s\-:]+)([\s\S]*?)(?=(?:Afternoon|Lunch|PM|Evening|Dinner|Accommodation|Day|$))', day_content, re.IGNORECASE)
            if morning_match:
                day_data["morning"] = morning_match.group(1).strip()
            
            # Also check for bullet points in the Morning section
            if "* **Morning:**" in day_content or "- **Morning:**" in day_content:
                morning_bullet = re.search(r'(?:\*|\-)\s+\*\*Morning:\*\*\s+([\s\S]*?)(?=(?:\*|\-)\s+\*\*(?:Afternoon|Lunch|Evening|Dinner|Meals|Accommodation)|$)', day_content, re.IGNORECASE)
                if morning_bullet:
                    day_data["morning"] = morning_bullet.group(1).strip()
            
            # Afternoon section
            afternoon_match = re.search(r'(?:Afternoon|PM)(?:[\s\-:]+)([\s\S]*?)(?=(?:Evening|Dinner|Accommodation|Day|$))', day_content, re.IGNORECASE)
            if afternoon_match:
                day_data["afternoon"] = afternoon_match.group(1).strip()
            
            # Also check for bullet points in the Afternoon section
            if "* **Afternoon:**" in day_content or "- **Afternoon:**" in day_content:
                afternoon_bullet = re.search(r'(?:\*|\-)\s+\*\*Afternoon:\*\*\s+([\s\S]*?)(?=(?:\*|\-)\s+\*\*(?:Evening|Dinner|Meals|Accommodation)|$)', day_content, re.IGNORECASE)
                if afternoon_bullet:
                    day_data["afternoon"] = afternoon_bullet.group(1).strip()
            
            # Evening section
            evening_match = re.search(r'(?:Evening|Night)(?:[\s\-:]+)([\s\S]*?)(?=(?:Accommodation|Day|$))', day_content, re.IGNORECASE)
            if evening_match:
                day_data["evening"] = evening_match.group(1).strip()
            
            # Also check for bullet points in the Evening section
            if "* **Evening:**" in day_content or "- **Evening:**" in day_content:
                evening_bullet = re.search(r'(?:\*|\-)\s+\*\*Evening:\*\*\s+([\s\S]*?)(?=(?:\*|\-)\s+\*\*(?:Meals|Accommodation)|$)', day_content, re.IGNORECASE)
                if evening_bullet:
                    day_data["evening"] = evening_bullet.group(1).strip()
            
            # Extract meals - enhanced to capture more details
            # Check for the Meals section with bullet points
            meals_section = re.search(r'(?:\*|\-)\s+\*\*Meals:\*\*([\s\S]*?)(?=(?:\*|\-)\s+\*\*(?:Accommodation)|$)', day_content, re.IGNORECASE)
            if meals_section:
                meals_content = meals_section.group(1).strip()
                
                # Extract breakfast details
                breakfast_match = re.search(r'(?:Breakfast|breakfast):\s+([^\n]+)', meals_content, re.IGNORECASE)
                if breakfast_match:
                    day_data["meals"]["breakfast"] = breakfast_match.group(1).strip()
                
                # Extract lunch details
                lunch_match = re.search(r'(?:Lunch|lunch):\s+([^\n]+)', meals_content, re.IGNORECASE)
                if lunch_match:
                    day_data["meals"]["lunch"] = lunch_match.group(1).strip()
                
                # Extract dinner details
                dinner_match = re.search(r'(?:Dinner|dinner):\s+([^\n]+)', meals_content, re.IGNORECASE)
                if dinner_match:
                    day_data["meals"]["dinner"] = dinner_match.group(1).strip()
            else:
                # Fallback to original approach
                breakfast_match = re.search(r'(?:Breakfast)(?:[\s\-:]+)([^#\n]+)', day_content, re.IGNORECASE)
                if breakfast_match:
                    day_data["meals"]["breakfast"] = breakfast_match.group(1).strip()
                
                lunch_match = re.search(r'(?:Lunch)(?:[\s\-:]+)([^#\n]+)', day_content, re.IGNORECASE)
                if lunch_match:
                    day_data["meals"]["lunch"] = lunch_match.group(1).strip()
                
                dinner_match = re.search(r'(?:Dinner)(?:[\s\-:]+)([^#\n]+)', day_content, re.IGNORECASE)
                if dinner_match:
                    day_data["meals"]["dinner"] = dinner_match.group(1).strip()
            
            # Extract accommodation with price details
            accommodation_section = re.search(r'(?:\*|\-)\s+\*\*Accommodation:\*\*\s+([\s\S]*?)(?=(?:\*|\-)|$)', day_content, re.IGNORECASE)
            if accommodation_section:
                accommodation_text = accommodation_section.group(1).strip()
                day_data["accommodation"] = accommodation_text
                
                # Extract accommodation details and add to accommodations list
                accommodation_items = re.findall(r'([\w\s]+)\s+\(([^\)]+)\)', accommodation_text)
                for item in accommodation_items:
                    accommodation_name = item[0].strip()
                    price_range = item[1].strip()
                    
                    # Check if this accommodation is already in the list
                    existing_acc = next((acc for acc in parsed_data["accommodations"] if acc["name"] == accommodation_name), None)
                    if not existing_acc:
                        parsed_data["accommodations"].append({
                            "name": accommodation_name,
                            "description": "",
                            "price_range": price_range
                        })
            else:
                # Fallback to original approach
                accommodation_match = re.search(r'(?:Accommodation|Stay|Hotel|Lodge)(?:[\s\-:]+)([^#\n]+)', day_content, re.IGNORECASE)
                if accommodation_match:
                    day_data["accommodation"] = accommodation_match.group(1).strip()
                    
                    # Also add to accommodations list if not already there
                    accommodation_name = accommodation_match.group(1).strip()
                    if not any(acc.get("name") == accommodation_name for acc in parsed_data["accommodations"]):
                        parsed_data["accommodations"].append({
                            "name": accommodation_name,
                            "description": "",
                            "price_range": ""
                        })
            
            # Extract dining details from meals
            extract_dining_from_meals(day_data, parsed_data)
            
            # Extract activities
            # First try bullet points with activity names
            activity_pattern = r'(?:^|\n)\s*(?:[\*\-•]|\d+\.)\s+([^\n]+)'
            activities = re.finditer(activity_pattern, day_content, re.MULTILINE)
            for act_match in activities:
                activity = act_match.group(1).strip()
                # Skip section headers that were matched
                if not activity.startswith("**") and ":**" not in activity:
                    day_data["activities"].append(activity)
            
            # If no activities were found via bullets, extract from the time-based sections
            if not day_data["activities"] and (day_data["morning"] or day_data["afternoon"] or day_data["evening"]):
                # Extract activities from time-based sections
                all_activities = []
                for section in [day_data["morning"], day_data["afternoon"], day_data["evening"]]:
                    if section:
                        # Split by semicolons, periods, or commas for potential activities
                        section_activities = re.split(r'(?<=[.;])\s+|\s*,\s*', section)
                        all_activities.extend([act.strip() for act in section_activities if act.strip()])
                
                day_data["activities"] = all_activities
            
            parsed_data["days"].append(day_data)
        
        # Extract transportation details
        extract_transportation(itinerary_text, parsed_data)
        
        # Extract attractions
        extract_attractions(itinerary_text, parsed_data)
        
        # Extract travel tips
        extract_travel_tips(itinerary_text, parsed_data)
        
        # Extract weather information
        extract_weather_info(itinerary_text, parsed_data)
        
        # Return the structured data
        return parsed_data
        
    except Exception as e:
        # If parsing fails, return a basic structure with error information
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "Failed to parse itinerary into structured JSON. Manual processing required.",
            "raw_text": itinerary_text
        }

# Helper function to extract meal details from text
def extract_meal_details(meal_text):
    # Create a basic structure
    meal_info = {
        "name": "",
        "description": "",
        "price_range": ""
    }
    
    # Extract restaurant name with price if available
    if "at" in meal_text.lower():
        restaurant_match = re.search(r'at\s+([^(]+)(?:\s*\(([^)]+)\))?', meal_text, re.IGNORECASE)
        if restaurant_match:
            meal_info["name"] = restaurant_match.group(1).strip()
            if restaurant_match.group(2):
                meal_info["price_range"] = restaurant_match.group(2).strip()
    elif ":" in meal_text:
        parts = meal_text.split(":", 1)
        meal_info["name"] = parts[0].strip()
        meal_info["description"] = parts[1].strip()
    else:
        meal_info["name"] = meal_text.strip()
    
    # Extract price range if available
    price_match = re.search(r'(?:[$€£₹]\d+(?:-|\s*to\s*)[$€£₹]?\d+|\w+\s+price(?:\s+range)?)', meal_text, re.IGNORECASE)
    if price_match and not meal_info["price_range"]:
        meal_info["price_range"] = price_match.group(0).strip()
    
    return meal_info

# Helper function to extract dining info from meals sections
def extract_dining_from_meals(day_data, parsed_data):
    # Extract detailed meals info and add to dining list
    for meal_type in ["breakfast", "lunch", "dinner"]:
        meal_text = day_data["meals"].get(meal_type, "")
        if meal_text and "N/A" not in meal_text:
            meal_info = extract_meal_details(meal_text)
            if meal_info and meal_info["name"]:
                # Check if this dining option is already in the list
                if not any(d.get("name") == meal_info["name"] for d in parsed_data["dining"]):
                    meal_info["meal_type"] = meal_type.capitalize()
                    parsed_data["dining"].append(meal_info)

# Helper function to extract transportation details
def extract_transportation(itinerary_text, parsed_data):
    # Extract from dedicated transportation section
    transport_section = re.search(r'(?:Transportation|Getting Around|Transport)[\s\S]*?(?=\n#|\Z)', itinerary_text, re.IGNORECASE)
    if transport_section:
        transport_text = transport_section.group(0)
        
        # Extract specific transportation details with prices
        transport_pattern = r'(?:[\*\-•]|\d+\.)\s+([^:]+)(?::\s+|\n\s*)([\s\S]*?)(?=(?:[\*\-•]|\d+\.)\s+|\n#|\Z)'
        transport_items = re.finditer(transport_pattern, transport_text)
        
        for match in transport_items:
            transport_type = match.group(1).strip()
            details = match.group(2).strip() if match.group(2) else ""
            
            parsed_data["transportation"].append({
                "type": transport_type,
                "details": details
            })
    
    # Also scan all day content for transportation mentions
    transport_keywords = ["taxi", "bus", "train", "subway", "metro", "car", "rental", "bike", "walk", "ferry", "boat", "transfer"]
    for day in parsed_data["days"]:
        day_content = day.get("morning", "") + " " + day.get("afternoon", "") + " " + day.get("evening", "")
        
        for keyword in transport_keywords:
            # Find transportation mentions with potential price info
            transport_pattern = r'(?:' + keyword + r')[^.]*?(?:[\$₹€£]\d+[^.]*?)?'
            transport_matches = re.finditer(transport_pattern, day_content, re.IGNORECASE)
            
            for transport_match in transport_matches:
                transport_text = transport_match.group(0).strip()
                
                # Check if this transportation option is already in the list
                if not any(t.get("details") == transport_text for t in parsed_data["transportation"]):
                    parsed_data["transportation"].append({
                        "type": keyword.title(),
                        "details": transport_text
                    })

# Helper function to extract attractions
def extract_attractions(itinerary_text, parsed_data):
    # First try to extract from a dedicated attractions section
    attraction_section = re.search(r'(?:Top Attractions|Must-Visit Attractions|Attractions)[\s\S]*?(?=\n#|\Z)', itinerary_text, re.IGNORECASE)
    if attraction_section:
        attraction_text = attraction_section.group(0)
        # Look for numbered or bulleted attraction listings
        attraction_pattern = r'(?:[\d\*\-]+\.?\s+)([^\n:]+)(?:\s*[:–-]\s*|\n\s*)([\s\S]*?)(?=\n\s*[\d\*\-]+\.|\n#|\Z)'
        attractions = re.finditer(attraction_pattern, attraction_text)
        
        for match in attractions:
            name = match.group(1).strip()
            description = match.group(2).strip()
            
            # Check if this attraction is already in the list
            if not any(a.get("name") == name for a in parsed_data["attractions"]):
                parsed_data["attractions"].append({
                    "name": name,
                    "description": description,
                    "visit_duration": ""
                })
    
    # Also extract attractions from activities
    for day in parsed_data["days"]:
        activities = day.get("activities", [])
        day_content = day.get("morning", "") + " " + day.get("afternoon", "") + " " + day.get("evening", "")
        
        # Extract potential attractions from activities and day content
        potential_attractions = activities.copy()
        
        # Add locations mentioned in day content
        location_pattern = r'(?:Visit|Explore|Tour|See)\s+([^,.]+)'
        locations = re.finditer(location_pattern, day_content, re.IGNORECASE)
        for loc_match in locations:
            location = loc_match.group(1).strip()
            potential_attractions.append(location)
        
        # Process potential attractions
        for attraction in potential_attractions:
            # Skip generic activities and meals
            generic_terms = ["breakfast", "lunch", "dinner", "check-in", "check-out", "hotel", "restaurant"]
            if any(term in attraction.lower() for term in generic_terms):
                continue
            
            # Check if this attraction is already in the list
            if not any(a.get("name") == attraction for a in parsed_data["attractions"]):
                # Try to extract visit duration if available
                duration_match = re.search(r'(?:spend|duration|for)\s+(\d+(?:\.\d+)?\s*(?:hour|hr|minute|min)s?)', attraction, re.IGNORECASE)
                visit_duration = duration_match.group(1) if duration_match else ""
                
                parsed_data["attractions"].append({
                    "name": attraction,
                    "description": "",
                    "visit_duration": visit_duration
                })

# Helper function to extract travel tips
def extract_travel_tips(itinerary_text, parsed_data):
    tips_section = re.search(r'(?:Travel Tips|Practical Information|Tips|Advice)[\s\S]*?(?=\n#|\Z)', itinerary_text, re.IGNORECASE)
    if tips_section:
        tips_text = tips_section.group(0)
        # Look for numbered or bulleted tips
        tip_pattern = r'(?:[\*\-•]|\d+\.)\s+([^\n]+)'
        tips = re.finditer(tip_pattern, tips_text)
        
        for match in tips:
            tip = match.group(1).strip()
            parsed_data["travel_tips"].append(tip)

# Helper function to extract weather information
def extract_weather_info(itinerary_text, parsed_data):
    weather_section = re.search(r'(?:Weather|Climate|Weather Forecast)[\s\S]*?(?=\n#|\Z)', itinerary_text, re.IGNORECASE)
    if weather_section:
        weather_text = weather_section.group(0)
        
        # Extract temperature ranges
        temp_pattern = r'(\d+)[°˚]?C?\s*(?:-|to)\s*(\d+)[°˚]?C?'
        temp_match = re.search(temp_pattern, weather_text)
        if temp_match:
            parsed_data["weather"]["temperature_range"] = {
                "min": int(temp_match.group(1)),
                "max": int(temp_match.group(2)),
                "unit": "Celsius"
            }
        
        # Extract temperature in Fahrenheit if available
        fahrenheit_pattern = r'(\d+)[°˚]?F?\s*(?:-|to)\s*(\d+)[°˚]?F?'
        fahrenheit_match = re.search(fahrenheit_pattern, weather_text)
        if fahrenheit_match and "°F" in weather_text:
            parsed_data["weather"]["temperature_fahrenheit"] = {
                "min": int(fahrenheit_match.group(1)),
                "max": int(fahrenheit_match.group(2)),
                "unit": "Fahrenheit"
            }
        
        # Extract general weather conditions
        conditions_pattern = r'(?:expect|anticipate|forecast|conditions)[^.]*?([^\.]+)'
        conditions_match = re.search(conditions_pattern, weather_text, re.IGNORECASE)
        if conditions_match:
            parsed_data["weather"]["conditions"] = conditions_match.group(1).strip()
        
        # Extract precipitation information
        precipitation_pattern = r'(?:rain|precipitation|shower)[^.]*?([^\.]+)'
        precipitation_match = re.search(precipitation_pattern, weather_text, re.IGNORECASE)
        if precipitation_match:
            parsed_data["weather"]["precipitation"] = precipitation_match.group(1).strip()
        
        # Extract clothing recommendations
        clothing_pattern = r'(?:wear|bring|pack|clothing)[^.]*?([^\.]+)'
        clothing_match = re.search(clothing_pattern, weather_text, re.IGNORECASE)
        if clothing_match:
            parsed_data["weather"]["clothing_recommendations"] = clothing_match.group(1).strip()

# Function to clean and normalize data before returning final JSON
def normalize_itinerary_data(parsed_data):
    """
    Clean and normalize the extracted data before returning the final JSON.
    This helps ensure consistent data structure and removes empty fields.
    """
    # Remove empty fields from trip_overview
    if "trip_overview" in parsed_data:
        parsed_data["trip_overview"] = {k: v for k, v in parsed_data["trip_overview"].items() if v}
    
    # Clean up days data
    for day in parsed_data.get("days", []):
        # Remove empty meals
        if "meals" in day:
            day["meals"] = {k: v for k, v in day["meals"].items() if v}
            if not day["meals"]:
                day.pop("meals", None)
        
        # Remove empty activities
        if "activities" in day:
            day["activities"] = [activity for activity in day["activities"] if activity]
            if not day["activities"]:
                day.pop("activities", None)
        
        # Remove other empty fields
        day = {k: v for k, v in day.items() if v or isinstance(v, (int, float))}
    
    # Clean up other lists
    for key in ["attractions", "accommodations", "dining", "transportation", "travel_tips"]:
        if key in parsed_data:
            # Remove items that are empty or have empty required fields
            if key in ["attractions", "accommodations", "dining"]:
                parsed_data[key] = [item for item in parsed_data[key] if item.get("name")]
            else:
                parsed_data[key] = [item for item in parsed_data[key] if item]
    
    # Clean up weather data
    if "weather" in parsed_data and not parsed_data["weather"]:
        parsed_data.pop("weather", None)
    
    return parsed_data

# Function to format and save the parsed itinerary to a file
def save_itinerary_json(parsed_data, output_file=None):
    """
    Save the parsed itinerary to a JSON file.
    
    Args:
        parsed_data (dict): The parsed itinerary data
        output_file (str, optional): Output file path. If None, generates a file name
                                    based on destination and date.
    
    Returns:
        str: Path to the saved file
    """
    import json
    import os
    from datetime import datetime
    
    # Generate output filename if not provided
    if not output_file:
        destination = parsed_data.get("trip_overview", {}).get("destination", "trip")
        destination = ''.join(c if c.isalnum() else '_' for c in destination)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"itinerary_{destination}_{timestamp}.json"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_file)) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    # Save to file with pretty formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=2, ensure_ascii=False)
    
    return output_file

# Function to extract costs and create a budget summary
def extract_budget_summary(parsed_data):
    """
    Extract all costs mentioned in the itinerary and generate a budget summary.
    
    Args:
        parsed_data (dict): The parsed itinerary data
        
    Returns:
        dict: Budget summary with categorized expenses
    """
    import re
    
    budget_summary = {
        "accommodation_costs": [],
        "dining_costs": [],
        "transportation_costs": [],
        "attraction_costs": [],
        "estimated_total": {
            "min": 0,
            "max": 0,
            "currency": "USD"  # Default currency
        }
    }
    
    # Extract currency symbol if present in any price
    currency_pattern = r'([$€£₹¥])'
    all_text = str(parsed_data)
    currency_matches = re.findall(currency_pattern, all_text)
    main_currency = max(currency_matches, key=currency_matches.count) if currency_matches else "$"
    
    # Function to extract numeric values from price strings
    def extract_price_range(price_str):
        # Handle patterns like "$100-$150", "$100 to $150", "100-150 USD", etc.
        if not price_str:
            return None
            
        # Extract all numbers
        nums = re.findall(r'\d+', price_str)
        if not nums:
            return None
            
        if len(nums) == 1:
            # Single number found
            return {"min": int(nums[0]), "max": int(nums[0])}
        elif len(nums) >= 2:
            # Range found
            return {"min": int(nums[0]), "max": int(nums[1])}
        
        return None
    
    # Extract accommodation costs
    for acc in parsed_data.get("accommodations", []):
        price_range = extract_price_range(acc.get("price_range", ""))
        if price_range:
            budget_summary["accommodation_costs"].append({
                "name": acc.get("name", "Accommodation"),
                "min": price_range["min"],
                "max": price_range["max"]
            })
    
    # Extract dining costs
    for dining in parsed_data.get("dining", []):
        price_range = extract_price_range(dining.get("price_range", ""))
        if price_range:
            budget_summary["dining_costs"].append({
                "name": dining.get("name", dining.get("meal_type", "Meal")),
                "min": price_range["min"],
                "max": price_range["max"],
                "meal_type": dining.get("meal_type", "")
            })
    
    # Extract transportation costs
    for transport in parsed_data.get("transportation", []):
        details = transport.get("details", "")
        # Look for price patterns in transportation details
        price_match = re.search(r'([$€£₹¥]?\d+(?:\s*-\s*|\s+to\s+)[$€£₹¥]?\d+|[$€£₹¥]\d+)', details)
        if price_match:
            price_range = extract_price_range(price_match.group(0))
            if price_range:
                budget_summary["transportation_costs"].append({
                    "type": transport.get("type", "Transportation"),
                    "min": price_range["min"],
                    "max": price_range["max"]
                })
    
    # Calculate estimated total
    min_total = 0
    max_total = 0
    
    for category in ["accommodation_costs", "dining_costs", "transportation_costs", "attraction_costs"]:
        for item in budget_summary[category]:
            min_total += item["min"]
            max_total += item["max"]
    
    budget_summary["estimated_total"]["min"] = min_total
    budget_summary["estimated_total"]["max"] = max_total
    budget_summary["estimated_total"]["currency"] = main_currency
    
    # Add to the main parsed data if anything was found
    if min_total > 0 or max_total > 0:
        if "trip_overview" not in parsed_data:
            parsed_data["trip_overview"] = {}
        parsed_data["trip_overview"]["budget_summary"] = budget_summary
    
    return budget_summary

# Main function to process itineraries
# Main function to process itineraries
def process_itinerary(itinerary_text, output_file=None, include_budget_summary=True):
    """
    Process an itinerary text to extract structured data and optionally save to a file.
    
    Args:
        itinerary_text (str): The raw itinerary text to process
        output_file (str, optional): Path to save the JSON output. If None, doesn't save to file.
        include_budget_summary (bool): Whether to include budget analysis in the output
        
    Returns:
        dict: The structured itinerary data with all extracted information
    """
    import json
    import re
    
    # Parse the itinerary text into structured data
    parsed_data = parse_itinerary(itinerary_text)
    
    # Generate budget summary if requested
    if include_budget_summary:
        budget_summary = extract_budget_summary(parsed_data)
        # Budget summary is already added to parsed_data in the extract_budget_summary function
    
    # Save to file if output_file is specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2)
            
    return parsed_data

def parse_itinerary(itinerary_text):
    """
    Parse raw itinerary text into structured data.
    
    Args:
        itinerary_text (str): The raw itinerary text to process
        
    Returns:
        dict: Structured itinerary data
    """
    import re
    
    # Initialize structured data dictionary
    parsed_data = {
        "trip_overview": {},
        "daily_schedule": [],
        "accommodations": [],
        "transportation": [],
        "dining": [],
        "attractions": []
    }
    
    # Extract trip title and dates
    title_match = re.search(r'^(.*?)(?:Itinerary|Trip|Tour)', itinerary_text, re.IGNORECASE | re.MULTILINE)
    if title_match:
        parsed_data["trip_overview"]["title"] = title_match.group(1).strip()
    
    # Extract dates
    date_pattern = r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})'
    date_matches = re.findall(date_pattern, itinerary_text[:500])  # Look only in the beginning
    if len(date_matches) >= 2:
        parsed_data["trip_overview"]["start_date"] = date_matches[0]
        parsed_data["trip_overview"]["end_date"] = date_matches[1]
    
    # Extract daily schedules
    day_patterns = [
        r'Day\s+(\d+)[:\s]+(.+?)(?=Day\s+\d+:|$)',
        r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+)(?:\s+\d{4})?[:\s]+(.+?)(?=\d{1,2}(?:st|nd|rd|th)?\s+\w+(?:\s+\d{4})?[:\s]+|$)'
    ]
    
    for pattern in day_patterns:
        day_matches = re.findall(pattern, itinerary_text, re.DOTALL)
        if day_matches:
            for day_num, day_content in day_matches:
                day_data = {"day": day_num.strip(), "activities": []}
                
                # Extract activities from the day
                activity_blocks = re.split(r'\n{2,}', day_content.strip())
                for block in activity_blocks:
                    if block.strip():
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)', block)
                        time = time_match.group(1) if time_match else None
                        
                        activity = {
                            "time": time,
                            "description": block.strip()
                        }
                        day_data["activities"].append(activity)
                
                parsed_data["daily_schedule"].append(day_data)
            break  # Use the first successful pattern
    
    # Extract accommodations
    accommodation_patterns = [
        r'(?:Accommodation|Hotel|Stay|Lodging)[:\s]+(.+?)(?=\n\n|\n[A-Z])',
        r'(?:Night at|Stay at|Hotel)[:\s]+(.+?)(?=\n\n|\n[A-Z])'
    ]
    
    for pattern in accommodation_patterns:
        acc_matches = re.findall(pattern, itinerary_text, re.DOTALL)
        for match in acc_matches:
            lines = match.strip().split('\n')
            name = lines[0].strip()
            details = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
            
            # Extract price if mentioned
            price_match = re.search(r'([$€£₹¥]?\d+(?:\s*-\s*|\s+to\s+)[$€£₹¥]?\d+|[$€£₹¥]\d+)(?:\s*per\s*night)?', match)
            price_range = price_match.group(0) if price_match else None
            
            parsed_data["accommodations"].append({
                "name": name,
                "details": details,
                "price_range": price_range
            })
    
    # Extract transportation
    transport_patterns = [
        r'(?:Transport|Transportation|Travel)[:\s]+(.+?)(?=\n\n|\n[A-Z])',
        r'(?:By|Via|Flight|Train|Bus|Car)[:\s]+(.+?)(?=\n\n|\n[A-Z])'
    ]
    
    for pattern in transport_patterns:
        transport_matches = re.findall(pattern, itinerary_text, re.DOTALL)
        for match in transport_matches:
            transport_type = re.search(r'(Flight|Train|Bus|Car|Taxi|Ferry|Transfer)', match, re.IGNORECASE)
            type_str = transport_type.group(1) if transport_type else "Transportation"
            
            parsed_data["transportation"].append({
                "type": type_str,
                "details": match.strip()
            })
    
    # Extract dining information
    dining_patterns = [
        r'(?:Breakfast|Lunch|Dinner|Meal)[:\s]+(.+?)(?=\n\n|\n[A-Z])',
        r'(?:Eat at|Dining at|Restaurant)[:\s]+(.+?)(?=\n\n|\n[A-Z])'
    ]
    
    for pattern in dining_patterns:
        dining_matches = re.findall(pattern, itinerary_text, re.DOTALL)
        for match in dining_matches:
            meal_type = re.search(r'(Breakfast|Lunch|Dinner|Brunch)', match, re.IGNORECASE)
            meal_type_str = meal_type.group(1) if meal_type else "Meal"
            
            lines = match.strip().split('\n')
            name = lines[0].strip()
            details = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
            
            # Extract price if mentioned
            price_match = re.search(r'([$€£₹¥]?\d+(?:\s*-\s*|\s+to\s+)[$€£₹¥]?\d+|[$€£₹¥]\d+)', match)
            price_range = price_match.group(0) if price_match else None
            
            parsed_data["dining"].append({
                "meal_type": meal_type_str,
                "name": name,
                "details": details,
                "price_range": price_range
            })
    
    # Extract attractions/activities
    attraction_patterns = [
        r'(?:Visit|Tour|Sightseeing|Explore|Attraction)[:\s]+(.+?)(?=\n\n|\n[A-Z])',
        r'(?:Activity|Experience)[:\s]+(.+?)(?=\n\n|\n[A-Z])'
    ]
    
    for pattern in attraction_patterns:
        attraction_matches = re.findall(pattern, itinerary_text, re.DOTALL)
        for match in attraction_matches:
            lines = match.strip().split('\n')
            name = lines[0].strip()
            details = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
            
            # Extract price if mentioned
            price_match = re.search(r'([$€£₹¥]?\d+(?:\s*-\s*|\s+to\s+)[$€£₹¥]?\d+|[$€£₹¥]\d+)', match)
            price_range = price_match.group(0) if price_match else None
            
            parsed_data["attractions"].append({
                "name": name,
                "details": details,
                "price_range": price_range
            })
    
    return parsed_data
def enhance_prompt_for_structured_output(prompt):
    return prompt + """
    
    IMPORTANT: Along with the human-readable itinerary, please include a structured JSON summary at the end of your response in the following format (enclosed in ```json tags):
    
    ```json
    {
      "trip_overview": {
        "destination": "destination name",
        "duration_days": number,
        "trip_type": "type of trip",
        "budget_range": "budget information"
      },
      "days": [
        {
          "day_number": 1,
          "date": "YYYY-MM-DD",
          "title": "Day title/theme",
          "morning": "Morning activities",
          "afternoon": "Afternoon activities",
          "evening": "Evening activities",
          "meals": {
            "breakfast": "Breakfast details",
            "lunch": "Lunch details",
            "dinner": "Dinner details"
          },
          "accommodation": "Accommodation details"
        }
      ],
      "attractions": [
        {
          "name": "Attraction name",
          "description": "Description of attraction",
          "visit_duration": "Estimated time to visit"
        }
      ],
      "accommodations": [
        {
          "name": "Accommodation name",
          "description": "Description",
          "price_range": "Price information"
        }
      ],
      "dining": [
        {
          "name": "Restaurant name 1",
          "cuisine": "Cuisine type 1",
          "price_range": "Price range 1",
          "meal_type": "Meal type 1"
        },
        {
          "name": "Restaurant name 2",
          "cuisine": "Cuisine type 2",
          "price_range": "Price range 2",
          "meal_type": "Meal type 2"
        }
      ],
      "transportation": [
        {
          "type": "Transportation type",
          "details": "Details and recommendations"
        }
      ],
      "travel_tips": [
        "Tip 1",
        "Tip 2"
      ],
      "budget": {
        "total_estimated_cost": "estimated total cost",
        "accommodation_cost": "estimated accommodation costs",
        "food_cost": "estimated food costs",
        "transportation_cost": "estimated transportation costs",
        "activities_cost": "estimated activities/attractions costs",
        "miscellaneous_cost": "estimated miscellaneous costs"
      },
      "essential_info": {
        "visa_requirements": "visa details",
        "emergency_contacts": "emergency numbers",
        "local_customs": "important local customs to be aware of",
        "safety_tips": "safety information",
        "language": "local language information",
        "currency_exchange": "currency exchange information"
      },
      "weather": {
        "temperature_range": {
          "min": 0,
          "max": 30,
          "unit": "Celsius"
        },
        "conditions": "Weather conditions description",
        "clothing": "Clothing recommendations"
      }
    }
    ```
    
    CRITICAL JSON SYNTAX REQUIREMENTS:
    
    1. COMMAS: Include commas BETWEEN array elements and object properties, but NOT after the last element in an array or object.
       ✓ CORRECT:   [{"name": "Place 1"}, {"name": "Place 2"}]
       ✗ INCORRECT: [{"name": "Place 1"} {"name": "Place 2"}]
       ✗ INCORRECT: [{"name": "Place 1"}, {"name": "Place 2"},]
    
    2. BRACKETS: Every opening bracket or brace must have a matching closing bracket or brace.
       - Array: [ ]
       - Object: { }
    
    3. CONSISTENCY: Use consistent indentation for better readability.
    
    4. QUOTING: All property names and string values must be enclosed in double quotes.
       ✓ CORRECT:   {"name": "Place"}
       ✗ INCORRECT: {name: "Place"}
       ✗ INCORRECT: {'name': 'Place'}
    
    5. COMPLETENESS: Include ALL relevant items in the arrays. Do not truncate the data or use placeholders.
    
    6. SCHEMA: Follow the exact schema structure provided above.
    
    7. DATA TYPES: Use appropriate data types:
       - Strings: Use quotes (e.g., "Barcelona")
       - Numbers: No quotes (e.g., 25)
       - Arrays: Square brackets (e.g., [ ])
       - Objects: Curly braces (e.g., { })
    
    Please structure your response using clear section headers for each day (Day 1, Day 2, etc.), and clearly mark morning, afternoon, and evening activities as well as meals and accommodations to facilitate accurate JSON extraction.
    """

def display_itinerary_tabs(itinerary_json):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🌍 Overview", "📅 Itinerary", "🏨 Accommodation", 
        "🍽️ Dining", "🎯 Attractions", "💰 Budget", "ℹ️ Essential Info"
    ])
    
    # Overview Tab
    with tab1:
        st.markdown("<h2 style='text-align: center;'>Trip Overview</h2>", unsafe_allow_html=True)
        overview = itinerary_json.get("trip_overview", {})
        
        # Create three columns for better organization
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.markdown("""
                <div style='background-color: #E3F2FD; padding: 1rem; border-radius: 10px;'>
                    <h3 style='color: #1E88E5; margin: 0;'>🌍 Destination</h3>
                    <p style='font-size: 1.2rem; margin: 0.5rem 0;'>{}</p>
                </div>
            """.format(overview.get("destination", "Not specified")), unsafe_allow_html=True)
            
            st.markdown("""
                <div style='background-color: #E8F5E9; padding: 1rem; border-radius: 10px; margin-top: 1rem;'>
                    <h3 style='color: #43A047; margin: 0;'>⏱️ Duration</h3>
                    <p style='font-size: 1.2rem; margin: 0.5rem 0;'>{} days</p>
                </div>
            """.format(overview.get("duration_days", "Not specified")), unsafe_allow_html=True)
        
        with col2:
            days = itinerary_json.get("days", [])
            if days:
                start_date = days[0].get("date", "Not specified")
                end_date = days[-1].get("date", "Not specified")
            else:
                start_date = overview.get("start_date", "Not specified")
                end_date = overview.get("end_date", "Not specified")
            
            st.markdown("""
                <div style='background-color: #FFF3E0; padding: 1rem; border-radius: 10px;'>
                    <h3 style='color: #EF6C00; margin: 0;'>📅 Travel Dates</h3>
                    <p style='margin: 0.5rem 0;'><b>Start:</b> {}</p>
                    <p style='margin: 0.5rem 0;'><b>End:</b> {}</p>
                </div>
            """.format(start_date, end_date), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
                <div style='background-color: #F3E5F5; padding: 1rem; border-radius: 10px;'>
                    <h3 style='color: #8E24AA; margin: 0;'>💰 Budget Range</h3>
                    <p style='font-size: 1.2rem; margin: 0.5rem 0;'>{}</p>
                </div>
            """.format(overview.get("budget_range", "Not specified")), unsafe_allow_html=True)
        
        # Weather information
        st.markdown("""
            <div style='background-color: #E1F5FE; padding: 1.5rem; border-radius: 10px; margin-top: 2rem;'>
                <h3 style='color: #0288D1; margin: 0;'>🌤️ Weather Information</h3>
        """, unsafe_allow_html=True)
        
        weather = itinerary_json.get("weather", {})
        if weather:
            temp_range = weather.get("temperature_range", {})
            if temp_range:
                st.markdown(f"""
                    <p style='margin: 0.5rem 0;'><b>Temperature:</b> {temp_range.get('min')}°{temp_range.get('unit', 'C')} to {temp_range.get('max')}°{temp_range.get('unit', 'C')}</p>
                    <p style='margin: 0.5rem 0;'><b>Conditions:</b> {weather.get('conditions', 'Not specified')}</p>
                    <p style='margin: 0.5rem 0;'><b>What to Wear:</b> {weather.get('clothing_recommendations', 'Not specified')}</p>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Best Time to Visit
        st.markdown("""
            <div style='background-color: #F5F5F5; padding: 1.5rem; border-radius: 10px; margin-top: 2rem;'>
                <h3 style='color: #424242; margin: 0;'>📅 Best Time to Visit</h3>
                <p style='margin: 0.5rem 0;'>{}</p>
            </div>
        """.format(itinerary_json.get("essential_info", {}).get("best_time_to_visit", "Not specified")), unsafe_allow_html=True)

    # Itinerary Tab
    with tab2:
        st.markdown("<h2 style='text-align: center;'>Daily Itinerary</h2>", unsafe_allow_html=True)
        days = itinerary_json.get("days", [])
        for day in days:
            with st.expander(f"Day {day.get('day_number')} - {day.get('title', '')}"):
                st.markdown("""
                    <div style='background-color: #E3F2FD; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;'>
                        <h3 style='color: #1E88E5; margin: 0;'>Morning</h3>
                        <p>{}</p>
                        <h3 style='color: #1E88E5; margin-top: 1rem;'>Afternoon</h3>
                        <p>{}</p>
                        <h3 style='color: #1E88E5; margin-top: 1rem;'>Evening</h3>
                        <p>{}</p>
                    </div>
                """.format(
                    day.get("morning", "No activities specified"),
                    day.get("afternoon", "No activities specified"),
                    day.get("evening", "No activities specified")
                ), unsafe_allow_html=True)
                
                meals = day.get("meals", {})
                st.markdown("""
                    <div style='background-color: #FFF3E0; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;'>
                        <h3 style='color: #EF6C00; margin: 0;'>Meals</h3>
                        <p><b>Breakfast:</b> {}</p>
                        <p><b>Lunch:</b> {}</p>
                        <p><b>Dinner:</b> {}</p>
                    </div>
                """.format(
                    meals.get("breakfast", "Not specified"),
                    meals.get("lunch", "Not specified"),
                    meals.get("dinner", "Not specified")
                ), unsafe_allow_html=True)
                
                st.markdown("""
                    <div style='background-color: #E8F5E9; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;'>
                        <h3 style='color: #43A047; margin: 0;'>Accommodation</h3>
                        <p>{}</p>
                    </div>
                """.format(day.get("accommodation", "Not specified")), unsafe_allow_html=True)

    # Accommodation Tab
    with tab3:
        st.markdown("<h2 style='text-align: center;'>Accommodations</h2>", unsafe_allow_html=True)
        accommodations = itinerary_json.get("accommodations", [])
        for acc in accommodations:
            with st.expander(acc.get("name", "Unnamed Accommodation")):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("""
                        <div style='background-color: #E3F2FD; padding: 1rem; border-radius: 10px;'>
                            <p><b>Price Range:</b> {}</p>
                            <p><b>Description:</b> {}</p>
                        </div>
                    """.format(
                        acc.get("price_range", "Not specified"),
                        acc.get("description", "No description available")
                    ), unsafe_allow_html=True)
                with col2:
                    # Add booking functionality with direct link
                    booking_url = f"https://www.booking.com/search.html?ss={acc.get('name', '')}"
                    st.markdown(f"""
                        <div style='text-align: center;'>
                            <a href="{booking_url}" target="_blank" style="
                                display: inline-block;
                                padding: 0.5rem 1rem;
                                background-color: #1E88E5;
                                color: white;
                                text-decoration: none;
                                border-radius: 5px;
                                margin: 0.5rem 0;
                                font-weight: bold;
                                transition: background-color 0.3s;">
                                🏨 Book Now
                            </a>
                        </div>
                        <div style='background-color: #E8F5E9; padding: 1rem; border-radius: 10px; margin-top: 1rem;'>
                            <p>✓ Direct booking available</p>
                            <p>✓ Best price guarantee</p>
                            <p>✓ Free cancellation</p>
                        </div>
                    """, unsafe_allow_html=True)

    # Dining Tab
    with tab4:
        st.markdown("<h2 style='text-align: center;'>Dining Recommendations</h2>", unsafe_allow_html=True)
        dining = itinerary_json.get("dining", [])
        for restaurant in dining:
            with st.expander(restaurant.get("name", "Unnamed Restaurant")):
                st.markdown("""
                    <div style='background-color: #FFF3E0; padding: 1rem; border-radius: 10px;'>
                        <p><b>Cuisine:</b> {}</p>
                        <p><b>Price Range:</b> {}</p>
                        <p><b>Meal Type:</b> {}</p>
                    </div>
                """.format(
                    restaurant.get("cuisine", "Not specified"),
                    restaurant.get("price_range", "Not specified"),
                    restaurant.get("meal_type", "Not specified")
                ), unsafe_allow_html=True)

    # Attractions Tab
    with tab5:
        st.markdown("<h2 style='text-align: center;'>Top Attractions</h2>", unsafe_allow_html=True)
        attractions = itinerary_json.get("attractions", [])
        for attraction in attractions:
            with st.expander(attraction.get("name", "Unnamed Attraction")):
                st.markdown("""
                    <div style='background-color: #E8F5E9; padding: 1rem; border-radius: 10px;'>
                        <p><b>Description:</b> {}</p>
                        <p><b>Visit Duration:</b> {}</p>
                    </div>
                """.format(
                    attraction.get("description", "No description available"),
                    attraction.get("visit_duration", "Not specified")
                ), unsafe_allow_html=True)

    # Budget Tab
    with tab6:
        st.markdown("<h2 style='text-align: center;'>Budget Breakdown</h2>", unsafe_allow_html=True)
        budget = itinerary_json.get("budget", {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div style='background-color: #E3F2FD; padding: 1rem; border-radius: 10px;'>
                    <h3 style='color: #1E88E5; margin: 0;'>Total Cost</h3>
                    <p style='font-size: 1.2rem;'>{}</p>
                    <h3 style='color: #1E88E5; margin-top: 1rem;'>Accommodation</h3>
                    <p>{}</p>
                    <h3 style='color: #1E88E5; margin-top: 1rem;'>Food</h3>
                    <p>{}</p>
                </div>
            """.format(
                budget.get("total_estimated_cost", "Not specified"),
                budget.get("accommodation_cost", "Not specified"),
                budget.get("food_cost", "Not specified")
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div style='background-color: #FFF3E0; padding: 1rem; border-radius: 10px;'>
                    <h3 style='color: #EF6C00; margin: 0;'>Transportation</h3>
                    <p>{}</p>
                    <h3 style='color: #EF6C00; margin-top: 1rem;'>Activities</h3>
                    <p>{}</p>
                    <h3 style='color: #EF6C00; margin-top: 1rem;'>Miscellaneous</h3>
                    <p>{}</p>
                </div>
            """.format(
                budget.get("transportation_cost", "Not specified"),
                budget.get("activities_cost", "Not specified"),
                budget.get("miscellaneous_cost", "Not specified")
            ), unsafe_allow_html=True)

    # Essential Info Tab
    with tab7:
        st.markdown("<h2 style='text-align: center;'>Essential Information</h2>", unsafe_allow_html=True)
        essential_info = itinerary_json.get("essential_info", {})
        
        # Travel Tips
        st.markdown("<h3 style='color: #1E88E5;'>💡 Travel Tips</h3>", unsafe_allow_html=True)
        tips = itinerary_json.get("travel_tips", [])
        for tip in tips:
            st.markdown(f"• {tip}")
        
        # Essential Information Cards
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div style='background-color: #E3F2FD; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;'>
                    <h3 style='color: #1E88E5; margin: 0;'>📋 Important Information</h3>
                    <p style='margin: 0.5rem 0;'><b>🛂 Visa:</b> {}</p>
                    <p style='margin: 0.5rem 0;'><b>🆘 Emergency:</b> {}</p>
                    <p style='margin: 0.5rem 0;'><b>🏺 Local Customs:</b> {}</p>
                </div>
            """.format(
                essential_info.get("visa_requirements", "Not specified"),
                essential_info.get("emergency_contacts", "Not specified"),
                essential_info.get("local_customs", "Not specified")
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div style='background-color: #FFF3E0; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;'>
                    <h3 style='color: #EF6C00; margin: 0;'>🔍 Additional Information</h3>
                    <p style='margin: 0.5rem 0;'><b>🛡️ Safety:</b> {}</p>
                    <p style='margin: 0.5rem 0;'><b>🗣️ Language:</b> {}</p>
                    <p style='margin: 0.5rem 0;'><b>💱 Currency:</b> {}</p>
                </div>
            """.format(
                essential_info.get("safety_tips", "Not specified"),
                essential_info.get("language", "Not specified"),
                essential_info.get("currency_exchange", "Not specified")
            ), unsafe_allow_html=True)

def main():
    st.title("Travel Plan Extractor")
    user_input = st.text_area("Enter your travel details:")
    if st.button("Plan my Trip", type='primary'):
        if user_input:
            details = extract_details(user_input)
            
            # Create a pandas DataFrame for table presentation
            details_df = pd.DataFrame(details.items(), columns=["Detail", "Value"])
            details_df.index = details_df.index + 1
            st.subheader("Extracted Travel Details")
            st.table(details_df)
            details_json = extract_details(user_input)
        
            # Display JSON output of user details
            with st.expander("View Extracted Travel Details (JSON)", expanded=False):
                st.json(details_json) 
            
            # Generate and display the itinerary prompt
            prompt = generate_prompt(details)
            # Enhance prompt to get structured output
            structured_prompt = enhance_prompt_for_structured_output(prompt)
            
            with st.expander("View Itinerary Request Prompt", expanded=False):
                st.write(prompt)
            
            # Check for errors
            error_messages = ["Error❗Error❗Error❗", "Failed to generate", "Invalid input"]
            if not any(error in prompt for error in error_messages):
                with st.spinner("Generating detailed itinerary with Google Gemini..."): 
                    itinerary_text = generate_itinerary_with_gemini(structured_prompt)  
                with st.expander("View Full Itinerary Text", expanded=False):
                    st.markdown(itinerary_text)
                # Extract structured JSON data from the itinerary
                with st.spinner("Extracting structured data from itinerary..."):
                    itinerary_json = extract_itinerary_json(itinerary_text)
                with st.expander("View Raw JSON Data", expanded=False):
                    st.json(itinerary_json)
                # Display the itinerary in tabs
                display_itinerary_tabs(itinerary_json)
                
                # Add download buttons
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="Download Itinerary Text",
                        data=itinerary_text,
                        file_name="travel_itinerary.txt",
                        mime="text/plain"
                    )
                with col2:
                    st.download_button(
                        label="Download Itinerary JSON",
                        data=json.dumps(itinerary_json, indent=2),
                        file_name="travel_itinerary.json",
                        mime="application/json"
                    )
            else:
                st.warning("An error occurred in itinerary generation. Please check your input and try again.")
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

if __name__ == "__main__":
    main()
