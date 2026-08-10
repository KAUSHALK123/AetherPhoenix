import { useState, useRef, useEffect } from 'react';

type Message = {
  role: 'user' | 'planner';
  content: string;
  status?: string;
};

function App() {
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentStatus, setCurrentStatus] = useState<string>("idle");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;

    const userMessage = goal;
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setGoal("");

    setLoading(true);
    setError(null);
    setCurrentStatus("processing");

    try {
      const body: any = { goal: userMessage };
      if (sessionId && currentStatus === "clarifying") {
        body.session_id = sessionId;
      }

      const res = await fetch("http://localhost:8000/api/v1/planner/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      
      if (!res.ok) {
        throw new Error(`API Error: ${res.statusText}`);
      }
      
      const data = await res.json();
      
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      setCurrentStatus(data.status);
      setMessages(prev => [...prev, { 
        role: 'planner', 
        content: data.reply,
        status: data.status 
      }]);

      if (data.status === "ready" || data.status === "error") {
        setSessionId(null);
      }

    } catch (err: any) {
      setError(err.message || "An error occurred");
      setCurrentStatus("error");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([]);
    setSessionId(null);
    setCurrentStatus("idle");
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8 flex flex-col">
      <div className="max-w-4xl mx-auto w-full bg-white p-6 rounded-lg shadow-md flex-1 flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800">Planner Agent V1</h1>
          {messages.length > 0 && (
            <button 
              onClick={handleReset}
              className="text-sm bg-gray-200 hover:bg-gray-300 text-gray-700 px-3 py-1 rounded"
            >
              New Plan
            </button>
          )}
        </div>
        
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
            <p className="font-bold">Error</p>
            <p>{error}</p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto mb-4 bg-gray-50 border border-gray-200 rounded p-4 h-[600px]">
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 mt-20">
              <p>No plan started yet.</p>
              <p>Enter your goal below to begin.</p>
            </div>
          ) : (
            <div className="flex flex-col space-y-4">
              {messages.map((msg, index) => (
                <div 
                  key={index} 
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-[85%] p-4 rounded-lg shadow-sm ${
                      msg.role === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : msg.status === 'clarifying'
                          ? 'bg-yellow-50 border border-yellow-200 text-yellow-900'
                          : msg.status === 'error'
                            ? 'bg-red-50 border border-red-200 text-red-900'
                            : 'bg-white border border-gray-200'
                    }`}
                  >
                    {msg.role === 'planner' && msg.status === 'clarifying' && (
                      <h3 className="font-bold text-yellow-800 text-sm mb-1">Clarification Needed:</h3>
                    )}
                    {msg.role === 'planner' && msg.status === 'error' && (
                      <h3 className="font-bold text-red-800 text-sm mb-1">Planner Error:</h3>
                    )}
                    
                    {msg.role === 'planner' && msg.status === 'ready' ? (
                      <div>
                        <h3 className="font-bold text-green-700 text-sm mb-2">Generated Plan:</h3>
                        <pre className="text-xs bg-gray-800 text-green-400 p-3 rounded overflow-x-auto whitespace-pre-wrap">
                          {JSON.stringify(JSON.parse(msg.content), null, 2)}
                        </pre>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-200 animate-pulse h-10 w-24 rounded-lg"></div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
        
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input 
            type="text" 
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder={
              currentStatus === "clarifying" 
                ? "Answer clarification..." 
                : "Enter your goal (e.g. 'Create a presentation on AI')"
            } 
            className="flex-1 p-3 border border-gray-300 rounded focus:outline-none focus:border-blue-500 shadow-sm"
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={loading || !goal.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors"
          >
            {currentStatus === "clarifying" ? "Answer" : "Generate"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
