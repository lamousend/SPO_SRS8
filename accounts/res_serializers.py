from rest_framework import serializers
from .models import Equipment, EquipmentReservation, ReservationEvent


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ('id', 'name', 'total_q', 'available_q')
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': 'идентификатор'},
            'name': {'help_text': 'название оборудования'},
            'total_q': {'help_text': 'общее количество'},
            'available_q': {'help_text': 'доступный остаток'},
        }


class EquipmentReservationSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(
        source='equipment.name',
        read_only=True,
        help_text='название оборудования',
    )

    class Meta:
        model = EquipmentReservation
        fields = (
            'id', 'purpose', 'equipment', 'equipment_name',
            'quantity', 'status', 'created_at'
        )
        read_only_fields = ('id', 'equipment_name', 'status', 'created_at')
        extra_kwargs = {
            'id': {'help_text': 'идентификатор'},
            'purpose': {'help_text': 'назначение, не короче 5 символов'},
            'equipment': {'help_text': 'id оборудования'},
            'quantity': {'help_text': 'количество, больше нуля'},
            'status': {'help_text': 'состояние; меняется только операциями issue и return_equipment'},
            'created_at': {'help_text': 'дата создания'},
        }

    def validate_purpose(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                'Назначение должно содержать не менее 5 символов'
            )
        return value.strip()

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Количество должно быть больше нуля'
            )
        return value

    def validate(self, attrs):
        if 'status' in self.initial_data or 'owner' in self.initial_data:
            raise serializers.ValidationError(
                'Нельзя вручную изменять статус или владельца'
            )

        if self.instance and self.instance.status != EquipmentReservation.Status.CREATED:
            raise serializers.ValidationError(
                'Редактировать можно только созданное бронирование'
            )

        return attrs


class ReservationEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.StringRelatedField(
        source='actor',
        read_only=True,
        help_text='инициатор события',
    )
    action_name = serializers.CharField(
        source='get_action_display',
        read_only=True,
        help_text='название действия',
    )

    class Meta:
        model = ReservationEvent
        fields = (
            'id', 'action', 'action_name',
            'actor_name', 'details', 'created_at'
        )
        read_only_fields = fields
        extra_kwargs = {
            'id': {'help_text': 'идентификатор'},
            'action': {'help_text': 'код действия'},
            'details': {'help_text': 'пояснение'},
            'created_at': {'help_text': 'время события'},
        }