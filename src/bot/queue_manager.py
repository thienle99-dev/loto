import asyncio
import logging
import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError

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
    retries: int = 0
    max_retries: int = 5

class QueueManager:
    """Quản lý hàng chờ chia vùng (Partitioned Queues) với cơ chế Retry & Rate Limit"""
    def __init__(self, num_workers: int = 8):
        self.num_workers = num_workers
        self.queues: List[asyncio.Queue] = [asyncio.Queue() for _ in range(num_workers)]
        self.workers = []
        self._running = False

    def _get_partition_index(self, chat_id: int) -> int:
        """Định tuyến chat_id vào một hàng chờ cố định bằng modulo nhanh"""
        return abs(chat_id) % self.num_workers

    async def add_job(self, chat_id: int, user_id: int, handler_func: Callable, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Thêm một công việc vào hàng chờ tương ứng với chat_id"""
        job = Job(
            chat_id=chat_id,
            user_id=user_id,
            handler_func=handler_func,
            update=update,
            context=context,
            created_at=time.time()
        )
        partition_idx = self._get_partition_index(chat_id)
        await self.queues[partition_idx].put(job)

    async def worker(self, worker_id: int):
        """Worker xử lý công việc với cơ chế Backoff & Retry"""
        logger.info(f"Resilient Worker {worker_id} started")
        queue = self.queues[worker_id]
        
        while self._running:
            job = await queue.get()
            try:
                await self._process_job(worker_id, job)
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Critical error in worker {worker_id}: {e}")
                queue.task_done() # Tránh treo queue nếu lỗi quá nặng

    async def _process_job(self, worker_id: int, job: Job):
        """Xử lý chi tiết một job với retry logic"""
        while job.retries <= job.max_retries:
            try:
                await job.handler_func(job.update, job.context)
                return # Thành công, thoát vòng lặp retry
                
            except RetryAfter as e:
                # Telegram yêu cầu chờ (Rate Limit 429)
                wait_time = e.retry_after + 0.1 # Thêm buffer nhỏ
                logger.warning(f"Worker {worker_id} hit Rate Limit. Sleeping {wait_time}s for chat {job.chat_id}")
                await asyncio.sleep(wait_time)
                # Không tăng retries vì đây là lỗi hệ thống (flood control), không phải lỗi logic
                continue
                
            except (TimedOut, NetworkError) as e:
                job.retries += 1
                if job.retries > job.max_retries:
                    logger.error(f"Worker {worker_id} failed after {job.max_retries} retries for chat {job.chat_id}: {e}")
                    break
                
                # Exponential backoff: 2^retries + jitter
                sleep_time = (2 ** job.retries) + (random.uniform(0, 1))
                logger.warning(f"Worker {worker_id} temporary error ({type(e).__name__}). Retry {job.retries}/{job.max_retries} in {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                # Lỗi logic app hoặc lỗi không thể retry
                logger.error(f"Worker {worker_id} non-retryable error in chat {job.chat_id}: {e}", exc_info=True)
                break

    def start(self):
        """Bắt đầu partitioned worker pool"""
        if self._running:
            return
        self._running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self.worker(i))
            self.workers.append(task)
        logger.info(f"Resilient QueueManager started with {self.num_workers} workers")

    async def stop(self):
        """Dừng worker pool"""
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers = []
        logger.info("Resilient QueueManager stopped")

# Global instance
queue_manager = QueueManager(num_workers=8)
