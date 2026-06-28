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

      {/* Lists Section (Threats, Edge Cases, Test Requirements) */}
      {listBlocks.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 'var(--gap-md)',
            marginTop: 'var(--gap-md)',
            borderTop: '1px solid var(--glass-border)',
            paddingTop: 'var(--gap-md)',
          }}
        >
          {listBlocks.map((lb) => (
            <div key={lb.key} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-sm)' }}>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--text-secondary)',
                  letterSpacing: '0.05em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>{lb.key === 'identified_threats' ? '🔥' : lb.key === 'edge_cases' ? '⚠' : '✓'}</span>
                {lb.label} ({lb.value.length})
              </span>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                {lb.value.map((item, idx) => (
                  <div
                    key={idx}
                    className="glass-sm"
                    style={{
                      padding: '8px 12px',
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      background: 'rgba(255,255,255,0.01)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '8px',
                    }}
                  >
                    <span style={{ color: agent.color, fontWeight: 700 }}>•</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
