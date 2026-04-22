# Portfolio RAG Chatbot

A professional, production-ready Retrieval-Augmented Generation (RAG) system designed to serve as an intelligent interface for a software engineering portfolio. This system allows users to interact with my professional history, project details, and technical expertise through a grounded AI assistant.

## Key Features

* **Real-Time Streaming**: Implements Server-Sent Events (SSE) to stream text generation chunk-by-chunk for a low-latency user experience.
* **Grounded RAG Engine**: Utilizes semantic search with ChromaDB and HuggingFace embeddings to ensure responses are strictly based on my verified resume and project data.
* **High-Performance Inference**: Integrated with the Groq API (Llama-3/Mixtral) to achieve response times under 2 seconds.
* **Session-Based Memory**: Features a sliding-window memory approach to maintain conversation context within a single browser session.
* **Robust API Design**: Built with a decoupled FastAPI backend that manages rate-limiting, session handling, and document ingestion.

## Technical Stack

* **Frontend**: Next.js, JavaScript, CSS.
* **Backend**: Python, FastAPI
* **LLM API**: Groq (Llama-3 8B / Mixtral) & Gemini 2.5-Flash
* **Vector DB**: ChromaDB (Persistent local storage)
* **Embeddings**: HuggingFace `all-MiniLM-L6-v2`

## System Architecture

The system utilizes a microservices-oriented architecture to achieve low latency and zero-cost scalability.

1.  **Ingestion Phase**: PDFs are parsed and split into 250-token semantic chunks with overlap to maintain context.
2.  **Retrieval Phase**: User queries are vectorized and a Top-K similarity search is performed against the vector store.
3.  **Generation Phase**: Retrieved context is compiled into a prompt and sent to Groq or Gemini for real-time streaming back to the Portfolio UI.
