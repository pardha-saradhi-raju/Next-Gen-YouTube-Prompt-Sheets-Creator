import streamlit as st
from dotenv import load_dotenv
import os
import re
import random
import base64
from google.cloud import language_v1
from google.cloud import translate_v2 as translate
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# Load environment variables
load_dotenv()
api_key = os.getenv("YOUR_API_KEY")
if not api_key:
    st.error("API key not found.")
    st.stop()

# Configure Google Generative AI
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Error configuring Google Generative AI: {e}")
    st.stop()

# --- Functions ---

def analyze_text(text):
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    response = client.analyze_sentiment(document=document)
    return response

def translate_text(text, target_language='en'):
    translate_client = translate.Client()
    translation = translate_client.translate(text, target_language=target_language)
    return translation['translatedText']

def extract_video_id(youtube_url):
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, youtube_url)
    if match:
        return match.group(1)
    else:
        st.error("Invalid YouTube URL.")
        return None

def get_transcript_languages(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        return [t.language_code for t in transcript_list]
    except Exception as e:
        st.error(f"Error retrieving transcript languages: {e}")
        return []

def extract_transcript_details(video_id, target_language='en'):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_languages = [t.language_code for t in transcript_list]

        # If transcript is available in English, use it, otherwise translate to English
        language_code = 'en' if 'en' in available_languages else available_languages[0]  # Fallback to first available language

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
        full_transcript = " ".join([segment['text'] for segment in transcript])

        # Translate if the transcript is not in the target language
        if language_code != target_language:
            full_transcript = translate_text(full_transcript, target_language=target_language)

        return full_transcript
    except Exception as e:
        st.error(f"Error extracting transcript: {e}")
        return None

def generate_note_cards_from_transcript(full_transcript, keywords, target_language='en'):
    prompt = f"""
    You are an advanced educational assistant with a deep understanding of content analysis and summarization. 
    Your task is to create detailed, engaging, and informative note cards from a YouTube video transcript, focusing specifically on the given keywords.



    The transcript is provided in {target_language}, and your goal is to produce note cards in {target_language}.

    Here is the full transcript of the video:
    "{full_transcript}"

    Keywords: {keywords}

    Your goal is to produce a set of comprehensive and concise note cards based on this transcript. Each note card should:
    1. Highlight the most important concepts, facts, or ideas mentioned in the video.
    2. Provide clear and brief explanations for each highlighted concept or fact.
    3. Include bullet points, sub-points and examples where relevant to enhance understanding.
    4. Be written in simple, easy-to-understand language that is also engaging and catchy.
    5. Focus specifically on the provided keywords to ensure relevance.
    6. Each card should have minimum 5 points and maximum of 8 points.
    7.Remove * in all notecards
    8.Give popular related resources links expect youtube links in last notecard.
    9.Write Code for every small possiblity related to topic.
    10. Ensure no mixing of subheadings with other content. Each section must be visually distinct and start on a new line for clarity.
   11.  Use Markdown formatting for heading and subheadings:
   - Bold the subheadings (e.g., **Keyword:**).
   - Separate sections with blank lines to improve readability.
   - Avoid long paragraphs; use bullet points or short sentences where necessary.
    Ensure that you generate a minimum of 10 and a maximum of 20 note cards. Each note card should cover unique content from the transcript, ensuring that the 
    entire video is comprehensively summarized. The note cards should be highly informative, engaging, and directly related to the content of the video.

    Please start by creating the note cards based on the above guidelines.
    """
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)

        # Check the response format and access the text correctly
        if hasattr(response, 'text'):
            return response.text  # Access the 'text' attribute properly
        elif 'text' in response:  # Try accessing if it's a dictionary-like response
            return response['text']
        else:
            raise ValueError("Unexpected response format: 'text' not found.")
    except Exception as e:
        st.error(f"Error generating note card content: {e}")
        return None


def format_note_cards(note_cards_content):
    note_cards = note_cards_content.split("Note Card ")
    formatted_note_cards = []
    colors = ['#FFCDD2', '#F8BBD0', '#E1BEE7', '#D1C4E9', '#C5CAE9', '#BBDEFB', '#B3E5FC', '#B2EBF2', '#B2DFDB', '#C8E6C9']
    for i, note_card in enumerate(note_cards[1:], start=1):
        note_card = note_card.strip()
        if note_card:
            color = random.choice(colors)
            formatted_note_cards.append(f"""
                <div class="note-card" style="background-color: {color};">
                    <h3>Note Card {i}</h3>
                    <ul>
                        {note_card.replace('. ', '.<br>')}
                    </ul>
                </div>
            """)
    return formatted_note_cards

