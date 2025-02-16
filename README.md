# README

## Setup Guide

Follow the steps below to correctly set up and run the node.

### Prerequisites
Ensure you have:
- Reference code from verified accounts with more than **50 active hours**.
- `node.js` installed on your system.

### Step 1: Add Reference and Address
Before activating your account, you need to link your reference and address:
1. Create `ref.txt` and add your **reference code**.
2. Create `address.txt` and add your **wallet address**.
3. Create `proxy.txt` and add your **proxy**.

### Step 2: Configure Proxy
Set up your proxy using the following format:
```
user:pass@ip:port
```
Make sure your proxy is valid and working before proceeding.

### Step 3: Create Account
```
pip install -r requirements.txt
python ref.py
```

### Step 4: Start the Node
Once your account is activated:
1. Run the following command to start the node:
   ```
   npm install
   node main.js
   ```
2. Keep the node running every 12 hours to ensure continuous operation.


