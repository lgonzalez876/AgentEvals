from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import List


@dataclass
class LogEntry:
    """Individual log entry in the ship's system log"""
    timestamp: str      # Mission time in [YYYY.DDD.HH:MM] format
    level: str         # ROUTINE, INFO, SYSTEM, ALERT, CRITICAL, etc.
    message: str       # Log message content
    
    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.level}: {self.message}"


class SimulationLogger:
    """Manages dynamic logging and time progression for the ship simulation"""
    
    def __init__(self, start_time: str = "2387.043.10:47"):
        """Initialize logger with starting mission time
        
        Args:
            start_time: Mission time in format "YYYY.DDD.HH:MM" (continues from static logs)
        """
        self.current_time = start_time
        self.dynamic_logs: List[LogEntry] = []
        
    def _parse_mission_time(self, time_str: str) -> dict:
        """Parse mission time string into components"""
        # Format: "YYYY.DDD.HH:MM"
        match = re.match(r"(\d{4})\.(\d{3})\.(\d{2}):(\d{2})", time_str)
        if not match:
            raise ValueError(f"Invalid mission time format: {time_str}")
        
        year, day_of_year, hour, minute = match.groups()
        return {
            'year': int(year),
            'day_of_year': int(day_of_year), 
            'hour': int(hour),
            'minute': int(minute)
        }
    
    def _format_mission_time(self, year: int, day_of_year: int, hour: int, minute: int) -> str:
        """Format mission time components into string"""
        return f"{year:04d}.{day_of_year:03d}.{hour:02d}:{minute:02d}"
    
    def advance_time(self, duration_minutes: float):
        """Advance mission time by specified duration
        
        Args:
            duration_minutes: Time to advance in minutes (can be fractional for seconds/milliseconds)
        """
        if duration_minutes <= 0:
            return  # No time advancement for zero or negative durations
            
        # Parse current time
        time_parts = self._parse_mission_time(self.current_time)
        
        # Calculate total minutes from start of year
        total_minutes = (time_parts['day_of_year'] - 1) * 24 * 60 + time_parts['hour'] * 60 + time_parts['minute']
        
        # Add duration (convert to minutes if needed)
        total_minutes += duration_minutes
        
        # Calculate new time components
        new_day_of_year = int(total_minutes // (24 * 60)) + 1
        remaining_minutes = total_minutes % (24 * 60)
        new_hour = int(remaining_minutes // 60)
        new_minute = int(remaining_minutes % 60)
        
        # Handle year rollover (unlikely but good to handle)
        new_year = time_parts['year']
        if new_day_of_year > 365:  # Simplified - assume 365 day years
            new_year += 1
            new_day_of_year -= 365
        
        # Update current time
        self.current_time = self._format_mission_time(new_year, new_day_of_year, new_hour, new_minute)
    
    def log_action(self, level: str, message: str, duration_minutes: float = 0):
        """Add a log entry for an agent action and advance time
        
        Args:
            level: Log level (ROUTINE, INFO, SYSTEM, ALERT, CRITICAL)
            message: Log message describing the action
            duration_minutes: Time the action takes (0 for instantaneous)
        """
        # Advance time before logging (action takes time to complete)
        if duration_minutes > 0:
            self.advance_time(duration_minutes)
        
        # Create and store log entry
        entry = LogEntry(
            timestamp=self.current_time,
            level=level.upper(),
            message=message
        )
        self.dynamic_logs.append(entry)
    
    def get_dynamic_logs(self) -> List[str]:
        """Get all dynamic log entries as formatted strings"""
        return [str(entry) for entry in self.dynamic_logs]
    
    def get_full_logs(self, static_logs: str) -> str:
        """Combine static logs with dynamic logs in chronological order
        
        Args:
            static_logs: Base static log content from prompt file
            
        Returns:
            Complete log with static + dynamic entries
        """
        if not self.dynamic_logs:
            return static_logs
        
        # Add dynamic logs to the end
        dynamic_log_strings = self.get_dynamic_logs()
        return static_logs + "\n" + "\n".join(dynamic_log_strings)
    
    def get_mission_time(self) -> str:
        """Get current mission time"""
        return self.current_time