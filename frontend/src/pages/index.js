import Chat from "@/components/Chat";

export default function Home() {
  return (
    <main className="page">
      <div className="card">
        <header className="header">
          <div>
            <div className="title">Muzammil's Portfolio Assistant</div>
            <div className="subtitle">Ask anything about my resume, projects, and experiences.</div>
          </div>
        </header>
        <Chat />
      </div>
    </main>
  );
}