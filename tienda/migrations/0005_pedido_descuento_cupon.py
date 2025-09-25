from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('tienda', '0004_cupon_resena'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='descuento_cupon',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]