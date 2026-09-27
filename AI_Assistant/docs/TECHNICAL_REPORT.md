# ideal-chainsaw — Technical & Functional Report

**Repository:** [github.com/Dr-Aura/ideal-chainsaw](https://github.com/Dr-Aura/ideal-chainsaw)
**Live app:** [ideal-chainsaw-but7vpbezomeqpqw6vghwa.streamlit.app](https://ideal-chainsaw-but7vpbezomeqpqw6vghwa.streamlit.app/)
**Android package ID:** `com.draura.aiassistant`
**Report date:** 27 September 2026
**Status:** Sideload release live on GitHub; Play Store submission pending

---

## 1. Project Overview

ideal-chainsaw is a chat application that lets a user converse with large
language models hosted on Groq Cloud's inference platform. It is built and
delivered in two layers: a Python/Streamlit web application that does the
actual work of talking to Groq's API and rendering the chat interface, and
an Android application shell (built with Apache Cordova) that wraps that
web app in a native, installable package.

The result is a single codebase that runs identically in a desktop
browser, on Streamlit Community Cloud, and as a standalone Android app —
without maintaining separate web and mobile implementations.

## 2. What the App Actually Does

From a user's perspective, the app provides:

- A chat interface for sending messages and receiving streamed AI
  responses in real time
- A model picker in the sidebar that dynamically lists whichever models
  are currently available on the user's Groq account, rather than a
  hardcoded list that goes stale
- An adjustable "creativity" (temperature) slider controlling how
  deterministic vs. varied the AI's responses are
- A "Clear Chat History" control to reset the conversation
- A clean, high-contrast grayscale visual theme

Conversation history persists only for the current session (in
Streamlit's `session_state`) and is not saved to disk or any server —
closing the app or the browser tab discards it.

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Frontend / UI | Streamlit (Python web app framework) |
| AI inference | Groq Cloud API, via the official `groq` Python SDK |
| Language | Python 3.13 |
| Mobile packaging | Apache Cordova (WebView-based native Android wrapper) |
| Android build system | Gradle 8.14.2 |
| Android SDK | Platform 36 (Android 16), Build-Tools 36.0.0 |
| JDK | OpenJDK 21 |
| Hosting (web app) | Streamlit Community Cloud |
| Distribution (Android) | Direct APK sideload via GitHub Releases; Google Play submission prepared but pending |
| Version control | Git / GitHub (`Dr-Aura/ideal-chainsaw`) |

## 4. Architecture

The system has two distinct layers that communicate over plain HTTPS:

- **Streamlit application (`app.py`)** — runs on Streamlit Community
  Cloud. Holds the Groq API key (via Streamlit's encrypted secrets
  manager), maintains chat session state, calls the Groq SDK, and streams
  tokens back to the browser as they're generated.
- **Cordova Android shell** — a thin native wrapper whose only job is to
  open a WebView pointed at the live Streamlit URL. It contains no
  application logic of its own; all functionality lives in the Streamlit
  layer.

This means the Android app requires an active internet connection at all
times — there is no offline mode, and no AI processing happens on-device.
Updating the Streamlit app's behavior (e.g. adding a feature to `app.py`)
updates every user of the Android app automatically, without requiring a
new APK release, since the Android shell simply loads whatever is
currently live at that URL.

### 4.1 Request flow

1. User types a message in the Android app (WebView) or a browser
2. Streamlit sends the full conversation history to Groq's
   `chat.completions.create()` endpoint with `stream=True`
3. Groq streams back response tokens ("chunks") over Server-Sent Events,
   handled internally by the official SDK
4. Streamlit's `st.write_stream()` renders tokens to the screen as they
   arrive
5. The completed message is appended to session state for context in the
   next turn

## 5. Security & Data Handling

### 5.1 API credentials

The Groq API key is stored exclusively in Streamlit's secrets manager
(`secrets.toml` locally, or the Streamlit Cloud dashboard in production)
and is never hardcoded into source, committed to git, or exposed to the
client/browser.

### 5.2 Android app signing

The release build is signed with a dedicated upload keystore (RSA 2048,
valid until 2054) generated specifically for this app. This keystore is
the app's permanent identity on any future Play Store listing — its loss
would prevent publishing further updates under the same listing.

### 5.3 Data sent to third parties

User-typed chat messages are transmitted to Groq Cloud over encrypted
HTTPS to generate responses. No other personal data (identity, location,
device information) is collected by the application itself. A published
privacy policy discloses this data flow, as required for Play Store
submission.

## 6. Build & Release Pipeline

The Android build was assembled and debugged from a clean Debian 13
environment. Key components had to be set up independently of any IDE:

- Android command-line SDK tools, installed manually via Google's SDK
  Manager
- A standalone Gradle 8.14.2 installation (the Debian-packaged version
  proved broken and was replaced)
- OpenJDK, matched to the version required by the targeted Android API
  level
- A Python virtual environment for the Streamlit app's dependencies,
  required on Debian 13's externally-managed Python installation

Two build outputs are produced from the same Cordova project:

| Build type | Command | Purpose |
|---|---|---|
| Debug APK | `cordova build android` | Quick local testing; installed directly via `adb` |
| Signed release bundle (`.aab`) | `cordova build android --release --buildConfig=build.json` | Required format for Google Play submission |

The debug APK has additionally been published as a public GitHub Release,
allowing direct installation without any app store, developer account, or
fee.

## 7. Current Status

| Component | Status | Reference |
|---|---|---|
| Streamlit web app | Live and functional | `ideal-chainsaw-but7vpbezomeqpqw6vghwa.streamlit.app` |
| Android debug build | Working, tested on-device | — |
| Android signed release (`.aab`) | Built and signed successfully | — |
| GitHub sideload release | Published, publicly downloadable | `github.com/Dr-Aura/ideal-chainsaw/releases/tag/v1.0.0` |
| Privacy policy | Written and published | See appendix |
| Google Play submission | Prepared, not yet submitted | Blocked on $25 developer registration fee |

## 8. Known Limitations

- **No offline support** — the app is entirely dependent on the Streamlit
  deployment staying online and reachable.
- **Chat history is not persistent** — it resets whenever the app or
  session ends. This is the top candidate for the next feature addition.
- **Debug build only, on the sideload release** — the GitHub release is
  not signed with the production release keystore; it is intended for
  testing and early feedback.
- **No native functionality beyond the WebView wrapper** — a real
  consideration for Google Play's minimum-functionality policy, which can
  flag simple website-wrapper apps; adding persistent local storage and
  offline handling would meaningfully strengthen the submission.

## 9. Roadmap

- [ ] Persistent chat history (local storage, e.g. SQLite)
- [ ] Offline / no-connection handling in the Android shell
- [ ] Complete Google Play Store submission once the developer account
      fee is paid
- [ ] Custom app icon, splash screen, and feature graphic
- [ ] Optional: multi-model side-by-side comparison mode
- [ ] Optional: basic rate-limiting if the app is shared publicly, to
      protect Groq API quota

## 10. Appendix — Key Links

- GitHub repository: <https://github.com/Dr-Aura/ideal-chainsaw>
- Live app: <https://ideal-chainsaw-but7vpbezomeqpqw6vghwa.streamlit.app/>
- GitHub release (sideload APK):
  <https://github.com/Dr-Aura/ideal-chainsaw/releases/tag/v1.0.0>

---

*This report reflects the state of the project as of the date above and
will drift out of date as the roadmap items are completed — treat it as
a snapshot, not a live status page.*
