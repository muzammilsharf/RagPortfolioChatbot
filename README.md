# Portfolio RAG Chatbot
**A Production-Ready Retrieval-Augmented Generation Engine for Technical Portfolios**

This system isn't just a chatbot; it’s a demonstration of low-latency AI engineering. It serves as an intelligent interface for my professional history, allowing users to interact with my project architecture and technical expertise through a grounded, high-performance RAG pipeline.

---

## Table of Contents
1. [System Architecture & Design](#system-architecture--design)
2. [The RAG Workflow](#the-rag-workflow)
3. [Key Features](#key-features)
4. [Technical Stack](#technical-stack)
5. [Use Cases](#use-cases)
6. [Hallucination Control & Reliability](#hallucination-control--reliability)
7. [Getting Started](#getting-started)
8. [Evaluation & Metrics](#evaluation--metrics)
9. [Project Structure](#project-structure)
10. [Future Roadmap](#future-roadmap)
11. [Contact & Connections](#contact--connections)

---

## System Architecture & Design
I designed this system using a **decoupled Microservices-oriented approach**. By separating the FastAPI backend from the Next.js frontend, the system ensures high scalability and allows for independent optimization of the AI inference engine.

* **Asynchronous Processing**: Leveraging FastAPI’s `async` capabilities to handle concurrent user sessions without blocking the event loop.
* **Persistent Vector Storage**: Unlike in-memory solutions, this uses **ChromaDB** with persistent storage to ensure fast cold-starts and consistent data indexing.
* **Streaming-First UX**: Implemented **Server-Sent Events (SSE)**. Instead of making users wait for the full LLM completion, tokens are streamed in real-time, drastically reducing the "Time to First Token" (TTFT).

---

## The RAG Workflow
The system follows a classic but highly tuned **Retrieve -> Augment -> Generate** pipeline:

1.  **Semantic Ingestion**: Documents are parsed and broken into **250-token chunks** with a 10% overlap. This ensures that technical context isn't lost at the boundaries of a split.
2.  **Vector Embedding**: Using the `all-MiniLM-L6-v2` transformer, text chunks are converted into 384-dimensional vectors and stored in ChromaDB.
3.  **Hybrid Retrieval**: When a query is received, the system performs a **Top-K similarity search** and also keyword search for better technical term matching.
4.  **Inference**: The retrieved context is injected into a system prompt that enforces strict grounding, then processed via **Groq (Llama-3)** for sub-2-second inference.

---

## Key Features
* **High-Performance Inference**: Integration with Groq's LPU architecture for near-instantaneous responses.
* **Session-Based Memory**: A sliding-window buffer retains the last few exchanges, allowing for natural follow-up questions.
* **Robust API Design**: Built-in rate limiting using `slowapi` to prevent API abuse and manage operational costs.
* **Hybrid LLM Support**: Configured to switch between **Groq** (for speed) and **Gemini 2.5-Flash** (for complex reasoning) based on availability.

---

## Technical Stack
| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js, JavaScript, Tailwind CSS |
| **Backend** | Python, FastAPI |
| **LLM APIs** | Groq (Llama-3/Mixtral), Google Gemini |
| **Vector DB** | ChromaDB (Local Persistence) |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` |
| **Security** | SlowAPI (Rate Limiting), CORS Middleware |

---

## Use Cases
* **Interactive Resume**: HR can ask, *"Does Muzamil have experience with FastAPI?"* and receive a cited answer.
* **Project Deep-Dive**: Developers can query, *"How was the car rental system structured?"* to understand my coding patterns.
* **Technical FAQ**: Instant answers regarding my tech stack, availability, and engineering philosophy.

---

## Hallucination Control & Reliability
To ensure the bot remains professional and accurate:
* **Strict Context Guarding**: The LLM is instructed to answer "I don't know" if the answer isn't in the provided document chunks.
* **Low Temperature Setting**: Set to `0.3` to prioritize factual accuracy over creative "hallucinations."
* **Error Handling**: Graceful degradation—if the vector store is empty or the API is down, the system provides a clean, pre-defined fallback response.

---

## Getting Started

### Prerequisites
* Python 3.10+
* Node.js 18+
* API Keys: Groq or Google Gemini

### Local Installation
1. **Clone the Repo**
   ```bash
   git clone [(https://github.com/muzammilsharf/RagPortfolioChatbot.git)]
   cd portfolio-rag

   cd backend
2. **Create virtual Environment and install requirements**
   ```
   python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    # Create a .env file and add your GROQ_API_KEY or GEMINI_API_KEY
    uvicorn main:app --reload
  3. **Frontend Setup**
     ```
     cd frontend
     npm install
     npm run dev
  ---

## Evaluation & Metrics

To move beyond "vibes-based" development, I monitor the following RAG metrics to ensure production-grade reliability:
* **Faithfulness**: Validates that the answer is derived *solely* from the retrieved documents, eliminating external hallucinations.
* **Answer Relevance**: Measures how effectively the response addresses the user's specific intent.
* **Context Precision**: Evaluates whether the Top-K retrieved chunks actually contain the information needed to answer the query.

---

## Project Structure
A modular directory design to separate concerns between AI logic, API handling, and the frontend interface.

```text
├── backend/
│   ├── app/
│   │   ├── core/           # RAG Logic, LLM Wrappers & Prompt Templates
│   │   ├── api/            # FastAPI Routes & SSE Streaming Logic
│   │   ├── db/             # ChromaDB initialization & Vector Store management
│   │   └── utils/          # PDF Parsing, Text Splitting & Cleaning
│   ├── data/               # Source Documents (Resume, Project Deep-dives)
│   └── main.py             # FastAPI Entry Point
├── frontend/
│   ├── components/         # Chat UI, Markdown Renderers & Loading States
│   ├── hooks/              # Custom Hooks for SSE & State Management
│   └── pages/              # Next.js Routing & Layout
└── requirements.txt        # Backend Dependencies
```
---
## Future Roadmap

* **Multi-Agent Architecture:** Implementing a "Reasoning Agent" to verify the answer before displaying it.

* **Analytics Dashboard:** Tracking common queries to identify what recruiters care about most.

* **Voice Integration:** Allowing users to query the portfolio via speech-to-text.

---
## Contact & Connections

Muzamil – Software Engineering Student & AI Enthusiast
* **LinkedIn:** [M. Muzammil](https://www.linkedin.com/in/m-muzammil-/)
* **Email:** sharfmuzamil@gmail.com
