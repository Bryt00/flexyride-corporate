from decimal import Decimal
from django.db import migrations


def seed_categories(apps, schema_editor):
    VehicleCategoryRate = apps.get_model('fleet', 'VehicleCategoryRate')
    defaults = [
        ('SEDAN', 'Standard Sedan', Decimal('200.00'), Decimal('4.50'), Decimal('600.00'), 4, 'Toyota Corolla, Hyundai Elantra, Honda Civic', 1),
        ('EXECUTIVE', 'Executive Saloon', Decimal('350.00'), Decimal('6.50'), Decimal('900.00'), 4, 'Toyota Camry, Mercedes E-Class, BMW 5 Series', 2),
        ('SUV', 'SUV / 4x4', Decimal('450.00'), Decimal('8.00'), Decimal('1200.00'), 5, 'Toyota Prado, Mitsubishi Pajero, Toyota Fortuner', 3),
        ('VAN', 'Passenger Van', Decimal('550.00'), Decimal('9.00'), Decimal('1400.00'), 8, 'Toyota HiAce, Hyundai H1, Ford Transit', 4),
        ('MINIBUS', 'Minibus / Shuttle', Decimal('700.00'), Decimal('10.50'), Decimal('1800.00'), 15, 'Toyota Coaster Short, Mercedes Sprinter', 5),
        ('COASTER_BUS', 'Coaster Bus', Decimal('1000.00'), Decimal('12.00'), Decimal('2200.00'), 30, 'Toyota Coaster 30-Seater, Mitsubishi Rosa', 6),
        ('LUXURY', 'VIP / Luxury Vehicle', Decimal('1200.00'), Decimal('15.00'), Decimal('3000.00'), 4, 'Range Rover, Mercedes S-Class, Lexus LX', 7),
    ]
    for cat, name, base, km, day, seats, models, order in defaults:
        VehicleCategoryRate.objects.get_or_create(
            category=cat,
            defaults={
                'display_name': name,
                'base_wholesale_rate': base,
                'per_km_rate': km,
                'daily_charter_rate': day,
                'min_seating_capacity': seats,
                'recommended_models': models,
                'display_order': order,
                'is_active': True,
            }
        )


def unseed_categories(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('fleet', '0003_vehiclecategoryrate_alter_driver_languages_spoken'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
