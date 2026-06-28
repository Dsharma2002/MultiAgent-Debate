/* Agent identity definitions with colors and icons */
export const AGENTS = {
  tech_lead: {
    id: 'tech_lead',
    name: 'Tech Lead',
    icon: '⚙️',
    color: '#448aff',
    specialty: 'Backend Architecture',
  },
  product_manager: {
    id: 'product_manager',
    name: 'Product Manager',
    icon: '📊',
    color: '#ffd600',
    specialty: 'Business Value',
  },
  qa_engineer: {
    id: 'qa_engineer',
    name: 'QA Engineer',
    icon: '🧪',
    color: '#00e5ff',
    specialty: 'Quality Assurance',
  },
  security_auditor: {
    id: 'security_auditor',
    name: 'Security Auditor',
    icon: '🛡️',
    color: '#ff006e',
    specialty: 'Threat Modeling',
  },
};

export const AGENT_ORDER = ['tech_lead', 'product_manager', 'qa_engineer', 'security_auditor'];

export const GATE_CHECKS = [
  { id: 'vocab', label: 'Vocabulary Check', icon: '📝' },
  { id: 'constraint', label: 'Constraint Check', icon: '🔒' },
  { id: 'peer', label: 'Peer Audit', icon: '👥' },
];

export const WS_URL = `ws://${window.location.host}/ws/pipeline`;
export const API_URL = '/api';
