import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ⚠️ ЗАМЕНИТЕ НА НОВЫЙ ТОКЕН!
TOKEN = 'TOKEN'

USER_DATA = {}


class AddTask(StatesGroup):
    waiting_for_description = State()


def get_formatted_task_list(tasks):
    if not tasks:
        return "Список задач пуст."
    
    text = "📋 **Ваши задачи:**\n\n"
    for task in tasks:
        status_icon = "✅" if task['done'] else "⬜"
        text += f"{task['id']}. {status_icon} {task['text']}\n"
    return text


def create_task_keyboard(task_id: int, is_done: bool) -> InlineKeyboardMarkup:
    status_text = "Вернуть в работу" if is_done else "✅ Готово"
    status_action = "undone" if is_done else "done"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=status_text, callback_data=f'{status_action}:{task_id}'),
            InlineKeyboardButton(text='🗑️ Удалить', callback_data=f'delete:{task_id}')
        ]
    ])
    return keyboard


async def cmd_start(message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] - Received /start command.")
    await message.answer(f'Привет! Я — твой Менеджер Списка Дел.\n'
                         f'Используй:\n'
                         f'/add - добавить задачу\n'
                         f'/list - посмотреть список\n'
                         f'/manage - управление задачами')


async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer('Введите описание новой задачи: ')
    await state.set_state(AddTask.waiting_for_description)

async def process_description(message: types.Message, state: FSMContext):
    logging.info(f"[{message.from_user.id}] - Processing description in state: '{message.text}'")
    user_id = message.from_user.id
    task_text = message.text
    
    if user_id not in USER_DATA:
        USER_DATA[user_id] = []
    
    new_id = len(USER_DATA[user_id]) + 1
    
    new_task = {
        'id': new_id,
        'text': task_text,
        'done': False
    }
    
    USER_DATA[user_id].append(new_task)
    
    await message.answer(f'Задача "{task_text}" добавлена!')
    await state.clear()

async def cmd_list(message: types.Message):
    user_id = message.from_user.id
    tasks = USER_DATA.get(user_id, [])
    text = get_formatted_task_list(tasks)
    await message.answer(text)

async def cmd_manage(message: types.Message):
    user_id = message.from_user.id
    tasks = USER_DATA.get(user_id, [])
    
    if not tasks:
        await message.answer("Список задач пуст.")
        return

    await message.answer("👇 **Управление задачами:**")
    
    for task in tasks:
        status_icon = "✅" if task['done'] else "⬜"
        text = f"{task['id']}. {status_icon} {task['text']}"
        kb = create_task_keyboard(task['id'], task['done'])
        await message.answer(text, reply_markup=kb)

async def process_callback(call: types.CallbackQuery):
    action, task_id_str = call.data.split(':')
    task_id = int(task_id_str)
    user_id = call.from_user.id

    user_tasks = USER_DATA.get(user_id, [])
    
    target_task = None
    task_index = -1
    
    for i, task in enumerate(user_tasks):
        if task['id'] == task_id:
            target_task = task
            task_index = i
            break
            
    if not target_task:
        await call.answer("Задача не найдена (возможно, удалена).")
        return

    if action == "delete":
        user_tasks.pop(task_index)
        await call.message.delete()
        await call.answer("Задача удалена")
        return

    elif action in ["done", "undone"]:
        target_task['done'] = (action == "done")
        
        status_icon = "✅" if target_task['done'] else "⬜"
        new_text = f"{target_task['id']}. {status_icon} {target_task['text']}"
        new_kb = create_task_keyboard(target_task['id'], target_task['done'])
        
        await call.message.edit_text(new_text, reply_markup=new_kb)
        await call.answer("Статус обновлен")



async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, Command('start'))
    dp.message.register(cmd_add, Command('add'))
    dp.message.register(cmd_list, Command('list'))
    dp.message.register(cmd_manage, Command('manage'))
    
    dp.message.register(process_description, AddTask.waiting_for_description)
    
    dp.callback_query.register(process_callback, F.data.startswith(("done:", "undone:", "delete:")))

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())