def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    st.markdown(
        f"""
    <style>
    .stApp {{
        background-image: url(data:image/{"png"};base64,{encoded_string.decode()});
        background-size: cover
    }}

    .main {{
        background-color: rgba(255, 255, 255, 0);
        margin: 80px auto;
        border-radius: 10px;
        margin-bottom: 20px;
        max-width: 900px;
    }}

    .stVideo {{
        margin-top: 2px;
        margin-bottom: 20px;
    }}

    </style>
    """,
        unsafe_allow_html=True
    )

# Custom CSS for input box design
st.markdown(
    """
    <style>
    .stTextInput > div > div > input {
        background-color: rgba(3, 3, 3, 0.22) !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Add background image
add_bg_from_local('image.jpg')

# --- Streamlit App ---
st.title("Next-Gen Youtube Prompt Sheets Creator")

# Custom CSS for note card design
st.markdown(""" 
<style>
/* Overall layout */
.main {
    margin: 80px auto;
    padding: 40px;
    background-color: rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    max-width: 1200px;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.12);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Custom note card style */
.note-card {
    border: 2px solid #e0e0e0;  /* Soft light grey border */
    background-color: #ffffff;
    padding: 25px;
    margin: 20px 0;
    border-radius: 12px;
    font-size: 1.15em;
    line-height: 1.75em;
    color: #333;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);  /* Soft shadow for depth */
    transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease;
    max-width: 95%;
    margin: 20px auto;
    cursor: pointer;
    overflow: hidden;
    position: relative;
    background-color: #ffffff;
}

/* Hover effect for note cards */
.note-card:hover {
    transform: translateY(-5px);  /* Slight lift on hover */
    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.15);  /* Stronger shadow effect */
    background-color: #f5f5f5;  /* Subtle background color change on hover */
}

/* Note card headings */
.note-card h3 {
    margin-top: 0;
    font-size: 1.7em;
    font-weight: 600;
    color: #34495E;  /* Darker blue for headings */
    padding-bottom: 15px;
    border-bottom: 3px solid #3498db;
    letter-spacing: 1px;
    margin-bottom: 15px;
}



/* Bullet points styling */
.note-card ul {
    padding-left: 25px;
    list-style: disc;
    margin: 0;
    padding: 10px 0;
}

/* Styling individual bullet points */
.note-card li {
    margin-bottom: 12px;
    font-size: 1.1em;
    color: #555;
    transition: color 0.3s ease;
}

.note-card li:hover {
    color: #3498db;  /* Hover effect for list items */
}

/* Add subtle background color based on note card index */
.note-card:nth-child(odd) {
    background-color: #f7f7f7;  /* Light grey background for odd cards */
}

.note-card:nth-child(even) {
    background-color: #e8f4f8;  /* Light blue background for even cards */
}

/* Add padding around the entire list of note cards */
.note-card-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 40px;
}

/* Styling for note card content */
.note-card-content {
    font-size: 1.05em;
    line-height: 1.65em;
    color: #666;
    padding: 10px 0;
}

/* Responsive design adjustments for smaller screens */
@media (max-width: 768px) {
    .main {
        padding: 20px;
    }

    .note-card {
        padding: 15px;
        font-size: 1em;
    }

    .note-card h3 {
        font-size: 1.5em;
    }

    .note-card li {
        font-size: 1em;
    }
}
</style>

""", unsafe_allow_html=True)



# Target language set to English
target_language = 'en'
st.markdown("**Target language - English**")

youtube_link = st.text_input("Enter YouTube Video Link:")

if youtube_link:
    video_id = extract_video_id(youtube_link)
    if video_id:
        st.video(f"https://www.youtube.com/watch?v={video_id}")

        # Keyword input
        keywords = st.text_input("Enter keywords (comma-separated):")

        if st.button("Generate Note Cards"):
            if not keywords:
                st.error("Please enter keywords.")
            else:
                with st.spinner("Extracting transcript..."):
                    full_transcript = extract_transcript_details(video_id, target_language)

                if full_transcript:
                    with st.spinner("Generating note cards..."):
                        note_cards_content = generate_note_cards_from_transcript(full_transcript, keywords, target_language)

                    if note_cards_content:
                        formatted_note_cards = format_note_cards(note_cards_content)
                        for note_card in formatted_note_cards:
                            st.markdown(note_card, unsafe_allow_html=True)
                    else:
                        st.error("Failed to generate note cards.")




