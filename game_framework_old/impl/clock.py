"""Game clock - places regular update events on the queue
"""
import time

from src.types import Event
from src.component import QueueComponent

class GameClock(AbstractEventComponent):

    frame_time: int
    running: bool

    def __init__(self, frame_time: int):
        self.frame_time = frame_time
        super.__init__(name="GameClock")
    
    def clock_event(self) -> None:
        self.queue.enqueue(Event(event_type="TICK"))
        return
    
    def run(self) -> None:
        while True:
            if int(time.time() * 1000) % frame_time == 0:
                if self.running:
                    self.clock_event()
    
    def handle_event(self, event: Event) -> None:
        if event.event_type == "START":
            self.running = True
        if event.event_type == "STOP":
            self.running = False