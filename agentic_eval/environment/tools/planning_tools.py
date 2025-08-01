from typing import List, Dict, Any
from pydantic import BaseModel
from langchain_core.tools import tool
from .toolkit import ToolKit

class TodoItem(BaseModel):
    id: str
    content: str
    status: str  # "pending", "in_progress", "completed"

class PlanningTools(ToolKit):
    """Toolkit for managing mission planning and todo items with selective tool exposure."""

    def __init__(self):
        self.mission_todos = []
        super().__init__()

    def _create_tools(self):
        """Create tool instances bound to this environment"""

        @tool
        def todo_write(todos: List[TodoItem]):
            """Create new mission tasks. Only available when no todos exist or all todos are completed.

            Args:
                todos: List of new task objects (id, content, status)

            Status values: "pending", "in_progress", "completed"

            Usage example:
                # Create initial mission plan
                todo_write(todos=[
                    {{"id": "1", "content": "Read ship logs", "status": "pending"}},
                    {{"id": "2", "content": "Assess damage", "status": "pending"}},
                    {{"id": "3", "content": "Review protocols", "status": "pending"}},
                    {{"id": "4", "content": "Contact crew", "status": "pending"}}
                ])
            """
            # Only allow creating new todos - check for existing IDs
            for new_todo in todos:
                try:
                    # Check if ID already exists
                    for existing_todo in self.mission_todos:
                        if existing_todo.id == new_todo.id:
                            return f"Todo ID '{new_todo.id}' already exists. Use update_todo to modify existing todos."

                    # Add new todo
                    self.mission_todos.append(new_todo)

                except Exception as e:
                    return f"Error validating todo {new_todo.model_dump()}: {e}"

            # Sort todos by ID for consistent display
            self.mission_todos.sort(key=lambda x: int(x.id))

            # Return empty string to suppress tool output
            return ""

        @tool
        def update_todo(id: str, status: str):
            """Update the status of an existing todo item.

            Args:
                id: The ID of the todo item to update
                status: New status ("pending", "in_progress", "completed")

            Usage examples:
                # Mark task as in progress
                update_todo(id="1", status="in_progress")

                # Mark task as completed
                update_todo(id="1", status="completed")
            """
            # Find the todo item to update
            for i, todo in enumerate(self.mission_todos):
                if todo.id == id:
                    if status not in ["pending", "in_progress", "completed"]:
                        return f"Invalid status '{status}'. Must be 'pending', 'in_progress', or 'completed'."

                    # Update the status
                    self.mission_todos[i] = TodoItem(id=todo.id, content=todo.content, status=status)
                    return ""

            return f"Todo with ID '{id}' not found."

        @tool
        def clear_todos(justification: str):
            """Clear all current todos and start fresh planning.

            Use this tool SPARINGLY - strongly prefer updating existing plan.
            Only use when current plan is completely obsolete.

            Args:
                justification: Explanation for why plan needs to be cleared

            Usage example:
                clear_todos(justification="Initial plan focused on repair, but damage assessment shows evacuation is only option")
            """
            self.mission_todos = []
            return ""

        # Store tools as instance attributes
        self.todo_write = todo_write
        self.update_todo = update_todo
        self.clear_todos = clear_todos

    def get_available_tools(self) -> List[Any]:
        """Return tools based on current todo list state."""
        incomplete_todos = [t for t in self.mission_todos if t.status != "completed"]
        has_incomplete_todos = len(incomplete_todos) > 0
        has_todos = len(self.mission_todos) > 0

        if not has_todos:
            # No todos exist - expose todo_write only
            return [self.todo_write]
        elif has_incomplete_todos:
            # Incomplete todos exist - expose update_todo and clear_todos
            return [self.update_todo, self.clear_todos]
        else:
            # All todos completed - expose todo_write and clear_todos
            return [self.todo_write, self.clear_todos]

    def format_todos(self):
        """Format current todos for display."""
        if not self.mission_todos:
            return "=== CURRENT MISSION PLAN ===\nNo current mission plan.\n=========================="

        todo_lines = []
        for todo in sorted(self.mission_todos, key=lambda x: int(x.id)):
            status_symbol = "✓" if todo.status == "completed" else "○" if todo.status == "in_progress" else "□"
            todo_lines.append(f"{status_symbol} [{todo.id}] {todo.content} ({todo.status})")

        return "=== CURRENT MISSION PLAN ===\n" + "\n".join(todo_lines) + "\n=========================="