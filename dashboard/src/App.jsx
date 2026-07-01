import { useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { usePipeline } from './hooks/usePipeline';
import DebateArena from './components/DebateArena';
import DebateSidebar from './components/DebateSidebar';

export default function App() {
  const { connect, send } = useWebSocket();
  const { state, handleEvent, reset } = usePipeline();

  const handleRun = useCallback(
    (context) => {
      reset();
      const ws = connect(handleEvent);
      ws.onopen = () => {
        ws.send(JSON.stringify(context));
      };
    },
    [connect, handleEvent, reset]
  );

  const isRunning = state.status === 'running';
  const totalCommitted = state.agents.filter(a => a.status === 'success').length;

  return (
    <div className="dashboard" style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--bg-primary)' }}>
      {/* Header */}
      <div className="dashboard-header" style={{ flexShrink: 0, borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '12px', paddingTop: '12px' }}>
        <div>
          <h1 style={{ letterSpacing: '-0.03em', fontWeight: 600, color: 'var(--text-primary)' }}>Multi-Agent Debate</h1>
          <span className="subtitle" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
            [MAD_CONCIERGE_DAEMON::ONLINE // RTT_LATENCY: 14MS // INTEGRITY_CHECK: PASS]
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-md)' }}>
          {state.status === 'complete' && (
            <button
              className="scenario-chip active"
              onClick={() => reset()}
              style={{ cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}
            >
              ↺ RESET_ARENA
            </button>
          )}
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: isRunning ? 'var(--accent-magenta)' : state.status === 'complete' ? 'var(--status-success)' : 'var(--text-tertiary)',
            animation: isRunning ? 'pulse-node 1.5s ease infinite' : 'none',
            boxShadow: isRunning ? '0 0 10px var(--accent-magenta)' : 'none'
          }} />
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ display: 'flex', flex: 1, gap: 'var(--gap-xl)', padding: 'var(--gap-xl)', overflow: 'hidden' }}>
        
        {/* Left: Debate Feed (Scrollable) */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '1rem', borderRight: '1px solid var(--glass-border)' }}>
          <DebateArena feed={state.debateFeed} />
        </div>

        {/* Right: Sidebar Controls & Ledger */}
        <DebateSidebar 
          isRunning={isRunning} 
          onRun={handleRun}
          totalCommitted={totalCommitted}
          chainValid={state.chainValid}
          budgetUsed={state.budgetUsed}
        />
        
      </div>
    </div>
  );
}
