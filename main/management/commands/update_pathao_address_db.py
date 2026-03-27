from django.core.management.base import BaseCommand
from utils.pathao import update_pathao_data

class Command(BaseCommand):
    help = 'Update Pathao address database with latest data from Pathao API'

    def handle(self, *args, **kwargs):
        try:
            update_pathao_data()
            self.stdout.write(self.style.SUCCESS('Successfully updated Pathao address database'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating Pathao address database: {str(e)}'))
