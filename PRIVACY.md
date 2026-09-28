# Privacy Policy — ideal-chainsaw

**Last updated:** 28 September 2026

## Overview

ideal-chainsaw is an AI chat application that lets you converse with large language models hosted on Groq Cloud. This policy explains what data is handled and how.

## Data We Process

### Chat messages
When you send a message, the text is transmitted over encrypted HTTPS to Groq Cloud so a response can be generated. The full conversation history for the current session is also sent with each request so the model has context.

### What we do **not** collect
- No account or identity information
- No location data
- No device identifiers beyond what is required for normal HTTPS communication
- No analytics or tracking pixels
- No chat history is stored on our servers after the session ends

Conversation history lives only in the current browser/app session (Streamlit `session_state`). Closing the tab or the app discards it.

## Third-Party Services

| Service | Purpose | Data shared |
|---------|---------|-------------|
| **Groq Cloud** | AI inference | Your chat messages and conversation context |
| **Streamlit Community Cloud** | Hosts the web application | Standard web request metadata (IP address, user-agent) as part of normal HTTPS traffic |

We do not sell or share your data with any other parties.

## Android App

The optional Android package is a thin WebView wrapper around the live Streamlit app. It does not process or store chat data on the device beyond what the WebView itself holds in memory for the current session.

## Changes

If this policy changes, the updated version will be posted in this repository. Continued use of the app after changes constitutes acceptance of the revised policy.

## Contact

Questions about this policy can be raised by opening an issue on the [GitHub repository](https://github.com/Dr-Aura/ideal-chainsaw).
