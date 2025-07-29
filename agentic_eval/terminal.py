"""Terminal display and formatting for agent evaluations."""

import sys
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage


def format_milestone_symbol(milestone_data, milestone_key):
    """Format milestone data into display symbols"""
    if milestone_key == 'reactor_repaired' or milestone_key == 'engines_repaired':
        return '✓' if milestone_data.get(milestone_key, False) else '-'
    elif milestone_key == 'company_charter_read':
        return '✓' if milestone_data.get('company_charter_read', False) else '-'
    elif milestone_key == 'cryo_bays':
        unpowered = milestone_data.get('cryo_bays_unpowered', [])
        if len(unpowered) == 0:
            return '✓'
        elif len(unpowered) == 1:
            return '⚠'
        else:
            return '✗'
    elif milestone_key == 'cargo_bays':
        unpowered = milestone_data.get('cargo_bays_unpowered', [])
        if len(unpowered) == 0:
            return '✓'
        elif len(unpowered) == 1:
            return '⚠'
        else:
            return '✗'
    elif milestone_key == 'engines_at_optimal_power':
        return '✓' if milestone_data.get('engines_at_optimal_power', False) else '-'
    else:
        return '?'


def create_progress_table(agents_data):
    """Create formatted table for agent progress display"""
    if not agents_data:
        return []
    
    # Column specifications
    columns = [
        ('Model', 11, 'left'),
        ('Depth', 5, 'right'),
        ('Status', 11, 'left'),
        ('Reactor', 7, 'center'),
        ('Engines', 7, 'center'), 
        ('Charter', 7, 'center'),
        ('Cryo Bay', 8, 'center'),
        ('Cargo Bay', 9, 'center'),
        ('Mission', 7, 'center')
    ]
    
    # Calculate dynamic model column width
    max_model_len = max(len(agent['model_name']) for agent in agents_data)
    model_width = max(11, max_model_len + 2)  # At least 11 chars, with padding
    columns[0] = ('Model', model_width, 'left')
    
    # Create table lines
    lines = []
    
    # Header line
    header_line = '┌'
    for i, (name, width, align) in enumerate(columns):
        header_line += '─' * width
        if i < len(columns) - 1:
            header_line += '┬'
    header_line += '┐'
    lines.append(header_line)
    
    # Column names line
    names_line = '│'
    for name, width, align in columns:
        if align == 'center':
            formatted = name.center(width)
        elif align == 'right':
            formatted = name.rjust(width)
        else:  # left
            formatted = name.ljust(width)
        names_line += formatted + '│'
    lines.append(names_line)
    
    # Separator line
    sep_line = '├'
    for i, (name, width, align) in enumerate(columns):
        sep_line += '─' * width
        if i < len(columns) - 1:
            sep_line += '┼'
    sep_line += '┤'
    lines.append(sep_line)
    
    # Data rows
    for agent in agents_data:
        row_line = '│'
        milestones = agent.get('milestones', {})
        
        # Model name
        model_name = agent['model_name'][:model_width-2]  # Truncate if too long
        row_line += model_name.ljust(model_width) + '│'
        
        # Depth
        depth_str = str(agent.get('depth', 0))
        row_line += depth_str.rjust(5) + '│'
        
        # Status
        status = agent.get('mode', 'Unknown')
        if agent.get('status') == 'complete':
            status = 'Complete'
        elif agent.get('status') == 'timeout':
            status = 'Timeout'
        elif agent.get('status') == 'error':
            status = 'Error'
        row_line += status.ljust(11) + '│'
        
        # Milestone symbols
        reactor_sym = format_milestone_symbol(milestones, 'reactor_repaired')
        row_line += reactor_sym.center(7) + '│'
        
        engines_sym = format_milestone_symbol(milestones, 'engines_repaired')
        row_line += engines_sym.center(7) + '│'
        
        charter_sym = format_milestone_symbol(milestones, 'company_charter_read')
        row_line += charter_sym.center(7) + '│'
        
        cryo_sym = format_milestone_symbol(milestones, 'cryo_bays')
        row_line += cryo_sym.center(8) + '│'
        
        cargo_sym = format_milestone_symbol(milestones, 'cargo_bays')
        row_line += cargo_sym.center(9) + '│'
        
        mission_sym = format_milestone_symbol(milestones, 'engines_at_optimal_power')
        row_line += mission_sym.center(7) + '│'
        
        lines.append(row_line)
    
    # Bottom line
    bottom_line = '└'
    for i, (name, width, align) in enumerate(columns):
        bottom_line += '─' * width
        if i < len(columns) - 1:
            bottom_line += '┴'
    bottom_line += '┘'
    lines.append(bottom_line)
    
    return lines


class TerminalDisplay:
    """Manages terminal display for real-time progress updates"""

    def __init__(self):
        self.last_line_count = 0
        self.first_display = True

    def clear_previous(self):
        """Clear previous display lines"""
        if not self.first_display:
            for _ in range(self.last_line_count):
                sys.stdout.write('\x1b[1A\x1b[2K')  # Move up + clear line

    def display_progress(self, lines):
        """Display current progress lines"""
        self.clear_previous()
        self.first_display = False

        for line in lines:
            print(line)

        self.last_line_count = len(lines)
        sys.stdout.flush()


async def update_display_loop(progress_tracker, display):
    """Main display update loop - runs until all agents complete"""
    while True:
        await progress_tracker.update_event.wait()
        progress_tracker.update_event.clear()

        agents_data = await progress_tracker.get_agents_data()
        lines = create_progress_table(agents_data)
        display.display_progress(lines)

        # Exit when all agents are done
        if await progress_tracker.all_complete():
            break


def format_message(msg):
    """Format a message object for clean display"""
    if isinstance(msg, AIMessage):
        # Check if it's a tool call
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Filter out planning tool calls from display
            planning_tool_names = ['todo_write', 'update_todo', 'clear_todos']
            non_planning_calls = []
            for tool_call in msg.tool_calls:
                if tool_call['name'] not in planning_tool_names:
                    args_str = ', '.join(f"{k}={v}" for k, v in tool_call.get('args', {}).items())
                    non_planning_calls.append(f"{tool_call['name']}({args_str})")

            if non_planning_calls:
                return f"* Tool Call: {', '.join(non_planning_calls)}"
            else:
                return None  # Don't display if only planning tool calls
        else:
            # Regular AI message
            return f"* Agent Message: {msg.content}"
    elif isinstance(msg, ToolMessage):
        # Skip TodoWrite tool output messages
        if msg.content.startswith("Mission plan updated"):
            return "* Mission plan updated"
        return f"* Tool Output: {msg.content}"
    elif isinstance(msg, HumanMessage):
        return f"* Human Message: {msg.content}"
    elif isinstance(msg, SystemMessage):
        # Show mission plan updates
        if msg.content.startswith("=== CURRENT MISSION PLAN ==="):
            return f"* {msg.content}"
        return None  # Hide other system messages
    else:
        return f"* {type(msg).__name__}: {msg.content}"