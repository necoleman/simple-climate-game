
class Queue:
    """Wrapper for a list that gives fifo functionality
    """

    name: str
    queue: List[Event]

    def __init__(self, name: str) -> None:
        self.name = name
        self.queue = []
        return
    
    def enqueue(self, event: Event) -> None:
        queue.append(event)
    
    def dequeue(self) -> Event:
        return queue.pop(0)
