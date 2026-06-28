import { useRef, useEffect } from 'react';
import { AGENTS } from '../utils/constants';

const EVENT_LABELS = {
  pipeline_start: { badge: 'info', label: 'START' },
  pipeline_complete: { badge: 'info', label: 'DONE' },
  agent_start: { badge: 'info', label: 'AGENT' },
  agent_complete: { badge: 'info', label: 'DONE' },
  draft_created: { badge: 'check', label: 'DRAFT' },
  vocab_check: { badge: 'check', label: 'VOCAB' },
  constraint_check: { badge: 'check', label: 'CONST' },
  peer_audit_start: { badge: 'audit', label: 'AUDIT' },
  peer_audit_result: { badge: 'audit', label: 'PEER' },
  gate_decision: { badge: 'commit', label: 'GATE' },
  retry: { badge: 'reject', label: 'RETRY' },
  error: { badge: 'reject', label: 'ERROR' },
};

function formatMessage(event) {
  const d = event.data || {};
  const agentName = event.agent_name || (AGENTS[event.agent_id]?.name) || '';

  switch (event.event_type) {
    case 'pipeline_start':
      return `Pipeline started with ${d.total_steps} agents`;
    case 'pipeline_complete':
      return `Pipeline complete — ${d.success ? 'All committed' : 'Partial failure'}`;
    case 'agent_start':
      return `${agentName} starting execution`;
    case 'agent_complete':
      return `${agentName} ${d.success ? '✓ committed' : '✗ rejected'}`;
    case 'draft_created':
      return `${agentName} draft generated (attempt ${d.attempt})`;
    case 'vocab_check':
      return `Vocabulary: ${d.passed ? '✓ passed' : `✗ ${(d.errors || []).length} violations`}`;
    case 'constraint_check':
      return `Constraints: ${d.passed ? '✓ all passed' : `✗ ${(d.violations || []).length} violations`}`;
    case 'peer_audit_start':
      return `Peer audit started — need ${d.min_required} from ${(d.peers || []).length}`;
    case 'peer_audit_result':
      return `${d.auditor_name} ${d.approved ? '✓ approved' : '✗ rejected'}`;
    case 'gate_decision': {
      if (d.decision === 'COMMIT') return `✓ COMMITTED — hash: ${d.entry_hash}`;
      return `✗ REJECTED — ${d.reason}`;
    }
    case 'retry':
      return `Retrying (attempt ${d.attempt})`;
    case 'error':
      return `Error: ${d.error || 'Unknown'}`;
    default:
      return event.event_type;
  }
}

export default function EventLog({ events }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  // Virtualize: only render last 100 events
  const visible = events.slice(-100);

  return (
    <div className="panel glass" style={{ gridColumn: '1 / -1' }}>
      <div className="panel-header">
        <span className="panel-title">📡 Event Stream</span>
        <span className="panel-badge">{events.length} events</span>
      </div>
      <div className="event-log" ref={scrollRef}>
        {visible.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-icon">📡</span>
            <span className="empty-state-text">Waiting for pipeline events…</span>
          </div>
        ) : (
          visible.map((event, i) => {
            const { badge, label } = EVENT_LABELS[event.event_type] || { badge: 'info', label: '?' };
            const isGateCommit = event.event_type === 'gate_decision' && event.data?.decision === 'COMMIT';
            const isGateReject = event.event_type === 'gate_decision' && event.data?.decision !== 'COMMIT';

            return (
              <div key={event.event_id || i} className="event-item">
                <span className="event-time">
                  {new Date(event._ts || event.timestamp * 1000).toLocaleTimeString('en', { hour12: false })}
                </span>
                <span className={`event-type-badge ${isGateCommit ? 'commit' : isGateReject ? 'reject' : badge}`}>
                  {isGateCommit ? 'COMMIT' : isGateReject ? 'REJECT' : label}
                </span>
                <span className="event-message">{formatMessage(event)}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
