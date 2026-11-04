const csrfToken = document.querySelector(
    "[name=csrfmiddlewaretoken]"
).value;

const validStatuses = {
    new: 'Новая',
    progress: 'В работе',
    done: 'Выполнена'
};

function formatErrors(data) {
    if (!data) {
        return "Ошибка выполнения запроса";
    }

    if (typeof data === "string") {
        return data;
    }

    return Object.values(data).flat().join(" ");
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
            ...(options.headers || {})
        },
        credentials: "same-origin"
    });

    let data = null;

    if (response.status !== 204) {
        data = await response.json().catch(() => null);
    }

    if (!response.ok) {
        throw new Error(formatErrors(data));
    }

    return data;
}

const categorySelect =
    document.getElementById("category");

const form =
    document.getElementById("ticket-form");

const titleInput =
    document.getElementById("title");

const message =
    document.getElementById("message");

function showMessage(text, isError = false) {
    message.textContent = text;
    message.className =
        "alert " + (isError ? "alert-danger" : "alert-success");
}

async function loadCategories() {
    const categories = await apiRequest(
        "/api/categories/"
    );

    categorySelect.replaceChildren();

    for (const category of categories) {
        const option = document.createElement("option");
        option.value = category.id;
        option.textContent = category.name;
        categorySelect.append(option);
    }
}

async function initialize() {
    try {
        await loadCategories();
        await loadTickets();
    } catch (error) {
        showMessage('Ошибка загрузки: ' + error.message, true);
    }
}

initialize();

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        await apiRequest("/api/tickets/", {
            method: "POST",
            body: JSON.stringify({
                title: titleInput.value,
                category: Number(categorySelect.value)
            })
        });

        titleInput.value = "";
        showMessage("Заявка успешно создана");

        await loadTickets();
    } catch (error) {
        showMessage(
            "Не удалось создать заявку: " + error.message,
            true
        );
    }
});

const list = document.getElementById("tickets-list");
const loading = document.getElementById("loading");
const filter = document.getElementById("status-filter");

const statusModalElement = document.getElementById('status-modal');
const statusModal = new tabler.Modal(statusModalElement);

const statusSelect = document.getElementById('new-status')

const saveStatusButton = document.getElementById('save-status')
saveStatusButton.addEventListener('click', async () => {
    try {await changeStatus(selectedTicketId, statusSelect.value);
    statusModal.hide()
        showMessage('Статус заявки успешно изменен')} catch(error) {
        showMessage('Не удалось изменить статус: ' + error.message, true);
    }
});

let selectedTicketId = null;

async function loadTickets() {
    loading.hidden = false;

    const params = new URLSearchParams();

    if (filter.value) {
        params.set("status", filter.value);
    }

    const query = params.toString();
    const url = "/api/tickets/" + (query ? "?" + query : "");

    try {
        const tickets = await apiRequest(url);

        list.replaceChildren();

        if (tickets.length === 0) {
            const empty = document.createElement("p");
            empty.textContent = "Заявки не найдены";
            list.append(empty);
            return;
        }

        for (const ticket of tickets) {
            const row = document.createElement("div");
            row.className =
                "d-flex justify-content-between align-items-center border-bottom py-3 gap-3";

            const title = document.createElement("div");
            title.textContent =
                ticket.title + " — " + ticket.category_name;

            const status = document.createElement("span");
            status.className = "badge bg-blue-lt";
            status.textContent = validStatuses[ticket.status] || ticket.status;

            const buttons = document.createElement('div');
            buttons.className = 'd-flex flex-wrap gap-2';

            const editButton = document.createElement("button");
            editButton.textContent = 'Изменить статус'

            editButton.setAttribute('type', 'button');
            editButton.classList.add('btn', 'btn-sm', 'btn-outline-primary');

            editButton.addEventListener('click', () => {
                selectedTicketId = ticket.id;
                statusSelect.value = ticket.status;
                for (const option of statusSelect.options) {
                if (
                    (ticket.status === 'done' && option.value !== 'done')
                    ||
                    (ticket.status === 'new' && option.value === 'done')
                    ||
                    (ticket.status === 'progress' && option.value === 'new')
                )  {
                    option.disabled = true;}
                else {
                    option.disabled = false;
                }
            }
                statusModal.show();
            });



            const deleteButton = document.createElement('Button');
            deleteButton.textContent = 'Удалить'

            deleteButton.setAttribute('type', 'button');
            deleteButton.classList.add('btn', 'btn-sm', 'btn-outline-danger');

            deleteButton.addEventListener('click', async() => {
                try {
                    const deleted = await deleteTicket(ticket.id, ticket.title);
                    if (deleted) {
                        showMessage('Заявка успешно удалена');}
                } catch(error) {
                    showMessage('Не удалось удалить заявку: ' + error.message, true);
                }
            });

            buttons.append(editButton, deleteButton);

            row.append(title, status, buttons);
            list.append(row);
        }
    } catch (error) {
        showMessage(
            "Не удалось загрузить заявки: " + error.message,
            true
        );
    } finally {
        loading.hidden = true;
    }
}

filter.addEventListener("change", loadTickets);

async function initialize() {
    try {
        await loadCategories();
        await loadTickets();
    } catch (error) {
        showMessage(
            "Ошибка инициализации: " + error.message,
            true
        );
    }
}

initialize();


async function changeStatus(ticketId, newStatus) {
    if (!(newStatus in validStatuses)) {
        throw new Error('Недопустимый статус заявки');
    }
    await apiRequest(`/api/tickets/${ticketId}/`, {
        method: "PATCH",
        body: JSON.stringify({
            status: newStatus
        })
    });

    await loadTickets();
}

async function deleteTicket(ticketId, ticketTitle) {
    const confirmed = confirm(
        `Удалить заявку «${ticketTitle}»?`
    );

    if (!confirmed) {
        return false;
    }

    await apiRequest(`/api/tickets/${ticketId}/`, {
        method: "DELETE"
    });

    await loadTickets();

    return true;
}
