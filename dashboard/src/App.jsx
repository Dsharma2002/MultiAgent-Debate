import { useCallback, useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { usePipeline } from './hooks/usePipeline';
import StatsBar from './components/StatsBar';
import AgentConstellation from './components/AgentConstellation';
import PipelineTimeline from './components/PipelineTimeline';
import VerificationGate from './components/VerificationGate';
import LedgerExplorer from './components/LedgerExplorer';
import ConstraintDashboard from './components/ConstraintDashboard';
import ProposalInput from './components/ProposalInput';
import DetailInspector from './components/DetailInspector';
import EventLog from './components/EventLog';

export default function App() {
  const { connect, send } = useWebSocket();
  const { state, handleEvent, reset } = usePipeline();
  const [selectedEntry, setSelectedEntry] = useState(null);

  const handleRun = useCallback(
    (context) => {
      reset();
      setSelectedEntry(null);
      const ws = connect(handleEvent);
      ws.onopen = () => {
        ws.send(JSON.stringify(context));
      };
    },
    [connect, handleEvent, reset]
  );

  const isRunning = state.status === 'running';

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <h1>Multi-Agent Debate</h1>
          <span className="subtitle">Decentralized Verification Pipeline</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-md)' }}>
          {state.status === 'complete' && (
            <button
              className="scenario-chip active"
              onClick={() => {
                reset();
                setSelectedEntry(null);
              }}
              style={{ cursor: 'pointer' }}
            >
              ↺ New Run
            </button>
          )}
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: isRunning ? 'var(--status-active)' : state.status === 'complete' ? 'var(--status-success)' : 'var(--text-tertiary)',
            animation: isRunning ? 'pulse-node 1.5s ease infinite' : 'none',
          }} />
        </div>
      </div>

      {/* Stats */}
      <StatsBar state={state} />

      {/* Proposal Input */}
      <ProposalInput onRun={handleRun} isRunning={isRunning} />

      {/* Agent Constellation */}
      <AgentConstellation
        agents={state.agents}
        activeAgentIndex={state.activeAgentIndex}
        ledgerEntries={state.ledgerEntries}
      />

      {/* Pipeline Timeline - full width */}
      <div style={{ gridColumn: '1 / -1' }}>
        <PipelineTimeline agents={state.agents} />
      </div>

      {/* Left column: Verification Gate + Constraints */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-md)' }}>
        <VerificationGate
          gateChecks={state.gateChecks}
          peerAudits={state.peerAudits}
          activeAgentIndex={state.activeAgentIndex}
        />
        <ConstraintDashboard
          budgetUsed={state.budgetUsed}
          gateChecks={state.gateChecks}
          activeAgentIndex={state.activeAgentIndex}
        />
      </div>

      {/* Right column: Ledger Explorer */}
      <LedgerExplorer
        ledgerEntries={state.ledgerEntries}
        selectedEntry={selectedEntry}
        onSelectEntry={setSelectedEntry}
      />

      {/* Details Inspector - full width when active */}
      {selectedEntry && (
        <DetailInspector
          entry={selectedEntry}
          onClose={() => setSelectedEntry(null)}
        />
      )}

      {/* Event Log - full width */}
      <EventLog events={state.events} />
    </div>
  );
}
