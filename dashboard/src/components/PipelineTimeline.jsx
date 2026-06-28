import { AGENTS, AGENT_ORDER } from '../utils/constants';

export default function PipelineTimeline({ agents }) {
  return (
    <div className="panel glass">
      <div className="panel-header">
        <span className="panel-title">⏱ Pipeline Timeline</span>
        <span className="panel-badge">
          {agents.filter((a) => a.status !== 'pending').length}/4 steps
        </span>
      </div>
      <div className="timeline">
        {agents.map((agent, i) => {
          const meta = AGENTS[agent.id];
          const isLast = i === agents.length - 1;
          return (
            <div key={agent.id} className={`timeline-step ${agent.status}`}>
              <div
                className={`timeline-node ${agent.status}`}
                style={{
                  borderColor:
                    agent.status === 'active'
                      ? meta.color
                      : undefined,
                }}
              >
                {agent.status === 'success'
                  ? '✓'
                  : agent.status === 'error'
                  ? '✗'
                  : agent.status === 'active'
                  ? '●'
                  : meta.icon}
              </div>
              {!isLast && (
                <div className="timeline-connector">
                  <div
                    className={`timeline-connector-fill ${
                      agent.status === 'success' || agent.status === 'error' ? 'complete' : ''
                    }`}
                    style={{
                      background:
                        agent.status === 'error'
                          ? 'linear-gradient(90deg, #ff1744, #ff174480)'
                          : undefined,
                    }}
                  />
                </div>
              )}
              <span className="timeline-label">{meta.name}</span>
              {agent.attempt > 1 && (
                <span style={{ fontSize: '0.6rem', color: 'var(--status-warning)' }}>
                  Attempt {agent.attempt}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
