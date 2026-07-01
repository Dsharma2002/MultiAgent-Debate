import { useState } from 'react';
import { AGENTS } from '../utils/constants';

const AGENT_SPECIALTIES = {
  discovery: "Gathers business problems, defines scope, and identifies key stakeholders.",
  business_analyst: "Converts discovery outputs into detailed requirements and structured user stories.",
  solution_deviser: "Generates high-level solution options, architectural options, and trade-offs.",
  technical_architect: "Designs system APIs, database models, and module interactions.",
  data_integration: "Establishes data contracts, sources, permission structures, and schemas.",
  builder: "Implements approved design patterns and drafts code/configuration recommendations.",
  test_qa: "Writes test suites, details edge cases, and verifies functional test coverage.",
  verifier: "Challenges core assumptions, identifies contradictions, and validates budget integrity.",
  business_reviewer: "Compares implemented drafts against original business needs and user impact.",
  compliance_risk: "Audits security boundaries, data compliance, privacy, and policy guidelines.",
  synthesizer: "Merges outputs, resolves peer contradictions, and yields final consensus."
};

const STAGES = [
  {
    name: "I. INCEPTION PROTOCOL",
    description: "Scope, requirements, & stakeholder alignment",
    agentIds: ["discovery", "business_analyst"]
  },
  {
    name: "II. ARCHITECTURAL LAYER",
    description: "System design, interfaces, & data integration",
    agentIds: ["solution_deviser", "technical_architect", "data_integration"]
  },
  {
    name: "III. COMPILE & INTEGRATE",
    description: "Code generation, modular build, & testing",
    agentIds: ["builder", "test_qa"]
  },
  {
    name: "IV. INTEGRITY SHIELD",
    description: "Security risk, business audit, & synthesis",
    agentIds: ["verifier", "business_reviewer", "compliance_risk", "synthesizer"]
  }
];

function AgentNode({ agent, specialty, index }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '12px var(--gap-md)',
        background: hovered ? 'rgba(255,255,255,0.02)' : 'var(--bg-surface)',
        border: `1px solid ${hovered ? agent.color : 'rgba(255,255,255,0.04)'}`,
        borderRadius: 'var(--radius-md)',
        boxShadow: hovered ? `0 8px 30px ${agent.color}15` : 'none',
        transform: hovered ? 'translateY(-2px)' : 'none',
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {hovered && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '2px',
          height: '100%',
          background: agent.color
        }} />
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1rem' }}>{agent.icon}</span>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {agent.name.toUpperCase()}
          </span>
        </div>
        <span style={{ fontSize: '0.65rem', color: agent.color, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
          PH_{String(index + 1).padStart(2, '0')}
        </span>
      </div>
      <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: '1.3', margin: 0 }}>
        {specialty}
      </p>
    </div>
  );
}

