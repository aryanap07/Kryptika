import streamlit as st
import requests 
import plotly.express as px
NODE_URL = "http://localhost:5000"

# Title.......................
st.title(" KRYPTIKA DASHBOARD ")

# Fetching Blockchain data.....

def get_chain():
    return requests.get(f"{NODE_URL}/chain").json()

# Fetch pending transactions....

def get_pending():
    return requests.get(f"{NODE_URL}/transactions/pending").json()

# Blockchain....................
st.subheader("Blockchain")
chain = get_chain()

block_indexes = []
tx_counts = []

for block in chain :
    block_indexes.append(block["index"])
    tx_counts.append(len(block["transactions"]))
    with st.expander(f"Block #{block['index']}") : 
        st.write("Hash:" , block['hash'])
        st.write("Previous Hash :" , block['prev_hash'])
        st.write("Transactions" , block['transactions'])

# Graph........................
st.subheader("Transactions per Block")
fig = px.line(
    x = block_indexes , 
    y = tx_counts,
    labels ={"x": "Block index" , "y": "Transactions"},
    title = "Blockchain Activity"
)
st.plotly_chart(fig)


# Mempool Section..............

st.subheader("Pending transactions")
pending = get_pending()
if pending["transactions"]:
    for tx in pending["transactions"]:
        st.write(f"{tx['sender']} -> {tx['recipient']} : {tx['amount']}")
else :
    st.write("No pending transactions")

#Balance........................

st.subheader("Wallet Balance")
address = st.text_input("Enter Wallet Address :  ")
if address:
    balance = requests.get(f"{NODE_URL}/balance/{address}").json()
    st.write("Balance:" , balance["balance"])












