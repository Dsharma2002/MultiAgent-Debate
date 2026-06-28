import { GATE_CHECKS } from '../utils/constants';

export default function VerificationGate({ gateChecks, peerAudits, activeAgentIndex }) {
  const isActive = activeAgentIndex >= 0;

  return (
    <div className="panel glass">
      <div className="panel-header">
        <span className="panel-title">🚪 Verification Gate</span>
        <span className="panel-badge">
          {gateChecks.vocab === true && gateChecks.constraint === true && gateChecks.peer === true
            ? '✓ PASSED'
            : isActive
            ? '● Checking'
            : 'Idle'}
        </span>
      </div>
      <div className="gate-checks">
        {GATE_CHECKS.map((check) => {
          const value = gateChecks[check.id];
          let iconClass = '';
          let iconContent = check.icon;
          if (value === true) {
            iconClass = 'pass';
            iconContent = '✓';
          } else if (value === false) {
            iconClass = 'fail';
            iconContent = '✗';
          } else if (value === 'checking') {
            iconClass = 'active';
            iconContent = '●';
          }

          return (
            <div key={check.id} className="gate-check">
              <div className={`gate-check-icon ${iconClass}`}>{iconContent}</div>
              <span className="gate-check-label">{check.label}</span>
              <span className="gate-check-detail">
                {value === true ? 'Passed' : value === false ? 'Failed' : value === 'checking' ? 'In Progress...' : '—'}
              </span>
            </div>
          );
        })}
      </div>

      {/* Peer audit details */}
      {peerAudits.length > 0 && (
        <div style={{ marginTop: 'var(--gap-sm)' }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-tertiary)', marginBottom: 'var(--gap-xs)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Peer Verdicts
          </div>
          {peerAudits.map((audit, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--gap-sm)',
              padding: '4px 8px',
              fontSize: '0.7rem',
              animation: 'fadeSlideIn 0.3s ease both',
              animationDelay: `${i * 0.1}s`,
            }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: audit.approved ? 'var(--status-success)' : 'var(--status-error)',
                flexShrink: 0,
              }} />
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                {audit.auditorName}
              </span>
              <span style={{ color: audit.approved ? 'var(--status-success)' : 'var(--status-error)', fontWeight: 600 }}>
                {audit.approved ? 'Approved' : 'Rejected'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
