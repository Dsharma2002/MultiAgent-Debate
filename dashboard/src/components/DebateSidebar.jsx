import { useState } from 'react';

export default function DebateSidebar({ isRunning, onRun, totalCommitted, chainValid, budgetUsed }) {
  const [budget] = useState(5000); // Fixed budget allocation passed to backend
  const [overlap, setOverlap] = useState(20);
  const [topic, setTopic] = useState("");

  const handleStart = () => {
    onRun({
      proposal_id: crypto.randomUUID(),
      description: topic,
      budget_allocation: budget,
      context_overlap_ratio: overlap / 100,
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-lg)', width: '340px', flexShrink: 0 }}>
      
      {/* IDE Style Prompt Input */}
      <div className="console-card" style={{ display: 'flex', flexDirection: 'column' }}>
        
        {/* Editor File Tab Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255,255,255,0.02)',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          padding: '6px 12px',
          borderTopLeftRadius: 'inherit',
          borderTopRightRadius: 'inherit'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.65rem' }}>📄</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>
              PROPOSAL_DRAFT.md
            </span>
          </div>
          <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
            UTF-8
          </span>
        </div>

        {/* Editor Content Area */}
        <div style={{ padding: 'var(--gap-md)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-md)' }}>
          <div style={{ display: 'flex', gap: 'var(--gap-sm)' }}>
            {/* Line numbers mock for IDE feel */}
            <div style={{ 
              fontFamily: 'var(--font-mono)', 
              fontSize: '0.75rem', 
              color: 'var(--text-tertiary)', 
              textAlign: 'right', 
              userSelect: 'none',
              paddingRight: '6px',
              borderRight: '1px solid rgba(255,255,255,0.02)'
            }}>
              <div>1</div>
              <div>2</div>
              <div>3</div>
              <div>4</div>
              <div>5</div>
            </div>
            
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={isRunning}
              placeholder="Describe your proposal or innovative concept to initiate the multi-agent debate (e.g., policy outline, tech stack trade-offs, space mission logistics)..."
              style={{
                flex: 1,
                minHeight: '110px',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                padding: '0',
                fontSize: '0.8rem',
                lineHeight: '1.5',
                resize: 'none',
                fontFamily: 'inherit',
                outline: 'none'
              }}
            />
          </div>

          {/* Context Overlap Hardware Slider */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              <span>CONTEXT_OVERLAP</span>
              <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{overlap}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              step="10"
              value={overlap}
              onChange={(e) => setOverlap(Number(e.target.value))}
              disabled={isRunning}
              className="budget-slider"
            />
          </div>

          <button
            onClick={handleStart}
            disabled={isRunning || !topic.trim()}
            style={{
              marginTop: '4px',
              background: isRunning ? 'rgba(255,255,255,0.02)' : (topic.trim() ? '#f4f4f5' : 'rgba(255,255,255,0.04)'),
              color: isRunning ? 'var(--text-tertiary)' : (topic.trim() ? '#09090b' : 'var(--text-tertiary)'),
              border: 'none',
              padding: '10px',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-sans)',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: isRunning || !topic.trim() ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s var(--ease-out)',
              textAlign: 'center',
              textTransform: 'uppercase',
              letterSpacing: '0.02em'
            }}
          >
            {isRunning ? 'Executing Consensus…' : 'Start Consensus'}
          </button>
        </div>
      </div>

      {/* Cryptographic Block Explorer Ledger */}
      <div className="console-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="terminal-header">
          <span style={{ display: 'inline-block', width: '5px', height: '5px', borderRadius: '50%', background: 'var(--status-success)' }} />
          <span>LEDGER_BLOCK_EXPLORER // v0.1.0</span>
        </div>
        
        <div style={{ padding: 'var(--gap-md)', display: 'flex', flexDirection: 'column', gap: '14px', flex: 1 }}>
          
          {/* Blocks Committed */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>BLOCKS_COMMITTED</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
              {totalCommitted} / 11
            </span>
          </div>

          {/* Chain Integrity */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>CHAIN_INTEGRITY</span>
            <span style={{ 
              fontSize: '0.7rem', 
              fontWeight: 600, 
              fontFamily: 'var(--font-mono)', 
              color: chainValid ? 'var(--status-success)' : 'var(--status-error)',
              background: chainValid ? 'rgba(52, 211, 153, 0.08)' : 'rgba(251, 113, 133, 0.08)',
              padding: '2px 8px',
              borderRadius: '4px',
              border: `1px solid ${chainValid ? 'rgba(52, 211, 153, 0.15)' : 'rgba(251, 113, 133, 0.15)'}`
            }}>
              {chainValid ? 'VERIFIED' : 'COMPROMISED'}
            </span>
          </div>

          {/* Budget Burned */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>ACCUMULATED_GAS_USED</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--accent-gold)' }}>
              ${budgetUsed.toLocaleString()}
            </span>
          </div>

          {/* Ledger Terminal Log Stream */}
          <div style={{ flex: 1, minHeight: '120px', background: 'var(--bg-deep)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 'var(--radius-sm)', padding: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px', overflowY: 'auto' }}>
            <div style={{ color: 'var(--text-tertiary)', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '4px', marginBottom: '4px' }}>
              // LIVE_STATE_TRANSACTIONS
            </div>
            {totalCommitted === 0 ? (
              <div style={{ color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                [Awaiting protocol initialization...]
              </div>
            ) : (
              <>
                <div style={{ color: 'var(--accent-teal)' }}>[00:00:01] INFO :: GENESIS_BLOCK_INITIALIZED</div>
                {totalCommitted >= 1 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:05] SECURE :: Discovery block verified.</div>}
                {totalCommitted >= 2 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:12] SECURE :: BA requirements validated.</div>}
                {totalCommitted >= 3 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:20] SECURE :: Solutions options compared.</div>}
                {totalCommitted >= 4 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:28] SECURE :: Tech Architect API specs verified.</div>}
                {totalCommitted >= 5 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:36] SECURE :: Data permission specs approved.</div>}
                {totalCommitted >= 6 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:44] SECURE :: Builder codebase plan committed.</div>}
                {totalCommitted >= 7 && <div style={{ color: 'var(--text-secondary)' }}>[00:00:52] SECURE :: QA test coverage audited.</div>}
                {totalCommitted >= 8 && <div style={{ color: 'var(--text-secondary)' }}>[00:01:00] SECURE :: Critic assumptions validated.</div>}
                {totalCommitted >= 9 && <div style={{ color: 'var(--text-secondary)' }}>[00:01:08] SECURE :: Business review criteria matched.</div>}
                {totalCommitted >= 10 && <div style={{ color: 'var(--text-secondary)' }}>[00:01:16] SECURE :: Compliance risk checklist passed.</div>}
                {totalCommitted >= 11 && <div style={{ color: 'var(--accent-purple)' }}>[00:01:24] STATUS :: Final synthesis consensus lock.</div>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
