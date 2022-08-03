"""Class containing an abstract event component
"""

from abc import ABC, abstractmethod

from .types import Event
from .queue import Queue


class QueueComponent:

    queue: Queue
    name: str

    def __init__(self, name: str):
        self.name = name
    
    def register_queue(self, queue: Queue):
        self.queue = queue

    def add_event(self, event):
        self.queue.enqueue(event)

class AbstractEventComponent(ABC, QueueComponent):

    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """Handle an event
        """
        raise NotImplementedError
