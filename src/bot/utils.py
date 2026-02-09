import asyncio
from datetime import datetime, timedelta
from telegram import Update
from src.bot.constants import TICKET_DISPLAY_NAMES, stats, last_results, BET_AMOUNT
from src.db.sqlite_store import load_stats, load_last_result
from src.bot.session_manager import SessionManager

session_manager = SessionManager()

def ticket_display_name(code: str) -> str:
    """Trả về tên hiển thị của vé, hoặc mã gốc nếu không có map."""
    return TICKET_DISPLAY_NAMES.get(code, code)

def escape_markdown(text: str) -> str:
    """Escape các ký tự đặc biệt trong Markdown"""
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def get_chat_stats(chat_id: int) -> dict:
    """
    Lấy thống kê cho một chat (Async).
    Ưu tiên cache RAM, nếu chưa có thì load từ SQLite.
    """
    chat_stats = stats.get(chat_id)
    if chat_stats is not None:
        return chat_stats

    loaded = await asyncio.to_thread(load_stats, chat_id)
    if loaded:
        stats[chat_id] = loaded
        return loaded

    # Nếu chưa có trong DB thì khởi tạo rỗng
    empty = {"wins": {}, "participations": {}}
    stats[chat_id] = empty
    return empty

async def get_last_result_for_chat(chat_id: int) -> dict | None:
    """
    Lấy kết quả game gần nhất cho một chat (Async).
    Ưu tiên cache RAM, nếu chưa có thì load từ SQLite.
    """
    data = last_results.get(chat_id)
    if data is not None:
        return data

    loaded = await asyncio.to_thread(load_last_result, chat_id)
    if loaded:
        last_results[chat_id] = loaded
        return loaded
    return None

def is_session_expired(session) -> bool:
    """Kiểm tra session có hết hạn do lâu không hoạt động (không quay số) hay không."""
    if not hasattr(session, "last_activity"):
        return False
    
    # 2 giờ không có hoạt động thì coi như hết hạn
    expiry_limit = timedelta(hours=2)
    return datetime.now() - session.last_activity > expiry_limit

async def ensure_active_session(update: Update, chat_id: int, session) -> bool:
    """
    Đảm bảo session còn hiệu lực (Async).
    Nếu đã hết hạn: xoá session, thông báo cho user và trả về False.
    """
    if is_session_expired(session):
        await session_manager.delete_session(chat_id)
        # Handle cases where update.message might be None (e.g. CallbackQuery)
        msg_target = update.message if update.message else update.callback_query.message
        await msg_target.reply_text(
            "⏱️ *Game đã hết hạn do quá lâu không quay số\\!* \n\n"
            "Host hãy dùng `/moi <tên_game>` hoặc `/pham_vi <x> <y>` để tạo game mới nhé.",
            parse_mode="Markdown",
        )
        return False
    return True
def calculate_round_tokens(games: list) -> dict:
    """
    Tính toán tổng token của các user trong một danh sách các game (vòng chơi).
    Trả về: {uid: {"name": name, "token": float}}
    """
    user_tokens = {}
    bet_amount = BET_AMOUNT

    for game in games:
        partics = game.get("participants", [])
        winners = game.get("winners", [])
        total_players = len(partics)
        
        # Xác định winners ID (ép kiểu int)
        winner_ids = set()
        for w in winners:
            raw_id = w.get("user_id")
            if raw_id is not None:
                try:
                    winner_ids.add(int(raw_id))
                except (ValueError, TypeError):
                    pass
        
        num_winners = len(winner_ids)
        token_win = 0
        if num_winners > 0:
            token_win = (total_players * bet_amount / num_winners) - bet_amount
            for p in partics:
                raw_uid = p.get("user_id")
                if raw_uid is None: continue
                try:
                    uid = int(raw_uid)
                except (ValueError, TypeError):
                    continue
                    
                name = p.get("name") or str(uid)
                
                if uid not in user_tokens:
                    user_tokens[uid] = {"name": name, "token": 0.0}
                
                # Update name mới nhất
                user_tokens[uid]["name"] = name
                
                if uid in winner_ids:
                    user_tokens[uid]["token"] += token_win
                else:
                    user_tokens[uid]["token"] -= bet_amount
        else:
            # Nếu không có ai thắng, vẫn khởi tạo user_tokens cho những người tham gia (nếu chưa có)
            # để đảm bảo họ hiện diện trong danh sách với token là 0
            for p in partics:
                raw_uid = p.get("user_id")
                if raw_uid is None: continue
                try:
                    uid = int(raw_uid)
                except (ValueError, TypeError):
                    continue
                name = p.get("name") or str(uid)
                if uid not in user_tokens:
                    user_tokens[uid] = {"name": name, "token": 0.0}
                user_tokens[uid]["name"] = name
                
    return user_tokens

def get_round_leaderboard_text(round_name: str, user_tokens: dict) -> str:
    """
    Tạo nội dung text cho bảng xếp hạng vòng chơi.
    """
    players = list(user_tokens.values())
    if not players:
        return "ℹ️ Chưa có dữ liệu người chơi trong vòng này."

    top_rich = sorted([p for p in players if p["token"] > 0], key=lambda x: x["token"], reverse=True)[:10]
    top_poor = sorted(players, key=lambda x: x["token"])[:10]
    top_poor = [p for p in top_poor if p["token"] < 0]

    message = f"🏆 *BXH TOKEN VÒNG: {escape_markdown(round_name)}*\n"
    message += "━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Top Đại Gia
    message += "💎 *TOP ĐẠI GIA:*\n"
    if top_rich:
        for i, p in enumerate(top_rich, 1):
            token = p["token"]
            prefix = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            txt_token = f"+{token:.1f}" if token > 0 else f"{token:.1f}"
            message += f"{prefix} {escape_markdown(p['name'])}: `{txt_token}`\n"
    else:
        message += "_(Chưa có ai)_\n"
    message += "\n"
    
    # Top Xa Bờ
    message += "🌊 *TOP XA BỜ:*\n"
    if top_poor:
        for i, p in enumerate(top_poor, 1):
            token = p["token"]
            message += f"{i}. {escape_markdown(p['name'])}: `{token:.1f}`\n"
    else:
        message += "_(Tất cả đều đang lời hoặc hòa)_\n"
        
    message += "\n━━━━━━━━━━━━━━━━━━━"
    return message
