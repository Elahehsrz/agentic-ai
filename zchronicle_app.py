import os
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain_community.utilities import SerpAPIWrapper
from langchain.memory import ConversationBufferMemory
import streamlit as st


# Load API keys securely
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["SERPAPI_API_KEY"] = os.getenv("SERPAPI_API_KEY")

# Initialize LLM (Gemini)
llm = GoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

# Initialize our Search Tool
search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_API_KEY"))
search_tool = Tool(
    name="Historical Web Search",
    func=search.run,
    description="Search for historical events, timelines, and perspectives on a topic"
)

# Memory to track user history across queries
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Initialize the Agent
agent = initialize_agent(
    tools=[search_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    memory=memory
)

def history_explorer(query):
    # Agent performs search and summarization
    response = agent.run(query)

    # Store result in FAISS vector store
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_db = FAISS.from_texts([response], embedding=embedding_model)
    vector_db.save_local("zchronicle_faiss_index")

    return response, vector_db

def extract_keywords(text):
    prompt = f"""
    Extract key people, places, dates, and events mentioned in the following historical summary.

    Return the result as a JSON object with keys: "people", "places", "dates", "events".

    Example output:
    {{
    "people": ["Winston Churchill"],
    "places": ["Germany", "Poland", "Manchuria"],
    "dates": ["1939", "1941"],
    "events": ["Invasion of Poland", "Attack on Pearl Harbor"]
    }}

    Summary:
    {text}
    """
    response = llm.invoke(prompt)
    # cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', response).strip()
    # Parse output JSON safely
    try:
        keywords_json = re.sub(r'```(?:json)?\s*|\s*```', '', response).strip()
    except Exception:
        keywords_json = {}
    return keywords_json

def extract_timeline(text):
    prompt = f"""
    Extract a timeline of historical events with dates from the following text. 
    Return the timeline as a JSON array of objects, each with "date" and "event" keys.

    Example output:
    [
    {{"date": "1939", "event": "Poland invasion"}},
    {{"date": "1941", "event": "Japan attacks Pearl Harbor"}}
    ]

    Text:
    {text}
    """
    response = llm.invoke(prompt)
    # cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', response).strip()
    try:
        timeline = re.sub(r'```(?:json)?\s*|\s*```', '', response).strip()
    except Exception:
        timeline = []
    return timeline

def analyze_sentiment(text):
    prompt = f"""
    Analyze the historical impact or sentiment conveyed in the following summary.
    Indicate whether the overall tone is Positive, Negative, or Neutral.
    Also, provide a short explanation of the historical consequences and who was affected.

    Return a JSON object with:
    - sentiment: "Positive", "Negative", or "Neutral"
    - impact_description: (a short paragraph)

    Summary:
    {text}
    """
    result = llm.invoke(prompt)
    try:
        sentiment = re.sub(r'```(?:json)?\s*|\s*```', '', result).strip()
        sentiment = json.loads(sentiment)
    except Exception:
        sentiment = {}
    return sentiment




# Streamlit UI
st.title("📜 zChronicle – Agentic AI History Explorer")
st.markdown("Ask about a historical event, person, or timeline.")

query = st.text_input("🕰️ Enter a historical question (e.g., 'What caused the fall of the Roman Empire?')")

if st.button("🔍 Explore History"):
    with st.spinner("Generating historical summary..."):
        summary, vector_db = history_explorer(query)
    st.subheader("📖 Historical Summary:")
    st.write(summary)

    with st.spinner("Extracting keywords..."):
        keywords = extract_keywords(summary)
    st.subheader("🔑 Extracted Keywords:")
    st.json(keywords)

    with st.spinner("Building timeline..."):
        timeline = extract_timeline(summary)
    st.subheader("🕰️ Timeline:")
    st.json(timeline)

    with st.spinner("Analyzing historical sentiment and impact..."):
        sentiment = analyze_sentiment(summary)
    st.subheader("📊 Sentiment / Impact Analysis:")
    st.markdown(f"**Sentiment:** {sentiment.get('sentiment')}")
    st.write(sentiment.get("impact_description"))
