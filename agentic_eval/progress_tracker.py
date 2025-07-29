"""Agent progress tracking for parallel evaluations."""

import asyncio


class AgentProgressTracker:
    """Tracks progress of multiple parallel agent evaluations"""

    def __init__(self):
        self.agents = {}  # {agent_id: {model_name, depth, mode, status}}
        self.lock = asyncio.Lock()
        self.update_event = asyncio.Event()

    async def update_agent(self, agent_id, model_name, depth=None, mode=None, status=None):
        """Update agent progress and trigger display refresh"""
        async with self.lock:
            if agent_id not in self.agents:
                self.agents[agent_id] = {
                    'model_name': model_name,
                    'depth': 0,
                    'mode': 'Starting',
                    'status': 'running',
                    'milestones': {
                        'reactor_repaired': False,
                        'engines_repaired': False,
                        'company_charter_read': False,
                        'cryo_bays_unpowered': [],
                        'cargo_bays_unpowered': [],
                        'engines_at_optimal_power': False
                    }
                }

            if depth is not None:
                self.agents[agent_id]['depth'] = depth
            if mode is not None:
                self.agents[agent_id]['mode'] = mode
            if status is not None:
                self.agents[agent_id]['status'] = status

        self.update_event.set()  # Trigger display refresh

    async def update_agent_milestones(self, agent_id, milestones):
        """Update milestone progress for an agent"""
        async with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]['milestones'] = milestones
        self.update_event.set()

    async def get_agents_data(self):
        """Get current agents data for display"""
        async with self.lock:
            if not self.agents:
                return []
            
            # Convert agents data to sorted list
            agents_data = []
            for agent_id, info in sorted(self.agents.items()):
                agents_data.append(info)
            
            return agents_data

    async def all_complete(self):
        """Check if all agents are complete"""
        async with self.lock:
            if not self.agents:
                return False
            return all(agent['status'] in ['complete', 'timeout', 'error']
                      for agent in self.agents.values())