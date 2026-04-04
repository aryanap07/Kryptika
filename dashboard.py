import streamlit as st
import requests 
import plotly.express as px
NODE_URL = "http://localhost:5000"

# Fetching Blockchain data.....
def get_chain():
    return requests.get(f"{NODE_URL}/chain").json()

# Fetch pending transactions....



