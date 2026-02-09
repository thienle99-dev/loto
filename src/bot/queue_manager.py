import asyncio
import logging
import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
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
    """Quản lý hàng chờ chia vùng (Partitioned Queues) và Worker Pool"""
    def __init__(self, num_workers: int = 8):
        self.num_workers = num_workers
        # Mỗi worker sẽ có một hàng chờ riêng
        self.queues: List[asyncio.Queue] = [asyncio.Queue() for _ in range(num_workers)]
        self.workers = []
        self._running = False

    def _get_partition_index(self, chat_id: int) -> int:
        """Định tuyến chat_id vào một hàng chờ cố định bằng hash"""
        # Sử dụng hash để đảm bảo phân phối đều và ổn định
        hash_val = int(hashlib.md5(str(chat_id).encode()).hexdigest(), 16)
        return hash_val % self.num_workers

    async def add_job(self, chat_id: int, user_id: int, handler_func: Callable, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Thêm một công việc vào hàng chờ tương ứng với chat_id"""
        job = Job(
            chat_id=chat_id,
            user_id=user_id,
            handler_func=handler_func,
            update=update,
            context=context,
            created_at=asyncio.get_event_loop().time()
        )
        partition_idx = self._get_partition_index(chat_id)
        await self.queues[partition_idx].put(job)
        # logger.debug(f"Job for chat {chat_id} added to partition {partition_idx}")

    async def worker(self, worker_id: int):
        """Worker xử lý công việc từ hàng chờ riêng của mình (Tuần tự tuyệt đối trong queue này)"""
        logger.info(f"Partitioned Worker {worker_id} started")
        queue = self.queues[worker_id]
        
        while self._running:
            try:
                # Lấy job từ queue riêng
                job = await queue.get()
                
                try:
                    # Xử lý tuần tự: worker này chỉ xử lý 1 job tại 1 thời điểm
                    # Vì chat_id được gán cố định vào worker này, các tin nhắn cùng chat sẽ luôn đúng thứ tự
                    await job.handler_func(job.update, job.context)
                except Exception as e:
                    logger.error(f"Error in partitioned worker {worker_id} processing chat {job.chat_id}: {e}", exc_info=True)
                
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Partitioned Worker {worker_id} unexpected error: {e}")
                await asyncio.sleep(1)

    def start(self):
        """Bắt đầu partitioned worker pool"""
        if self._running:
            return
        self._running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self.worker(i))
            self.workers.append(task)
        logger.info(f"Partitioned QueueManager started with {self.num_workers} dedicated workers")

    async def stop(self):
        """Dừng worker pool"""
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers = []
        logger.info("Partitioned QueueManager stopped")

# Global instance
queue_manager = QueueManager(num_workers=8)
