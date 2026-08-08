import uuid

from backend.app.engine.queue import ExecutionQueue


def test_queue_enqueue():
    shared_list = []
    queue = ExecutionQueue(shared_list)

    t1 = uuid.uuid4()
    queue.enqueue(t1)

    assert len(shared_list) == 1
    assert shared_list[0] == t1
    assert queue.size() == 1
    assert queue.is_empty() is False

    # test duplicate prevention
    queue.enqueue(t1)
    assert queue.size() == 1


def test_queue_dequeue():
    t1, t2 = uuid.uuid4(), uuid.uuid4()
    shared_list = [t1, t2]
    queue = ExecutionQueue(shared_list)

    popped = queue.dequeue()
    assert popped == t1
    assert queue.size() == 1

    assert queue.peek() == t2

    queue.dequeue()
    assert queue.is_empty() is True
    assert queue.dequeue() is None
    assert queue.peek() is None
