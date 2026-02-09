import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

@dataclass
class Job:
    """Đại diện cho một công việc trong hàng đợi"""
    chat_id: int
    user_id: int
    handler_func: Callable
    update: Update
    context: ContextTypes.DEFAULT_TYPE
    created_at: float

class QueueManager:
    """Quản lý hàng đợi công việc và Worker Pool"""
    def __init__(self, num_workers: int = 4):
        self.queue = asyncio.Queue()
        self.num_workers = num_workers
        self.workers = []
        self._chat_locks: Dict[int, asyncio.Lock] = {}
        self._running = False

    def get_chat_lock(self, chat_id: int) -> asyncio.Lock:
        """Lấy hoặc tạo lock cho từng chat để đảm bảo thứ tự xử lý"""
        if chat_id not in self._chat_locks:
            self._chat_locks[chat_id] = asyncio.Lock()
        return self._chat_locks[chat_id]

    async def add_job(self, chat_id: int, user_id: int, handler_func: Callable, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Thêm một công việc mới vào hàng đợi"""
        job = Job(
            chat_id=chat_id,
            user_id=user_id,
            handler_func=handler_func,
            update=update,
            context=context,
            created_at=asyncio.get_event_loop().time()
        )
        await self.queue.put(job)
        # logger.debug(f"Job added to queue for chat {chat_id}")

    async def worker(self, worker_id: int):
        """Worker xử lý công việc từ hàng đợi"""
        logger.info(f"Worker {worker_id} started")
        while self._running:
            try:
                # Lấy job từ queue
                job = await self.queue.get()
                
                # Sử dụng lock theo chat để đảm bảo tin nhắn không bị chồng chéo/mất thứ tự trong 1 chat
                lock = self.get_chat_lock(job.chat_id)
                async with lock:
                    try:
                        # logger.info(f"Worker {worker_id} processing job for chat {job.chat_id}")
                        await job.handler_func(job.update, job.context)
                    except Exception as e:
                        logger.error(f"Error in worker {worker_id} processing job: {e}", exc_info=True)
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}")
                await asyncio.sleep(1)

    def start(self):
        """Bắt đầu worker pool"""
        if self._running:
            return
        self._running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self.worker(i))
            self.workers.append(task)
        logger.info(f"QueueManager started with {self.num_workers} workers")

    async def stop(self):
        """Dừng worker pool"""
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers = []
        logger.info("QueueManager stopped")

# Global instance
queue_manager = QueueManager(num_workers=8)
