export default function ConstraintDashboard({ budgetUsed, gateChecks, activeAgentIndex }) {
  const budgetPercent = Math.min(100, (budgetUsed / 5000) * 100);
  const budgetClass = budgetPercent > 80 ? 'danger' : budgetPercent > 50 ? 'warning' : '';
  const isChecking = activeAgentIndex >= 0;

  return (
    <div className="panel glass">
      <div className="panel-header">
        <span className="panel-title">🔒 Constraints</span>
        <span className="panel-badge">3 active</span>
      </div>
      <div className="constraint-cards">
        {/* Constraint 01: Budget */}
        <div className={`constraint-card ${isChecking && gateChecks.constraint === null ? 'checking' : ''}`}>
          <div className="constraint-header">
            <span className="constraint-name">💰 Budget Limit</span>
            <span className="constraint-id">constraint_01</span>
          </div>
          <div className="budget-bar">
            <div
              className={`budget-bar-fill ${budgetClass}`}
              style={{ width: `${budgetPercent}%` }}
            />
          </div>
          <div className="budget-text">
            ${budgetUsed.toLocaleString()} / $5,000 ({budgetPercent.toFixed(0)}%)
          </div>
        </div>

        {/* Constraint 02: Security */}
        <div className={`constraint-card ${isChecking && gateChecks.constraint === null ? 'checking' : ''}`}>
          <div className="constraint-header">
            <span className="constraint-name">🛡️ Security Boundary</span>
            <span className="constraint-id">constraint_02</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 'var(--gap-xs)' }}>
            QA Engineer restricted from high-security data
          </div>
          <div style={{ marginTop: 'var(--gap-xs)', display: 'flex', alignItems: 'center', gap: 'var(--gap-xs)' }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: 'var(--status-success)',
            }} />
            <span style={{ fontSize: '0.7rem', color: 'var(--status-success)', fontWeight: 600 }}>Enforced</span>
          </div>
        </div>

        {/* Constraint 03: Peer Validation */}
        <div className={`constraint-card ${isChecking && gateChecks.peer === 'checking' ? 'checking' : ''}`}>
          <div className="constraint-header">
            <span className="constraint-name">👥 Peer Validation</span>
            <span className="constraint-id">constraint_03</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 'var(--gap-xs)' }}>
            Minimum 2 peer approvals required per entry
          </div>
          <div style={{ marginTop: 'var(--gap-xs)', display: 'flex', alignItems: 'center', gap: 'var(--gap-xs)' }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: gateChecks.peer === 'checking' ? 'var(--status-active)' : 'var(--status-success)',
              animation: gateChecks.peer === 'checking' ? 'pulse-node 1.5s ease infinite' : 'none',
            }} />
            <span style={{
              fontSize: '0.7rem',
              color: gateChecks.peer === 'checking' ? 'var(--status-active)' : 'var(--status-success)',
              fontWeight: 600,
            }}>
              {gateChecks.peer === 'checking' ? 'Auditing…' : 'Enforced'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