export default function DebateArena({ feed = [] }) {
  // Helper to generate a short mock tx hash from a string ID
  const getTxHash = (id) => {
    if (!id) return "0x0000000000000000";
    let hash = 0;
    for (let i = 0; i < id.length; i++) {
      hash = id.charCodeAt(i) + ((hash << 5) - hash);
    }
    return "0x" + Math.abs(hash).toString(16).padEnd(16, 'f').substring(0, 16);
  };

  return (
    <div className="debate-arena" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-lg)', padding: 'var(--gap-sm)' }}>
      {feed.length === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-xl)', animation: 'fadeSlideIn 0.4s var(--ease-out)' }}>
          
          {/* Header Console Banner */}
          <div className="console-card" style={{ padding: 'var(--gap-md) var(--gap-lg)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderLeft: '2px solid var(--text-tertiary)' }}>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.05em' }}>
                SYSTEM_CORE // MAD_PIPELINE
              </div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px', letterSpacing: '-0.03em' }}>
                Consensus Engine Core
              </h2>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
              <span style={{ display: 'inline-block', width: '5px', height: '5px', borderRadius: '50%', background: 'var(--status-success)' }} />
              DORMANT // AWAITING_INITIALIZATION
            </div>
          </div>

          {/* Structured Pipeline Flow */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-lg)' }}>
            {STAGES.map((stage, sIdx) => (
              <div key={stage.name} className="console-card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap-md)', padding: 'var(--gap-md)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '8px' }}>
                  <div>
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {stage.name}
                    </h3>
                    <p style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                      {stage.description}
                    </p>
                  </div>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                    STAGE_{String(sIdx + 1).padStart(2, '0')}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--gap-md)' }}>
                  {stage.agentIds.map((id) => {
                    const agent = AGENTS[id];
                    const specialty = AGENT_SPECIALTIES[id] || "";
                    const orderIndex = Object.keys(AGENTS).indexOf(id);
                    return (
                      <AgentNode key={id} agent={agent} specialty={specialty} index={orderIndex} />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {feed.map((event, i) => {
        const agent = AGENTS[event.agentId] || { name: event.agentName || 'System', color: 'var(--accent-cyan)', icon: '🤖' };
        const txHash = getTxHash(event.id);
        const timestamp = new Date(event._ts).toLocaleTimeString();
        
        let borderAccent = 'rgba(255, 255, 255, 0.03)';
        let statusText = 'PROPOSAL_ENTRY';
        let statusColor = 'var(--text-secondary)';
        
        if (event.type === 'objection') {
          borderAccent = 'rgba(251, 113, 133, 0.2)'; // Muted rose border
          statusText = 'DISAGREEMENT_REPORTED';
          statusColor = 'var(--accent-magenta)';
        } else if (event.type === 'support') {
          borderAccent = 'rgba(52, 211, 153, 0.2)'; // Muted emerald border
          statusText = 'PEER_VERDICT_APPROVED';
          statusColor = 'var(--accent-teal)';
        } else if (event.type === 'thinking') {
          borderAccent = 'rgba(125, 211, 252, 0.2)'; // Muted sky border
          statusText = 'ANALYSIS_IN_PROGRESS';
          statusColor = 'var(--accent-cyan)';
        } else if (event.type === 'synthesis') {
          borderAccent = 'rgba(192, 132, 252, 0.2)'; // Muted purple border
          statusText = 'FINAL_CONSENSUS_SYNTHESIS';
          statusColor = 'var(--accent-purple)';
        }

        return (
          <div key={`${event.id}-${i}`} className="console-card" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            borderRadius: 'var(--radius-md)', 
            border: `1px solid ${borderAccent}`,
            boxShadow: `0 4px 20px rgba(0, 0, 0, 0.3)`,
            animation: 'fadeSlideIn 0.25s var(--ease-out) both',
            overflow: 'hidden'
          }}>
            {/* Ledger Block Header */}
            <div className="terminal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ 
                  display: 'inline-block', 
                  width: '6px', 
                  height: '6px', 
                  borderRadius: '50%', 
                  background: statusColor, 
                  boxShadow: `0 0 6px ${statusColor}` 
                }} />
                <span style={{ fontWeight: 700, color: statusColor }}>{statusText}</span>
              </div>
              <div style={{ display: 'flex', gap: '16px', color: 'var(--text-tertiary)' }}>
                <span>TX_HASH: <span style={{ color: 'var(--text-secondary)' }}>{txHash}</span></span>
                <span>{timestamp}</span>
              </div>
            </div>

            {/* Block Body Content */}
            <div style={{ padding: 'var(--gap-md)', display: 'flex', gap: 'var(--gap-md)' }}>
              {/* Agent Badge Icon */}
              <div style={{
                width: 38, height: 38, borderRadius: '50%', background: `${agent.color}15`,
                border: `1px solid ${agent.color}30`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.1rem',
                flexShrink: 0
              }}>
                {agent.icon}
              </div>

              {/* Transaction Payload */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 800, color: agent.color, fontFamily: 'var(--font-mono)' }}>
                    {agent.name.toUpperCase()}
                  </span>
                  {event.type === 'objection' && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-magenta)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                      // REJECTED_TARGET::[{event.data.target_agent.toUpperCase()}]
                    </span>
                  )}
                  {event.type === 'support' && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-teal)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                      // APPROVED_TARGET::[{event.data.target_agent.toUpperCase()}]
                    </span>
                  )}
                </div>

                {/* Event Type: Thinking Status */}
                {event.type === 'thinking' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.8rem', padding: '4px 0' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>&gt;</span>
                    {event.target ? `Executing cross-audit on ${event.target}'s claims...` : 'Analyzing proposal specification...'}
                    <span className="terminal-cursor" />
                  </div>
                )}

                {/* Event Type: Proposal / Synthesis Contents */}
                {(event.type === 'proposal' || event.type === 'synthesis') && event.data.content && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '4px' }}>
                    {/* Final Answer */}
                    <div style={{ 
                      color: 'var(--text-primary)', 
                      fontSize: '0.85rem', 
                      lineHeight: '1.55', 
                      background: 'rgba(255,255,255,0.01)', 
                      padding: '10px 12px', 
                      borderRadius: 'var(--radius-sm)',
                      borderLeft: `2px solid ${agent.color}`
                    }}>
                      {event.data.content.final_answer}
                    </div>

                    {/* Claims Section */}
                    {event.data.content.claims && event.data.content.claims.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.7rem', color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                          // CLAIMS_VERIFICATION_MATRIX
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '8px' }}>
                          {event.data.content.claims.map((c, idx) => (
                            <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', fontSize: '0.8rem' }}>
                              <span style={{ color: agent.color, fontFamily: 'var(--font-mono)' }}>[+]</span>
                              <span style={{ color: 'var(--text-secondary)' }}>{c}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Evidence & Assumptions */}
                    {(event.data.content.evidence?.length > 0 || event.data.content.assumptions?.length > 0) && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gap-md)', borderTop: '1px solid rgba(255,255,255,0.02)', paddingTop: '10px' }}>
                        {event.data.content.evidence && event.data.content.evidence.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.65rem', color: 'var(--accent-cyan)' }}>
                              // EVIDENCE_SUPPORT
                            </div>
                            {event.data.content.evidence.map((e, idx) => (
                              <div key={idx} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                • {e}
                              </div>
                            ))}
                          </div>
                        )}

                        {event.data.content.assumptions && event.data.content.assumptions.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                              // DECLARED_ASSUMPTIONS
                            </div>
                            {event.data.content.assumptions.map((a, idx) => (
                              <div key={idx} style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                                • {a}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Uncertainties or Blockers */}
                    {(event.data.content.metadata?.uncertainties?.length > 0 || event.data.content.metadata?.blockers?.length > 0) && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {event.data.content.metadata.uncertainties && event.data.content.metadata.uncertainties.length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.65rem', color: 'var(--accent-gold)' }}>
                              // UNCERTAINTIES_WARNING
                            </div>
                            {event.data.content.metadata.uncertainties.map((u, idx) => (
                              <div key={idx} style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', opacity: 0.85 }}>
                                ! {u}
                              </div>
                            ))}
                          </div>
                        )}

                        {event.data.content.metadata.blockers && event.data.content.metadata.blockers.length > 0 && (
                          <div style={{ 
                            background: 'rgba(255, 0, 127, 0.04)', 
                            border: '1px solid rgba(255, 0, 127, 0.15)', 
                            padding: '8px var(--gap-md)', 
                            borderRadius: 'var(--radius-sm)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px'
                          }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.7rem', color: 'var(--accent-magenta)' }}>
                              [!] CRITICAL_BLOCKER_DETECTED
                            </div>
                            {event.data.content.metadata.blockers.map((b, idx) => (
                              <div key={idx} style={{ fontSize: '0.75rem', color: 'var(--accent-magenta)' }}>
                                - {b}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Next Action Command */}
                    {event.data.content.metadata?.recommended_next_action && (
                      <div style={{ 
                        borderTop: '1px solid rgba(255,255,255,0.02)', 
                        paddingTop: '8px', 
                        fontFamily: 'var(--font-mono)', 
                        fontSize: '0.75rem', 
                        color: 'var(--status-success)', 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '6px' 
                      }}>
                        <span>NEXT_CMD:</span>
                        <span style={{ background: 'rgba(0, 230, 118, 0.08)', padding: '2px 8px', borderRadius: '4px' }}>
                          mad-cli --run-next "{event.data.content.metadata.recommended_next_action}"
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Event Type: Audits (Objections / Supports) Reasons */}
                {(event.type === 'objection' || event.type === 'support') && event.data.reasons && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px' }}>
                    {event.data.reasons.map((r, idx) => (
                      <div key={idx} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                        {r}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
