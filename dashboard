import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import io

# Set page config
st.set_page_config(
    page_title="Japan Travel Itinerary",
    layout="wide"
)

# Custom CSS to improve the appearance
st.markdown("""
    <style>
    .main-header {
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .section-header {
        font-size: 24px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 15px;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 8px;
    }
    .sub-header {
        font-size: 20px;
        font-weight: bold;
        color: #34495e;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4682b4;
        color: white;
    }
    .info-card {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 4px solid #4682b4;
    }
    .highlight {
        color: #4682b4;
        font-weight: bold;
    }
    .weather-card {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin: 5px;
        text-align: center;
    }
    .cost-bar {
        height: 20px;
        background-color: #3498db;
        border-radius: 5px;
        margin-bottom: 5px;
    }
    .review-card {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #2ecc71;
    }
    .stExpander {
        border-left: 2px solid #4682b4;
        padding-left: 10px;
    }
    .footer {
        text-align: center;
        padding: 20px;
        font-size: 14px;
        color: #7f8c8d;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Helper functions
def generate_map_data():
    # Tokyo coordinates
    tokyo_lat, tokyo_lon = 35.6762, 139.6503
    
    # Generate points around Tokyo
    locations = {
        "Tokyo Station": [35.6812, 139.7671],
        "Shinjuku": [35.6938, 139.7034],
        "Shibuya": [35.6580, 139.7016],
        "Asakusa": [35.7147, 139.7967],
        "Hakone": [35.2323, 139.1069]
    }
    
    # Create DataFrame
    df = pd.DataFrame(
        locations.items(),
        columns=['location', 'coordinates']
    )
    
    df['lat'] = df['coordinates'].apply(lambda x: x[0])
    df['lon'] = df['coordinates'].apply(lambda x: x[1])
    
    return df

def create_expense_chart():
    categories = ['Accommodation', 'Food', 'Transportation', 'Activities', 'Miscellaneous']
    max_amounts = [25000, 25000, 15000, 10000, 10000]
    min_amounts = [20000, 20000, 10000, 5000, 5000]
    
    x = np.arange(len(categories))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width/2, max_amounts, width, label='Max Amount (¥)', color='#3498db')
    ax.bar(x + width/2, min_amounts, width, label='Min Amount (¥)', color='#2ecc71')
    
    ax.set_title('Budget Breakdown')
    ax.set_ylabel('Amount (¥)')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend()
    
    plt.tight_layout()
    
    # Convert the plot to an image
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    return buf

def currency_converter(amount, from_currency, to_currency):
    # Simplified exchange rates
    rates = {
        'JPY': {'USD': 0.007, 'INR': 0.58, 'EUR': 0.0064},
        'USD': {'JPY': 142.86, 'INR': 82.93, 'EUR': 0.92},
        'INR': {'JPY': 1.72, 'USD': 0.012, 'EUR': 0.011},
        'EUR': {'JPY': 156.25, 'USD': 1.09, 'INR': 90.91}
    }
    
    if from_currency == to_currency:
        return amount
    
    return amount * rates[from_currency][to_currency]

# Main title
st.markdown('<div class="main-header">Leisure Trip to Japan (April 6-10, 2025)</div>', unsafe_allow_html=True)

# Create tabs
tabs = st.tabs(["Overview", "Itinerary", "Accommodations", "Flights", "Budget", "Essential Info", "Photos", "Reviews", "Interactive"])

with tabs[0]:
    st.markdown('<div class="section-header">Trip Details</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown('<span class="highlight">Travel Date:</span> April 6-10, 2025', unsafe_allow_html=True)
        st.markdown('<span class="highlight">Duration:</span> 5 days, 4 nights', unsafe_allow_html=True)
        st.markdown('<span class="highlight">Budget Level:</span> ₹50,000 (¥85,000-¥90,000)', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown('<span class="highlight">Best Time to Visit:</span> Cherry blossom season', unsafe_allow_html=True)
        st.markdown('<span class="highlight">Language:</span> Japanese', unsafe_allow_html=True)
        st.markdown('<span class="highlight">Currency:</span> Japanese Yen (¥)', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Weather Forecast</div>', unsafe_allow_html=True)
    
    # Weather data
    weather_data = {
        "Day": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"],
        "Condition": ["Stormy", "Partly Cloudy", "Stormy", "Stormy", "Stormy"],
        "Temperature": ["22°C", "34°C", "20°C", "18°C", "20°C"]
    }
    
    weather_cols = st.columns(5)
    for i, col in enumerate(weather_cols):
        with col:
            st.markdown(f'''
            <div class="weather-card">
                <h4>{weather_data["Day"][i]}</h4>
                <p>{weather_data["Condition"][i]}</p>
                <h3>{weather_data["Temperature"][i]}</h3>
            </div>
            ''', unsafe_allow_html=True)
    
    st.markdown('''
    <div class="info-card">
    <p>It's impossible to provide a precise forecast this far in advance. However, early April in Tokyo is typically mild and pleasant with cherry blossoms in bloom.</p>
    <ul>
        <li><strong>Temperature:</strong> 10-18°C (50-64°F)</li>
        <li><strong>Precipitation:</strong> Occasional rain showers possible</li>
        <li><strong>Clothing:</strong> Light layers, a light jacket, and comfortable walking shoes</li>
    </ul>
    </div>
    ''', unsafe_allow_html=True)
    
    # Trip Countdown Timer
    import datetime
    today = datetime.date.today()
    trip_date = datetime.date(2025, 4, 6)
    days_left = (trip_date - today).days
    
    st.markdown('<div class="section-header">Trip Countdown</div>', unsafe_allow_html=True)
    st.markdown(f'''
    <div class="info-card" style="text-align: center;">
        <h1>{days_left} days</h1>
        <p>until your Japan adventure begins!</p>
    </div>
    ''', unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="section-header">Daily Itinerary</div>', unsafe_allow_html=True)
    
    days = ["Day 1: Arrival in Tokyo & Shinjuku Exploration", 
            "Day 2: Culture & Trendy Vibes", 
            "Day 3: Day Trip to Hakone", 
            "Day 4: Ancient & Modern Tokyo", 
            "Day 5: Departure"]
    
    day_content = [
        '''
        <ul>
            <li><strong>Morning:</strong> Arrive at Narita (NRT) or Haneda (HND) airport. Take the Narita Express or Limousine Bus to Shinjuku (¥3,000-¥4,000). Check in to your accommodation.</li>
            <li><strong>Afternoon:</strong> Explore Shinjuku Gyoen National Garden (¥500), a beautiful oasis offering diverse garden styles. Ascend the Tokyo Metropolitan Government Building for panoramic city views (Free).</li>
            <li><strong>Evening:</strong> Enjoy dinner in Shinjuku's vibrant entertainment district, Kabukicho.</li>
            <li><strong>Meals:</strong>
                <ul>
                    <li><strong>Breakfast:</strong> On the plane or grab a quick bite at the airport.</li>
                    <li><strong>Lunch:</strong> Convenience store like 7-Eleven or FamilyMart (¥500-¥800).</li>
                    <li><strong>Dinner:</strong> Omoide Yokocho (memory lane) for yakitori skewers (¥1,500-¥2,500) or Ichiran Ramen (¥1,000).</li>
                </ul>
            </li>
            <li><strong>Accommodation:</strong> Shinjuku Kuyakusho-mae Capsule Hotel (Capsule Hotel, budget-friendly, around ¥4,000 per night).</li>
        </ul>
        ''',
        '''
        <ul>
            <li><strong>Morning:</strong> Immerse yourself in the Tsukiji Outer Market (free entry, but food costs vary). Sample fresh seafood, street food, and local produce.</li>
            <li><strong>Afternoon:</strong> Explore the trendy Harajuku district, known for its unique street style and Takeshita Street's quirky shops. Visit Meiji Jingu Shrine, a peaceful oasis dedicated to Emperor Meiji and Empress Shoken (Free).</li>
            <li><strong>Evening:</strong> Enjoy dinner and explore the vibrant Shibuya crossing.</li>
            <li><strong>Meals:</strong>
                <ul>
                    <li><strong>Breakfast:</strong> Bakery near your accommodation (¥500).</li>
                    <li><strong>Lunch:</strong> Tsukiji Outer Market – Sushi, Ramen, or various street food options (¥1,000-¥2,000).</li>
                    <li><strong>Dinner:</strong> Shibuya – Genki Sushi (Conveyor belt sushi, affordable) or a ramen shop (¥800-¥1,500).</li>
                </ul>
            </li>
            <li><strong>Accommodation:</strong> Same as Day 1.</li>
        </ul>
        ''',
        '''
        <ul>
            <li><strong>Morning:</strong> Take a scenic train ride to Hakone (approx. ¥2,000 roundtrip).</li>
            <li><strong>Afternoon:</strong> Cruise across Lake Ashi, surrounded by stunning views of Mt. Fuji (weather permitting). Ride the Hakone Ropeway, offering volcanic hot spring views.</li>
            <li><strong>Evening:</strong> Return to Tokyo.</li>
            <li><strong>Meals:</strong>
                <ul>
                    <li><strong>Breakfast:</strong> Convenience store near your accommodation.</li>
                    <li><strong>Lunch:</strong> Restaurant near Lake Ashi offering Hoto noodles or other local specialties (¥1,500-¥2,500).</li>
                    <li><strong>Dinner:</strong> Shinjuku – Dinner near your accommodation.</li>
                </ul>
            </li>
            <li><strong>Accommodation:</strong> Same as Day 1.</li>
        </ul>
        ''',
        '''
        <ul>
            <li><strong>Morning:</strong> Visit Sensō-ji Temple, Tokyo's oldest temple, and explore the Nakamise-dori market.</li>
            <li><strong>Afternoon:</strong> Explore the Imperial Palace East Garden (Free). Visit the Edo-Tokyo Museum (¥600) to learn about Tokyo's history.</li>
            <li><strong>Evening:</strong> Enjoy dinner in the Asakusa area and see Tokyo Skytree illuminated.</li>
            <li><strong>Meals:</strong>
                <ul>
                    <li><strong>Breakfast:</strong> Onigiri from a convenience store.</li>
                    <li><strong>Lunch:</strong> Monjayaki (savory pancake) in Asakusa (¥1,000-¥1,500).</li>
                    <li><strong>Dinner:</strong> Asakusa - Ramen or other local dishes.</li>
                </ul>
            </li>
            <li><strong>Accommodation:</strong> Same as Day 1.</li>
        </ul>
        ''',
        '''
        <ul>
            <li><strong>Morning:</strong> Last-minute souvenir shopping at a Don Quijote store.</li>
            <li><strong>Afternoon:</strong> Travel to Narita (NRT) or Haneda (HND) airport for your departure.</li>
            <li><strong>Meals:</strong>
                <ul>
                    <li><strong>Breakfast:</strong> Near your accommodation.</li>
                    <li><strong>Lunch:</strong> At the airport.</li>
                </ul>
            </li>
        </ul>
        '''
    ]
    
    # Create expanders for each day
    for i, day in enumerate(days):
        with st.expander(day, expanded=(i==0)):
            st.markdown(day_content[i], unsafe_allow_html=True)
    
    # Add download button for itinerary
    st.markdown('<div class="section-header">Download Itinerary</div>', unsafe_allow_html=True)
    
    itinerary_text = "Japan Travel Itinerary (April 6-10, 2025)\n\n"
    for i, day in enumerate(days):
        itinerary_text += f"{day}\n"
        # Strip HTML tags for plain text
        import re
        content = re.sub('<[^<]+?>', '', day_content[i])
        itinerary_text += f"{content}\n\n"
    
    st.download_button(
        label="Download Itinerary as Text",
        data=itinerary_text,
        file_name="japan_itinerary.txt",
        mime="text/plain"
    )

with tabs[2]:
    st.markdown('<div class="section-header">Accommodation Options (Tokyo)</div>', unsafe_allow_html=True)
    st.markdown('''
    Budget-friendly options focusing on Shinjuku due to its central location:
    ''')
    
    accommodations = [
        {
            "name": "Shinjuku Kuyakusho-mae Capsule Hotel",
            "type": "Capsule Hotel", 
            "price": "¥3,500-¥4,500 / $25-$30",
            "description": "Basic but clean capsule hotel."
        },
        {
            "name": "UNPLAN Shinjuku",
            "type": "Hostel", 
            "price": "¥4,000-¥6,000 / $28-$42",
            "description": "Stylish hostel with social atmosphere."
        },
        {
            "name": "Khaosan Tokyo Kabuki",
            "type": "Hostel", 
            "price": "¥3,000-¥5,000 / $21-$35",
            "description": "Lively hostel with various room types."
        },
        {
            "name": "Park Hyatt Tokyo",
            "type": "Luxury Hotel", 
            "price": "¥80,000+ / $560+",
            "description": "(Splurge option) Luxurious hotel featured in 'Lost in Translation'."
        }
    ]
    
    # Create a dataframe and display it
    df_accommodations = pd.DataFrame(accommodations)
    st.dataframe(df_accommodations, use_container_width=True, hide_index=True)
    
    st.info("Note: Accommodation prices can vary depending on the season and availability.")
    
    # Add a comparison feature
    st.markdown('<div class="section-header">Compare Accommodations</div>', unsafe_allow_html=True)
    
    # Select accommodations to compare
    selected_accommodations = st.multiselect(
        "Select accommodations to compare:",
        options=[acc["name"] for acc in accommodations],
        default=[accommodations[0]["name"], accommodations[1]["name"]]
    )
    
    if selected_accommodations:
        # Create comparison data
        comparison_data = []
        for acc in accommodations:
            if acc["name"] in selected_accommodations:
                comparison_data.append({
                    "Name": acc["name"],
                    "Type": acc["type"],
                    "Price Range": acc["price"],
                    "Description": acc["description"],
                    "Distance to Center": "10-15 min walk to Shinjuku Station" if "Shinjuku" in acc["name"] else "Varies",
                    "Amenities": "Wifi, Shared bathroom" if "Capsule" in acc["type"] or "Hostel" in acc["type"] else "Wifi, Private bathroom, Room service",
                    "Rating": "4.2/5" if "Capsule" in acc["type"] else "4.5/5" if "Hostel" in acc["type"] else "4.8/5"
                })
        
        # Display comparison
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    # Add a map of accommodation locations
    st.markdown('<div class="section-header">Accommodation Map</div>', unsafe_allow_html=True)
    
    accommodation_locations = {
        "Shinjuku Kuyakusho-mae Capsule Hotel": [35.6908, 139.7077],
        "UNPLAN Shinjuku": [35.6945, 139.7065],
        "Khaosan Tokyo Kabuki": [35.7064, 139.7966],
        "Park Hyatt Tokyo": [35.6866, 139.6936]
    }
    
    map_data = pd.DataFrame({
        "lat": [loc[0] for loc in accommodation_locations.values()],
        "lon": [loc[1] for loc in accommodation_locations.values()],
        "name": accommodation_locations.keys()
    })
    
    st.map(map_data, size=15)

with tabs[3]:
    st.markdown('<div class="section-header">Flights</div>', unsafe_allow_html=True)
    
    st.markdown('''
    <div class="info-card">
    <p>This section would typically contain flight details. Based on the provided information, you would arrive at either:</p>
    <ul>
        <li><strong>Narita International Airport (NRT)</strong></li>
        <li><strong>Haneda Airport (HND)</strong></li>
    </ul>
    <p>From the airport, you can take:</p>
    <ul>
        <li><strong>Narita Express</strong> or <strong>Limousine Bus</strong> to Shinjuku (¥3,000-¥4,000 / $20-$30)</li>
    </ul>
    </div>
    ''', unsafe_allow_html=True)
    
    # Add sample flight options
    st.markdown('<div class="section-header">Sample Flight Options</div>', unsafe_allow_html=True)
    
    # Flight options data - replace with realistic data for your case
    flight_options = [
        {
            "airline": "All Nippon Airways (ANA)",
            "departure": "DEL 08:30",
            "arrival": "NRT 19:45",
            "duration": "11h 15m",
            "price": "₹42,500 / ¥73,100",
            "stops": "1 (Bangkok)"
        },
        {
            "airline": "Japan Airlines (JAL)",
            "departure": "DEL 07:15",
            "arrival": "HND 18:20",
            "duration": "11h 05m",
            "price": "₹45,200 / ¥77,744",
            "stops": "1 (Singapore)"
        },
        {
            "airline": "Air India",
            "departure": "DEL 05:55",
            "arrival": "NRT 17:30",
            "duration": "11h 35m",
            "price": "₹39,800 / ¥68,456",
            "stops": "1 (Hong Kong)"
        }
    ]
    
    flight_df = pd.DataFrame(flight_options)
    st.dataframe(flight_df, use_container_width=True, hide_index=True)
    
    # Add airport transport options
    st.markdown('<div class="section-header">Airport to City Transport Options</div>', unsafe_allow_html=True)
    
    transport_options = [
        {
            "method": "Narita Express (N'EX)",
            "duration": "53 min (to Shinjuku)",
            "price": "¥3,270 / ₹1,900",
            "frequency": "Every 30-60 min",
            "notes": "Fastest and most comfortable option"
        },
        {
            "method": "Limousine Bus",
            "duration": "1h 45m (to Shinjuku)",
            "price": "¥3,200 / ₹1,860",
            "frequency": "Every 15-30 min",
            "notes": "Direct to many hotels, no transfers needed"
        },
        {
            "method": "Regular Train",
            "duration": "1h 30m (to Shinjuku)",
            "price": "¥1,340 / ₹780",
            "frequency": "Every 30 min",
            "notes": "Economical but requires transfers"
        }
    ]
    
    transport_df = pd.DataFrame(transport_options)
    st.dataframe(transport_df, use_container_width=True, hide_index=True)

with tabs[4]:
    st.markdown('<div class="section-header">Budget Breakdown (Estimated)</div>', unsafe_allow_html=True)
    
    budget_items = [
        {
            "category": "Accommodation",
            "amount": "¥20,000-¥25,000 ($140-$175)",
            "details": "4 nights in a budget hotel/capsule hotel"
        },
        {
            "category": "Food",
            "amount": "¥20,000-¥25,000 ($140-$175)",
            "details": "5 days (eating affordably)"
        },
        {
            "category": "Transportation",
            "amount": "¥10,000-¥15,000 ($70-$105)",
            "details": "Within Tokyo and day trip to Hakone"
        },
        {
            "category": "Activities",
            "amount": "¥5,000-¥10,000 ($35-$70)",
            "details": "Including entry fees and souvenirs"
        },
        {
            "category": "Miscellaneous",
            "amount": "¥5,000-¥10,000 ($35-$70)",
            "details": "For unforeseen expenses"
        },
        {
            "category": "Total",
            "amount": "¥60,000-¥85,000 ($420-$595)",
            "details": "Aligning with your budget of ₹50,000 (¥85,000-¥90,000)"
        }
    ]
    
    df_budget = pd.DataFrame(budget_items)
    st.dataframe(df_budget, use_container_width=True, hide_index=True)
    
    # Add budget visualization
    st.markdown('<div class="section-header">Budget Visualization</div>', unsafe_allow_html=True)
    
    # Display the chart
    expense_chart = create_expense_chart()
    st.image(expense_chart)
    
    st.markdown('''
    <div class="section-header">Dining Recommendations</div>
    <div class="info-card">
    <p><strong>Budget-friendly options:</strong></p>
    <ul>
        <li><strong>Ramen shops:</strong> Numerous options throughout Tokyo (¥800-¥1,500 / $5.50-$10)</li>
        <li><strong>Yoshinoya/Sukiya/Matsuya (Gyudon chains):</strong> Quick and cheap beef bowls (¥400-¥700 / $2.80-$4.90)</li>
        <li><strong>Conveyor belt sushi:</strong> Affordable sushi options (¥100-¥300 per plate)</li>
        <li><strong>Convenience stores:</strong> Wide selection of ready-to-eat meals and snacks</li>
        <li><strong>Standing soba/udon shops:</strong> Quick and cheap noodle options</li>
    </ul>
    </div>
    ''', unsafe_allow_html=True)
    
    # Add currency converter
    st.markdown('<div class="section-header">Currency Converter</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        amount = st.number_input("Amount", min_value=0.0, value=1000.0, step=100.0)
    
    with col2:
        from_currency = st.selectbox("From", ["JPY", "USD", "INR", "EUR"], index=0)
    
    with col3:
        to_currency = st.selectbox("To", ["JPY", "USD", "INR", "EUR"], index=2)
    
    converted_amount = currency_converter(amount, from_currency, to_currency)
    
    st.markdown(f'''
    <div class="info-card" style="text-align: center;">
        <h2>{amount} {from_currency} = {converted_amount:.2f} {to_currency}</h2>
    </div>
    ''', unsafe_allow_html=True)

with tabs[5]:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="section-header">Top Attractions</div>', unsafe_allow_html=True)
        
        attractions = [
            {
                "name": "Senso-ji Temple",
                "cost": "Free entry",
                "description": "Tokyo's oldest temple, offering a glimpse into Japanese history and culture"
            },
            {
                "name": "Meiji Jingu Shrine",
                "cost": "Free entry",
                "description": "Peaceful oasis dedicated to Emperor Meiji and Empress Shoken"
            },
            {
                "name": "Tokyo Skytree",
                "cost": "¥2,060-¥3,090 / $14-$21",
                "description": "Tallest structure in Japan with panoramic city views"
            },
            {
                "name": "Shinjuku Gyoen National Garden",
                "cost": "¥500 / $3.50",
                "description": "Beautiful garden with diverse landscapes"
            },
            {
                "name": "Tsukiji Outer Market",
                "cost": "Free entry",
                "description": "A bustling market with fresh seafood, produce, and street food"
            },
            {
                "name": "Hakone",
                "cost": "Hakone Free Pass recommended",
                "description": "Mountain resort town known for its hot springs, views of Mt. Fuji, and art museums"
            },
            {
                "name": "Ghibli Museum",
                "cost": "¥1,000 / $7, reservations required",
                "description": "For fans of Studio Ghibli films"
            }
        ]
        
        for attraction in attractions:
            st.markdown(f'''
            <div style="margin-bottom: 15px;">
                <p><strong>{attraction['name']}</strong> ({attraction['cost']})<br>
                {attraction['description']}</p>
            </div>
            ''', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="section-header">Travel Tips</div>', unsafe_allow_html=True)
        
        st.markdown('''
        <ul>
            <li><strong>Cash is king:</strong> Many smaller establishments don't accept credit cards.</li>
            <li><strong>Bowing is customary:</strong> A slight bow is a polite greeting.</li>
            <li><strong>Remove your shoes:</strong> When entering homes and some traditional establishments.</li>
            <li><strong>Be quiet on public transport:</strong> Talking loudly on phones is considered rude.</li>
            <li><strong>Learn basic Japanese phrases:</strong> "Arigato" (thank you) and "Sumimasen" (excuse me) are useful.</li>
            <li><strong>Pocket Wifi:</strong> Rent a pocket wifi or buy a SIM card for convenient internet access.</li>
            <li><strong>Tipping is not expected:</strong> Service charge is typically included.</li>
            <li><strong>Carry a handkerchief:</strong> Many restrooms don't provide paper towels.</li>
            <li><strong>Trash bins are scarce:</strong> Be prepared to carry your trash with you.</li>
            <li><strong>Utilize convenience stores:</strong> They offer ATMs, food, and daily necessities.</li>
        </ul>
        ''', unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">Weather Forecast</div>', unsafe_allow_html=True)
        
        # Sample weather data (in a real app, this would come from an API)
        weather_data = [
            {"day": "Day 1", "temp": "18°C/64°F", "condition": "Partly Cloudy"},
            {"day": "Day 2", "temp": "20°C/68°F", "condition": "Sunny"},
            {"day": "Day 3", "temp": "19°C/66°F", "condition": "Light Rain"},
            {"day": "Day 4", "temp": "17°C/63°F", "condition": "Cloudy"},
            {"day": "Day 5", "temp": "21°C/70°F", "condition": "Sunny"}
        ]
        
        for day in weather_data:
            st.markdown(f'''
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span><strong>{day['day']}</strong></span>
                <span>{day['temp']}</span>
                <span>{day['condition']}</span>
            </div>
            ''', unsafe_allow_html=True)

with tabs[6]:
    st.markdown('<div class="section-header">Emergency Information</div>', unsafe_allow_html=True)
    
    emergency_info = [
        {"service": "Police", "number": "110"},
        {"service": "Ambulance/Fire", "number": "119"},
        {"service": "Japan Helpline (English 24/7)", "number": "0570-000-911"},
        {"service": "Tokyo Tourist Information Center", "number": "+81-3-5321-3077"},
        {"service": "Indian Embassy in Japan", "number": "+81-3-3262-2391"}
    ]
    
    for info in emergency_info:
        st.markdown(f'''
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span><strong>{info['service']}</strong></span>
            <span>{info['number']}</span>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Language Essentials</div>', unsafe_allow_html=True)
    
    phrases = [
        {"english": "Hello", "japanese": "Konnichiwa (こんにちは)"},
        {"english": "Thank you", "japanese": "Arigato (ありがとう)"},
        {"english": "Excuse me/Sorry", "japanese": "Sumimasen (すみません)"},
        {"english": "Yes", "japanese": "Hai (はい)"},
        {"english": "No", "japanese": "Iie (いいえ)"},
        {"english": "How much?", "japanese": "Ikura desu ka? (いくらですか？)"},
        {"english": "Where is...?", "japanese": "...wa doko desu ka? (〜はどこですか？)"},
        {"english": "I don't understand", "japanese": "Wakarimasen (わかりません)"},
        {"english": "Help!", "japanese": "Tasukete! (助けて！)"}
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<strong>English</strong>", unsafe_allow_html=True)
        for phrase in phrases:
            st.markdown(f"<div style='margin-bottom: 10px;'>{phrase['english']}</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<strong>Japanese</strong>", unsafe_allow_html=True)
        for phrase in phrases:
            st.markdown(f"<div style='margin-bottom: 10px;'>{phrase['japanese']}</div>", unsafe_allow_html=True)
            
    st.markdown('<div class="section-header">Useful Apps</div>', unsafe_allow_html=True)
    
    apps = [
        {"name": "Google Translate", "purpose": "Translation with offline capabilities"},
        {"name": "Japan Transit Planner", "purpose": "Navigation on public transportation"},
        {"name": "Tokyo Subway Navigation", "purpose": "Official Tokyo metro app"},
        {"name": "XE Currency", "purpose": "Real-time currency conversion"},
        {"name": "TripAdvisor", "purpose": "Reviews and recommendations"}
    ]
    
    for app in apps:
        st.markdown(f'''
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <span><strong>{app['name']}</strong></span>
            <span>{app['purpose']}</span>
        </div>
        ''', unsafe_allow_html=True)

# Add custom CSS for better styling
st.markdown('''
<style>
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 15px;
        padding-bottom: 5px;
        border-bottom: 2px solid #ff4b4b;
    }
    
    .info-card {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
    }
    
    .stDataFrame {
        margin-top: 15px;
        margin-bottom: 30px;
    }
</style>
''', unsafe_allow_html=True)

# Function to create expense chart (placeholder for actual implementation)
def create_expense_chart():
    # This would typically use matplotlib, plotly, or another visualization library
    # For simplicity, I'm using a placeholder here
    # In a real application, this would generate an actual visualization
    
    # Create a figure and plot data
    fig, ax = plt.subplots(figsize=(10, 6))
    
    categories = ["Accommodation", "Food", "Transportation", "Activities", "Miscellaneous"]
    amounts = [22500, 22500, 12500, 7500, 7500]  # Middle values of ranges
    
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
    
    ax.bar(categories, amounts, color=colors)
    ax.set_ylabel('Amount (¥)')
    ax.set_title('Budget Breakdown')
    
    # Add value labels on top of each bar
    for i, v in enumerate(amounts):
        ax.text(i, v + 500, f"¥{v:,}", ha='center')
    
    plt.tight_layout()
    
    # Save to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # In a real app, you would return this buffer to be displayed
    # For this example, we can pretend this is an image path or buffer
    return buf

# Function to convert currencies (placeholder implementation)
def currency_converter(amount, from_currency, to_currency):
    # This would typically use an API or pre-defined exchange rates
    # For simplicity, using fixed exchange rates
    rates = {
        "JPY": 1,
        "USD": 0.007,
        "INR": 0.58,
        "EUR": 0.0065
    }
    
    # Convert to base currency (JPY) first, then to target currency
    in_jpy = amount / rates[from_currency]
    converted = in_jpy * rates[to_currency]
    
    return converted
