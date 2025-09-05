from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('app_contracts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contractsmodel',
            name='upload_contract',
            field=models.FileField(
                upload_to='contract_docs/',
                blank=True,
                null=True,
                verbose_name='ເອກະສານສັນຍາ'
            ),
        ),
    ]
