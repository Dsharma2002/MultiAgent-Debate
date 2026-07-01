import { useState, useEffect } from 'react';
import { API_URL } from '../utils/constants';

export default function ProposalInput({ onRun, isRunning }) {
  const [description, setDescription] = useState('');
  const [budget, setBudget] = useState(2000);
  const [overlap, setOverlap] = useState(0.5);
  const [scenarios, setScenarios] = useState([]);
  const [activeScenario, setActiveScenario] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/scenarios`)
      .then((r) => r.json())
      .then(setScenarios)
      .catch(() => {});
  }, []);

  const selectScenario = (scenario) => {
    setActiveScenario(scenario.id);
    setDescription(scenario.description);
    setBudget(scenario.budget);
  };

  const handleRun = () => {
    if (!description.trim()) return;
    const selected = scenarios.find((s) => s.id === activeScenario);
    const context = {
      description,
      budget_allocation: budget,
      context_overlap_ratio: overlap,
      complexity: selected?.complexity || 'medium',
      user_impact: selected?.user_impact || 'medium',
      effort: selected?.effort || 'medium',
      ...(selected?.database && { database: selected.database }),
      ...(selected?.scale_requirements && { scale_requirements: selected.scale_requirements }),
    };
    onRun(context);
  };

  return (
    <div className="proposal-section panel glass">
      <div className="panel-header">
        <span className="panel-title">📋 Proposal Input</span>
        <span className="panel-badge">Submit to run pipeline</span>
      </div>

      {/* Scenario chips */}
      <div className="scenario-chips">
        {scenarios.map((s) => (
          <button
            key={s.id}
            className={`scenario-chip ${activeScenario === s.id ? 'active' : ''}`}
            onClick={() => selectScenario(s)}
            disabled={isRunning}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Input group */}
      <div className="proposal-input-group">
        <textarea
          className="proposal-textarea"
          placeholder="Describe your proposal... or select a scenario above"
          value={description}
          onChange={(e) => {
            setDescription(e.target.value);
            setActiveScenario(null);
          }}
          disabled={isRunning}
          rows={3}
        />
        <div className="proposal-controls">
          <div className="budget-slider-group" style={{ display: 'flex', gap: 'var(--gap-lg)', flex: 1 }}>
            <div style={{ flex: 1 }}>
              <div className="budget-slider-label">
                <span>Budget</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-gold)' }}>
                  ${budget.toLocaleString()}
                </span>
              </div>
              <input
                type="range"
                className="budget-slider"
                min={100}
                max={5000}
                step={100}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                disabled={isRunning}
              />
            </div>
            
            <div style={{ flex: 1 }}>
              <div className="budget-slider-label">
                <span>Context Overlap Size</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                  {Math.round(overlap * 100)}%
                </span>
              </div>
              <input
                type="range"
                className="budget-slider"
                min={0.1}
                max={1.0}
                step={0.1}
                value={overlap}
                onChange={(e) => setOverlap(Number(e.target.value))}
                disabled={isRunning}
                style={{
                  '--accent': 'var(--accent-cyan)',
                }}
              />
            </div>
          </div>
          <button
            className={`run-button ${isRunning ? 'running' : ''}`}
            onClick={handleRun}
            disabled={isRunning || !description.trim()}
          >
            {isRunning ? '⟳ Running Pipeline…' : '▶ Run Pipeline'}
          </button>
        </div>
      </div>
    </div>
  );
}
