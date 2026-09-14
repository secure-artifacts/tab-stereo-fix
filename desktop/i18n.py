"""UI language. Detects Windows UI language; unknown locales use English."""

from __future__ import annotations

import locale

SUPPORTED = ("zh", "en", "ru", "uk")
LANG = "en"

STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "window_title": "立体声修复 - 选用户",
        "app_name": "立体声修复",
        "categories": "分类",
        "user_categories": "用户分类",
        "browsers": "浏览器",
        "new_category": "新建分类",
        "rename": "重命名",
        "delete_category": "删除分类",
        "category_name": "分类名称：",
        "rename_category": "重命名分类",
        "new_name": "新的名称：",
        "help": "使用说明",
        "hide_help": "收起说明",
        "header_hint": "关掉 Wide AEC，让浏览器声音进入 VoiceMeeter / AUX / CABLE / Line 1。必须从本软件点「打开」。",
        "help_text": (
            "1. 选一个用户，点「打开（关掉 Wide AEC）」。浏览器必须由本软件启动。\n"
            "2. 关掉这套浏览器后，不能从任务栏、开始菜单或桌面图标再开。"
            "那样声音进不了 VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1。\n"
            "3. 要继续用，再打开本软件，选同一用户，再点「打开」。\n"
            "4. 要恢复原来的回声消除，选同一用户，点「关闭（恢复）」。\n"
            "5. 只动你选的这一套。其它浏览器不关。不改 VoiceMeeter / AUX / CABLE / Line 1。\n"
            "6. 「开机启动」只打开本软件窗口，不会自动打开浏览器。开机后仍要点「打开」。"
        ),
        "scanning": "正在扫描…",
        "pick_user": "选择一个用户",
        "search_users": "搜索用户名字",
        "progress_hint": "选好后点「打开」。关掉浏览器后，必须再回到这里点「打开」，不要从图标自己开。",
        "gain": "这套浏览器增益",
        "refresh": "刷新",
        "autostart_on": "开机启动：开",
        "autostart_off": "开机启动：关",
        "boost_volume": "只加大这套音量",
        "close_restore": "关闭（恢复）",
        "open_fix": "打开（关掉 Wide AEC）",
        "log_must_open": "必须从本软件点「打开」启动浏览器。",
        "log_no_icon": "关掉后再从任务栏/开始菜单/桌面图标打开，声音进不了立体声混音。",
        "log_one_user": "只打开你选的那一个用户。其它浏览器不关、不改音量。",
        "scan_failed": "扫描失败：{error}",
        "no_browsers": "没有可处理的浏览器。",
        "no_browser_found": "没有找到可用的浏览器。",
        "no_matching_users": "没有符合条件的用户。",
        "running": "正在运行",
        "not_running": "未运行",
        "fixed": "已修复",
        "not_fixed": "未修复",
        "install_status": "{browser}（{run} · {fix}）",
        "current_user": "当前：{label}。只打开这一个。{stay}",
        "others_idle": " 其它浏览器完全不动：{names}。",
        "click_open": "点「打开」启动 {label}。关掉后必须再从本软件打开，从图标自己开声音进不了立体声混音。",
        "autostart": "开机启动",
        "autostart_fail": "没能改开机启动。",
        "autostart_enabled": "已打开开机启动。开机后只出现本软件，仍要点「打开」才能启动浏览器。",
        "autostart_disabled": "已关闭开机启动。",
        "not_selected": "还没选",
        "pick_a_user": "请先选一个用户。",
        "volume_ok": "已拉满 {browser} 的系统音量（{count} 个会话）。",
        "others_line": "\n其它浏览器完全不动：{names}",
        "same_running": "\n同一套里正在开的「{names}」会先关掉，然后只打开你选的这个。",
        "same_not_opened": "\n同一套里的其它用户不会被打开。",
        "open_action": "打开（关掉 Wide AEC）",
        "close_action": "关闭（恢复原来的回声消除）",
        "confirm_open": (
            "只打开这一个用户：\n· {label}{same}{stay}\n\n"
            "关掉后再从任务栏或图标打开，声音进不了立体声混音。必须再回到本软件点「打开」。\n\n继续？"
        ),
        "opening": "正在打开 {label}…",
        "not_done": "没有完成。",
        "done": "完成",
        "done_ok": "已完成。其它浏览器没有动。",
        "done_open": "已打开。以后这套浏览器关掉了，必须再从本软件点「打开」。从任务栏或图标自己开，声音进不了立体声混音。",
        "done_close": "已关闭。这套浏览器恢复原来的回声消除。",
        "all": "全部",
        "uncategorized": "未分类",
        "work": "工作",
        "personal": "个人",
        "rename_pick_user_cat": "请先点左边的用户分类。浏览器分类不能改名。",
        "rename_reserved": "「全部」和「未分类」不能改名。",
        "delete_pick_user_cat": "请先点左边的用户分类。浏览器分类不能删除。",
        "delete_reserved": "「全部」和「未分类」不能删除。",
        "delete_confirm": "删除「{name}」？里面的用户会回到「未分类」。",
        "empty_category": "分类名不能为空",
        "bad_category_name": "不能使用这个名称",
        "cannot_rename": "这个分类不能改名",
        "no_such_category": "没有这个分类",
        "category_exists": "已有同名分类",
        "closing_browser": "正在关闭 {browser}…",
        "writing_settings": "正在写入 {browser} 的设置…",
        "remembering_launch": "正在记住 {browser} 的启动方式…",
        "opening_user": "正在打开你选的用户…",
        "progress_done": "完成",
    },
    "en": {
        "window_title": "Stereo Fix - Pick a user",
        "app_name": "Stereo Fix",
        "categories": "Categories",
        "user_categories": "User categories",
        "browsers": "Browsers",
        "new_category": "New category",
        "rename": "Rename",
        "delete_category": "Delete category",
        "category_name": "Category name:",
        "rename_category": "Rename category",
        "new_name": "New name:",
        "help": "Help",
        "hide_help": "Hide help",
        "header_hint": "Turn off Wide AEC so browser audio can reach VoiceMeeter / AUX / CABLE / Line 1. You must click Open in this app.",
        "help_text": (
            "1. Select a user and click Open (turn off Wide AEC). The browser must be started from this app.\n"
            "2. After you close that browser, do not open it from the taskbar, Start menu, or desktop shortcut. "
            "Audio will not reach VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1.\n"
            "3. To keep using it, open this app again, select the same user, and click Open.\n"
            "4. To restore the original echo cancellation, select the same user and click Close (restore).\n"
            "5. Only the selected browser is changed. Other browsers stay untouched. VoiceMeeter / AUX / CABLE / Line 1 are not changed.\n"
            "6. Autostart only opens this app, not the browser. After login you still need to click Open."
        ),
        "scanning": "Scanning…",
        "pick_user": "Select a user",
        "search_users": "Search users",
        "progress_hint": "Select a user and click Open. After closing the browser, come back here and click Open. Do not start it from an icon.",
        "gain": "Gain for this browser",
        "refresh": "Refresh",
        "autostart_on": "Autostart: On",
        "autostart_off": "Autostart: Off",
        "boost_volume": "Boost this volume",
        "close_restore": "Close (restore)",
        "open_fix": "Open (turn off Wide AEC)",
        "log_must_open": "You must click Open in this app to start the browser.",
        "log_no_icon": "If you start it from the taskbar, Start menu, or desktop icon, audio will not reach stereo mix.",
        "log_one_user": "Only the selected user is opened. Other browsers are not closed or retuned.",
        "scan_failed": "Scan failed: {error}",
        "no_browsers": "No browsers to process.",
        "no_browser_found": "No Chrome / Edge / Brave / Vivaldi found.",
        "no_matching_users": "No matching users.",
        "running": "running",
        "not_running": "not running",
        "fixed": "fixed",
        "not_fixed": "not fixed",
        "install_status": "{browser} ({run} · {fix})",
        "current_user": "Current: {label}. Only this one will be opened.{stay}",
        "others_idle": " Other browsers stay untouched: {names}.",
        "click_open": "Click Open to start {label}. After it is closed you must open it from this app, or audio will not reach stereo mix.",
        "autostart": "Autostart",
        "autostart_fail": "Could not change autostart.",
        "autostart_enabled": "Autostart is on. At login only this app opens; you still need to click Open.",
        "autostart_disabled": "Autostart is off.",
        "not_selected": "Nothing selected",
        "pick_a_user": "Select a user first.",
        "volume_ok": "Set {browser} session volume to max ({count} sessions).",
        "others_line": "\nOther browsers stay untouched: {names}",
        "same_running": "\nRunning users in the same install ({names}) will be closed first, then only your selection is opened.",
        "same_not_opened": "\nOther users in the same install will not be opened.",
        "open_action": "Open (turn off Wide AEC)",
        "close_action": "Close (restore echo cancellation)",
        "confirm_open": (
            "Open only this user:\n· {label}{same}{stay}\n\n"
            "If you start it again from the taskbar or an icon, audio will not reach stereo mix. Come back here and click Open.\n\nContinue?"
        ),
        "opening": "Opening {label}…",
        "not_done": "Not completed.",
        "done": "Done",
        "done_ok": "Done. Other browsers were not changed.",
        "done_open": "Opened. After this browser is closed, you must click Open in this app. Starting it from an icon will not reach stereo mix.",
        "done_close": "Closed. This browser’s original echo cancellation is restored.",
        "all": "All",
        "uncategorized": "Uncategorized",
        "work": "Work",
        "personal": "Personal",
        "rename_pick_user_cat": "Select a user category on the left. Browser groups cannot be renamed.",
        "rename_reserved": "All and Uncategorized cannot be renamed.",
        "delete_pick_user_cat": "Select a user category on the left. Browser groups cannot be deleted.",
        "delete_reserved": "All and Uncategorized cannot be deleted.",
        "delete_confirm": "Delete “{name}”? Users in it will go back to Uncategorized.",
        "empty_category": "Category name cannot be empty",
        "bad_category_name": "This name cannot be used",
        "cannot_rename": "This category cannot be renamed",
        "no_such_category": "That category does not exist",
        "category_exists": "A category with this name already exists",
        "closing_browser": "Closing {browser}…",
        "writing_settings": "Writing {browser} settings…",
        "remembering_launch": "Remembering how {browser} starts…",
        "opening_user": "Opening the selected user…",
        "progress_done": "Done",
    },
    "ru": {
        "window_title": "Исправление стерео — выбор пользователя",
        "app_name": "Исправление стерео",
        "categories": "Категории",
        "user_categories": "Категории пользователей",
        "browsers": "Браузеры",
        "new_category": "Новая категория",
        "rename": "Переименовать",
        "delete_category": "Удалить категорию",
        "category_name": "Название категории:",
        "rename_category": "Переименовать категорию",
        "new_name": "Новое имя:",
        "help": "Справка",
        "hide_help": "Скрыть справку",
        "header_hint": "Отключите Wide AEC, чтобы звук браузера шёл в VoiceMeeter / AUX / CABLE / Line 1. Браузер нужно открывать кнопкой «Открыть» в этой программе.",
        "help_text": (
            "1. Выберите пользователя и нажмите «Открыть (выключить Wide AEC)». Браузер должен запускаться из этой программы.\n"
            "2. После закрытия браузера не открывайте его с панели задач, из меню «Пуск» или с ярлыка. "
            "Звук не попадёт в VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1.\n"
            "3. Чтобы продолжить, снова откройте эту программу, выберите того же пользователя и нажмите «Открыть».\n"
            "4. Чтобы вернуть исходное эхоподавление, выберите того же пользователя и нажмите «Закрыть (восстановить)».\n"
            "5. Меняется только выбранный браузер. Остальные не трогаются. VoiceMeeter / AUX / CABLE / Line 1 не меняются.\n"
            "6. Автозапуск открывает только эту программу, не браузер. После входа всё равно нужно нажать «Открыть»."
        ),
        "scanning": "Сканирование…",
        "pick_user": "Выберите пользователя",
        "search_users": "Поиск пользователей",
        "progress_hint": "Выберите пользователя и нажмите «Открыть». После закрытия браузера вернитесь сюда и снова нажмите «Открыть», не запускайте его с ярлыка.",
        "gain": "Усиление этого браузера",
        "refresh": "Обновить",
        "autostart_on": "Автозапуск: вкл.",
        "autostart_off": "Автозапуск: выкл.",
        "boost_volume": "Увеличить эту громкость",
        "close_restore": "Закрыть (восстановить)",
        "open_fix": "Открыть (выключить Wide AEC)",
        "log_must_open": "Браузер нужно запускать кнопкой «Открыть» в этой программе.",
        "log_no_icon": "Если открыть его с панели задач, из меню «Пуск» или с ярлыка, звук не попадёт в стереомикшер.",
        "log_one_user": "Открывается только выбранный пользователь. Другие браузеры не закрываются и не перенастраиваются.",
        "scan_failed": "Ошибка сканирования: {error}",
        "no_browsers": "Нет браузеров для обработки.",
        "no_browser_found": "Chrome / Edge / Brave / Vivaldi не найдены.",
        "no_matching_users": "Нет подходящих пользователей.",
        "running": "запущен",
        "not_running": "не запущен",
        "fixed": "исправлено",
        "not_fixed": "не исправлено",
        "install_status": "{browser} ({run} · {fix})",
        "current_user": "Сейчас: {label}. Будет открыт только он.{stay}",
        "others_idle": " Другие браузеры не затрагиваются: {names}.",
        "click_open": "Нажмите «Открыть», чтобы запустить {label}. После закрытия открывайте его только из этой программы, иначе звук не попадёт в стереомикшер.",
        "autostart": "Автозапуск",
        "autostart_fail": "Не удалось изменить автозапуск.",
        "autostart_enabled": "Автозапуск включён. При входе открывается только эта программа; браузер всё равно нужно открыть кнопкой «Открыть».",
        "autostart_disabled": "Автозапуск выключен.",
        "not_selected": "Не выбрано",
        "pick_a_user": "Сначала выберите пользователя.",
        "volume_ok": "Громкость {browser} установлена на максимум ({count} сеансов).",
        "others_line": "\nДругие браузеры не затрагиваются: {names}",
        "same_running": "\nОткрытые пользователи этой же установки («{names}») будут закрыты, затем откроется только выбранный.",
        "same_not_opened": "\nДругие пользователи этой же установки не будут открыты.",
        "open_action": "Открыть (выключить Wide AEC)",
        "close_action": "Закрыть (восстановить эхоподавление)",
        "confirm_open": (
            "Открыть только этого пользователя:\n· {label}{same}{stay}\n\n"
            "Если потом открыть браузер с панели задач или с ярлыка, звук не попадёт в стереомикшер. Нужно снова нажать «Открыть» здесь.\n\nПродолжить?"
        ),
        "opening": "Открытие {label}…",
        "not_done": "Не выполнено.",
        "done": "Готово",
        "done_ok": "Готово. Другие браузеры не изменялись.",
        "done_open": "Открыто. После закрытия этого браузера снова нажмите «Открыть» в этой программе. Запуск с ярлыка не даст звук в стереомикшер.",
        "done_close": "Закрыто. Исходное эхоподавление этого браузера восстановлено.",
        "all": "Все",
        "uncategorized": "Без категории",
        "work": "Работа",
        "personal": "Личное",
        "rename_pick_user_cat": "Сначала выберите категорию пользователя слева. Группы браузеров нельзя переименовывать.",
        "rename_reserved": "«Все» и «Без категории» нельзя переименовать.",
        "delete_pick_user_cat": "Сначала выберите категорию пользователя слева. Группы браузеров нельзя удалять.",
        "delete_reserved": "«Все» и «Без категории» нельзя удалить.",
        "delete_confirm": "Удалить «{name}»? Пользователи из неё вернутся в «Без категории».",
        "empty_category": "Название категории не может быть пустым",
        "bad_category_name": "Это имя использовать нельзя",
        "cannot_rename": "Эту категорию нельзя переименовать",
        "no_such_category": "Такой категории нет",
        "category_exists": "Категория с таким именем уже есть",
        "closing_browser": "Закрытие {browser}…",
        "writing_settings": "Запись настроек {browser}…",
        "remembering_launch": "Запоминание способа запуска {browser}…",
        "opening_user": "Открытие выбранного пользователя…",
        "progress_done": "Готово",
    },
    "uk": {
        "window_title": "Виправлення стерео — вибір користувача",
        "app_name": "Виправлення стерео",
        "categories": "Категорії",
        "user_categories": "Категорії користувачів",
        "browsers": "Браузери",
        "new_category": "Нова категорія",
        "rename": "Перейменувати",
        "delete_category": "Видалити категорію",
        "category_name": "Назва категорії:",
        "rename_category": "Перейменувати категорію",
        "new_name": "Нова назва:",
        "help": "Довідка",
        "hide_help": "Сховати довідку",
        "header_hint": "Вимкніть Wide AEC, щоб звук браузера йшов у VoiceMeeter / AUX / CABLE / Line 1. Браузер потрібно відкривати кнопкою «Відкрити» в цій програмі.",
        "help_text": (
            "1. Виберіть користувача й натисніть «Відкрити (вимкнути Wide AEC)». Браузер має запускатися з цієї програми.\n"
            "2. Після закриття браузера не відкривайте його з панелі завдань, меню «Пуск» або ярлика. "
            "Звук не потрапить у VoiceMeeter / VoiceMeeter AUX / CABLE / Line 1.\n"
            "3. Щоб продовжити, знову відкрийте цю програму, виберіть того самого користувача й натисніть «Відкрити».\n"
            "4. Щоб повернути початкове приглушення луни, виберіть того самого користувача й натисніть «Закрити (відновити)».\n"
            "5. Змінюється лише вибраний браузер. Інші не чіпаються. VoiceMeeter / AUX / CABLE / Line 1 не змінюються.\n"
            "6. Автозапуск відкриває лише цю програму, не браузер. Після входу все одно потрібно натиснути «Відкрити»."
        ),
        "scanning": "Сканування…",
        "pick_user": "Виберіть користувача",
        "search_users": "Пошук користувачів",
        "progress_hint": "Виберіть користувача й натисніть «Відкрити». Після закриття браузера поверніться сюди й знову натисніть «Відкрити», не запускайте його з ярлика.",
        "gain": "Підсилення цього браузера",
        "refresh": "Оновити",
        "autostart_on": "Автозапуск: увімк.",
        "autostart_off": "Автозапуск: вимк.",
        "boost_volume": "Збільшити цю гучність",
        "close_restore": "Закрити (відновити)",
        "open_fix": "Відкрити (вимкнути Wide AEC)",
        "log_must_open": "Браузер потрібно запускати кнопкою «Відкрити» в цій програмі.",
        "log_no_icon": "Якщо відкрити його з панелі завдань, меню «Пуск» або ярлика, звук не потрапить у стереомікшер.",
        "log_one_user": "Відкривається лише вибраний користувач. Інші браузери не закриваються й не переналаштовуються.",
        "scan_failed": "Помилка сканування: {error}",
        "no_browsers": "Немає браузерів для обробки.",
        "no_browser_found": "Chrome / Edge / Brave / Vivaldi не знайдено.",
        "no_matching_users": "Немає відповідних користувачів.",
        "running": "запущено",
        "not_running": "не запущено",
        "fixed": "виправлено",
        "not_fixed": "не виправлено",
        "install_status": "{browser} ({run} · {fix})",
        "current_user": "Зараз: {label}. Буде відкрито лише його.{stay}",
        "others_idle": " Інші браузери не змінюються: {names}.",
        "click_open": "Натисніть «Відкрити», щоб запустити {label}. Після закриття відкривайте його лише з цієї програми, інакше звук не потрапить у стереомікшер.",
        "autostart": "Автозапуск",
        "autostart_fail": "Не вдалося змінити автозапуск.",
        "autostart_enabled": "Автозапуск увімкнено. Після входу відкривається лише ця програма; браузер усе одно потрібно відкрити кнопкою «Відкрити».",
        "autostart_disabled": "Автозапуск вимкнено.",
        "not_selected": "Нічого не вибрано",
        "pick_a_user": "Спочатку виберіть користувача.",
        "volume_ok": "Гучність {browser} встановлено на максимум ({count} сеансів).",
        "others_line": "\nІнші браузери не змінюються: {names}",
        "same_running": "\nВідкриті користувачі цієї ж установки («{names}») будуть закриті, потім відкриється лише вибраний.",
        "same_not_opened": "\nІнші користувачі цієї ж установки не будуть відкриті.",
        "open_action": "Відкрити (вимкнути Wide AEC)",
        "close_action": "Закрити (відновити приглушення луни)",
        "confirm_open": (
            "Відкрити лише цього користувача:\n· {label}{same}{stay}\n\n"
            "Якщо потім відкрити браузер з панелі завдань або ярлика, звук не потрапить у стереомікшер. Потрібно знову натиснути «Відкрити» тут.\n\nПродовжити?"
        ),
        "opening": "Відкриття {label}…",
        "not_done": "Не виконано.",
        "done": "Готово",
        "done_ok": "Готово. Інші браузери не змінювалися.",
        "done_open": "Відкрито. Після закриття цього браузера знову натисніть «Відкрити» в цій програмі. Запуск з ярлика не дасть звук у стереомікшер.",
        "done_close": "Закрито. Початкове приглушення луни цього браузера відновлено.",
        "all": "Усі",
        "uncategorized": "Без категорії",
        "work": "Робота",
        "personal": "Особисте",
        "rename_pick_user_cat": "Спочатку виберіть категорію користувача ліворуч. Групи браузерів не можна перейменовувати.",
        "rename_reserved": "«Усі» та «Без категорії» не можна перейменувати.",
        "delete_pick_user_cat": "Спочатку виберіть категорію користувача ліворуч. Групи браузерів не можна видаляти.",
        "delete_reserved": "«Усі» та «Без категорії» не можна видалити.",
        "delete_confirm": "Видалити «{name}»? Користувачі з неї повернуться до «Без категорії».",
        "empty_category": "Назва категорії не може бути порожньою",
        "bad_category_name": "Цю назву використовувати не можна",
        "cannot_rename": "Цю категорію не можна перейменувати",
        "no_such_category": "Такої категорії немає",
        "category_exists": "Категорія з такою назвою вже є",
        "closing_browser": "Закриття {browser}…",
        "writing_settings": "Запис налаштувань {browser}…",
        "remembering_launch": "Запам’ятовування способу запуску {browser}…",
        "opening_user": "Відкриття вибраного користувача…",
        "progress_done": "Готово",
    },
}


