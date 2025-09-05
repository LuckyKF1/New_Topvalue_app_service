from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('app_contracts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenerateContractNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_generate_number', models.BigIntegerField(default=0)),
            ],
        ),
    ]
