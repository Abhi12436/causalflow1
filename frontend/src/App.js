import { useState, useEffect } from 'react';
import axios from 'axios';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

const API = 'http://localhost:8000/api/v1';

export default function App() {

  const [summary, setSummary] = useState(null);

  const [trend, setTrend] = useState([]);

  const [projectedTrend, setProjectedTrend] = useState([]);

  const [counterfactual, setCounterfactual] = useState(null);

  const [activeTab, setActiveTab] = useState('overview');

  const [question, setQuestion] = useState('');

  const [aiResponse, setAiResponse] = useState('');

  const [cfForm, setCfForm] = useState({
    intervention: 'Increase warehouse workers by 10%',
    effect_size: 0.02
  });

  // =====================================================
  // LOAD DATA
  // =====================================================

  useEffect(() => {

    axios
      .get(`${API}/analytics/summary`)
      .then((response) => {
        setSummary(response.data);
      });

    axios
      .get(`${API}/analytics/monthly-trend`)
      .then((response) => {
        setTrend(response.data);
      });

  }, []);

  // =====================================================
  // RUN COUNTERFACTUAL
  // =====================================================

  const runCounterfactual = async () => {

    try {

      const response = await axios.post(
        `${API}/causal/counterfactual`,
        cfForm
      );

      setCounterfactual(response.data);

      const simulated = trend.map((item) => {

        const reducedOrders = Math.round(
          response.data.late_orders_prevented / 12
        );

        return {
          ...item,
          projected_orders: Math.max(
            0,
            item.order_count - reducedOrders
          )
        };

      });

      setProjectedTrend(simulated);

    } catch (error) {

      console.error(error);

    }
  };

  // =====================================================
  // ASK AI
  // =====================================================

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

      setAiResponse('Error getting AI response');

    }
  };

  // =====================================================
  // UI
  // =====================================================

  return (

    <div
      style={{
        backgroundColor: '#0f172a',
        minHeight: '100vh',
        padding: '20px',
        color: 'white',
        fontFamily: 'Arial'
      }}
    >

      {/* HEADER */}

      <h1
        style={{
          color: '#6366f1',
          marginBottom: '30px'
        }}
      >
        ⚡ CausalFlow Dashboard
      </h1>

      {/* KPI */}

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

      {/* NAVIGATION */}

      <div style={{ marginBottom: '20px' }}>

        <button
          onClick={() => setActiveTab('overview')}
          style={{
            marginRight: '10px',
            padding: '10px 20px'
          }}
        >
          Overview
        </button>

        <button
          onClick={() => setActiveTab('causal')}
          style={{
            padding: '10px 20px'
          }}
        >
          Causal Analysis
        </button>

      </div>

      {/* OVERVIEW */}

      {activeTab === 'overview' && (

        <div
          style={{
            background: '#1e293b',
            padding: '35px',
            borderRadius: '20px',
            overflowX: 'auto'
          }}
        >

          <h2>Historical Order Trend</h2>

          <div
            style={{
              display: 'flex',
              justifyContent: 'center'
            }}
          >

            <LineChart
              width={1200}
              height={400}
              data={trend}
            >

              <CartesianGrid stroke="#444" />

              <XAxis dataKey="month" />

              <YAxis />

              <Tooltip />

              <Legend />

              <Line
                type="monotone"
                dataKey="order_count"
                stroke="#60a5fa"
                strokeWidth={2}
                dot={true}
                name="Historical Orders"
              />

            </LineChart>

          </div>

        </div>
      )}

      {/* CAUSAL */}

      {activeTab === 'causal' && (

        <div
          style={{
            background: '#1e293b',
            padding: '20px',
            borderRadius: '12px'
          }}
        >

          <h2>AI What-If Simulator</h2>

          <input
            value={cfForm.intervention}
            onChange={(e) =>
              setCfForm({
                ...cfForm,
                intervention: e.target.value
              })
            }
            style={{
              width: '100%',
              padding: '12px',
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
              width: '100%',
              padding: '12px',
              marginBottom: '10px'
            }}
          />

          <button
            onClick={runCounterfactual}
            style={{
              padding: '12px 20px'
            }}
          >
            Run Simulation
          </button>

          {/* RESULT */}

          {counterfactual && (

            <div
              style={{
                marginTop: '20px',
                background: '#0f172a',
                padding: '20px',
                borderRadius: '12px'
              }}
            >

              <h3>Simulation Result</h3>

              <p>
                Current Late Rate:
                {' '}
                {counterfactual.current_late_rate_pct}%
              </p>

              <p>
                Predicted Late Rate:
                {' '}
                {counterfactual.new_late_rate_pct}%
              </p>

              <p>
                Orders Saved:
                {' '}
                {counterfactual.late_orders_prevented}
              </p>

              <p>
                Estimated Impact:
                {' '}
                {counterfactual.estimated_impact_pct}%
              </p>

            </div>
          )}

          {/* AI ANALYSIS */}

          {counterfactual?.ai_reasoning && (

            <div
              style={{
                marginTop: '20px',
                background: '#111827',
                padding: '20px',
                borderRadius: '12px'
              }}
            >

              <h3>AI Operational Analysis</h3>

              <p>{counterfactual.ai_reasoning}</p>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4,1fr)',
                  gap: '15px',
                  marginTop: '20px'
                }}
              >

                <InsightCard
                  title="Efficiency Gain"
                  value={`${counterfactual.estimated_impact_pct}%`}
                  color="#22c55e"
                />

                <InsightCard
                  title="Risk Level"
                  value={
                    counterfactual.new_late_rate_pct > 10
                      ? 'Medium'
                      : 'Low'
                  }
                  color="#ef4444"
                />

                <InsightCard
                  title="Orders Saved"
                  value={counterfactual.late_orders_prevented}
                  color="#eab308"
                />

                <InsightCard
                  title="Recommendation"
                  value="Optimize weekend staffing"
                  color="#3b82f6"
                />

              </div>

            </div>
          )}

          {/* PROJECTED GRAPH */}

          {counterfactual && (

            <div
              style={{
                marginTop: '30px',
                background: '#111827',
                padding: '20px',
                borderRadius: '12px'
              }}
            >

              <h2>Projected Operational Impact</h2>

              <LineChart
                width={1100}
                height={400}
                data={projectedTrend}
              >

                <CartesianGrid stroke="#444" />

                <XAxis dataKey="month" />

                <YAxis />

                <Tooltip />

                <Legend />

                <Line
                  type="monotone"
                  dataKey="order_count"
                  stroke="#06b6d4"
                  strokeWidth={1}
                  dot={true}
                  name="Historical Orders"
                />

                <Line
                  type="monotone"
                  dataKey="projected_orders"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={true}
                  name="Projected Improvement"
                />

              </LineChart>

            </div>
          )}

        </div>
      )}

      {/* AI ASSISTANT */}

      <div
        style={{
          marginTop: '30px',
          background: '#1e293b',
          padding: '20px',
          borderRadius: '12px'
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
            marginBottom: '10px'
          }}
        />

        <button
          onClick={askAI}
          style={{
            padding: '12px 20px'
          }}
        >
          Ask AI
        </button>

        <div
          style={{
            marginTop: '20px',
            background: '#0f172a',
            padding: '15px',
            borderRadius: '10px'
          }}
        >

          {aiResponse}

        </div>

      </div>

    </div>
  );
}

// =====================================================
// CARD
// =====================================================

function Card({ title, value }) {

  return (

    <div
      style={{
        background: '#1e293b',
        padding: '20px',
        borderRadius: '12px'
      }}
    >

      <p>{title}</p>

      <h2>{value}</h2>

    </div>
  );
}

// =====================================================
// INSIGHT CARD
// =====================================================

function InsightCard({
  title,
  value,
  color
}) {

  return (

    <div
      style={{
        background: '#0f172a',
        padding: '20px',
        borderRadius: '14px',
        borderLeft: `5px solid ${color}`
      }}
    >

      <p
        style={{
          color: '#94a3b8',
          fontSize: '14px'
        }}
      >
        {title}
      </p>

      <h3
        style={{
          color: 'white',
          marginTop: '10px'
        }}
      >
        {value}
      </h3>

    </div>
  );
}