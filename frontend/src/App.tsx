import { useState } from 'react';

function App() {
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch("http://localhost:8000/api/v1/planner/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal })
      });
      
      if (!res.ok) {
        throw new Error(`API Error: ${res.statusText}`);
      }
      
      const data = await res.json();
      setResponse(data);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-3xl mx-auto bg-white p-6 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-4 text-center">Planner Agent V1</h1>
        
        <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
          <input 
            type="text" 
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Enter your goal (e.g. 'Create a presentation on AI')" 
            className="flex-1 p-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Planning..." : "Generate Plan"}
          </button>
        </form>

        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-6" role="alert">
            <p className="font-bold">Error</p>
            <p>{error}</p>
          </div>
        )}

        {response && (
          <div className="bg-gray-50 p-4 rounded border border-gray-200 overflow-auto max-h-[600px]">
            <h2 className="text-lg font-semibold mb-2">
              Status: <span className="text-blue-600">{response.status}</span>
            </h2>
            
            {response.status === "clarifying" && (
              <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded">
                <h3 className="font-bold text-yellow-800">Clarification Needed:</h3>
                <p className="text-yellow-900 mt-1">{response.reply}</p>
              </div>
            )}
            
            {response.status === "ready" && (
              <div>
                <h3 className="font-bold text-green-700 mb-2">Generated Plan:</h3>
                <pre className="text-sm bg-gray-800 text-green-400 p-4 rounded overflow-x-auto">
                  {JSON.stringify(JSON.parse(response.reply), null, 2)}
                </pre>
              </div>
            )}
            
            {response.status === "error" && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded">
                <h3 className="font-bold text-red-800">Planner Error:</h3>
                <p className="text-red-900 mt-1">{response.reply}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
