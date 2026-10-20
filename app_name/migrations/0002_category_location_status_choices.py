from django.db import migrations, models

def populate_directories(apps, schema_editor):
    Item = apps.get_model('app_name', 'LostFound')
    Category = apps.get_model('app_name', 'Category')
    Location = apps.get_model('app_name', 'Location')
    for value in Item.objects.values_list('category', flat=True).distinct():
        if value and value.strip(): Category.objects.get_or_create(name=value.strip())
    for value in Item.objects.values_list('location', flat=True).distinct():
        if value and value.strip(): Location.objects.get_or_create(name=value.strip())

def normalize_statuses(apps, schema_editor):
    Item = apps.get_model('app_name', 'LostFound')
    for old, new in [('lost', 'Lost'), ('found', 'Found'), ('claimed', 'Claimed'), ('pending', 'Pending')]:
        Item.objects.filter(status__iexact=old).update(status=new)


class Migration(migrations.Migration):
    dependencies = [('app_name', '0001_initial')]
    operations = [
        migrations.CreateModel(name='Category', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=100, unique=True))]),
        migrations.CreateModel(name='Location', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('name', models.CharField(max_length=200, unique=True))]),
        migrations.AlterField(model_name='lostfound', name='status', field=models.CharField(choices=[('Lost', 'Lost'), ('Found', 'Found'), ('Claimed', 'Claimed'), ('Pending', 'Pending')], default='Pending', max_length=20)),
        migrations.RunPython(normalize_statuses, migrations.RunPython.noop),
        migrations.RunPython(populate_directories, migrations.RunPython.noop),
    ]
