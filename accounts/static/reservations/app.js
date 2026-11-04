const getEl = id => document.getElementById(id);
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const statusNames = {
    created: 'Создано',
    issued: 'Выдано',
    returned: 'Возвращено'
};

let editingId = null;
let selectedId = null;


function errorText(data) {
    if (typeof data === 'string') return data;
    if (Array.isArray(data)) return data.map(errorText).join(' ');
    if (data && typeof data === 'object')
        return Object.values(data).map(errorText).join(' ');
    return 'Описание ошибки отсутствует';
}


async function apiRequest(url, options = {}) {
    let response;

    try {
        response = await fetch(url, {
            ...options,
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
    } catch {
        throw new Error('Нет соединения с сервером.');
    }

    const data = response.status === 204
        ? null
        : await response.json().catch(() => null);

    if (!response.ok) {
        const message = response.status === 403 ? 'Нет доступа. '
            : response.status === 404 ? 'Объект не найден. '
            : response.status >= 500 ? 'Ошибка сервера. ' : '';

        throw new Error(
            `Ошибка ${response.status}. ${message}${errorText(data)}`
        );
    }

    return data;
}


function showMessage(text, error = false) {
    getEl('message').hidden = false;
    getEl('message').textContent = text;
    getEl('message').className = 'alert mb-3 ' +
        (error ? 'alert-danger' : 'alert-success');
}


function element(tag, text = '', className = '') {
    const result = document.createElement(tag);
    result.textContent = String(text);
    result.className = className;
    return result;
}


function button(label, style, action) {
    const result = element('button', label, 'btn btn-sm ' + style);
    result.type = 'button';

    result.onclick = async () => {
        result.disabled = true;

        try {
            await action();
        } catch (error) {
            showMessage(error.message, true);
        } finally {
            result.disabled = false;
        }
    };

    return result;
}


async function loadEquipment() {
    const items = await apiRequest('/api/equipment/');
    const selectedFilter = getEl('equipment-filter').value;

    getEl('equipment-list').replaceChildren();
    getEl('equipment').replaceChildren();
    getEl('equipment-filter').replaceChildren(
        new Option('Всё оборудование', '')
    );

    for (const item of items) {
        const row = document.createElement('tr');

        [item.name, item.available_q, item.total_q]
            .forEach(value => row.append(element('td', value)));

        getEl('equipment-list').append(row);
        getEl('equipment').add(new Option(item.name, item.id));
        getEl('equipment-filter').add(new Option(item.name, item.id));
    }

    if (!items.length) {
        const empty = element(
            'td',
            'Оборудование пока не добавлено. Откройте /admin/.'
        );
        empty.colSpan = 3;

        const row = document.createElement('tr');
        row.append(empty);
        getEl('equipment-list').append(row);
    }

    getEl('equipment-filter').value = selectedFilter;
    getEl('submit-button').disabled = !items.length;
}


function resetForm() {
    editingId = null;
    getEl('reservation-form').reset();
    getEl('quantity').value = 1;
    getEl('form-heading').textContent = 'Создать бронирование';
    getEl('submit-button').textContent = 'Создать бронирование';
    getEl('cancel-edit').hidden = true;
}


getEl('cancel-edit').onclick = resetForm;


getEl('reservation-form').onsubmit = async event => {
    event.preventDefault();
    const isEdit = editingId !== null;

    const data = {
        purpose: getEl('purpose').value,
        equipment: Number(getEl('equipment').value),
        quantity: Number(getEl('quantity').value)
    };

    try {
        await apiRequest(
            isEdit
                ? `/api/reservations/${editingId}/`
                : '/api/reservations/',
            {
                method: isEdit ? 'PATCH' : 'POST',
                body: JSON.stringify(data)
            }
        );

        resetForm();
        showMessage(
            isEdit ? 'Бронирование изменено.' : 'Бронирование создано.'
        );
        await refresh();

    } catch (error) {
        showMessage(error.message, true);
    }
};


async function runAction(item, action) {
    if (action === 'edit') {
        editingId = item.id;

        getEl('purpose').value = item.purpose;
        getEl('equipment').value = item.equipment;
        getEl('quantity').value = item.quantity;
        getEl('form-heading').textContent = 'Редактирование бронирования';
        getEl('submit-button').textContent = 'Сохранить изменения';
        getEl('cancel-edit').hidden = false;
        getEl('purpose').focus();
        return;
    }

    if (action === 'delete') {
        if (!confirm(`Удалить бронирование «${item.purpose}»?`))
            return;

        await apiRequest(
            `/api/reservations/${item.id}/`,
            {method: 'DELETE'}
        );

        if (editingId === item.id) resetForm();

        if (selectedId === item.id) {
            selectedId = null;
            getEl('details-card').hidden = true;
        }

    } else {
        await apiRequest(
            `/api/reservations/${item.id}/${action}/`,
            {method: 'POST'}
        );
    }

    showMessage('Операция выполнена.');
    await refresh();
}


async function loadReservations() {
    const params = new URLSearchParams();

    if (getEl('status-filter').value)
        params.set('status', getEl('status-filter').value);

    if (getEl('equipment-filter').value)
        params.set('equipment', getEl('equipment-filter').value);

    const query = params.toString();
    getEl('loading').hidden = false;

    try {
        const items = await apiRequest(
            '/api/reservations/' + (query ? '?' + query : '')
        );

        getEl('reservations-list').replaceChildren();

        if (!items.length) {
            getEl('reservations-list').append(
                element('p', 'Бронирования не найдены.', 'text-secondary')
            );
        }

        for (const item of items) {
            const row = element(
                'div', '',
                'd-flex flex-wrap align-items-center justify-content-between gap-3 py-3 border-bottom'
            );

            const info = document.createElement('div');

            info.append(
                element('strong', item.purpose),
                element(
                    'div',
                    `${item.equipment_name} · ${item.quantity} шт. · ${statusNames[item.status]}`,
                    'text-secondary'
                )
            );

            const actions = element('div', '', 'd-flex flex-wrap gap-2');

            actions.append(
                button(
                    'Карточка и история',
                    'btn-outline-primary',
                    async () => {
                        selectedId = item.id;
                        await loadDetails();
                    }
                )
            );

            if (item.status === 'created') {
                actions.append(
                    button(
                        'Редактировать',
                        'btn-outline-secondary',
                        () => runAction(item, 'edit')
                    ),
                    button(
                        'Выдать',
                        'btn-primary',
                        () => runAction(item, 'issue')
                    ),
                    button(
                        'Удалить',
                        'btn-danger',
                        () => runAction(item, 'delete')
                    )
                );

            } else if (item.status === 'issued') {
                actions.append(
                    button(
                        'Вернуть',
                        'btn-success',
                        () => runAction(item, 'return_equipment')
                    )
                );
            }

            row.append(info, actions);
            getEl('reservations-list').append(row);
        }

    } finally {
        getEl('loading').hidden = true;
    }
}


async function loadDetails() {
    if (selectedId === null) return;

    const [item, events] = await Promise.all([
        apiRequest(`/api/reservations/${selectedId}/`),
        apiRequest(`/api/reservations/${selectedId}/history/`)
    ]);

    getEl('details-card').hidden = false;

    getEl('reservation-details').textContent =
        `№${item.id}: ${item.purpose}. ` +
        `${item.equipment_name}, ${item.quantity} шт. ` +
        `Статус: ${statusNames[item.status]}.`;

    getEl('history-list').replaceChildren();

    if (!events.length) {
        getEl('history-list').textContent = 'Событий пока нет.';
    } else {
        const list = element('ul', '', 'list-group');

        for (const event of events) {
            list.append(
                element(
                    'li',
                    `${new Date(event.created_at).toLocaleString('ru-RU')} - ` +
                    `${event.action_name}. ${event.details} ` +
                    `(Пользователь: ${event.actor_name})`,
                    'list-group-item'
                )
            );
        }

        getEl('history-list').append(list);
    }
}


async function refresh() {
    await loadEquipment();
    await loadReservations();

    if (selectedId !== null)
        await loadDetails();
}


for (const id of ['status-filter', 'equipment-filter']) {
    getEl(id).onchange = () =>
        loadReservations().catch(error =>
            showMessage(error.message, true)
        );
}


refresh().catch(error =>
    showMessage('Ошибка загрузки: ' + error.message, true)
);
