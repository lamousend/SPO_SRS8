from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound, ValidationError

from .models import Equipment, EquipmentReservation, ReservationEvent


def _get_own_reservation(reservation_id, actor):
    try:
        return (EquipmentReservation.objects.select_for_update()
                .get(pk=reservation_id, owner=actor, deleted_at__isnull=True))
    except EquipmentReservation.DoesNotExist:
        raise NotFound('Бронирование не найдено')


@transaction.atomic
def issue_reservation(reservation_id, actor):
    reservation = _get_own_reservation(reservation_id, actor)
    if reservation.status != EquipmentReservation.Status.CREATED:
        raise ValidationError({'status': 'Выдать можно только созданное бронирование'})

    changed = Equipment.objects.filter(
        pk=reservation.equipment_id,
        available_q__gte=reservation.quantity,
    ).update(available_q=F('available_q') - reservation.quantity)
    if not changed:
        raise ValidationError({'quantity': 'Недостаточно доступного оборудования'})

    changed = EquipmentReservation.objects.filter(
        pk=reservation.pk,
        status=EquipmentReservation.Status.CREATED,
        deleted_at__isnull=True,
    ).update(status=EquipmentReservation.Status.ISSUED)
    if not changed:
        raise ValidationError({'status': 'Бронирование уже было изменено.'})

    ReservationEvent.objects.create(
        reservation=reservation, actor=actor,
        action=ReservationEvent.Action.ISSUED,
        details=f'Выдано {reservation.quantity} ед. оборудования',
    )
    reservation.refresh_from_db()
    return reservation


@transaction.atomic
def return_reservation(reservation_id, actor):
    reservation = _get_own_reservation(reservation_id, actor)
    if reservation.status != EquipmentReservation.Status.ISSUED:
        raise ValidationError({'status': 'Вернуть можно только выданное оборудование.'})

    changed = Equipment.objects.filter(
        pk=reservation.equipment_id,
        available_q__lte=F('total_q') - reservation.quantity,
    ).update(available_q=F('available_q') + reservation.quantity)
    if not changed:
        raise ValidationError({'quantity': 'Возврат превысил бы общий остаток.'})

    changed = EquipmentReservation.objects.filter(
        pk=reservation.pk,
        status=EquipmentReservation.Status.ISSUED,
        deleted_at__isnull=True,
    ).update(status=EquipmentReservation.Status.RETURNED)
    if not changed:
        raise ValidationError({'status': 'Бронирование уже было изменено.'})

    ReservationEvent.objects.create(
        reservation=reservation, actor=actor,
        action=ReservationEvent.Action.RETURNED,
        details=f'Возвращено {reservation.quantity} ед. оборудования',
    )
    reservation.refresh_from_db()
    return reservation