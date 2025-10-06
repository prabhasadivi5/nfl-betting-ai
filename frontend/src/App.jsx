import React, { useState } from 'react';
import { Send, BarChart3, MessageSquare, Info, Home } from 'lucide-react';

const NFLPredictorSite = () => {
  const [activeTab, setActiveTab] = useState('home');
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I can predict NFL game scores. Try asking me something like "Predict WSH vs LAC" or "What do you think about the Bills vs Chiefs game?"' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const API_BASE_URL = 'http://localhost:5001/api';

  const getPrediction = async (teamA, teamB) => {
    const response = await fetch(`${API_BASE_URL}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ teamA, teamB })
    });
    
    if (!response.ok) {
      throw new Error('Failed to get prediction');
    }
    
    return await response.json();
  };

  const getChatResponse = async (message) => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    if (!response.ok) {
      throw new Error('Failed to get response');
    }
    
    const data = await response.json();
    return data.response;
  };

  const parseGameRequest = (message) => {
    const text = message.toLowerCase();
    
    const vsPattern = /(\w+)\s+(?:vs|versus|@|at)\s+(\w+)/i;
    const spacePattern = /^(\w{2,3})\s+(\w{2,3})$/i;
    
    let match = text.match(vsPattern);
    if (match) {
      return { teamA: match[1], teamB: match[2] };
    }
    
    match = text.match(spacePattern);
    if (match) {
      return { teamA: match[1], teamB: match[2] };
    }
    
    return null;
  };

  const formatPredictionResponse = (pred) => {
    if (!pred || pred.error) {
      return pred?.error || "I couldn't find that game. Make sure you're using valid team abbreviations like WSH, LAC, BUF, KC, etc.";
    }

    const marginA = pred.pred_teamA - pred.pred_teamB;
    let response = `**Prediction: ${pred.teamA} vs ${pred.teamB}**\n\n`;
    response += `📊 **Model Prediction:**\n`;
    response += `• ${pred.teamA}: ${pred.pred_teamA.toFixed(1)} points\n`;
    response += `• ${pred.teamB}: ${pred.pred_teamB.toFixed(1)} points\n`;
    response += `• Total: ${pred.pred_total.toFixed(1)} points\n`;
    response += `• Margin: ${pred.teamA} ${marginA > 0 ? '+' : ''}${marginA.toFixed(1)}\n\n`;

    if (pred.odds) {
      const isTeamAHome = pred.odds.home_team.toLowerCase().includes(pred.teamA.toLowerCase());
      const vegasMarginA = isTeamAHome ? pred.odds.spread : -pred.odds.spread;
      const spreadEdge = marginA - vegasMarginA;
      const totalEdge = pred.pred_total - pred.odds.total;

      response += `📈 **Vegas Lines:**\n`;
      response += `• Spread: ${pred.odds.spread} (${pred.odds.home_team})\n`;
      response += `• Total: ${pred.odds.total}\n\n`;

      response += `💡 **Betting Analysis:**\n`;
      
      if (Math.abs(spreadEdge) >= 3) {
        const favoredTeam = spreadEdge > 0 ? pred.teamA : pred.teamB;
        response += `• **SPREAD VALUE**: Model likes ${favoredTeam} (${Math.abs(spreadEdge).toFixed(1)} pt edge)\n`;
      } else {
        response += `• Spread: No significant edge (<3 pts)\n`;
      }

      if (Math.abs(totalEdge) >= 3) {
        const overUnder = totalEdge > 0 ? 'OVER' : 'UNDER';
        response += `• **TOTAL VALUE**: Model likes ${overUnder} ${pred.odds.total} (${Math.abs(totalEdge).toFixed(1)} pt edge)\n`;
      } else {
        response += `• Total: No significant edge (<3 pts)\n`;
      }
    } else {
      response += `⚠️ No betting odds available for this matchup.\n`;
    }

    return response;
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const gameRequest = parseGameRequest(input);
      
      if (gameRequest) {
        const prediction = await getPrediction(gameRequest.teamA, gameRequest.teamB);
        const response = formatPredictionResponse(prediction);
        setMessages(prev => [...prev, { role: 'assistant', content: response }]);
      } else {
        const response = await getChatResponse(input);
        setMessages(prev => [...prev, { role: 'assistant', content: response }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please make sure the backend is running on http://localhost:5000' 
      }]);
    }

    setIsLoading(false);
  };

  const renderMessage = (msg, idx) => {
    const isUser = msg.role === 'user';
    return (
      <div key={idx} style={{ 
        display: 'flex', 
        justifyContent: isUser ? 'flex-end' : 'flex-start', 
        marginBottom: '16px' 
      }}>
        <div style={{
          maxWidth: '700px',
          padding: '12px 16px',
          borderRadius: '8px',
          backgroundColor: isUser ? '#2563eb' : '#f3f4f6',
          color: isUser ? 'white' : '#111827'
        }}>
          <div style={{ whiteSpace: 'pre-line', fontSize: '14px' }}>
            {msg.content.split('\n').map((line, i) => {
              if (line.startsWith('**') && line.endsWith('**')) {
                return <div key={i} style={{ fontWeight: 'bold', marginTop: '8px', marginBottom: '4px' }}>{line.slice(2, -2)}</div>;
              }
              if (line.startsWith('•')) {
                return <div key={i} style={{ marginLeft: '20px' }}>{line}</div>;
              }
              return <div key={i}>{line}</div>;
            })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(to bottom right, #0f172a, #1e3a8a, #0f172a)' }}>
      {/* Header */}
      <div style={{ backgroundColor: '#1e293b', borderBottom: '1px solid #475569', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <BarChart3 style={{ width: '32px', height: '32px', color: '#60a5fa' }} />
            <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: 'white', margin: 0 }}>NFL Score Predictor</h1>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ backgroundColor: '#1e293b', borderBottom: '1px solid #475569' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px', display: 'flex', gap: '4px' }}>
          {[
            { id: 'home', label: 'Home', icon: Home },
            { id: 'how-to', label: 'How to Use', icon: MessageSquare },
            { id: 'about', label: 'About', icon: Info }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 24px',
                borderBottom: activeTab === tab.id ? '2px solid #60a5fa' : '2px solid transparent',
                color: activeTab === tab.id ? '#60a5fa' : '#9ca3af',
                background: 'none',
                border: 'none',
                borderTop: 'none',
                borderLeft: 'none',
                borderRight: 'none',
                cursor: 'pointer',
                fontWeight: '500',
                fontSize: '14px'
              }}
            >
              <tab.icon style={{ width: '16px', height: '16px' }} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
        {activeTab === 'home' && (
          <div style={{ backgroundColor: '#1e293b', borderRadius: '8px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', overflow: 'hidden' }}>
            {/* Chat Messages */}
            <div style={{ height: '500px', overflowY: 'auto', padding: '24px' }}>
              {messages.map((msg, idx) => renderMessage(msg, idx))}
              {isLoading && (
                <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                  <div style={{ backgroundColor: '#f3f4f6', padding: '12px 16px', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <div style={{ width: '8px', height: '8px', backgroundColor: '#6b7280', borderRadius: '50%', animation: 'bounce 1s infinite' }}></div>
                      <div style={{ width: '8px', height: '8px', backgroundColor: '#6b7280', borderRadius: '50%', animation: 'bounce 1s infinite', animationDelay: '0.1s' }}></div>
                      <div style={{ width: '8px', height: '8px', backgroundColor: '#6b7280', borderRadius: '50%', animation: 'bounce 1s infinite', animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div style={{ borderTop: '1px solid #475569', padding: '16px', backgroundColor: '#1e293b' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSend()}
                  placeholder="Ask me to predict a game... (e.g., 'Predict WSH vs LAC')"
                  style={{
                    flex: 1,
                    padding: '12px 16px',
                    backgroundColor: '#334155',
                    border: '1px solid #475569',
                    borderRadius: '8px',
                    color: 'white',
                    outline: 'none',
                    fontSize: '14px'
                  }}
                  disabled={isLoading}
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading}
                  style={{
                    padding: '12px 24px',
                    backgroundColor: isLoading ? '#4b5563' : '#2563eb',
                    color: 'white',
                    borderRadius: '8px',
                    border: 'none',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '14px',
                    fontWeight: '500'
                  }}
                >
                  <Send style={{ width: '20px', height: '20px' }} />
                  <span>Send</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'how-to' && (
          <div style={{ backgroundColor: '#1e293b', borderRadius: '8px', padding: '32px', color: '#d1d5db' }}>
            <h2 style={{ fontSize: '30px', fontWeight: 'bold', color: 'white', marginBottom: '24px' }}>How to Use</h2>
            <div style={{ lineHeight: '1.8' }}>
              <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#60a5fa', marginTop: '20px', marginBottom: '12px' }}>Predict a Game</h3>
              <p>Try: "Predict WSH vs LAC", "Bills at Chiefs", or just "WSH LAC"</p>
              
              <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#60a5fa', marginTop: '20px', marginBottom: '12px' }}>Understanding Results</h3>
              <p><strong>Model Prediction:</strong> AI-generated score forecast</p>
              <p><strong>Vegas Lines:</strong> Current betting odds</p>
              <p><strong>Betting Analysis:</strong> Value bets (3+ point edges)</p>
            </div>
          </div>
        )}

        {activeTab === 'about' && (
          <div style={{ backgroundColor: '#1e293b', borderRadius: '8px', padding: '32px', color: '#d1d5db' }}>
            <h2 style={{ fontSize: '30px', fontWeight: 'bold', color: 'white', marginBottom: '24px' }}>About</h2>
            <div style={{ lineHeight: '1.8' }}>
              <p>NFL Score Predictor uses XGBoost machine learning models trained on historical game data, team statistics, and performance metrics.</p>
              <p style={{ marginTop: '16px' }}><strong style={{ color: 'white' }}>Disclaimer:</strong> For entertainment purposes only. Gamble responsibly.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NFLPredictorSite;