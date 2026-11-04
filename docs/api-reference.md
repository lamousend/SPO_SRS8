# Справочник REST API (создан автоматически)

> Файл и машиночитаемая схема [openapi.json](openapi.json) создаются командой
> `python manage.py generate_api_docs` из реальных маршрутов, сериализаторов и
> моделей проекта. Вручную не редактируются; карточки методов с примерами -
> в [api.md](api.md).

## Маршруты

| Метод | URL | Обработчик | Действие | Успех | Права доступа |
|-------|-----|------------|----------|-------|---------------|
| GET | `/api/categories/` | `CategoryViewSet.list` | список объектов | 200 | IsAuthenticated |
| GET | `/api/categories/{id}/` | `CategoryViewSet.retrieve` | получение объекта | 200 | IsAuthenticated |
| GET | `/api/equipment/` | `EquipmentViewSet.list` | список объектов | 200 | IsAuthenticated |
| GET | `/api/equipment/{id}/` | `EquipmentViewSet.retrieve` | получение объекта | 200 | IsAuthenticated |
| GET | `/api/reservations/` | `ReservationViewSet.list` | список объектов | 200 | IsAuthenticated |
| POST | `/api/reservations/` | `ReservationViewSet.create` | создание объекта | 201 | IsAuthenticated |
| GET | `/api/reservations/{id}/` | `ReservationViewSet.retrieve` | получение объекта | 200 | IsAuthenticated |
| PUT | `/api/reservations/{id}/` | `ReservationViewSet.update` | полное изменение | 200 | IsAuthenticated |
| PATCH | `/api/reservations/{id}/` | `ReservationViewSet.partial_update` | частичное изменение | 200 | IsAuthenticated |
| DELETE | `/api/reservations/{id}/` | `ReservationViewSet.destroy` | удаление | 204 | IsAuthenticated |
| GET | `/api/reservations/{id}/history/` | `ReservationViewSet.history` | История событий бронирования по возрастанию времени | 200 | IsAuthenticated |
| POST | `/api/reservations/{id}/issue/` | `ReservationViewSet.issue` | Выдать оборудование: created → issued, остаток уменьшается (транзакция) | 200 | IsAuthenticated |
| POST | `/api/reservations/{id}/return_equipment/` | `ReservationViewSet.return_equipment` | Вернуть оборудование: issued → returned, остаток увеличивается (транзакция) | 200 | IsAuthenticated |
| GET | `/api/tickets/` | `TicketViewSet.list` | список объектов | 200 | IsAuthenticated |
| POST | `/api/tickets/` | `TicketViewSet.create` | создание объекта | 201 | IsAuthenticated |
| GET | `/api/tickets/{id}/` | `TicketViewSet.retrieve` | получение объекта | 200 | IsAuthenticated |
| PUT | `/api/tickets/{id}/` | `TicketViewSet.update` | полное изменение | 200 | IsAuthenticated |
| PATCH | `/api/tickets/{id}/` | `TicketViewSet.partial_update` | частичное изменение | 200 | IsAuthenticated |
| DELETE | `/api/tickets/{id}/` | `TicketViewSet.destroy` | удаление | 204 | IsAuthenticated |

Все маршруты требуют входа в систему (сессия Django); изменяющие запросы - заголовок `X-CSRFToken`.

## Параметры отбора

| URL | Параметр | Тип | Описание |
|-----|----------|-----|----------|
| `/api/reservations/` | `status` | string | состояние: created, issued или returned |
| `/api/reservations/` | `equipment` | integer | id оборудования; нечисловое или 0 - ошибка 400 |
| `/api/tickets/` | `status` | string | статус: new, progress или done |

## Поля данных

### Category (модель `Category`)

| Поле | Тип | В запросе | Описание |
|------|-----|-----------|----------|
| `id` | integer | только чтение | идентификатор |
| `name` | string | обязательно | название категории |

### Equipment (модель `Equipment`)

| Поле | Тип | В запросе | Описание |
|------|-----|-----------|----------|
| `id` | integer | только чтение | идентификатор |
| `name` | string | только чтение | название оборудования |
| `total_q` | integer | только чтение | общее количество |
| `available_q` | integer | только чтение | доступный остаток |

### EquipmentReservation (модель `EquipmentReservation`)

| Поле | Тип | В запросе | Описание |
|------|-----|-----------|----------|
| `id` | integer | только чтение | идентификатор |
| `purpose` | string | обязательно | назначение, не короче 5 символов |
| `equipment` | integer | обязательно | id оборудования |
| `equipment_name` | string | только чтение | название оборудования |
| `quantity` | integer | обязательно | количество, больше нуля |
| `status` | created \| issued \| returned | только чтение | состояние; меняется только операциями issue и return_equipment |
| `created_at` | date-time | только чтение | дата создания |

### ReservationEvent (модель `ReservationEvent`)

| Поле | Тип | В запросе | Описание |
|------|-----|-----------|----------|
| `id` | integer | только чтение | идентификатор |
| `action` | created \| edited \| issued \| returned \| deleted | только чтение | код действия |
| `action_name` | string | только чтение | название действия |
| `actor_name` | string | только чтение | инициатор события |
| `details` | string | только чтение | пояснение |
| `created_at` | date-time | только чтение | время события |

### Ticket (модель `Ticket`)

| Поле | Тип | В запросе | Описание |
|------|-----|-----------|----------|
| `id` | integer | только чтение | идентификатор |
| `title` | string | обязательно | название, не короче 5 символов |
| `description` | string | необязательно | описание |
| `category` | integer | обязательно | id категории |
| `category_name` | string | только чтение | название категории |
| `status` | new \| progress \| done | необязательно | статус; при создании только new, далее new -> progress -> done |
| `created_at` | date-time | только чтение | дата создания |
