export const AGENTS = {
  discovery: { id: 'discovery', name: 'Discovery Agent', icon: '🔍', color: '#ffb300' },
  business_analyst: { id: 'business_analyst', name: 'Business Analyst', icon: '📋', color: '#fb8c00' },
  solution_deviser: { id: 'solution_deviser', name: 'Solution Deviser', icon: '💡', color: '#43a047' },
  technical_architect: { id: 'technical_architect', name: 'Technical Architect', icon: '📐', color: '#1e88e5' },
  data_integration: { id: 'data_integration', name: 'Data / Integration', icon: '🔌', color: '#3949ab' },
  builder: { id: 'builder', name: 'Builder Agent', icon: '👷', color: '#8e24aa' },
  test_qa: { id: 'test_qa', name: 'Test / QA', icon: '🧪', color: '#00acc1' },
  verifier: { id: 'verifier', name: 'Verifier / Critic', icon: '⚖️', color: '#e53935' },
  business_reviewer: { id: 'business_reviewer', name: 'Business Reviewer', icon: '👔', color: '#fdd835' },
  compliance_risk: { id: 'compliance_risk', name: 'Compliance / Risk', icon: '🛡️', color: '#d81b60' },
  synthesizer: { id: 'synthesizer', name: 'Synthesizer', icon: '🎯', color: '#00e676' },
};

export const AGENT_ORDER = [
  'discovery', 'business_analyst', 'solution_deviser', 'technical_architect',
  'data_integration', 'builder', 'test_qa', 'verifier',
  'business_reviewer', 'compliance_risk', 'synthesizer'
];

export const GATE_CHECKS = [
  { id: 'vocab', label: 'Vocabulary Check', icon: '📝' },
  { id: 'constraint', label: 'Constraint Check', icon: '🔒' },
  { id: 'peer', label: 'Peer Audit', icon: '👥' },
];

export const WS_URL = `ws://${window.location.host}/ws/pipeline`;
export const API_URL = '/api';
