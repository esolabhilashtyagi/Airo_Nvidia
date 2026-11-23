"""
Async Scheduler and Task Queue for executing background pipeline runs.
"""

import asyncio
from typing import Callable, Coroutine, Any, List
from .logging import logger


class TaskScheduler:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self._running = False

    async def add_task(self, coro_func: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs):
        await self.queue.put((coro_func, args, kwargs))

    async def start(self, num_workers: int = 2):
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self.workers.append(task)
        logger.info(f"TaskScheduler started with {num_workers} async worker(s).")

    async def _worker(self, worker_id: int):
        while self._running:
            try:
                coro_func, args, kwargs = await self.queue.get()
                try:
                    await coro_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Task execution error in worker {worker_id}: {e}", exc_info=True)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} loop encountered unexpected error: {e}")

    async def stop(self):
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
