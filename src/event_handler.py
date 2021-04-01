"""The Event Handler processes events and distributes them to event components.
"""
from typing import List

from .types import Event
from .queue import Queue
from .abstract_event_component import AbstractEventComponent

class EventHandler:
    """Contains infra to: dequeue and distribute events to registered event components
    """

    queue: Queue
    components: List[AbstractEventComponent]

    def __init__(self, queue: Queue):
        self.queue = queue

    def register_event_component(
        self,
        component: AbstractEventComponent
    ) -> None:
        self.components.append(component)
        component.register_queue(self.queue)
        return

    def run(self):
        while True:
            next_event = self.queue.dequeue()
            for component in self.components:
                component.handle_event(next_event)
        return
