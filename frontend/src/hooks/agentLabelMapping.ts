// ============= USER-FRIENDLY AGENT NAME MAPPING =============
// Hide internal implementation details from users (Bolt.new style)

interface AgentLabelInfo {
  label: string
  icon: string
  hidden?: boolean
}

const agentNameMapping: Record<string, AgentLabelInfo> = {
  'Planner Agent': { label: 'Planning project structure', icon: '📋' },
  'Writer Agent': { label: 'Generating code', icon: '✍️' },
  'Documenter Agent': { label: 'Creating documentation', icon: '📝' },
  'Fixer Agent': { label: 'Fixing issues', icon: '🔧' },
  'Runner Agent': { label: 'Running commands', icon: '▶️' },
  'bolt_instant': { label: '', icon: '', hidden: true },
  'Analyzer': { label: '', icon: '', hidden: true },
  'Verifier': { label: '', icon: '', hidden: true },
}

/**
 * Get user-friendly agent label (returns null to hide the step)
 * This prevents internal agent names from being shown to users.
 */
export const getAgentLabel = (internalName: string): { label: string; icon: string } | null => {
  const mapping = agentNameMapping[internalName]
  if (mapping?.hidden) return null
  if (mapping) return { label: mapping.label, icon: mapping.icon }
  // For unknown agents, show a generic friendly name (don't expose internal names)
  return { label: 'Processing...', icon: '⚙️' }
}
