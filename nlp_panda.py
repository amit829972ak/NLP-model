import streamlit as st
import spacy
import dateparser
import re
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateparser.search import search_dates
import openai
import subprocess
import geonamescache


# Load spaCy model globally
@st.cache_resource
def load_spacy_model():
    try:
       return spacy.load("en_core_web_lg")
    except OSError as e:
        print("Error: spaCy model not found. Make sure `en_core_web_lg` is installed.")
        raise e
nlp = load_spacy_model()

# Load city database from geonamescache
gc = geonamescache.GeonamesCache()
cities = {city["name"].lower(): city for city in gc.get_cities().values()}

# Define seasonal mappings
seasonal_mappings = {
  "summer": "06-01",
    "mid summer": "07-01",
    "end of summer": "08-01",
    "autumn": "09-01",
    "monsoon": "09-01",
    "winter": "12-01",
    "spring": "04-01"  
}
# code for getting user live location (streamlit do not this live location feature) 
def get_user_location():
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        city = data.get("city", "Unknown City")
        region = data.get("region", "Unknown State")
        country = data.get("country", "Unknown Country")
        return f"{city}, {region}, {country}"
    except Exception:
        return "Location Unavailable"

def extract_details(text):
    doc = nlp(text)
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
    locations = [ent.text for ent in doc.ents if ent.label_ == ["GPE","LOC"]]

    # Check for cities using geonamescache
    for word in text.split():
        if word.lower() in cities:
            locations.append(word)

    # Remove duplicates
    locations = list(set(locations))
    
    if len(locations) > 1:
        details["Starting Location"] = locations[0]
        details["Destination"] = locations[1]
    elif len(locations) == 1:
        details["Destination"] = locations[0]
    
    # Extract duration
    duration_match = re.search(r'(?P<value>\d+)\s*[-]?\s*(?P<unit>day|days|night|nights|week|weeks|month|months)', text, re.IGNORECASE)
    duration_days = None
    if duration_match:
        unit = duration_match.group("unit").lower()
        value = int(duration_match.group("value"))
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
    date_range_match = re.search(r'(?P<start>\d{1,2} [A-Za-z]+) to (?P<end>\d{1,2} [A-Za-z]+)', text, re.IGNORECASE)
    dates = []
    if date_range_match:
        start_date_text = date_range_match.group("start")
        end_date_text = date_range_match.group("end")
        start_date = dateparser.parse(start_date_text, settings={'PREFER_DATES_FROM': 'future'})
        end_date = dateparser.parse(end_date_text, settings={'PREFER_DATES_FROM': 'future'})
        if start_date and end_date:
            details["Start Date"] = start_date.strftime('%Y-%m-%d')
            details["End Date"] = end_date.strftime('%Y-%m-%d')
            details["Trip Duration"] = f"{(end_date - start_date).days} days"
    else:
        extracted_dates = search_dates(text, settings={'PREFER_DATES_FROM': 'future'})
        if extracted_dates:
            dates = [d[1].strftime('%Y-%m-%d') for d in extracted_dates]
        
        if len(dates) > 1:
            details["Start Date"], details["End Date"] = dates[:2]
            start_date = datetime.strptime(details["Start Date"], "%Y-%m-%d")
            end_date = datetime.strptime(details["End Date"], "%Y-%m-%d")
            details["Trip Duration"] = f"{(end_date - start_date).days} days"
        elif len(dates) == 1:
            details["Start Date"] = dates[0]
            if duration_days:
                start_date = datetime.strptime(dates[0], "%Y-%m-%d")
                details["End Date"] = (start_date + timedelta(days=duration_days)).strftime('%Y-%m-%d')
        
        else:
            for season, start_month_day in seasonal_mappings.items():
                if season in text.lower():
                    today = datetime.today().year
                    start_date = f"{today}-{start_month_day}"
                    details["Start Date"] = start_date
                    if duration_days:
                        details["End Date"] = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=duration_days)).strftime('%Y-%m-%d')
                    break
        
    # Extract number of travelers
    travelers_match = re.search(r'(?P<adults>\d+)\s*(?:people|persons|adult|adults)', text, re.IGNORECASE)
    children_match = re.search(r'(?P<children>\d+)\s*(?:child|children)', text, re.IGNORECASE)
    infants_match = re.search(r'(?P<infants>\d+)\s*(?:infant|infants)', text, re.IGNORECASE)
    
    solo_match = re.search(r'\bsolo\b', text, re.IGNORECASE)
    duo_match = re.search(r'\bduo\b', text, re.IGNORECASE)
    trio_match = re.search(r'\btrio\b', text, re.IGNORECASE)
    
    travelers = {
        "Adults": travelers_match.group("adults") if travelers_match else "Not specified",
        "Children": children_match.group("children") if children_match else "0",
        "Infants": infants_match.group("infants") if infants_match else "0"
    }
    
    if solo_match:
       travelers["Adults"] = "1"
    elif duo_match:
       travelers["Adults"] = "2"
    elif trio_match:
       travelers["Adults"] = "3"
    
    details["Number of Travelers"] = travelers

    # Extract transportation preferences
    transport_modes = {
        "flight": ["flight", "fly", "airplane", "aeroplane"],
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
    
    # Extract budget range
    budget_keywords = {
        "friendly budget": "Mid range-Budget",
        "mid-range budget": "Mid-range",
        "luxury": "Luxury",
        "cheap": "Low Budget",
        "expensive": "Luxury",
        "premium": "Luxury",
        "high-range": "Luxury"
    }
    
    budget_matches = []
    for key, val in budget_keywords.items():
        if re.search(r'\b' + re.escape(key) + r'\b', text, re.IGNORECASE):
            budget_matches.append(val)
    
    if not budget_matches:
        for key, val in budget_keywords.items():
            if key.lower() in text.lower():
                budget_matches.append(val)
    
    details["Budget Range"] = budget_matches[0] if budget_matches else "Mid-range"
    
    # Extract trip type
    trip_type = {
    "Adventure Travel": ["hiking", "skiing", "extreme sports"],
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
    "Family Travel": ["Family trip","theme parks", "kid-friendly resorts", "multi-generational travel","Family vaccation"]
}
    trip_type_matches = []
    for trip, keywords in trip_type.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
               trip_type_matches.append(trip)
               break
    
    details["Trip Type"] = trip_type_matches if trip_type_matches else "Not specified"
    
    
    
    # Extract accommodation preferences
    accommodation_types = {
    "Boutique hotels": ["hotel", "boutique hotel", "small hotel", "intimate hotel"],
    "Resorts": ["resort", "holiday resort", "self-contained resort", "luxury resort"],
    "Hostels": ["hostel", "dormitory", "shared accommodation"],
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
    prompt = f"Generate a detailed itinerary for a {details['Trip Type']} trip to {details['Destination']} for {details['Number of Travelers']['Adults']} adults"
    
    if details['Number of Travelers']['Children'] != "0":
        prompt += f" and {details['Number of Travelers']['Children']} children"
    
    if details['Number of Travelers']['Infants'] != "0":
        prompt += f" and {details['Number of Travelers']['Infants']} infants"
    
    prompt += f", starting from {details['Starting Location']} and departing on {details['Start Date']}."
    
    if details["End Date"]:
        prompt += f" The trip ends on {details['End Date']}."
    
    prompt += f" Please consider a {details['Budget Range']} budget and provide accommodation, dining, and activity recommendations."
    
    if details["Transportation Preferences"] != "Any":
        prompt += f" Suggested transportation methods include: {', '.join(details['Transportation Preferences'])}."
    
    if details["Accommodation Preferences"] != "Any":
        prompt += f" Accommodation preference: {details['Accommodation Preferences']}."
    
    if details["Special Requirements"] != "None":
        prompt += f" Special requirements: {details['Special Requirements']}."
    
    return prompt

st.title("Travel Plan Extractor")

user_input = st.text_area("Enter your travel details in natural language:")

if st.button("Extract Details"):
    if user_input:
        details = extract_details(user_input)
        
        # Create a pandas DataFrame for table presentation
        details_df = pd.DataFrame(details.items(), columns=["Detail", "Value"])
        details_df.index = details_df.index + 1
        
        st.subheader("Extracted Travel Details")
        st.table(details_df)
        
        # Generate and display the itinerary prompt
        prompt = generate_prompt(details)
        st.subheader("Itinerary Request Prompt")
        st.write(prompt)
        
    else:
        st.warning("Please enter some text to extract details.")
