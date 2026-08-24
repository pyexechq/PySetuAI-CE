"use client";

import { useState } from "react";
import { Search, Copy } from "lucide-react";

interface StatusResponse {
  status: string;
  api_key?: string;
  mcp_config?: any;
}

export default function DeveloperPortalStatusPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [requestId, setRequestId] = useState("");

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !requestId) {
      setError("Please fill out all fields");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const res = await fetch(`/api/v1/mcp/portal/request-status/${requestId}?email=${encodeURIComponent(email)}`);
      
      if (res.ok) {
        const json = await res.json();
        setResult(json);
      } else if (res.status === 404) {
        setError("Request not found. Please check your Request ID.");
      } else if (res.status === 403) {
        setError("Email does not match the request.");
      } else {
        const err = await res.json();
        setError(err.detail || "An error occurred while fetching the status.");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch status.");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center">
          <Search className="mx-auto h-12 w-12 text-blue-600" />
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-gray-900">
            Check Request Status
          </h2>
          <p className="mt-2 text-lg text-gray-600">
            Enter your Email and Request ID to check approval status and retrieve your API key.
          </p>
        </div>

        <div className="bg-white shadow sm:rounded-lg overflow-hidden">
          <div className="px-4 py-5 sm:p-6">
            <form onSubmit={onSubmit} className="space-y-6">
              
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email Address
                </label>
                <div className="mt-1">
                  <input
                    type="email"
                    id="email"
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                    placeholder="developer@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="request_id" className="block text-sm font-medium text-gray-700">
                  Request ID
                </label>
                <div className="mt-1">
                  <input
                    type="text"
                    id="request_id"
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                    placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                    value={requestId}
                    onChange={(e) => setRequestId(e.target.value)}
                    required
                  />
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
                  {error}
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                >
                  {loading ? "Checking..." : "Check Status"}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="bg-white shadow sm:rounded-lg overflow-hidden border-t-4 border-blue-500">
            <div className="px-4 py-5 sm:p-6 space-y-6">
              
              <div>
                <h3 className="text-lg font-medium leading-6 text-gray-900">Status</h3>
                <div className="mt-2">
                  <span className={`inline-flex items-center rounded-full px-3 py-0.5 text-sm font-medium ${
                    result.status === 'approved' ? 'bg-green-100 text-green-800' :
                    result.status === 'rejected' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {result.status.toUpperCase()}
                  </span>
                </div>
              </div>

              {result.status === 'approved' && result.api_key && (
                <>
                  <div className="pt-4 border-t border-gray-200">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 flex justify-between items-center">
                      Your API Key
                      <button type="button" onClick={() => copyToClipboard(result.api_key!)} className="text-blue-600 hover:text-blue-500 flex items-center text-sm">
                        <Copy className="h-4 w-4 mr-1" /> Copy
                      </button>
                    </h3>
                    <div className="mt-2 p-3 bg-gray-50 rounded-md border break-all font-mono text-sm">
                      {result.api_key}
                    </div>
                    <p className="mt-2 text-sm text-gray-500">Keep this key secret. You will not be able to retrieve it again from the dashboard.</p>
                  </div>

                  <div className="pt-4 border-t border-gray-200">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 flex justify-between items-center">
                      Claude Desktop Configuration
                      <button type="button" onClick={() => copyToClipboard(JSON.stringify(result.mcp_config, null, 2))} className="text-blue-600 hover:text-blue-500 flex items-center text-sm">
                        <Copy className="h-4 w-4 mr-1" /> Copy JSON
                      </button>
                    </h3>
                    <p className="mt-1 text-sm text-gray-500">Add the following snippet to your `claude_desktop_config.json` file:</p>
                    <div className="mt-2 p-4 bg-gray-900 text-gray-100 rounded-md overflow-x-auto text-sm font-mono whitespace-pre">
                      {JSON.stringify(result.mcp_config, null, 2)}
                    </div>
                  </div>
                </>
              )}

            </div>
          </div>
        )}

      </div>
    </div>
  );
}
