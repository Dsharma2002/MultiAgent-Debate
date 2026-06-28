import { useCallback, useReducer } from 'react';
import { AGENT_ORDER } from '../utils/constants';

/**
 * Pipeline state machine — processes WebSocket events into UI state.
 * Designed for minimal re-renders: only the changed slice updates.
 */

const initialState = {
  status: 'idle', // idle | running | complete
  agents: AGENT_ORDER.map((id) => ({
    id,
    status: 'pending', // pending | active | success | error
    attempt: 0,
  })),
  activeAgentIndex: -1,
  gateChecks: { vocab: null, constraint: null, peer: null },
  peerAudits: [],
  events: [],
  ledgerEntries: [],
  budgetUsed: 0,
  totalCommitted: 0,
  totalFailed: 0,
  chainValid: true,
  drafts: {},
};

function pipelineReducer(state, action) {
  const { type, payload } = action;

  switch (type) {
    case 'pipeline_start':
      return {
        ...initialState,
        status: 'running',
        events: [{ ...payload, _ts: Date.now() }],
      };

    case 'agent_start': {
      const agents = state.agents.map((a) =>
        a.id === payload.agent_id ? { ...a, status: 'active', attempt: 1 } : a
      );
      return {
        ...state,
        agents,
        activeAgentIndex: payload.step_index,
        gateChecks: { vocab: null, constraint: null, peer: null },
        peerAudits: [],
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };
    }

    case 'draft_created':
      return {
        ...state,
        drafts: {
          ...state.drafts,
          [payload.agent_id]: payload.data.content,
        },
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };

    case 'vocab_check':
      return {
        ...state,
        gateChecks: { ...state.gateChecks, vocab: payload.data.passed },
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };

    case 'constraint_check':
      return {
        ...state,
        gateChecks: { ...state.gateChecks, constraint: payload.data.passed },
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };

    case 'peer_audit_start':
      return {
        ...state,
        gateChecks: { ...state.gateChecks, peer: 'checking' },
        peerAudits: [],
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };

    case 'peer_audit_result': {
      const audit = {
        auditorId: payload.data.auditor_id,
        auditorName: payload.data.auditor_name,
        approved: payload.data.approved,
        reasons: payload.data.reasons,
      };
      const newAudits = [...state.peerAudits, audit];
      const allDone = newAudits.length >= 3;
      const allPassed = allDone && newAudits.filter((a) => a.approved).length >= 2;
      return {
        ...state,
        peerAudits: newAudits,
        gateChecks: {
          ...state.gateChecks,
          peer: allDone ? allPassed : 'checking',
        },
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };
    }

    case 'gate_decision': {
      const isCommit = payload.data.decision === 'COMMIT';
      let ledger = state.ledgerEntries;
      let budget = state.budgetUsed;
      let committed = state.totalCommitted;
      let failed = state.totalFailed;

      if (isCommit) {
        ledger = [
          ...ledger,
          {
            agentId: payload.agent_id,
            entryHash: payload.data.entry_hash,
            prevHash: payload.data.prev_hash,
            approvals: payload.data.approvals,
            content: payload.data.content,
          },
        ];
        budget = payload.data.budget_used || budget;
        committed += 1;
      } else {
        failed += 1;
      }

      return {
        ...state,
        ledgerEntries: ledger,
        budgetUsed: budget,
        totalCommitted: committed,
        totalFailed: failed,
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };
    }

    case 'retry': {
      const agents = state.agents.map((a) =>
        a.id === payload.agent_id
          ? { ...a, attempt: payload.data.attempt }
          : a
      );
      return {
        ...state,
        agents,
        gateChecks: { vocab: null, constraint: null, peer: null },
        peerAudits: [],
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };
    }

    case 'agent_complete': {
      const agents = state.agents.map((a) =>
        a.id === payload.agent_id
          ? { ...a, status: payload.data.success ? 'success' : 'error' }
          : a
      );
      return {
        ...state,
        agents,
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };
    }

    case 'pipeline_complete':
      return {
        ...state,
        status: 'complete',
        chainValid: payload.data?.ledger?.chain_valid ?? true,
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };

    case 'error':
      return {
        ...state,
        events: [...state.events, { ...payload, _ts: Date.now() }],
      };

    case 'RESET':
      return initialState;

    default:
      return state;
  }
}

export function usePipeline() {
  const [state, dispatch] = useReducer(pipelineReducer, initialState);

  const handleEvent = useCallback((event) => {
    dispatch({ type: event.event_type, payload: event });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return { state, handleEvent, reset };
}
