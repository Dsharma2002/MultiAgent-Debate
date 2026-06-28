import { AGENTS } from '../utils/constants';

export default function StatsBar({ state }) {
  const { status, totalCommitted, totalFailed, budgetUsed, chainValid, ledgerEntries } = state;

  return (
    <div className="stats-bar">
      <div className="stat-card glass-sm">
        <span className="stat-label">Pipeline Status</span>
        <span className={`stat-value ${status === 'complete' ? (totalFailed === 0 ? 'success' : 'error') : 'accent'}`}>
          {status === 'idle' ? 'Ready' : status === 'running' ? '● Running' : totalFailed === 0 ? '✓ Success' : '⚠ Partial'}
        </span>
      </div>
      <div className="stat-card glass-sm">
        <span className="stat-label">Committed</span>
        <span className="stat-value success">{totalCommitted}</span>
      </div>
      <div className="stat-card glass-sm">
        <span className="stat-label">Rejected</span>
        <span className="stat-value error">{totalFailed}</span>
      </div>
      <div className="stat-card glass-sm">
        <span className="stat-label">Budget Used</span>
        <span className="stat-value gold">${budgetUsed.toLocaleString()}</span>
      </div>
      <div className="stat-card glass-sm">
        <span className="stat-label">Ledger Entries</span>
        <span className="stat-value accent">{ledgerEntries.length}</span>
      </div>
      <div className="stat-card glass-sm">
        <span className="stat-label">Chain Integrity</span>
        <span className={`stat-value ${chainValid ? 'success' : 'error'}`}>
          {status === 'idle' ? '—' : chainValid ? '✓ Valid' : '✗ Broken'}
        </span>
      </div>
    </div>
  );
}