def language_from_code(code: str | None) -> str:
    text = (code or "").strip().lower().replace("_", "-")
    if text.startswith("zh"):
        return "zh"
    if text.startswith("ru"):
        return "ru"
    if text.startswith("uk"):
        return "uk"
    return "en"


def detect_language() -> str:
    try:
        import ctypes

        langid = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
        primary = langid & 0xFF
        if primary == 0x04:
            return "zh"
        if primary == 0x19:
            return "ru"
        if primary == 0x22:
            return "uk"
    except Exception:
        pass
    code = ""
    try:
        code = locale.getlocale()[0] or ""
    except Exception:
        code = ""
    if not code:
        try:
            code = locale.getdefaultlocale()[0] or ""
        except Exception:
            code = ""
    return language_from_code(code)


def set_language(code: str) -> str:
    global LANG
    LANG = code if code in SUPPORTED else "en"
    return LANG


def t(key: str, **kwargs) -> str:
    table = STRINGS.get(LANG) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        return text.format(**kwargs)
    return text


def all_window_titles() -> tuple[str, ...]:
    return tuple(dict.fromkeys(STRINGS[lang]["window_title"] for lang in SUPPORTED))


def ui_font(size: int, bold: bool = False):
    family = "Microsoft YaHei UI" if LANG == "zh" else "Segoe UI"
    return (family, size, "bold" if bold else "normal")


def category_label(name: str) -> str:
    mapping = {
        "全部": t("all"),
        "未分类": t("uncategorized"),
        "工作": t("work"),
        "个人": t("personal"),
    }
    return mapping.get(name, name)


def category_from_label(label: str, names: list[str]) -> str:
    for name in names:
        if category_label(name) == label:
            return name
    return label


set_language(detect_language())
