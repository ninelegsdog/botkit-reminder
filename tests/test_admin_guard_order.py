"""Админ-гард обязан стоять вплотную к обработчику, под декоратором роутера.

`@admin_only` / `@require_admin` оборачивают обработчик, а декоратор роутера
(`@router.message(...)`, `@admin.callback_query(...)`) регистрирует ту функцию,
которую получил. Декораторы применяются снизу вверх, поэтому строка роутера должна
идти СВЕРХУ, а гард — ПОСЛЕДНИМ, прямо над `def`. Тогда роутер регистрирует именно
завёрнутую функцию.

Если гард оказался выше роутера, роутер регистрирует голый обработчик, а обёртка
навешивается уже после регистрации и в рантайме не вызывается — админская
поверхность открыта любому. Ровно этот класс дефекта поймал кейс
`reminder-admin-guard` в botkit-farm: не-админ по кнопке «📊 Статистика» получал
статистику.

Проверка строчная намеренно: обработчики вложены в `create_*_router`, поэтому
интроспекция модуля не дотянется до зарегистрированных функций.
"""

from __future__ import annotations

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"

GUARD = re.compile(r"^\s*@(admin_only|require_admin)\b")
DECO = re.compile(r"^\s*@")
DEF = re.compile(r"^\s*(async\s+)?def\s")


def test_админ_гард_идёт_последним_декоратором() -> None:
    bad: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not GUARD.match(line):
                continue
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and DECO.match(lines[j]) and not DEF.match(lines[j]):
                bad.append(f"{path.relative_to(SRC)}:{i + 1}")

    assert not bad, (
        "гард стоит ВЫШЕ декоратора роутера (роутер зарегистрирует "
        "незащищённый обработчик, и гард не сработает) в:\n  "
        + "\n  ".join(bad)
        + "\nПоставьте строку @router.../@admin... выше, а @admin_only/@require_admin — "
        "последней, прямо над def."
    )
