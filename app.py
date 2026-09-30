import streamlit as st
from groq import Groq
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
        .stApp {
            background-color: #f8f9fa !important;
            color: #1a1a1a !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background-color: #e9ecef !important;
            border-right: 1px solid #dee2e6 !important;
        }
        .block-container {
            max-width: 900px !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            width: 100% !important;
        }
        h1, h2, h3 {
            color: #111111 !important;
            font-weight: 700 !important;
        }
        .stChatMessage {
            background-color: #ffffff !important;
            border: 1px solid #dee2e6 !important;
            border-radius: 8px !important;
            padding: 1.25rem !important;
            margin-bottom: 0.75rem !important;
            color: #212529 !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            width: 100% !important;
        }
        div[data-testid="stChatInput"] {
            background-color: #ffffff !important;
            border-top: 1px solid #dee2e6 !important;
        }
    </style>
""", unsafe_allow_html=True)

FALLBACK_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]
EMBEDDING_MODEL = "nomic-embed-text-v1_5"

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    st.error("Please add your GROQ_API_KEY to the Streamlit Secrets manager.")
    st.stop()

client = Groq(api_key=api_key)


@st.cache_data(ttl=3600)
def fetch_available_models(_client: Groq) -> list[str]:
    """List active model IDs via the SDK. Falls back to a known-good list on any failure."""
    try:
        models = _client.models.list()
        model_ids = [m.id for m in models.data if getattr(m, "active", True)]
        return sorted(model_ids) if model_ids else FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


def get_embeddings(texts: list[str]) -> np.ndarray:
    """Embed a list of texts using Groq's nomic-embed-text-v1_5 model."""
    if not texts:
        return np.array([])
    # Batch in chunks of 32 to stay safe with API limits
    all_embeddings = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            encoding_format="float",
        )
        # Sort by index to preserve order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([item.embedding for item in sorted_data])
    return np.array(all_embeddings)


def run_kmeans_clustering(
    texts: list[str], n_clusters: int, random_state: int = 42
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """
    Embed texts, run K-means, and return (embeddings_2d, labels, cluster_sizes).
    Uses PCA to project to 2D for visualization.
    """
    embeddings = get_embeddings(texts)
    if len(embeddings) < n_clusters:
        raise ValueError(f"Need at least {n_clusters} messages to form {n_clusters} clusters.")

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Project to 2D for plotting
    if embeddings.shape[1] > 2:
        pca = PCA(n_components=2, random_state=random_state)
        embeddings_2d = pca.fit_transform(embeddings)
    else:
        embeddings_2d = embeddings

    cluster_sizes = [int(np.sum(labels == i)) for i in range(n_clusters)]
    return embeddings_2d, labels, cluster_sizes


def generate_cluster_labels(
    texts: list[str], labels: np.ndarray, n_clusters: int, model: str
) -> list[str]:
    """Ask the LLM to invent short topic names for each cluster."""
    cluster_names = []
    for i in range(n_clusters):
        members = [texts[j] for j in range(len(texts)) if labels[j] == i]
        # Take up to 5 representative snippets
        sample = members[:5]
        prompt = (
            "Given these conversation snippets that belong to the same topic cluster, "
            "reply with ONLY a short 2-5 word topic title. No quotes, no explanation.\n\n"
            + "\n---\n".join(sample)
        )
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a concise topic-labeling assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=20,
            )
            name = completion.choices[0].message.content.strip().strip('"').strip("'")
            cluster_names.append(name or f"Topic {i + 1}")
        except Exception:
            cluster_names.append(f"Topic {i + 1}")
    return cluster_names


# --------------- Sidebar ---------------
with st.sidebar:
    st.title("⚙️ Configuration")
    available_models = fetch_available_models(client)
    model_option = st.selectbox("Choose a model:", available_models, index=0)
    temperature = st.slider(
        "Creativity Level (Temperature):", min_value=0.0, max_value=1.0, value=0.7, step=0.1
    )
    st.markdown("---")

    # ---- Topic Clustering section ----
    st.subheader("📊 Topic Clustering")
    st.caption("Uses K-means on Groq embeddings of the current conversation.")

    messages_for_clustering = [
        m for m in st.session_state.get("messages", []) if m["role"] != "system"
    ]
    n_msgs = len(messages_for_clustering)

    if n_msgs < 4:
        st.info("Chat a bit more (at least 4 messages) to enable topic clustering.")
    else:
        max_k = min(8, n_msgs // 2)
        n_clusters = st.slider(
            "Number of topics (K)",
            min_value=2,
            max_value=max_k,
            value=min(3, max_k),
            step=1,
        )
        if st.button("🔍 Run K-means Clustering", use_container_width=True):
            with st.spinner("Embedding messages & clustering…"):
                try:
                    texts = [
                        f"{m['role'].upper()}: {m['content'][:800]}"
                        for m in messages_for_clustering
                    ]
                    embeddings_2d, labels, sizes = run_kmeans_clustering(texts, n_clusters)
                    cluster_names = generate_cluster_labels(
                        texts, labels, n_clusters, model_option
                    )

                    st.session_state["cluster_result"] = {
                        "texts": texts,
                        "labels": labels.tolist(),
                        "embeddings_2d": embeddings_2d.tolist(),
                        "names": cluster_names,
                        "sizes": sizes,
                        "n_clusters": n_clusters,
                    }
                    st.success(f"Found {n_clusters} topic clusters")
                except Exception as e:
                    st.error(f"Clustering failed: {e}")

    st.markdown("---")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        if "cluster_result" in st.session_state:
            del st.session_state["cluster_result"]
        st.rerun()

# --------------- Main chat area ---------------
st.title("🤖 AI Assistant")
st.caption(f"Powered by Groq Cloud | Model: {model_option} | Temp: {temperature}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is on your mind?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        api_messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant. You must always reply in English.",
            }
        ]
        api_messages.extend(st.session_state.messages)

        def response_generator():
            try:
                stream = client.chat.completions.create(
                    model=model_option,
                    messages=api_messages,
                    temperature=temperature,
                    stream=True,
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            except Exception as e:
                yield f"⚠️ API Error: {str(e)}"

        full_reply = st.write_stream(response_generator())
        st.session_state.messages.append({"role": "assistant", "content": full_reply})

# --------------- Cluster results display ---------------
if "cluster_result" in st.session_state:
    result = st.session_state["cluster_result"]
    st.markdown("---")
    st.subheader("📊 Conversation Topic Clusters")

    # 2D scatter plot
    emb = np.array(result["embeddings_2d"])
    labels = np.array(result["labels"])
    names = result["names"]

    fig = px.scatter(
        x=emb[:, 0],
        y=emb[:, 1],
        color=[names[l] for l in labels],
        hover_data={"text": result["texts"]},
        labels={"x": "PCA 1", "y": "PCA 2", "color": "Topic"},
        title="Message embeddings projected to 2D (PCA)",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(marker=dict(size=12, opacity=0.85))
    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        legend_title_text="Topic",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Cluster cards
    cols = st.columns(min(3, result["n_clusters"]))
    for i, name in enumerate(names):
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(f"{result['sizes'][i]} message(s)")
                members = [
                    result["texts"][j]
                    for j in range(len(result["texts"]))
                    if result["labels"][j] == i
                ]
                for m in members[:3]:
                    preview = m[:120] + ("…" if len(m) > 120 else "")
                    st.markdown(f"- _{preview}_")
                if len(members) > 3:
                    st.caption(f"+ {len(members) - 3} more")
