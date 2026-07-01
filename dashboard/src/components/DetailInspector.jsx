import { AGENTS } from '../utils/constants';

export default function DetailInspector({ entry, onClose }) {
  if (!entry) return null;

  const agent = AGENTS[entry.agentId] || { name: entry.agentId, color: 'var(--accent-cyan)', icon: '🤖' };
  const content = entry.content || {};

  // Group content keys for better rendering
  const metrics = [];
  const textBlocks = [];
  const listBlocks = [];

  Object.entries(content).forEach(([key, val]) => {
    if (key === 'peer_validations' || key === 'assessment_type') return;

    const formattedKey = key
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');

    if (Array.isArray(val)) {
      listBlocks.push({ key, label: formattedKey, value: val });
    } else if (typeof val === 'string' && val.length > 60) {
      textBlocks.push({ key, label: formattedKey, value: val });
    } else {
      metrics.push({ key, label: formattedKey, value: val });
    }
  });

  return (
    <div
      className="panel glass"
      style={{
        gridColumn: '1 / -1',
        border: `1px solid ${agent.color}30`,
        animation: 'fadeSlideIn 0.3s var(--ease-out) both',
      }}
    >
      <div className="panel-header" style={{ borderBottomColor: `${agent.color}20` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)' }}>
          <span
            style={{
              fontSize: '1.2rem',
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: `${agent.color}15`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {agent.icon}
          </span>
          <div>
            <span className="panel-title" style={{ color: agent.color }}>
              {agent.name} Assessment Detail
            </span>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
              Hash: <code style={{ fontFamily: 'var(--font-mono)' }}>{entry.entryHash}</code>
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'rgba(255,255,255,0.05)',
            border: 'none',
            color: 'var(--text-secondary)',
            padding: '4px 12px',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            fontSize: '0.75rem',
            fontWeight: 600,
          }}
        >
          ✕ Close
        </button>
      </div>

      {/* Main Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--gap-md)',
          marginTop: 'var(--gap-sm)',
        }}
      >
        {/* Metrics Section */}
        {metrics.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)' }}>
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
                letterSpacing: '0.08em',
              }}
            >
              Key Metrics
            </span>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 'var(--gap-sm)',
              }}
            >
              {metrics.map((m) => (
                <div
                  key={m.key}
                  className="glass-sm"
                  style={{
                    padding: 'var(--gap-sm) var(--gap-md)',
                    background: 'rgba(255,255,255,0.01)',
                  }}
                >
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>{m.label}</div>
                  <div
                    style={{
                      fontSize: '1.1rem',
                      fontWeight: 700,
                      color:
                        m.key === 'budget_allocation'
                          ? 'var(--accent-gold)'
                          : m.key === 'tech_feasibility_score'
                          ? 'var(--accent-cyan)'
                          : 'var(--text-primary)',
                    }}
                  >
                    {m.key === 'budget_allocation'
                      ? `$${m.value.toLocaleString()}`
                      : typeof m.value === 'number'
                      ? m.value.toFixed(2)
                      : String(m.value)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Text Blocks (Notes, Descriptions) */}
        {textBlocks.map((tb) => (
          <div key={tb.key} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)' }}>
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
                letterSpacing: '0.08em',
              }}
            >
              {tb.label}
            </span>
            <div
              className="glass-sm"
              style={{
                padding: 'var(--gap-md)',
                fontSize: '0.8rem',
                lineHeight: '1.5',
                color: 'var(--text-secondary)',
                background: 'rgba(255,255,255,0.01)',
                borderLeft: `2px solid ${agent.color}`,
                whiteSpace: 'pre-line',
              }}
            >
              {tb.value}
            </div>
          </div>
        ))}
      </div>

      {/* Lists Section (Claims, Disagreements, Audit Trail) */}
      {listBlocks.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: 'var(--gap-lg)',
            marginTop: 'var(--gap-md)',
            borderTop: '1px solid var(--glass-border)',
            paddingTop: 'var(--gap-md)',
          }}
        >
          {listBlocks.map((lb) => (
            <div key={lb.key} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-md)' }}>
              <span
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--text-secondary)',
                  letterSpacing: '0.05em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <span>{lb.key === 'claims' ? '💡' : lb.key === 'resolved_disagreements' ? '⚖️' : lb.key === 'audit_trail' ? '📜' : '✓'}</span>
                {lb.label} ({lb.value.length})
              </span>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: lb.key === 'claims' ? 'repeat(auto-fit, minmax(320px, 1fr))' : '1fr',
                  gap: 'var(--gap-sm)',
                }}
              >
                {lb.value.map((item, idx) => {
                  if (lb.key === 'claims') {
                    // Render complex Claim object
                    return (
                      <div
                        key={idx}
                        className="glass"
                        style={{
                          padding: 'var(--gap-md)',
                          borderRadius: 'var(--radius-md)',
                          borderLeft: `3px solid ${agent.color}`,
                          background: 'rgba(255,255,255,0.02)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px'
                        }}
                      >
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          "{item.claim}"
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          <span style={{ color: 'var(--accent-cyan)' }}>Evidence:</span> {item.evidence}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                          <span style={{ color: 'var(--accent-purple)' }}>Assumptions:</span> {item.assumptions}
                        </div>
                        <div style={{ alignSelf: 'flex-end', fontSize: '0.7rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
                          Confidence: {Math.round(item.confidence * 100)}%
                        </div>
                      </div>
                    );
                  }

                  // Render standard string list (e.g. audit_trail, resolved_disagreements)
                  return (
                    <div
                      key={idx}
                      className="glass-sm"
                      style={{
                        padding: '12px 16px',
                        fontSize: '0.8rem',
                        lineHeight: '1.4',
                        color: 'var(--text-secondary)',
                        background: 'rgba(255,255,255,0.01)',
                        borderLeft: `2px solid ${lb.key === 'resolved_disagreements' ? 'var(--accent-pink)' : 'var(--text-tertiary)'}`,
                      }}
                    >
                      {item}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
