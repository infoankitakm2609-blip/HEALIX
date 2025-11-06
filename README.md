# HEALIX
GenAI Hackathon
AarogyaAIApp is a Streamlit-based application that allows users to speak or type their health symptoms, and generates a simple and easy-to-understand medical summary using Gemini. The app can also convert Hindi or English speech to text using Google Cloud Speech-to-Text.

Features

1. Record voice symptoms (Hindi or English)
2. Upload audio files Or type symptoms manually
3. Converts speech to text (Google STT)
4. Generates a clean medical summary (Gemini API)
5. Allows downloading the summary as a text file

Technology Used

```Streamlit (UI)
Google Cloud Speech-to-Text
Gemini API (google-genai)
audio_recorder_streamlit (for mic input)
python-dotenv (to load environment variables)
```

Requirements

Python 3.9 or later

Google Cloud account
Speech-to-Text API enabled
Service Account Key (JSON file)
Gemini API Key

Installation
Install required libraries:

pip install -r requirements.txt

Setup Environment Variables
Create a file named .env in the project folder and add:

GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/your_service_account.json

How to Run
Run the app with:

streamlit run app.py

Then open the link is not available currently as it is not hosted.

How to Use the App

1. Open the app
2. Fill patient information (optional)
3.Tick the consent checkbox

Provide symptom input using one of the following:

1. Speak through microphone
2.Upload an audio file
3.Type symptoms manually
4.Click “Generate Summary”
5.Read or download the generated summary

Notes

1.Make sure your microphone is allowed in the browser.
2.Recordings should be short and clear.
3.This tool is for awareness and communication only, not medical diagnosis.
