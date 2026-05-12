import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

import axios from 'axios';

const API = 'http://localhost:8000/api/v1';

export default function App() {

  const [summary, setSummary] = useState(null);
  const [trend, setTrend] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  const [counterfactual, setCounterfactual] = useState(null);

  const [cfForm, setCfForm] = useState({
    intervention: 'Priority shipping program',
    effect_size: 0.02
  });

  const [question, setQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState('');

  useEffect(() => {

    axios
      .get(`${API}/analytics/summary`)
      .then(r => setSummary(r.data));

    axios
      .get(`${API}/analytics/monthly-trend`)
      .then(r => setTrend(r.data));

  }, []);

  const runCounterfactual = async () => {

    const result = await axios.post(
      `${API}/causal/counterfactual`,
      cfForm
    );

    setCounterfactual(result.data);
  };

  const askAI = async () => {

    try {

      const response = await axios.post(
        `${API}/query/natural-language`,
        {
          question: question
        }
      );

      setAiResponse(response.data.answer);

    } catch (error) {

      console.error(error);

      setAiResponse(
        'Error getting AI response'
      );
    }
  };

  return (

    <div
      style={{
        fontFamily: 'Arial',
        backgroundColor: '#0f0f1a',
        minHeight: '100vh',
        color: 'white',
        padding: '20px'
      }}
    >

      <h1 style={{ color: '#6366f1' }}>
        ⚡ CausalFlow Dashboard
      </h1>

      {summary && (

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4,1fr)',
            gap: '15px',
            marginBottom: '30px'
          }}
        >

          <Card
            title="Total Orders"
            value={summary.total_orders}
          />

          <Card
            title="Avg Delivery Days"
            value={summary.avg_delivery_days}
          />

          <Card
            title="Late Orders"
            value={summary.late_orders}
          />

          <Card
            title="Late Rate"
            value={`${summary.late_rate_pct}%`}
          />

        </div>
      )}

      <div style={{ marginBottom: '20px' }}>

        <button
          onClick={() => setActiveTab('overview')}
          style={{ marginRight: '10px' }}
        >
          Overview
        </button>

        <button
          onClick={() => setActiveTab('causal')}
        >
          Causal Analysis
        </button>

      </div>

      {activeTab === 'overview' && (

        <div
          style={{
            background: '#1e1e2e',
            padding: '20px',
            borderRadius: '12px'
          }}
        >

          <h2>Monthly Order Trend</h2>

          <ResponsiveContainer
            width="100%"
            height={300}
          >

            <LineChart data={trend}>

              <CartesianGrid
                strokeDasharray="3 3"
              />

              <XAxis dataKey="month" />

              <YAxis />

              <Tooltip />
              <Line type="monotone" dataKey="orders" stroke="#8884d8" />

              <Line
                type="monotone"
                dataKey="order_count"
                stroke="#6366f1"
              />

            </LineChart>

          </ResponsiveContainer>

        </div>
      )}

      {activeTab === 'causal' && (

        <div
          style={{
            background: '#1e1e2e',
            padding: '20px',
            borderRadius: '12px'
          }}
        >

          <h2>What-If Simulator</h2>

          <input
            value={cfForm.intervention}
            onChange={(e) =>
              setCfForm({
                ...cfForm,
                intervention: e.target.value
              })
            }
            style={{
              padding: '10px',
              width: '100%',
              marginBottom: '10px'
            }}
          />

          <input
            type="number"
            step="0.01"
            value={cfForm.effect_size}
            onChange={(e) =>
              setCfForm({
                ...cfForm,
                effect_size: parseFloat(e.target.value)
              })
            }
            style={{
              padding: '10px',
              width: '100%',
              marginBottom: '10px'
            }}
          />

          <button
            onClick={runCounterfactual}
          >
            Run Simulation
          </button>

          {counterfactual && (

            <div
              style={{
                marginTop: '20px',
                background: '#0f172a',
                padding: '20px',
                borderRadius: '12px'
              }}
            >

              <h3>
                {counterfactual.intervention}
              </h3>

              <p>
                Current Late Rate:
                {' '}
                {counterfactual.current_late_rate_pct}%
              </p>

              <p>
                New Late Rate:
                {' '}
                {counterfactual.new_late_rate_pct}%
              </p>

              <p>
                Orders Saved:
                {' '}
                {counterfactual.late_orders_prevented}
              </p>

            </div>
          )}

        </div>
      )}

      <div
        style={{
          marginTop: '30px',
          padding: '20px',
          background: '#1e293b',
          borderRadius: '10px'
        }}
      >

        <h2>AI Business Assistant</h2>

        <input
          type="text"
          placeholder="Ask business questions..."
          value={question}
          onChange={(e) =>
            setQuestion(e.target.value)
          }
          style={{
            width: '100%',
            padding: '12px',
            marginTop: '10px'
          }}
        />

        <button
          onClick={askAI}
          style={{
            marginTop: '10px',
            padding: '10px 20px',
            cursor: 'pointer'
          }}
        >
          Ask AI
        </button>

        <div
          style={{
            marginTop: '20px',
            background: '#0f172a',
            padding: '15px',
            borderRadius: '8px'
          }}
        >

          {aiResponse}

        </div>

      </div>

    </div>
  );
}

function Card({ title, value }) {

  return (

    <div
      style={{
        background: '#1e1e2e',
        padding: '20px',
        borderRadius: '12px'
      }}
    >

      <p>{title}</p>

      <h2>{value}</h2>

    </div>
  );
}